#!/usr/bin/env python3
"""How well does the model know the target language? Short zero-shot probes for a fresh agent with no tools and
no files; their scores set `familiarity` (scripts/modes.py, docs/onboarding.md, step 2).

  python3 scripts/probe_language.py <project> [write] [--n 16] > prompt.md
      write: translate N BSB verses into the language from its own knowledge (production).
  python3 scripts/probe_language.py <project> read [--n 16] > prompt.md
      read: translate N corpus verses, shown without their references, into English (understanding).
  python3 scripts/probe_language.py <project> tell --write-answer WRITE.txt [--n 24] > prompt.md
      tell apart: pairs of a corpus verse and an altered copy; which one is the published text? Three kinds of
      alteration, a third each: the model's own slips (forms of its write answer that the corpus never has, put in
      place of the corpus form they stand for: the standard language's spelling for the variety's), a word ending (another corpus form of the
      same stem), and two neighbouring words swapped. Chance is 50%.
  python3 scripts/probe_language.py <project> run [--route api|claude-code] [--model M]
      all three, each sent to a fresh model with no tools: through the API when ANTHROPIC_API_KEY is set (environment or .env) (billed per
      token), else through Claude Code (claude -p, no tools, your subscription); scores, the suggested familiarity and
      the model's slips. Prompts and answers go to _eval/local/probes/ (local: they print corpus verses).
  ... --score ANSWER.txt
      the probe's score: write chrF against the edition; read chrF against the BSB; tell % right, by kind.
      Lines of the answer: "<reference or item number><TAB><text or A/B>". With --record the scores go to
      export/<project>/_learn/probe.json.

The verses are spread over the corpus (half narrative) with fixed seeds, so a probe can be repeated; the three
probes use different verses. Thresholds (calibrated on the three pilots, docs/onboarding.md): write known >= 65,
partial 30-65. Read the answers too: a write answer that slips into the standard language is what `partial` means.
"""
import datetime, difflib, json, os, random, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import langtools as LT  # noqa: E402

KNOWN, PARTIAL = 65.0, 30.0


def sample(P, n, seed=20261014, avoid=()):
    """N verses of 8-30 words, half from narrative books (Gospels, Acts, OT narrative), the rest spread over the
    other books in canonical order; fixed seed, so a probe can be repeated."""
    from books import BY_CODE
    order = list(BY_CODE)
    narrative = {"gen", "exo", "num", "jos", "jdg", "rut", "1sa", "2sa", "1ki", "2ki", "jon", "mat", "mrk", "luk", "jhn", "act"}
    rows = [r for r in P.corpus() if r[3] and r[4] and 8 <= len(r[3].split()) <= 30 and r[0] not in avoid]
    rnd = random.Random(seed)
    by_book = {}
    for r in rows:
        by_book.setdefault(r[1], []).append(r)
    books = sorted(by_book, key=order.index)
    narr = [b for b in books if b in narrative] or books
    other = [b for b in books if b not in narrative]
    pick = []
    for group, k in ((narr, (n + 1) // 2), (other, n // 2)):
        if not group:
            continue
        for i in range(k):
            b = group[int(i * len(group) / k) % len(group)]
            cand = [r for r in by_book[b] if r not in pick]
            if cand:
                pick.append(rnd.choice(cand))
    return sorted(pick, key=lambda r: (order.index(r[1]), r[2]))


def clean(t):
    """A verse as a reader sees it: notes ({T: …}), bracketed reader notes and verse markers out."""
    t = re.sub(r"\{[^{}]*\}", " ", t)
    t = re.sub(r"\[[^\[\]]*\]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


GOD_WORDS = {"I", "God", "LORD", "Lord", "He", "His", "Him", "Himself", "My", "Me", "Mine", "You", "Your", "Yours", "O", "Spirit",
             "Holy", "Father", "Son", "Almighty", "Most", "High"}


def bsb_names(P):
    """Words the BSB capitalises inside a sentence (names, places, peoples), from the whole corpus."""
    out = set()
    for r in P.corpus():
        for pre, w in re.findall(r"(^|[.!?:;“‘\"(]\s*|\s)([A-Z][a-z’']+)", r[3]):
            if w not in GOD_WORDS and not re.search(r"(^|[.!?“‘\"(]\s*)$", pre):
                out.add(w)
    return out


def has_names(bsb, names):
    """A proper name in the BSB verse: the model would recognise the verse from it in any language and recall its
    English, so the read probe leaves such verses out."""
    return any(w in names for w in re.findall(r"[A-Z][a-z’']+", bsb))


def read_rows(P, n):
    w = {r[0] for r in sample(P, 16)}
    names = bsb_names(P)
    named = {r[0] for r in P.corpus() if has_names(r[3], names)}
    return sample(P, n, seed=20261015, avoid=w | named)


def answers(path):
    out = {}
    for l in open(path, encoding="utf-8").read().splitlines():
        if "\t" in l:
            k, t = l.split("\t", 1)
            out[k.strip()] = t.strip()
    return out


def fold(w):
    """Without diacritics, for comparing spellings (öich ~ euch)."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", w) if not unicodedata.combining(c))


def is_word(w):
    """Letters, combining marks (Indic vowel signs, viramas) and zero-width joiners only: str.isalpha() fails on those."""
    import unicodedata
    return bool(w) and w[0].isalpha() and all(c.isalpha() or unicodedata.category(c).startswith("M") or c in "\u200c\u200d" for c in w)


def swap_word(text, old, new):
    """Replace the first whole-word occurrence of old (any case) with new, keeping a capital."""
    m = re.search(rf"(?<!\w){re.escape(old)}(?!\w)", text, re.I)
    if not m:
        return None
    rep = new[:1].upper() + new[1:] if m[0][:1].isupper() else new
    return text[:m.start()] + rep + text[m.end():]


def corpus_vocab(P):
    vocab = {}
    for r in P.corpus():
        for t in P.tok.tokens(r[4]):
            vocab[t] = vocab.get(t, 0) + 1
    return vocab


def find_slips(P, write_ans, vocab):
    """[(corpus form, the model's form)]: words of the write answer that the corpus never has, paired with the corpus
    word they stand for in the same verse (1:1 in the aligned word sequences, or a near spelling of a name: Tloas ~ Troas)."""
    slips = []
    ref = {r[0]: r for r in sample(P, 16)}
    for key, text in write_ans.items():
        if key not in ref:
            continue
        mine, theirs = P.tok.tokens(text), P.tok.tokens(ref[key][4])
        sm = difflib.SequenceMatcher(None, theirs, mine, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op != "replace" or i2 - i1 > 3 or j2 - j1 > 3:
                continue
            for w in mine[j1:j2]:
                if w in vocab:
                    continue
                sim, c = max(((difflib.SequenceMatcher(None, fold(w), fold(c)).ratio(), c) for c in theirs[i1:i2]
                              if c not in mine and vocab.get(c, 0) >= 3), default=(0, None))
                if sim >= 0.4 and (c, w) not in slips:
                    slips.append((c, w))
        for w in mine:
            if w in vocab or len(w) < 2 or any(x[1] == w for x in slips):
                continue
            sim, c = max(((difflib.SequenceMatcher(None, w, c).ratio(), c) for c in theirs if c not in mine and vocab.get(c, 0) >= 3),
                         default=(0, None))
            if sim >= 0.7 and abs(len(w) - len(c)) <= 3:
                slips.append((c, w))
    return slips


def tell_items(P, write_answer, n):
    """[(item no, genuine text, altered text, kind, genuine first?)], deterministic for the same inputs."""
    rnd = random.Random(20261016)
    w = {r[0] for r in sample(P, 16)}      # not the write verses, nor the read probe's first draw (fixed, so the
    used = w | {r[0] for r in sample(P, 16, seed=20261015, avoid=w)}   # pairs stay the same when read_rows changes)
    pool = [r for r in P.corpus() if r[4] and 8 <= len(clean(r[4]).split()) <= 30 and r[0] not in used]
    rnd.shuffle(pool)
    vocab = corpus_vocab(P)
    k = n // 3
    items = []
    slips = find_slips(P, answers(write_answer), vocab)
    taken = set()
    for corpus_form, slip in slips:
        if len([i for i in items if i[3] == "slip"]) >= k:
            break
        for r in pool:
            if r[0] in taken:
                continue
            alt = swap_word(clean(r[4]), corpus_form, slip)
            if alt and alt != clean(r[4]):
                items.append((r[0], clean(r[4]), alt, "slip"))
                taken.add(r[0])
                break
    # 2. an ending: another frequent corpus form of the same stem (first 4 letters), of similar length
    by_stem = {}
    for t, c in vocab.items():
        if len(t) >= 5 and c >= 5 and is_word(t):
            by_stem.setdefault(t[:4], []).append(t)
    for r in pool:
        if len([i for i in items if i[3] == "ending"]) >= k + max(0, (k - len(items)) // 2):
            break
        if r[0] in taken:
            continue
        toks = [t for t in P.tok.tokens(r[4]) if t in vocab and len(t) >= 5]
        rnd.shuffle(toks)
        for t in toks:
            alts = [a for a in by_stem.get(t[:4], []) if a != t and abs(len(a) - len(t)) <= 2]
            if alts:
                alt = swap_word(clean(r[4]), t, rnd.choice(sorted(alts)))
                if alt and alt != clean(r[4]):
                    items.append((r[0], clean(r[4]), alt, "ending"))
                    taken.add(r[0])
                    break
    # 3. word order: two neighbouring words swapped (not the first word, not around punctuation)
    for r in pool:
        if len(items) >= n:
            break
        if r[0] in taken:
            continue
        ws = clean(r[4]).split(" ")
        spots = [i for i in range(1, len(ws) - 2) if is_word(ws[i]) and is_word(ws[i + 1]) and ws[i].lower() != ws[i + 1].lower()]
        if spots:
            i = rnd.choice(spots)
            ws2 = ws[:i] + [ws[i + 1], ws[i]] + ws[i + 2:]
            items.append((r[0], clean(r[4]), " ".join(ws2), "order"))
            taken.add(r[0])
    rnd.shuffle(items)
    return [(no, g, a, kind, rnd.random() < 0.5) for no, (_, g, a, kind) in enumerate(items, 1)]


def record(P, probe, result, quiet=False):
    f = os.path.join(P.learn, "probe.json")
    d = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    d[probe] = dict(result, date=datetime.date.today().isoformat())
    os.makedirs(P.learn, exist_ok=True)
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not quiet:
        print(f"  recorded in {os.path.relpath(f, ROOT)}")


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


NO_TOOLS = ("Use no tools at all: don't read, search or run anything. Don't look for an existing translation.")
PROBES = ("write", "read", "tell")
DEFAULT_MODEL = "claude-opus-5-5"     # for the API route: the model that drafts should be the one probed


# ---------- the three probes: prompt and score ----------

# display names of ISO 15924 codes where the Unicode name is not the one people use
SCRIPT_NAMES = {"Latn": "Latin", "Orya": "Odia", "Deva": "Devanagari", "Cyrl": "Cyrillic", "Arab": "Arabic",
                "Hebr": "Hebrew", "Grek": "Greek", "Beng": "Bengali", "Ethi": "Ethiopic", "Hani": "Chinese (Han)",
                "Jpan": "Japanese", "Hang": "Hangul", "Mymr": "Myanmar", "Khmr": "Khmer", "Laoo": "Lao", "Tibt": "Tibetan",
                "Taml": "Tamil", "Telu": "Telugu", "Knda": "Kannada", "Mlym": "Malayalam", "Gujr": "Gujarati",
                "Guru": "Gurmukhi", "Sinh": "Sinhala", "Thai": "Thai", "Geor": "Georgian", "Armn": "Armenian",
                "Syrc": "Syriac", "Thaa": "Thaana", "Nkoo": "N'Ko", "Adlm": "Adlam", "Tfng": "Tifinagh", "Cans": "Canadian Syllabics"}


def script_of(P):
    """The writing system's display name, e.g. 'Latin', 'Odia', 'Arabic': from the ISO 15924 code that
    scripts/script_code.py gives (recorded `script:`, else the corpus letters)."""
    import script_code as SC
    code, _ = SC.target_script(P)
    return SCRIPT_NAMES.get(code, code)


def prompt_write(P, n=16):
    lang = P.p.get("language_name") or P.p.get("language")
    script = script_of(P)
    out = [f"Translate each verse below from English into **{lang}**, from your own knowledge of the language"
           f"{'' if script == 'Latin' else f', written in the {script} script, as published {lang} texts are'}.\n\n"
           f"{NO_TOOLS} If you don't know {lang}, write your best attempt anyway (or the closest language you can, and say which).\n\n"
           "Answer with one line per verse, the reference, a TAB, your translation, and nothing else:\n"]
    out += [f"{r[0]}\t{r[3]}" for r in sample(P, n)]
    return "\n".join(out) + "\n"


def prompt_read(P, n=16):
    lang = P.p.get("language_name") or P.p.get("language")
    rows = read_rows(P, n)
    out = [f"Below are {len(rows)} sentences in **{lang}**. Translate each into plain English, from your own knowledge of the "
           f"language.\n\n{NO_TOOLS} Where you don't understand a sentence, give your best guess at its meaning anyway; "
           "where you understand only some words, translate those.\n\n"
           "Answer with one line per sentence, its number, a TAB, your English, and nothing else:\n"]
    out += [f"{i}\t{clean(r[4])}" for i, r in enumerate(rows, 1)]
    return "\n".join(out) + "\n"


def prompt_tell(P, write_answer, n=24):
    lang = P.p.get("language_name") or P.p.get("language")
    out = [f"Each item below shows two versions, A and B, of a sentence in **{lang}**. One is exactly as published in a "
           f"{lang} text; in the other, one or two words were changed. Say which is the published one, from your own knowledge "
           f"of {lang}.\n\n{NO_TOOLS} Answer every item, guessing where you must.\n\n"
           "Answer with one line per item, its number, a TAB, A or B, and nothing else.\n"]
    for no, g, alt, kind, gfirst in tell_items(P, write_answer, n):
        A, B = (g, alt) if gfirst else (alt, g)
        out.append(f"{no}.\n   A: {A}\n   B: {B}\n")
    return "\n".join(out) + "\n"


def score_write(P, ans, n=16):
    rows = sample(P, n)
    hyp = " ".join(P.tok.plain(ans.get(r[0], "")) for r in rows)
    ref = " ".join(P.tok.plain(r[4]) for r in rows)
    return {"chrf": round(LT.chrf(hyp, ref), 1),
            "chrf_by_verse": round(mean(LT.chrf(P.tok.plain(ans.get(r[0], "")), P.tok.plain(r[4])) for r in rows), 1),
            "floor": round(mean(LT.chrf(P.tok.plain(b[4]), P.tok.plain(r[4])) for r, b in zip(rows, rows[1:] + rows[:1])), 1),
            "answered": sum(1 for r in rows if r[0] in ans), "n": len(rows)}


def score_read(P, ans, n=16):
    # verse by verse (a pooled chrF ignores which verse is which), with the floor of unrelated English: each verse
    # scored against the BSB of the next one
    rows = read_rows(P, n)
    return {"chrf": round(mean(LT.chrf(ans.get(str(i), "").lower(), r[3].lower()) for i, r in enumerate(rows, 1)), 1),
            "floor": round(mean(LT.chrf(b[3].lower(), r[3].lower()) for r, b in zip(rows, rows[1:] + rows[:1])), 1),
            "answered": sum(1 for i in range(1, len(rows) + 1) if str(i) in ans), "n": len(rows)}


def score_tell(P, write_answer, ans, n=24):
    right, by = 0, {}
    items = tell_items(P, write_answer, n)
    for no, g, alt, kind, gfirst in items:
        ok = ans.get(str(no), "").strip().strip(".").upper()[:1] == ("A" if gfirst else "B")
        right += ok
        by.setdefault(kind, [0, 0])
        by[kind][0] += ok
        by[kind][1] += 1
    return {"right": right, "n": len(items), "by_kind": by}


def suggest(res):
    """familiarity from the three probes, and why (calibrated on the pilots, docs/onboarding.md: Calibration)."""
    r, w, t = res.get("read"), res.get("write"), res.get("tell")
    if r and r["chrf"] - r["floor"] < 15:
        return "unknown", f"read {r['chrf']} is near the floor of unrelated text ({r['floor']}): the model doesn't understand it"
    if w and w["chrf_by_verse"] - w["floor"] < 10:
        return "unknown", (f"the model understands it (read {r['chrf'] if r else '?'}), but can't write it (write {w['chrf_by_verse']} "
                           f"by verse, at the floor of {w['floor']}): it likely knows a related language, not this one")
    if w and w["chrf_by_verse"] >= KNOWN_BY_VERSE:
        return "known", f"write {w['chrf_by_verse']} by verse: the model writes it well"
    slips = (t or {}).get("by_kind", {}).get("slip")
    seen = f"; it recognises {slips[0]} of its {slips[1]} slips" if slips and slips[1] else ""
    return "partial", f"the model understands it but writes it with slips (write {w['chrf_by_verse'] if w else '?'} by verse{seen})"


KNOWN_BY_VERSE = 58.0     # Danish 64.4, Jamaican 47.9


# ---------- running them: the API (ANTHROPIC_API_KEY) or Claude Code (claude -p, no tools) ----------

def api_key():
    """ANTHROPIC_API_KEY from the environment, else from .env (git-ignored; scripts/localenv.py)."""
    import localenv
    return localenv.key("ANTHROPIC_API_KEY")


def route_available():
    import shutil
    return [r for r, ok in (("api", bool(api_key())), ("claude-code", bool(shutil.which("claude")))) if ok]


def ask_model(prompt, route, model=None):
    """-> (text, {input_tokens, output_tokens}). A fresh model with no tools and no files, as the probes require."""
    if route == "api":
        import urllib.request
        body = json.dumps({"model": model or DEFAULT_MODEL, "max_tokens": 8000,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
            "x-api-key": api_key(), "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            d = json.load(r)
        text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
        u = d.get("usage", {})
        return text, {"input_tokens": u.get("input_tokens", 0), "output_tokens": u.get("output_tokens", 0)}
    if route == "claude-code":
        import subprocess, tempfile
        cmd = ["claude", "-p", "--tools", "", "--no-session-persistence", "--strict-mcp-config", "--output-format", "json"]
        if model:
            cmd += ["--model", model]
        with tempfile.TemporaryDirectory() as empty:     # no project files, no CLAUDE.md in reach
            r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=empty, timeout=900)
        if r.returncode:
            raise SystemExit(f"claude -p failed: {(r.stderr or r.stdout)[-400:]}")
        d = json.loads(r.stdout)
        if d.get("is_error"):
            raise SystemExit(f"claude -p: {d.get('result')}")
        u = d.get("usage", {})
        return d.get("result", ""), {"input_tokens": u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                                     + u.get("cache_read_input_tokens", 0), "output_tokens": u.get("output_tokens", 0)}
    raise SystemExit(f"unknown route {route!r} (api, claude-code)")


def run(pname, route, model=None, say=print):
    """All three probes, one fresh model each; prompts and answers kept in _eval/local/probes/ (they print corpus
    verses: local only), scores recorded in _learn/probe.json. -> (results, familiarity, why, slips)"""
    P = LT.Project(pname)
    d = os.path.join(P.dir, "_eval", "local", "probes")
    os.makedirs(d, exist_ok=True)
    res, tokens = {}, {"input_tokens": 0, "output_tokens": 0}

    def one(name, prompt):
        open(os.path.join(d, f"{name}_prompt.md"), "w", encoding="utf-8").write(prompt)
        say(f"  {name} ...")
        text, u = ask_model(prompt, route, model)
        for k in tokens:
            tokens[k] += u[k]
        path = os.path.join(d, f"{name}_answer.txt")
        open(path, "w", encoding="utf-8").write(text)
        return path

    wpath = one("write", prompt_write(P))
    res["write"] = score_write(P, answers(wpath))
    res["read"] = score_read(P, answers(one("read", prompt_read(P))))
    res["tell"] = score_tell(P, wpath, answers(one("tell", prompt_tell(P, wpath))))
    fam, why = suggest(res)
    for k, v in res.items():
        record(P, k, dict(v, route=route, model=model or (DEFAULT_MODEL if route == "api" else "claude-code default")), quiet=True)
    record(P, "suggested", {"familiarity": fam, "why": why, "tokens": tokens}, quiet=True)
    # slips only mean something when the answer is the language at all (well above the floor)
    w = res["write"]
    slips = find_slips(P, answers(wpath), corpus_vocab(P)) if w["chrf_by_verse"] - w["floor"] >= 10 else []
    return res, fam, why, slips, tokens


def example(pname):
    """One write-probe verse: the model's answer beside the edition, for a speaker to judge."""
    P = LT.Project(pname)
    f = os.path.join(P.dir, "_eval", "local", "probes", "write_answer.txt")
    ans = answers(f) if os.path.exists(f) else {}
    for r in sample(P, 16):
        if r[0] in ans:
            return r[0], ans[r[0]], clean(r[4])
    return None


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    pname = a[0]
    P = LT.Project(pname)
    probe = next((x for x in a[1:] if x in PROBES + ("run",)), "write")
    n = int(a[a.index("--n") + 1]) if "--n" in a else (24 if probe == "tell" else 16)
    score = a[a.index("--score") + 1] if "--score" in a else None
    model = a[a.index("--model") + 1] if "--model" in a else None

    if probe == "run":
        routes = route_available()
        route = a[a.index("--route") + 1] if "--route" in a else (routes[0] if routes else None)
        if not route:
            raise SystemExit("no model to run the probes: set ANTHROPIC_API_KEY, or install Claude Code (claude)")
        res, fam, why, slips, tokens = run(pname, route, model)
        w, r, t = res["write"], res["read"], res["tell"]
        print(f"{pname} ({route}): write {w['chrf_by_verse']} by verse (floor {w['floor']}), read {r['chrf']} (floor {r['floor']}), "
              f"tell apart {t['right']}/{t['n']}")
        print(f"  suggested familiarity: {fam}: {why}")
        if slips:
            print("  slips (model -> corpus): " + ", ".join(f"{m} -> {c}" for c, m in slips[:12]))
        print(f"  tokens: {tokens['input_tokens']} in, {tokens['output_tokens']} out")
        return
    if probe == "tell" and "--write-answer" not in a:
        raise SystemExit("tell: needs --write-answer WRITE.txt (the write probe's answer: its slips make a third of the pairs)")
    wa = a[a.index("--write-answer") + 1] if "--write-answer" in a else None
    if not score:
        print({"write": lambda: prompt_write(P, n), "read": lambda: prompt_read(P, n),
               "tell": lambda: prompt_tell(P, wa, n)}[probe](), end="")
        return
    ans = answers(score)
    if probe == "write":
        res = score_write(P, ans, n)
        fam = "known" if res["chrf"] >= KNOWN else "partial" if res["chrf"] >= PARTIAL else "unknown"
        print(f"{pname}: write chrF {res['chrf']} on {res['answered']} of {res['n']} verses: familiarity {fam} "
              f"(known >= {KNOWN:.0f}, partial >= {PARTIAL:.0f}); verse by verse {res['chrf_by_verse']} (another corpus verse: {res['floor']})")
    elif probe == "read":
        res = score_read(P, ans, n)
        print(f"{pname}: read chrF {res['chrf']} against the BSB, verse by verse, on {res['answered']} of {res['n']} verses "
              f"(unrelated English: {res['floor']})")
    else:
        res = score_tell(P, wa, ans, n)
        kinds = ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(res["by_kind"].items()))
        print(f"{pname}: tell apart {100 * res['right'] / res['n']:.0f}% right ({res['right']}/{res['n']}; chance 50%): {kinds}")
    if "--record" in a:
        record(P, probe, res)


if __name__ == "__main__":
    main()
