#!/usr/bin/env python3
"""Alternations: word forms of the target language written with the same letters but other marks (tone, length,
diacritics), and what decides between them, learned from the NT aligned to the Greek (scripts/lang.py build). For any
project; the study keeps the test texts (OT books, held-out chapters) out, so they stay clean.

    python3 scripts/alternations.py <project> find [--min N] [--share F]       the alternation groups of the NT
    python3 scripts/alternations.py <project> study <form> [<form> ...] [--context greek,near,speech] [--min N] [--top K]
    python3 scripts/alternations.py <project> rules [<form> ...] [--write]     store entries (alt:<plain>) from the cues
    python3 scripts/alternations.py <project> examples <form> [--previous W | --next W | --lemma L] [--n N]   verses (local)

find: NT tokens (as lang.py stores them) grouped by their plain spelling (combining marks off); a group = two or more
written forms with >= N tokens each (default 20) whose smaller forms make >= F of the group (default 0.05).

study: one group (give one form, its plain spelling, or several forms). For each form, against the group's other forms:
the features most raised and most lowered, from three contexts:
  greek   the linked Greek word: lang.greek_features (person, number, tense, mood, ... negated, object), its lemma, class
  near    the target words around it (plain): the next word, the previous one, any word within three
  speech  the speech it stands in or introduces, from bcv-commons/greek-nt-clause-layout (setup.py --only gntl; needs
          pyarrow): inside a speech (and its depth), introduces a speech, the speech's length in words, who speaks (the
          Greek name), a reply (the speech before it was by someone else and ended just before), after a speech
Per feature: its share with the form and with the other forms, their ratio, and the same ratio on even and odd verses
(stable: both halves on the same side, >= 1.5 or <= 0.67). The report goes to export/<project>/_eval/local/alternations/
(local: it names target words; their verses stay out).

rules: per group (the given ones, else all that find lists) the cues a draft can be checked on: the previous or next word
and the Greek lemma (only from a Greek word linked to this word alone), stable, ratio >= 10, >= 10 tokens, >= 80% of the
cue's tokens in the group written that form, in 3 books or more with none above 60% of them; printed, and with --write added to the store as `feature` entries
with an `alternation` block, status open (docs/language-store.md, *Alternations*). chapter_check.py reports a draft word
whose cues point only to another form of its group (review()); in the OT the lemma cue is the LXX word of the Hebrew the
draft word renders (MACULA Hebrew's `greek`, its NT lemma), so it needs the .align.
"""
import collections, glob, os, sys, unicodedata

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
GNTL = os.path.join(ROOT, "download", "greek-nt-clause-layout")
# the feature names of each context (the Greek ones are lang.greek_features' plus lemma and class)
CONTEXTS = {"near": {"next", "previous", "within 3", "position"},
            "speech": {"speech", "speech depth", "speech length", "speaker"}}


def plain(w):
    """w without its combining marks (á -> a, ǿ -> ø), lowercase, NFC"""
    return unicodedata.normalize("NFC", "".join(c for c in unicodedata.normalize("NFD", w.lower()) if not unicodedata.combining(c)))


def nt_tokens(con):
    """{(book, ch, v): [(pos, written form)]} in verse order, NFC lowercase"""
    out = collections.defaultdict(list)
    for b, c, v, p, raw in con.execute("select book, ch, v, pos, coalesce(raw, form) from nt_tokens order by book, ch, v, pos"):
        if raw:
            out[(b, c, v)].append((p, unicodedata.normalize("NFC", raw.lower())))
    return out


def groups(toks, min_n=20, share=0.05):
    """[(plain spelling, Counter(written form))] of the alternations, largest second form first"""
    by = collections.defaultdict(collections.Counter)
    for ws in toks.values():
        for _, w in ws:
            by[plain(w)][w] += 1
    out = []
    for base, c in by.items():
        big = [(w, n) for w, n in c.items() if n >= min_n]
        if len(big) >= 2 and 1 - max(c.values()) / sum(c.values()) >= share:
            out.append((base, collections.Counter(dict(big))))
    return sorted(out, key=lambda g: -sorted(g[1].values())[-2])


def speech_index():
    """{MACULA Greek key: speech features} from the newest greek-nt-clause-layout here, or None (no file, no pyarrow)"""
    files = sorted(glob.glob(os.path.join(GNTL, "v*", "clauses.parquet")))
    if not files:
        return None, "no greek-nt-clause-layout (python3 scripts/setup.py --only gntl)"
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return None, "no pyarrow (pip install pyarrow) for greek-nt-clause-layout"
    rows = pq.read_table(files[-1], columns=["book", "seg", "depth", "quotation", "speaker", "speaker_id", "speaker_name",
                                            "words"]).to_pylist()
    rows.sort(key=lambda r: (r["book"], r["seg"]))
    qwords = collections.Counter()
    qrows = collections.defaultdict(list)
    for i, r in enumerate(rows):
        if r["quotation"]:
            qwords[r["quotation"]] += len(r["words"])
            qrows[r["quotation"]].append(i)
    starts = {v[0]: q for q, v in qrows.items()}
    ends = {v[-1]: q for q, v in qrows.items()}
    order = sorted(qrows, key=lambda q: qrows[q][0])
    prev_of = {q: order[k - 1] for k, q in enumerate(order) if k}

    def who(q):
        r = rows[qrows[q][0]]
        return r["speaker_id"] or r["speaker"] or "?"

    def size(n):
        return "1-10" if n <= 10 else "11-30" if n <= 30 else "31-100" if n <= 100 else ">100"

    idx = {}
    for i, r in enumerate(rows):
        f = set()
        if r["quotation"]:
            f |= {("speech", "inside"), ("speech depth", str(min(r["depth"], 3)))}
        # a speech starting in the next three lines, not the one this line is in: this line introduces it
        q = next((starts[j] for j in range(i + 1, min(i + 4, len(rows))) if j in starts and starts[j] != r["quotation"]
                  and rows[j]["book"] == r["book"]), None)
        if q:
            f |= {("speech", "introduces"), ("speech length", size(qwords[q])),
                  ("speaker", rows[qrows[q][0]]["speaker_name"] or rows[qrows[q][0]]["speaker"] or "?")}
            p = prev_of.get(q)
            if p and who(p) != who(q) and qrows[q][0] - qrows[p][-1] <= 4:
                f.add(("speech", "a reply"))
        elif any(j in ends and ends[j] != r["quotation"] for j in range(max(0, i - 2), i)):
            f.add(("speech", "after a speech"))
        for k in r["words"]:
            idx[k] = f
    return idx, os.path.basename(os.path.dirname(files[-1]))


def link_maps(con):
    """{(book, ch, v, pos): [Greek keys]} of the NT links, and {Greek key: number of target tokens linked to it}"""
    links, shared = collections.defaultdict(list), collections.Counter()
    for b, c, v, p, k in con.execute("select book, ch, v, pos, key from nt_links"):
        links[(b, c, v, p)].append(k)
        shared[k] += 1
    return links, shared


def study(pname, forms, contexts=("greek", "near", "speech"), min_n=10, top=8):
    import lang
    P, con = lang.connect(pname)
    toks = nt_tokens(con)
    if len(forms) == 1:                        # one form or its plain spelling: its whole group
        base = plain(forms[0])
        g = dict(groups(toks, min_n=1, share=0)).get(base)
        if not g:
            raise SystemExit(f"{forms[0]}: no alternation of {base!r} in the NT")
        forms = [w for w, n in g.most_common() if n >= min_n]
    forms = [unicodedata.normalize("NFC", f.lower()) for f in forms]
    import sqlite3
    con.row_factory = sqlite3.Row
    gtok = {r["key"]: r for r in con.execute("select * from g.tokens")}
    feat = lang.greek_features(con, gtok)
    links, shared = link_maps(con)
    CONTEXTS["greek"] = None                    # everything not near or speech
    sp, sp_note = speech_index() if "speech" in contexts else (None, "speech context not asked for")
    occ = []                                   # (form, even verse, {features}, ref)
    for (b, c, v), ws in toks.items():
        for i, (p, w) in enumerate(ws):
            if w not in forms:
                continue
            f = set()
            ks = links.get((b, c, v, p), [])
            if "greek" in contexts:
                if not ks:
                    f.add(("greek", "no link"))
                for k in ks:
                    t = gtok.get(k)
                    if t is not None:
                        f |= set(feat(t)) | {("class", t["class"])}
                        if shared[k] == 1:            # the lemma only where the Greek word renders this word alone
                            f.add(("lemma", t["lemma"]))
            if "near" in contexts:
                if i + 1 < len(ws):
                    f.add(("next", plain(ws[i + 1][1])))
                if i:
                    f.add(("previous", plain(ws[i - 1][1])))
                f |= {("within 3", plain(x)) for _, x in ws[max(0, i - 3):i] + ws[i + 1:i + 4]}
                if i + 1 == len(ws):
                    f.add(("position", "verse end"))
            if sp is not None:
                for k in ks:
                    f |= sp.get(k, set())
            occ.append((w, v % 2 == 0, f, f"{b} {c}:{v}"))
    n_of = collections.Counter(o[0] for o in occ)

    def ratio(a, na, b, nb):
        return ((a + .5) / (na + 1)) / ((b + .5) / (nb + 1))

    res = {}
    for form in forms:
        A = [o for o in occ if o[0] == form]
        B = [o for o in occ if o[0] != form]
        cnt = {h: (collections.Counter(), collections.Counter()) for h in ("all", True, False)}
        nn = {h: [0, 0] for h in ("all", True, False)}
        for side, os_ in ((0, A), (1, B)):
            for _, even, fs, _ in os_:
                for h in ("all", even):
                    nn[h][side] += 1
                    cnt[h][side].update(fs)
        rows = []
        for x in set(cnt["all"][0]) | set(cnt["all"][1]):
            a, b = cnt["all"][0][x], cnt["all"][1][x]
            if a + b < min_n:
                continue
            r = ratio(a, nn["all"][0], b, nn["all"][1])
            halves = [ratio(cnt[h][0][x], nn[h][0], cnt[h][1][x], nn[h][1]) for h in (True, False)]
            stable = all(q >= 1.5 for q in halves) or all(q <= 0.67 for q in halves)
            rows.append((r, x, a / max(1, nn["all"][0]), b / max(1, nn["all"][1]), halves, stable))
        rows.sort(key=lambda t: -t[0])
        res[form] = {"n": len(A), "by": {}, "rows": rows,
                     "refs": collections.defaultdict(list), "books": collections.defaultdict(collections.Counter)}
        for _, _, fs, ref in A:
            for x in fs:
                res[form]["books"][x][ref.split()[0]] += 1
                if len(res[form]["refs"][x]) < 3:
                    res[form]["refs"][x].append(ref)
        for ctx, keys in CONTEXTS.items():
            if ctx in contexts:
                rs = [t for t in rows if (t[1][0] in keys if keys else
                                           not any(t[1][0] in k for k in CONTEXTS.values() if k))]
                res[form]["by"][ctx] = [t for t in rs if t[0] >= 1.5][:top] + [t for t in reversed(rs) if t[0] <= 0.67][:top]
    return forms, n_of, res, sp_note


# --- rules: the store entries, and the check of a draft ---------------------------------------------------------------
CUE_CONTEXTS = ("previous", "next", "lemma")   # what a draft has too: its neighbours, and the Greek lemma (NT) or the
                                               # LXX word of the Hebrew it renders (OT, MACULA Hebrew's `greek` field)
MIN_RATIO, MIN_CUE, MIN_P = 10.0, 10, 0.8   # a cue: ratio, tokens, and the share of the cue's tokens with this form
MIN_BOOKS, MAX_BOOK = 3, 0.6                # ... in 3 books or more, none with more than 60% of its tokens (not one
                                            # book's habit or one repeated passage)


def cues(res, n_of, top=6):
    """[cue] per form: previous / next word or Greek lemma, stable on both halves, ratio >= MIN_RATIO, >= MIN_CUE tokens,
    >= MIN_P of the group's tokens with the cue written this form (p), spread over >= MIN_BOOKS books with none above
    MAX_BOOK of them (books, top_book)"""
    out = []
    total = sum(r["n"] for r in res.values())
    for form, r in res.items():
        k = 0
        for q, (ctx, val), pa, pb, hv, st in r["rows"]:
            a, b = round(pa * r["n"]), round(pb * (total - r["n"]))
            bk = r["books"][(ctx, val)]
            if ctx in CUE_CONTEXTS and st and q >= MIN_RATIO and a >= MIN_CUE and a / (a + b) >= MIN_P \
                    and len(bk) >= MIN_BOOKS and max(bk.values()) <= MAX_BOOK * sum(bk.values()):
                out.append({"form": form, "context": ctx, "value": val, "n": a, "p": round(a / (a + b), 3),
                            "books": len(bk), "top_book": round(max(bk.values()) / sum(bk.values()), 2),
                            "with": round(pa, 3), "others": round(pb, 3), "ratio": round(q, 1),
                            "refs": r["refs"][(ctx, val)][:2]})
                k += 1
                if k == top:
                    break
    return out


def entry(pname, forms, n_of, res, today):
    """a feature entry with an `alternation` block (docs/language-store.md, *Alternations*), or None without cues"""
    cs = cues(res, n_of)
    if not cs:
        return None
    base = plain(forms[0])
    by = collections.defaultdict(list)
    for c in cs:
        by[c["form"]].append(f"{c['context']} {c['value']}")
    ev, seen = [], set()
    for c in cs:
        if c["form"] not in seen and c["refs"]:
            seen.add(c["form"])
            ev.append({"ref": c["refs"][0], "form": c["form"], "n": n_of[c["form"]]})
    return {"id": f"alt:{base}", "kind": "feature", "value": " / ".join(forms),
            "alternation": {"plain": base, "forms": {f: n_of[f] for f in forms},
                            "cues": [{k: v for k, v in c.items() if k != "refs"} for c in cs]},
            "evidence": ev, "confidence": "medium", "method": "corpus-derived", "by": "script:alternations.py",
            "date": today, "status": "open",
            "note": "Forms with the same letters and other marks, told apart in the NT by the cues (form: context value; "
                    "share with the form vs the group's other forms, stable on even and odd verses). "
                    + "; ".join(f"{f}: {', '.join(v)}" for f, v in by.items())
                    + ". An agent checks a few verses per cue and sets observed, or retires the entry."}


def lxx_lemmas(min_share=0.75):
    """{plain Greek form: NT lemma} where one lemma makes up min_share of the form's NT tokens: the lemma of MACULA
    Hebrew's per-word LXX form (ἦν, ἔσομαι -> εἰμί)"""
    import ot_routes
    by = collections.defaultdict(collections.Counter)
    import sqlite3
    for t, lem in sqlite3.connect(os.path.join(ROOT, "orig", "grc.sqlite")).execute("select text, lemma from tokens"):
        by[ot_routes.plain(t)][lem] += 1
    return {f: c.most_common(1)[0][0] for f, c in by.items()
            if f and c.most_common(1)[0][1] >= min_share * sum(c.values())}


def live_alternations(pname):
    import grammar
    return [e for e in grammar.entries(pname) if e.get("alternation") and e.get("status") != "superseded"]


def review(pname, code, ch, cap=12, path=None):
    """REVIEW lines for chapter_check.py: a draft word of a store alternation whose cues point only to another form
    (its neighbours in the draft; in the OT, with a .align, the LXX lemma of the Hebrew it renders); path: another
    draft file of the chapter (a test draft: neighbours only)"""
    alts = live_alternations(pname)
    if not alts:
        return []
    import langtools as LT, lang
    import full_align as F
    from project import project_dir
    from books import BY_CODE
    P = LT.Project(pname)
    by_plain = {a["alternation"]["plain"]: a["alternation"] for a in alts}
    path = path or os.path.join(project_dir(pname), code, f"{code}{ch:03d}.txt")
    lemma_at = {}                                # (verse, plain word) -> {Greek lemmas}, OT drafts with an alignment
    if BY_CODE[code][2] == "ot" and any(c["context"] == "lemma" for a in by_plain.values() for c in a["cues"]):
        d = os.path.join(project_dir(pname), code, f"{code}{ch:03d}")
        if os.path.abspath(path) == os.path.abspath(d + ".txt") and os.path.exists(d + ".align") or os.path.exists(d + ".tagged"):
            import morphs, sqlite3, ot_routes
            lx = lxx_lemmas()
            gk = dict(sqlite3.connect(os.path.join(ROOT, "orig", "heb.sqlite")).execute(
                "select key, greek from tokens where book = ? and ch = ?", (code.upper(), ch)))
            for v, words in morphs.draft_words(pname, code, ch).items():
                for k, ws in words.items():
                    lem = lx.get(ot_routes.plain(gk.get(k) or ""))
                    if lem and len(ws) == 1:        # as in the NT: the Hebrew word rendered by this word alone
                        lemma_at.setdefault((v, plain(ws[0])), set()).add(lem)
    out = []
    for v, text in F.draft_texts(path):
        ws = lang.raw_tokens(P, text)
        for i, w in enumerate(ws):
            a = by_plain.get(plain(w))
            if not a or w not in a["forms"]:
                continue
            ctx = {("previous", plain(ws[i - 1])) if i else None, ("next", plain(ws[i + 1])) if i + 1 < len(ws) else None}
            ctx |= {("lemma", x) for x in lemma_at.get((v, plain(w)), ())}
            fired = [c for c in a["cues"] if (c["context"], c["value"]) in ctx]
            if fired and all(c["form"] != w for c in fired):
                c = max(fired, key=lambda c: c["ratio"])
                out.append(f"alternation {ch}:{v} {w}: with {c['context']} {c['value']} the NT writes {c['form']} "
                           f"({c['p']:.0%} of {round(c['n'] / c['p'])}; store alt:{a['plain']})")
    return out[:cap] + ([f"alternation: {len(out) - cap} more"] if len(out) > cap else [])


def examples(pname, form, cue=None, n=5):
    """lines for an agent checking a cue: NT verses where `form` stands (with the cue, if given: (context, value)), the
    words around it as written, and the Greek word it is linked to (lemma, tense, mood, person, number, case); also the
    verses where the cue stands with another form of the group, so both sides can be read"""
    import lang, sqlite3
    _, con = lang.connect(pname)
    con.row_factory = sqlite3.Row
    gtok = {r["key"]: r for r in con.execute("select * from g.tokens")}
    links, shared = link_maps(con)
    form = unicodedata.normalize("NFC", form.lower())
    base = plain(form)
    hit, other = [], []
    for (b, c, v), ws in nt_tokens(con).items():
        for i, (p, w) in enumerate(ws):
            if plain(w) != base:
                continue
            if cue:
                ctx, val = cue
                ks = links.get((b, c, v, p), [])
                have = (ctx == "previous" and i and plain(ws[i - 1][1]) == val) or \
                       (ctx == "next" and i + 1 < len(ws) and plain(ws[i + 1][1]) == val) or \
                       (ctx == "lemma" and any(gtok.get(k) is not None and gtok[k]["lemma"] == val and shared[k] == 1
                                               for k in ks))
                if not have:
                    continue
            g = "; ".join(" ".join(str(x) for x in (t["text"], t["lemma"], t["tense"], t["mood"], t["person"],
                                                     t["number"], t["gcase"]) if x)
                          for t in (gtok.get(k) for k in links.get((b, c, v, p), [])) if t is not None)
            line = (f"{b} {c}:{v}  " + " ".join(x for _, x in ws[max(0, i - 4):i]) + f" [{w}] "
                    + " ".join(x for _, x in ws[i + 1:i + 5]) + f"   <- {g or 'no link'}")
            (hit if w == form else other).append((b, line))
    return spread(hit, n), spread(other, n), books(hit), books(other)


def spread(lines, n):
    """n of the (book, line) pairs, one book after another (round robin), so a one-book cue shows as one"""
    by = collections.defaultdict(list)
    for b, l in lines:
        by[b].append(l)
    out = []
    while len(out) < n and any(by.values()):
        for b in sorted(by, key=lambda b: -len(by[b])):
            if by[b] and len(out) < n:
                out.append(by[b].pop(0))
    return out


def books(lines):
    """'N tokens in K books: MAT 12, LUK 9, ...'"""
    c = collections.Counter(b for b, _ in lines)
    return f"{sum(c.values())} tokens in {len(c)} books" + (": " + ", ".join(f"{b} {k}" for b, k in c.most_common(8)) if c else "")


def write_entries(pname, new):
    """add the entries to the store's observations.json; an id already live is left alone (reported)"""
    import json, langtools as LT
    f = os.path.join(LT.Project(pname).profile, "observations.json")
    data = json.load(open(f, encoding="utf-8"))
    live = {e["id"] for e in data["entries"] if e.get("status") != "superseded"}
    added = [e for e in new if e["id"] not in live]
    data["entries"] += added
    json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(f, "a", encoding="utf-8").write("\n")
    return added, [e["id"] for e in new if e["id"] in live]


def report(pname, forms, n_of, res, sp_note):
    L = [f"# Alternation {' / '.join(forms)} ({pname}, NT aligned to the Greek)", "",
         "Tokens: " + ", ".join(f"{f} {n_of[f]}" for f in forms) + f". Speech context: {sp_note}.", "",
         "Per form, against the group's other forms: the feature's share with it and with the others, the ratio, and the ratio on "
         "even / odd verses (stable = both halves on the same side).", ""]
    for f in forms:
        r = res[f]
        L += [f"## {f} ({r['n']} tokens)", ""]
        for ctx, rows in r["by"].items():
            L += [f"### {ctx}", "", "| feature | with it | others | ratio | even / odd | |", "|---|---|---|---|---|---|"]
            for q, (k, v), pa, pb, hv, st in rows:
                L.append(f"| {k}: {v} | {pa:.0%} | {pb:.0%} | {q:.2f} | {hv[0]:.2f} / {hv[1]:.2f} | {'stable' if st else ''} |")
            L.append("" if rows else "(nothing raised or lowered)\n")
    return "\n".join(L)


def main(a):
    if len(a) < 2 or a[1] not in ("find", "study", "rules", "examples"):
        print(__doc__)
        return
    pname, cmd = a[0], a[1]
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d
    rest = [x for i, x in enumerate(a[2:], 2) if not x.startswith("--") and not a[i - 1].startswith("--")]
    if cmd == "find":
        import lang
        _, con = lang.connect(pname)
        gs = groups(nt_tokens(con), int(opt("--min", 20)), float(opt("--share", 0.05)))
        print(f"{pname}: {len(gs)} alternation groups in the NT (forms >= {opt('--min', 20)} tokens)")
        for base, c in gs:
            print(f"  {base:16} {sum(c.values()):6}  " + "  ".join(f"{w} {n}" for w, n in c.most_common()))
        return
    if cmd == "examples":
        cue = next(((k[2:], opt(k, None)) for k in ("--previous", "--next", "--lemma") if k in a), None)
        if cue and cue[0] != "lemma":
            cue = (cue[0], plain(cue[1]))
        hit, other, nh, no = examples(pname, rest[0], cue, int(opt("--n", 5)))
        print(f"{rest[0]}{' with ' + ' '.join(cue) if cue else ''}: {nh}")
        print("\n".join("  " + x for x in hit))
        print(f"the other forms of {plain(rest[0])!r}{' with the same cue' if cue else ''}: {no}")
        print("\n".join("  " + x for x in other))
        return
    if cmd == "rules":
        import datetime, json
        import lang
        if rest:
            bases = [plain(x) for x in rest]
        else:
            _, con = lang.connect(pname)
            bases = [b for b, _ in groups(nt_tokens(con), int(opt("--min", 20)), float(opt("--share", 0.05)))]
        today = datetime.date.today().isoformat()
        new = []
        for b in bases:
            forms, n_of, res, _ = study(pname, [b], ("greek", "near"), int(opt("--min", 10)))
            e = entry(pname, forms, n_of, res, today)
            if e:
                new.append(e)
                print(f"{e['id']:20} {e['value']:40} " + "; ".join(f"{c['form']}: {c['context']} {c['value']} x{c['ratio']}"
                                                                   for c in e["alternation"]["cues"][:4]))
        print(f"{len(new)} of {len(bases)} groups have cues")
        if "--write" in a:
            added, kept = write_entries(pname, new)
            print(f"written: {len(added)} entries (status open); already live, left alone: {', '.join(kept) or 'none'}")
        return
    forms, n_of, res, note = study(pname, rest, tuple(opt("--context", "greek,near,speech").split(",")),
                                   int(opt("--min", 10)), int(opt("--top", 8)))
    txt = report(pname, forms, n_of, res, note)
    print(txt)
    import langtools as LT
    d = os.path.join(LT.Project(pname).dir, "_eval", "local", "alternations")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, plain(forms[0]) + ".md")
    open(path, "w", encoding="utf-8").write(txt + "\n")
    print(f"\n-> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
