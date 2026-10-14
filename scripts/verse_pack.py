#!/usr/bin/env python3
"""Precompile a verse pack for one chapter: everything a drafting agent would otherwise look up, in one file.

For export/<project>/_learn/packs/<code>NNN.md, per verse:
  - the original's clause lines and the assisting translation (BSB/MSB) verse;
  - store hits from export/<project>/profile/ (docs/proposals/language-profile/): terms whose rendering
    the alignment lexicon links to a word of the verse (or whose gloss is in it), formulas whose source
    phrase occurs in the verse, names, and the gaps recorded for this verse;
  - for every content word of the assisting verse, the lexicon's renderings with counts
    (export/<project>/_learn/lexicon_eng.tsv, if present), and '—' where it has none: the words that
    still need a search;
  - phrases: the verse's 2-4-word phrases of the assisting translation that occur in the style corpus
    (light stemming: lie/lies, morning), chosen to cover the verse, each with its shortest corpus verses,
    source and target side by side. These show constructions, which shared single words don't;
  - the K most similar verses of the style corpus by word overlap (rare shared words weigh more);
  - "still needs a search": the content words that no store entry, lexicon row or phrase covers.
And a chapter header: the store's features in one line each, an index of all live terms, formulas and
names (one line each; `concord.py store <id>` prints an entry in full), the names in the chapter, the
glossary entries (edition glossary.tsv) whose English equivalent occurs in the chapter.

The pack replaces reading the store's JSON files; the agent searches only for what the pack lacks.
The book being drafted never enters the corpus, even where the style edition has it (a test or a revision).

Levels (`--level`, default from the project's mode, scripts/modes.py):
  full      everything above (familiarity unknown);
  dialect   without the similar verses (partial: the phrases and lexicon show the variety's forms);
  memory    the header and each verse's store hits only (known: the model writes the language; the pack
            keeps the project's decisions in front of it).

Usage: python3 scripts/verse_pack.py <project> <code> <chapter> [--level full|dialect|memory] [--similar K] [--out FILE]
"""
import collections, glob, json, math, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from books import BY_CODE  # noqa: E402
from project import project, sources, edition  # noqa: E402
import langtools as LT  # noqa: E402

COMMON = {"one", "said", "man", "men", "people", "place", "land", "day", "days", "came", "went", "come", "go", "give", "gave", "put", "made", "make", "took", "take", "see", "saw", "know", "like", "way", "thing", "things", "time", "hand", "house", "son", "sons", "name"}
STOP = set("""a an the and or but of to in on at by for with from as is are was were be been being it its this that these
those he she they them his her their him we you i me my our your us who whom which what when where how not no so
then there here into unto upon will shall would should may might can could do does did have has had if than too very
also all any each every some such own same out up down over off again further once more most other only very""".split())


def verses_of(path):
    """{(chapter, verse): text} of a repo chapter file: vN markers; notes, headings and poetry marks removed."""
    ch = int(os.path.basename(path)[3:6])
    body = [re.sub(r"^//\d+ ", "", l) for l in open(path, encoding="utf-8").read().splitlines()
            if not l.startswith(("!!", "===")) and not re.fullmatch(r"==.*==", l)]
    text = re.sub(r"\{[A-Z]:[^{}]*\}", " ", " ".join(body))
    parts = re.split(r"(?<![\w>.])v(\d+)(?:-\d+)?(?=\s)", text)
    return {(ch, int(parts[i])): re.sub(r"\s+", " ", parts[i + 1]).strip() for i in range(1, len(parts) - 1, 2)}


def orig_lines(path, nt):
    """{verse: [clause lines]} of an original file (OT 'verse:level text'; NT 'chapter:verse text')."""
    out = collections.defaultdict(list)
    for l in open(path, encoding="utf-8").read().splitlines()[1:]:
        m = re.match(r"(\d+):(\d+) ?(.*)", l)
        if m:
            v = int(m[2]) if nt else int(m[1])
            out[v].append(m[3].strip() if nt else f"{m[2]} {m[3].strip()}")
    return out


def strip_marks(s, marks=None):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not (unicodedata.combining(c) if marks is None else c in marks))
    return unicodedata.normalize("NFC", s)


def heb_consonants(s):
    return re.sub(r"[֑-ׇ‍]", "", s).replace("־", " ").replace("׃", "").strip()


def tokens(s):
    return re.findall(r"[a-z]+(?:'[a-z]+)?", s.lower().replace("’", "'"))


def stem(t):
    """Crude English stem for phrase matching: lies/lie, lying/lie, threshed/thresh."""
    t = t.split("'")[0]
    for suf, rep_ in (("ying", "ie"), ("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if len(t) > len(suf) + 2 and t.endswith(suf):
            return t[: -len(suf)] + rep_
    return t


def content_words(s):
    return [t for t in tokens(s) if t not in STOP and len(t) > 1]


def load_lexicon(path):
    lex = collections.defaultdict(list)
    if os.path.exists(path):
        for l in open(path, encoding="utf-8").read().splitlines()[1:]:
            s, k, c, sh = l.split("\t")
            lex[s].append((k, int(c), float(sh)))
    return lex


def load_profile(folder):
    entries = []
    for fn in ("observations.json", "decisions.json"):
        p = os.path.join(folder, fn)
        if os.path.exists(p):
            entries += json.load(open(p, encoding="utf-8")).get("entries", [])
    live = {}
    for e in entries:                      # the merged view: a later entry with the same id wins; superseded ones drop out
        live[e["id"]] = e
    for e in entries:
        if e.get("supersedes") in live and live[e["supersedes"]] is not e:
            live.pop(e["supersedes"], None)
    return [e for e in live.values() if e.get("status") != "superseded"]


def gloss_words(e):
    """English words that name a term's meaning: from source (after a Strong's number), the first clause of note."""
    words = set()
    src = e.get("source") or ""
    words |= set(content_words(re.sub(r"[HG]\d+", " ", src)))
    note = (e.get("note") or "").split(";")[0].split(":")[0]
    words |= set(content_words(note)[:4])
    words |= {w.lower() for w in e.get("words") or []}
    return {w for w in words if w not in COMMON}


def main():
    args = sys.argv[1:]
    if len(args) < 3:
        raise SystemExit(__doc__)
    pname, code, chapter = args[0], args[1], int(args[2])
    k = int(args[args.index("--similar") + 1]) if "--similar" in args else 2
    p = project(pname)
    import modes
    level = args[args.index("--level") + 1] if "--level" in args else modes.mode(p)["pack"]
    if level not in ("full", "dialect", "memory"):
        raise SystemExit(f"--level {level}: full, dialect or memory")
    orig_dir, _, assist_dir = sources(p, code)
    nt = BY_CODE[code][2] == "nt"
    nnn = f"{chapter:03d}"
    pdir = os.path.join(ROOT, "export", pname)
    out = args[args.index("--out") + 1] if "--out" in args else os.path.join(pdir, "_learn", "packs", f"{code}{nnn}.md")

    orig = orig_lines(os.path.join(ROOT, orig_dir, f"{code}{nnn}.txt"), nt)
    assist = verses_of(os.path.join(ROOT, assist_dir, f"{code}{nnn}.txt"))
    LP = LT.Project(pname)                         # the style corpus, paired with the BSB (scripts/langtools.py)
    glossary = LP.glossary()
    corpus = [(r[0], r[3], r[4]) for r in LP.corpus(exclude={code}) if r[3]]   # never the book being drafted
    df = collections.Counter(t for r in corpus for t in set(tokens(r[1])))
    N = len(corpus)
    stoks = [[stem(t) for t in tokens(r[1])] for r in corpus]
    grams = collections.defaultdict(set)          # stemmed n-gram -> corpus row indices
    for i, ts in enumerate(stoks):
        for n in (2, 3, 4):
            for j in range(len(ts) - n + 1):
                grams[tuple(ts[j:j + n])].add(i)
    lex = load_lexicon(os.path.join(pdir, "_learn", "lexicon_eng.tsv"))
    prof = load_profile(os.path.join(pdir, "profile"))
    marks = set()
    for fn in ("observations.json", "decisions.json"):
        pp = os.path.join(pdir, "profile", fn)
        if os.path.exists(pp):
            marks |= {chr(int(m[2:], 16)) for m in (json.load(open(pp, encoding="utf-8")).get("orthography") or {}).get("ignore_marks", [])}
    norm = lambda s: strip_marks(s.lower(), marks) if marks else s.lower()

    terms = [e for e in prof if e["kind"] == "term"]
    formulas = [e for e in prof if e["kind"] == "formula"]
    names = [e for e in prof if e["kind"] == "name"]
    gaps = [e for e in prof if e["kind"] == "gap"]
    features = [e for e in prof if e["kind"] == "feature"]
    letters = [e for e in prof if e["kind"] == "letter"]
    term_tokens = {e["id"]: {norm(t) for t in re.findall(r"[^\s<>,.;:()]+", e["value"] if isinstance(e["value"], str) else "")} for e in terms}
    term_gloss = {e["id"]: gloss_words(e) for e in terms}

    term_head = {e["id"]: norm(re.findall(r"[^\s<>,.;:()]+", e["value"])[0]) if isinstance(e["value"], str) and re.findall(r"[^\s<>,.;:()]+", e["value"]) else "" for e in terms}

    def term_hits(bsb_words):
        hits = []
        for e in terms:
            why = None
            if term_gloss[e["id"]] & set(bsb_words):
                why = "gloss"
            else:
                for w in bsb_words:
                    if w in COMMON:
                        continue
                    strong = {norm(kk) for kk, c, sh in lex.get(w, []) if c >= 3 and sh >= 0.2}
                    if term_head[e["id"]] and term_head[e["id"]] in strong:
                        why = f"lexicon:{w}"; break
            if why:
                hits.append((e, why))
        return hits

    def formula_hits(heb_text, bsb_text):
        hits = []
        hc, bt = heb_consonants(heb_text), " " + " ".join(tokens(bsb_text)) + " "
        for e in formulas:
            src = e.get("source") or ""
            heb_part = heb_consonants(src.split("/")[0])
            eng_part = " ".join(tokens(src.split("/")[-1]))
            ok = False
            if re.search(r"[א-ת]", heb_part) and heb_part.replace("<X>", "").strip():
                probe = heb_part.replace("<X>", "").replace("<N>", "").strip()
                ok = probe and probe in hc
            if not ok and eng_part:
                cw = [w for w in content_words(eng_part) if w not in ("x", "n")]
                ok = bool(cw) and all(f" {w} " in bt for w in cw)
            if ok:
                hits.append(e)
        return hits

    def name_hits(heb_text, bsb_text):
        hc, bw = heb_consonants(heb_text), set(tokens(bsb_text))
        hits = []
        for e in names:
            src = heb_consonants(e.get("source") or "")
            eng = e["id"].split(":", 1)[-1].replace("_", " ")
            if (src and src in hc) or eng in bw:
                hits.append(e)
        return hits

    name_words = {e["id"].split(":", 1)[-1] for e in names}

    def phrases(bsb_text, cap=5):
        """Phrases of the verse found in the corpus, longest and rarest first, chosen to cover new words."""
        raw = tokens(bsb_text)
        st = [stem(t) for t in raw]
        cand = []
        for n in (4, 3, 2):
            for j in range(len(st) - n + 1):
                g = tuple(st[j:j + n])
                words = raw[j:j + n]
                if all(w in STOP for w in words) or any(w in name_words for w in words):
                    continue
                if n == 2 and sum(w not in STOP and w not in COMMON for w in words) == 0:
                    continue
                f = len(grams.get(g, ()))
                if 1 <= f <= 400:
                    cand.append((n, f, j, g, " ".join(words)))
        cand.sort(key=lambda c: (-c[0], c[1]))
        covered, out = set(), []
        for n, f, j, g, text in cand:
            span = {x for x in range(j, j + n) if raw[x] not in STOP}
            if not span - covered or any(o[0] == text for o in out):
                continue
            covered |= span
            ex = sorted(grams[g], key=lambda i: len(corpus[i][2]))[:2 if f <= 20 else 1]
            out.append((text, f, [corpus[i] for i in ex], {raw[x] for x in span}))
            if len(out) >= cap:
                break
        return out

    def similar(bsb_text):
        q = set(tokens(bsb_text))
        def score(r):
            return sum(math.log(N / (1 + df[t])) for t in set(tokens(r[1])) if t in q)
        best = sorted(corpus, key=score, reverse=True)[:k]
        return [(r, score(r)) for r in best]

    book_title = (p.get("book_titles") or {}).get(code, BY_CODE[code][1])
    L = [f"# Verse pack: {book_title} {chapter} ({code}{nnn}), project {pname}", "",
         f"Built by scripts/verse_pack.py from {orig_dir}, {assist_dir}, the style corpus ({', '.join(p['style_from'])}, "
         f"{N} verses), the lexicon and the store (`profile/`, {len(prof)} live entries); level {level}. Read this before drafting; "
         "search with concord.py only for what it lacks. Renderings marked (by-rule) were built by analogy, not found.", ""]
    if features:
        L += ["## Grammar (the store's features, one line each)", ""]
        for e in features:
            L.append(f"- **{e['id']}** [{e['confidence']}]: {e['value']}" + (f" — pattern: `{e['pattern']}`" if e.get("pattern") else ""))
        L.append("")
    if terms or formulas or names:
        L += ["## Store index (all live terms, formulas and names; `concord.py store <id>` prints one in full)", ""]
        for e in terms + formulas + names:
            L.append(f"- `{e['id']}` {e.get('source') or ''} → {e['value'] if isinstance(e['value'], str) else e['value']}"
                     + (" (by-rule)" if e.get("attested") == "by-rule" else "") + (" [open]" if e.get("status") == "open" else ""))
        L.append("")
    if letters:
        L += ["## Name letters", ""] + [f"- {e['value']}" for e in letters] + [""]
    chapter_heb = " ".join(l for v in orig.values() for l in v)
    chapter_bsb = " ".join(assist.values())
    nh = name_hits(chapter_heb, chapter_bsb)
    if nh:
        L += ["## Names in this chapter", ""]
        for e in nh:
            L.append(f"- {e['value']} ({e['source']}, {e['attested']}, {e['confidence']})" + (f": {e['note']}" if e.get("note") else ""))
        L.append("")
    cw_chapter = set(content_words(chapter_bsb))
    bsb_flat = " " + " ".join(tokens(chapter_bsb)) + " "
    gh = [g for g in glossary if len(g) >= 2 and content_words(g[1].split(",")[0])
          and all(f" {w} " in bsb_flat for w in content_words(g[1].split(",")[0]))]
    if gh:
        L += ["## Glossary entries whose English occurs in this chapter", ""] + [f"- **{g[0]}** = {g[1]}" for g in gh] + [""]

    L += ["## Verses", ""]
    need_total = []
    for v in sorted(assist):
        ch_, vn = v
        bsb = assist[v]
        heb = "\n".join(f"    {l}" for l in orig.get(vn, []))
        L += [f"### {code.upper()} {chapter}:{vn}", "", f"**{BY_CODE[code][1]} {chapter}:{vn}, {assist_dir.split('/')[-1]}:** {bsb}", ""]
        if heb:
            L += ["Original, one clause per line (level after the colon):", "", heb, ""]
        bw = content_words(bsb)
        th = term_hits(bw)
        fh = formula_hits(" ".join(orig.get(vn, [])), bsb)
        nh = name_hits(" ".join(orig.get(vn, [])), bsb)
        vstems = {stem(w) for w in bw}
        gh = [e for e in gaps if (e.get("source") or "").upper() == f"{code.upper()} {chapter}:{vn}"
              or any(r.get("ref") == f"{code.upper()} {chapter}:{vn}" for r in e.get("evidence", []))
              or {stem(w.lower()) for w in e.get("words") or []} & vstems]
        if th or fh or nh or gh:
            L += ["Store:", ""]
            for e in nh:
                L.append(f"- name **{e['value']}** ({e['attested']})")
            for e, why in th:
                alts = "; alternatives: " + ", ".join(a["value"] for a in e.get("alternatives", [])) if e.get("alternatives") else ""
                ev = ", ".join(r["ref"] for r in e.get("evidence", [])[:2])
                L.append(f"- term {e['source']} → **{e['value']}** [{e['attested']}, {e['confidence']}, {e['status']}] ({ev}; via {why}){alts}" + (f" — {e['note']}" if e.get("note") else ""))
            for e in fh:
                ev = ", ".join(r["ref"] for r in e.get("evidence", [])[:2])
                L.append(f"- formula {e['source']} → **{e['value']}** [{e['attested']}, {e['confidence']}] ({ev})" + (f" — {e['note']}" if e.get("note") else ""))
            for e in gh:
                L.append(f"- gap [{e['status']}]" + (f" ({', '.join(e['words'])})" if e.get("words") else "") + f": {e['value']}")
            L.append("")
        lexed = set()
        if level == "memory":
            continue
        if lex:
            L += ["Lexicon (BSB word → renderings, count/share; only count ≥3, share ≥0.15; — none):", ""]
            seen = set()
            cells = []
            name_words = {e["id"].split(":", 1)[-1] for e in names}
            for w in bw:
                w = w.split("'")[0]
                if w in seen or w in name_words or len(w) < 3:
                    continue
                seen.add(w)
                r = [(kk, c, sh) for kk, c, sh in lex.get(w, []) if c >= 3 and sh >= 0.15][:3]
                if r:
                    lexed.add(w)
                cells.append(f"{w}: " + (", ".join(f"{kk} {c}/{sh:.2f}" for kk, c, sh in r) if r else "—"))
            L += ["; ".join(cells), ""]
        shown = set()
        ph = phrases(bsb)
        if ph:
            L += ["Phrases found in the corpus (verse count; the shortest verses):", ""]
            for text, f, ex, _ in ph:
                L.append(f"- \"{text}\" ({f})")
                for ref, a, t in ex:
                    if ref in shown:
                        L.append(f"  - {ref} (above)")
                        continue
                    shown.add(ref)
                    L += [f"  - {ref}: {a}", f"    → {t}"]
            L.append("")
        sim = [x for x in similar(bsb) if x[0][0] not in shown] if level == "full" else []
        if sim:
            L += ["Most similar corpus verses (word overlap):", ""]
            for (ref, a, t), sc in sim:
                L += [f"- {ref}: {a}", f"  → {t}"]
            L.append("")
        stored = set()
        for e, why in th:
            stored |= gloss_words(e) | ({why.split(":", 1)[1]} if why.startswith("lexicon:") else set())
        for e in fh:
            stored |= set(content_words((e.get("source") or "").split("/")[-1]))
        for e in gh:
            stored |= {w.lower() for w in e.get("words") or []}
        in_phr = set().union(*[w for *_, w in ph]) if ph else set()
        need = []
        for w in bw:
            w = w.split("'")[0]
            if (len(w) < 3 or w in name_words or w in COMMON or w in need or w in lexed or w in stored
                    or w in in_phr or stem(w) in {stem(x) for x in stored | in_phr}):
                continue
            need.append(w)
        L += ["**Still needs a search:** " + (", ".join(need) if need else "nothing (the pack covers every content word)"), ""]
        need_total.append(len(need))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"{out}: {len(assist)} verses, {len(L)} lines, {os.path.getsize(out) // 1024} KB; store hits: "
          f"{sum(1 for v in assist for _ in term_hits(content_words(assist[v])))} terms; still to search: {sum(need_total)} words")


if __name__ == "__main__":
    main()
