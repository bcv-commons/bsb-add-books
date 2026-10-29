#!/usr/bin/env python3
"""The cell check: does a draft mark what its source verse marks? For each verse, the source's marked verb cells
(scripts/source_cells.py: a negated verb, a subject other than 3rd singular) that the store has a pattern for
(scripts/grammar.py: an observed cell entry, its value and alternatives), against the draft verse's tokens that carry
the pattern (a prefix at a token's start, a suffix at its end or as a split '-x' token). A verse passes a cell when it
has at least as many such tokens as the source has verbs of the cell.

A verse-level count, not an alignment: it can't tell which verb carries the mark, and a pattern a word has anyway (a
noun that starts like a prefix) passes. So a cell is judged only where it can be: its pattern is in at most half of the
verses whose source has no such verb (else it passes anyway: a one-letter prefix many words start with), and, with --human, the human translation of the
same verses passes it at least --min-ceiling of the time (its pass rate is the ceiling).

With a tagged draft beside the file (<code>NNN.tagged, the OT drafting's interim file) the check is at the word level:
the target words tagged with each source verb of a marked cell, against the same pattern on the words tagged with the
paradigm's unmarked verbs (the background); --verse forces the verse-level count.

In the drafting loop (scripts/chapter_check.py, book_review()) the check is a comparison, not a rule: the human text
leaves many verbs of a marked cell unmarked too, so a cell is flagged only where the book's drafts mark it clearly less
often than the style corpus's human OT does, verse level on both sides.

A form without hyphens in a cell's value or alternatives is a separate word that marks it (a particle: the morph slot
`free`): a verse passes with it anywhere in the verse (word level: anywhere in the verse's words, as the word may be
tagged with the source's particle rather than the verb).

Candidates from the drafting loop: in a binding project an agent explains each unmarked verb in the notes
(`unmarked <ch>:<v> <cell>: <reason>`, citing the words it used in *italics*); `unmarked` lists them by cell. `try`
measures each candidate form on the style corpus's human text before it goes into the store, and `--write` adds the
kept ones to the cell and records every form tried as a claim with its figures (kept or not).

Usage: python3 scripts/cell_check.py <project> unmarked
       python3 scripts/cell_check.py <project> try <paradigm> <bundle> <form> ... [--write] [--by NAME]
       python3 scripts/cell_check.py <project> <chapter file> ... [--list] [--verse] [--min-ceiling R]
  --list           the verses that miss a cell (REVIEW lines), for a draft
  --min-ceiling R  with a human file given as --human DIR: only cells whose human pass rate is at least R (default 0.5)
  --human DIR      the human translation's folder (files named as the drafts): its pass rate per cell beside the draft's
"""
import collections, os, re, sys, unicodedata

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
import grammar  # noqa: E402
import langtools as LT  # noqa: E402
import source_cells as SC  # noqa: E402
import verse_analysis as VA  # noqa: E402
from books import BY_CODE  # noqa: E402


def fold(w):
    """lower case without accents and tone marks, as the tokeniser may give a word (mbaín -> mbain)"""
    return "".join(c for c in unicodedata.normalize("NFD", w.lower()) if not unicodedata.combining(c))


def free_form(v):
    """a form without hyphens (a particle, an auxiliary: a morph of slot `free`) -> the word as written (NFC, lower
    case): its tone and accent marks are part of it (ambá "please" is not amba "wanted")"""
    v = (v or "").strip()
    return unicodedata.normalize("NFC", v.lower()) if v and v != "Ø" and "-" not in v and "…" not in v else ""


TONES = set()          # the forms of the store's grammatical tone morphs (tone-proh), set by view()
FORCE_VIEW = None      # "strings" | "morphs": overrides the store's analysis.match (for comparisons)
_VIEWS = {}


def view(P):
    """the project's morph view (scripts/morphs.py) when its store sets `analysis.match: morphs` (or FORCE_VIEW does),
    else None: affixes are then matched as strings at the token's edges. A tone morph needs the segmenter either way;
    it is built whenever the store has one."""
    import json
    import morphs
    if P.name not in _VIEWS:
        f = os.path.join(P.profile, "observations.json")
        d = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
        S = morphs.load(P.name, P)
        _VIEWS[P.name] = (S, (d.get("analysis") or {}).get("match", "strings"))
    S, match = _VIEWS[P.name]
    TONES.clear()
    TONES.update(t.form for t in (S.tones if S else []))
    return S if (FORCE_VIEW or match) == "morphs" else None


def tone_view(P):
    view(P)
    return _VIEWS[P.name][0]


def patterns(ce):
    """(prefix, suffix, word, tone) of a cell entry: its value and its alternatives of two letters or more; a form
    without hyphens is a separate word that marks the cell; a grammatical tone morph's form (tone-proh) the tone"""
    out = []
    alts = [a.get("value") for a in ce.get("alternatives", [])]
    for v in [ce.get("value")] + alts:
        if v in TONES:
            out.append(("", "", "", v))
            continue
        pre, suf = VA.parts(v)
        w = free_form(v)
        if w:
            out.append(("", "", w, ""))
        elif (pre or suf) and (v == ce.get("value") or len(pre + suf) >= 2):  # a one-letter alternative passes anything
            out.append((pre, suf, "", ""))
    return out


def has_prefix(labels, pre):
    """the morph labels carry the prefix: as it is (ka-), or reduplicated (kaka-, a store morph of its own that repeats
    it: the same prefix, not another one)"""
    if pre + "-" in labels:
        return True
    return any(l.endswith("-") and len(l) - 1 > len(pre) and (len(l) - 1) % len(pre) == 0 and l[:-1] == pre * ((len(l) - 1) // len(pre))
               for l in labels)


def carries(tokens, pats, exact=None, seg=None, tones=None):
    """the number of tokens that carry one of the patterns. A free word is matched as written, on `exact` (the same
    tokens with every mark kept: Tokeniser.tokens(s, exact=True)); without it, with the marks folded on both sides.
    With `seg` (the morph view) an affix must be a morph of the token (qo-, -eav), not merely its first or last letters
    (an affix the store has no morph entry for is still matched as a string);
    a tone pattern is matched by `tones` (the segmenter, also when affixes are matched as strings)."""
    n = 0
    for i, t in enumerate(tokens):
        lab = None
        # a word written with a hyphen after its prefix (ká-bonà: tokens ka, -bona) is the same form as kábonà:
        # the prefix token is read together with the stem token after it
        joined = i + 1 < len(tokens) and tokens[i + 1].startswith("-") and len(tokens[i + 1]) > 1 and not t.startswith("-")
        for pre, suf, w, tn in pats:
            if tn or (seg is not None and (pre or suf)):
                if lab is None:
                    S = seg or tones
                    lab = S.labels(exact[i]) if S is not None and exact is not None else set()
                    if joined and S is not None and exact is not None:
                        lab = lab | S.labels(exact[i] + exact[i + 1][1:])
            if tn:
                ok = tn in lab
            elif w:
                ok = exact[i] == w if exact is not None else fold(t) == fold(w)
            elif seg is not None and (not pre or pre in seg.pre) and (not suf or suf in seg.suf):
                ok = (t == "-" + suf and not pre) or ((not pre or has_prefix(lab, pre)) and (not suf or "-" + suf in lab
                      or (i + 1 < len(tokens) and tokens[i + 1] == "-" + suf)))
            elif pre and suf:
                ok = t.startswith(pre) and (t.endswith(suf) or (i + 1 < len(tokens) and tokens[i + 1] == "-" + suf))
            elif pre:
                ok = t.startswith(pre) and (len(t) > len(pre) + 1 or (t == pre and joined))
            else:
                ok = t == "-" + suf or (t.endswith(suf) and len(t) > len(suf) + 1)
            if ok:
                n += 1
                break
    return n


def required(G, code, ch):
    """{verse: Counter((paradigm, bundle used) -> verbs)} of the marked cells the store has an observed pattern for"""
    nt = BY_CODE[code][2] == "nt"
    toks = SC.cells_of(code, "nt" if nt else "ot")
    out = collections.defaultdict(collections.Counter)
    pats = {}
    for key, t in toks.items():
        c, v = int(key[2:5]), int(key[5:8])          # MACULA keys, both testaments: book, chapter, verse, word
        if c != ch:
            continue
        for par, bundle in t.cells:
            if par not in VA.VERB_PARADIGMS or not VA.marked(par, bundle):
                continue
            ce, used = VA.store_cell(G, par, bundle)
            if ce and ce.get("status") in ("observed", "decided") and not ce.get("gap") and patterns(ce):
                out[v][(par, used)] += 1
                pats[(par, used)] = patterns(ce)
    return out, pats


def check(P, G, path):
    """per cell: [verses required, verses passed], and the verses that miss a cell"""
    code, ch = os.path.basename(path)[:3], int(os.path.basename(path)[3:6])
    return check_text(P, G, code, ch, LT.verses_of(path))


def check_text(P, G, code, ch, text):
    """check() on {(chapter, verse): text}"""
    S, T = view(P), tone_view(P)
    req, pats = required(G, code, ch)
    res = collections.defaultdict(lambda: [0, 0, 0, 0])     # verses needing, passing; verses not needing, with it
    miss = []
    allpats = dict(pats)
    for (c_, v), t in text.items():                          # the pattern where the source has no such verb
        if c_ != ch:
            continue
        toks, ex = P.tok.tokens(t), P.tok.tokens(t, exact=True)
        for cell, ps in allpats.items():
            if not req.get(v, {}).get(cell):
                res[cell][2] += 1; res[cell][3] += carries(toks, ps, ex, S, T) > 0
    for v, cells in sorted(req.items()):
        if (ch, v) not in text:
            continue
        toks, ex = P.tok.tokens(text[(ch, v)]), P.tok.tokens(text[(ch, v)], exact=True)
        for cell, n in cells.items():
            ok = carries(toks, pats[cell], ex, S, T) >= n
            res[cell][0] += 1; res[cell][1] += ok
            if not ok:
                miss.append((f"{code.upper()} {ch}:{v}", cell, n, pats[cell]))
    return res, miss


def check_tagged(P, G, path):
    """word level, for a tagged draft (<code>NNN.tagged, scripts/full_align.py): per source verb of a marked cell, do
    the target words tagged with it carry the pattern; the background is the pattern on the words tagged with the
    paradigm's unmarked verbs (3rd singular, positive). Same result shape as check()."""
    import full_align as F
    code, ch = os.path.basename(path)[:3], int(os.path.basename(path)[3:6])
    nt = BY_CODE[code][2] == "nt"
    cells = SC.cells_of(code, "nt" if nt else "ot")
    text = F.ADDED.sub("", open(path, encoding="utf-8").read())
    parts = re.split(r"(?<![\w>.])v(\d+)(?=\s)", text)
    res = collections.defaultdict(lambda: [0, 0, 0, 0])
    miss, pats, unmarked = [], {}, collections.defaultdict(list)    # paradigm -> token lists of its unmarked verbs
    S, T = view(P), tone_view(P)
    for i in range(1, len(parts) - 1, 2):
        v, body = int(parts[i]), parts[i + 1]
        ref = f"{code.upper()} {ch}:{v}"
        num = {n: keys for n, _, _, keys in F.numbering(code.upper(), ref)}
        words = collections.defaultdict(list)            # source key -> the target tokens of the words tagged with it
        vtext = re.sub(r"\^\d+(?:,\d+)*", "", body)         # a free word may be tagged with the source's particle
        vtoks = (P.tok.tokens(vtext), P.tok.tokens(vtext, exact=True))
        for w, ns in re.findall(r"(\S+?)\^(\d+(?:,\d+)*)", body):
            toks = (P.tok.tokens(w), P.tok.tokens(w, exact=True))
            for n in ns.split(","):
                for k in num.get(int(n), []):
                    words[k].append(toks)
        for k, tl in words.items():
            t = cells.get(k)
            if not t:
                continue
            toks = ([x for tt in tl for x in tt[0]], [x for tt in tl for x in tt[1]])
            for par, bundle in t.cells:
                if par not in VA.VERB_PARADIGMS:
                    continue
                if VA.marked(par, bundle):
                    ce, used = VA.store_cell(G, par, bundle)
                    if not (ce and ce.get("status") in ("observed", "decided") and not ce.get("gap") and patterns(ce)):
                        continue
                    pats[(par, used)] = ps = patterns(ce)
                    ok = (carries(toks[0], [p for p in ps if not p[2]], toks[1], S, T) > 0
                          or carries(vtoks[0], [p for p in ps if p[2]], vtoks[1]) > 0)
                    res[(par, used)][0] += 1; res[(par, used)][1] += ok
                    if not ok:
                        miss.append((ref, (par, used), 1, pats[(par, used)]))
                else:
                    unmarked[par].append((toks, vtoks))
    for cell, ps in pats.items():                        # the background: the pattern on the unmarked verbs' words
        tl = unmarked.get(cell[0], [])
        aff, free = [p for p in ps if not p[2]], [p for p in ps if p[2]]
        res[cell][2] = len(tl)
        res[cell][3] = sum(carries(t[0], aff, t[1], S, T) > 0 or carries(vt[0], free, vt[1]) > 0 for t, vt in tl)
    return res, miss


def human_rates(P, G, testament="ot"):
    """per cell: [verses required, passed, not required, with the pattern anyway] in the style corpus's OT chapters
    (or NT: testament "nt"; verse level): the human ceiling and its background"""
    by = collections.defaultdict(dict)
    for _, code, (c, v), _, t in P.corpus():
        if BY_CODE[code][2] == testament:
            by[(code, c)][(c, v)] = t
    out = collections.defaultdict(lambda: [0, 0, 0, 0])
    for (code, c), text in by.items():
        for cell, x in check_text(P, G, code, c, text)[0].items():
            for i in range(4):
                out[cell][i] += x[i]
    return out


def book_review(pname, code, ch, margin=0.2, min_n=5, min_human=10):
    """REVIEW lines for the drafting loop (scripts/chapter_check.py): a cell the book's drafts so far (chapters up to
    ch, verse level) mark clearly less often than the human OT of the style corpus does (by more than margin), with
    this chapter's verses that miss it. A verb the human text leaves unmarked as often is no flag: the store's pattern
    is how a cell is marked, not that it always is. [] without an OT in the corpus or observed verb cells in the store."""
    P, G = LT.Project(pname), grammar.load(pname)
    if not G.cells:
        return []
    hum = human_rates(P, G)
    if not hum:
        return []
    import glob
    from project import project_dir
    tot, misses = collections.defaultdict(lambda: [0, 0, 0, 0]), []
    for f in sorted(glob.glob(os.path.join(project_dir(pname), code, f"{code}[0-9][0-9][0-9].txt"))):
        c = int(os.path.basename(f)[3:6])
        if c > ch:
            continue
        r, m = check(P, G, f)
        for cell, x in r.items():
            for i in range(4):
                tot[cell][i] += x[i]
        if c == ch:
            misses += m
    out = []
    for cell, (n, k, nb, kb) in tot.items():
        hn, hk, hnb, hkb = hum.get(cell, (0, 0, 0, 0))
        if (n < min_n or hn < min_human or (nb and kb / nb > 0.5) or (hnb and hkb / hnb > 0.5)
                or k / n >= hk / hn - margin):            # the pattern common anyway, on either side: can't be judged
            continue
        vs = [ref.split()[-1] for ref, c, _, _ in misses if c == cell]
        out.append(f"cell {cell[0]} {cell[1]} ({show(VA.store_cell(G, *cell)[0])}): the book's drafts so far mark it in "
                   f"{k}/{n} verses, the human OT in {hk}/{hn} ({hk / hn:.0%})"
                   + (f"; here without it: {', '.join(vs)}" if vs else ""))
    return out


def binding_cells(P, G, lift=0.25, min_n=10):
    """the cells a binding project (project.yaml `pack_grammar: binding`) must mark: those the style corpus's human OT
    marks clearly more often where the source has such a verb than where it hasn't (by at least `lift`, verse level).
    A cell whose pattern the human text has about as often anyway (a common prefix) is no rule. {cell: pattern}"""
    out = {}
    for cell, (n, k, nb, kb) in human_rates(P, G).items():
        if n >= min_n and nb and k / n - kb / nb >= lift:
            ce = VA.store_cell(G, *cell)[0]
            if ce and patterns(ce):
                out[cell] = show(ce)
    return out


def binding_list(pname, code, ch):
    """[(verse, source word, gloss, cell, pattern)]: the chapter's verbs of the binding cells, for the chapter prompt"""
    import sqlite3
    P, G = LT.Project(pname), grammar.load(pname)
    cells = binding_cells(P, G)
    if not cells:
        return []
    nt = BY_CODE[code][2] == "nt"
    db = sqlite3.connect(os.path.join(ROOT, "orig", "grc.sqlite" if nt else "heb.sqlite"))
    toks = SC.cells_of(code.upper(), "nt" if nt else "ot")
    out = []
    for key, v, gloss in db.execute("select key, v, gloss from tokens where book = ? and ch = ? order by key",
                                    (code.upper(), ch)):
        t = toks.get(key)
        for par, bundle in (t.cells if t else []):
            if par in VA.VERB_PARADIGMS and VA.marked(par, bundle):
                used = VA.store_cell(G, par, bundle)[1]
                if (par, used) in cells:
                    out.append((v, t.text, (gloss or "").replace(".", " "), (par, used), cells[(par, used)]))
    return out


def binding_fix(pname, code, ch):
    """FIX lines for chapter_check.py: in a binding project, a verb of a binding cell whose tagged words lack the
    pattern, unless the chapter's notes have a line `unmarked <ch>:<v> ...` saying why"""
    from project import project_dir
    import modes
    if modes.pack_grammar(pname) != "binding":
        return []
    d = os.path.join(project_dir(pname), code)
    tg = os.path.join(d, f"{code}{ch:03d}.tagged")
    if not os.path.exists(tg):
        return []
    P, G = LT.Project(pname), grammar.load(pname)
    cells = binding_cells(P, G)
    nf = os.path.join(d, f"{code}{ch:03d}_notes.md")
    notes = open(nf, encoding="utf-8").read() if os.path.exists(nf) else ""
    explained = set(re.findall(r"unmarked\W+(\d+:\d+)", notes, re.I))
    out, seen = [], set()
    for ref, cell, _, _ in check_tagged(P, G, tg)[1]:
        cv = ref.split()[-1]
        if cell in cells and cv not in explained and (cv, cell) not in seen:
            seen.add((cv, cell))
            out.append(f"verb marking {ref}: {cell[1]} ({cells[cell]}): the word tagged with the verb lacks it: mark it, "
                       f"or say why in the notes in a line `unmarked {cv} {cell[1]}: <reason>`")
    return out


def unmarked_notes(pname):
    """{bundle: [(chapter file, ch:v, reason, [the *italic* words it cites])]}: the `unmarked` lines of the project's
    notes, where a drafting agent said why a verb of a binding cell carries no mark: the candidates for the store"""
    import glob
    from project import project_dir
    out = collections.defaultdict(list)
    for nf in sorted(glob.glob(os.path.join(project_dir(pname), "*", "*_notes.md"))):
        for m in re.finditer(r"^\W*unmarked\W+(\d+:\d+)\s+([\w.]+):\s*(.*)$", open(nf, encoding="utf-8").read(), re.M | re.I):
            out[m[2]].append((os.path.basename(nf)[:6], m[1], m[3], [w for w in re.findall(r"\*([^*\s][^*]*?)\*", m[3]) if " " not in w]))
    return out


def try_forms(P, G, cell, forms, min_gain=0.01):
    """does each candidate form (a free word, `mbaín`, or an affix, `-eav`) help the cell? Per testament of the style
    corpus: the human pass rate and background (human_rates) with the cell's patterns as they are, with each form
    added alone, and with the forms kept. A form is kept when the lift (pass rate minus background) rises by at least
    `min_gain` in every testament with at least 10 verses of the cell. [(form, {testament: (before, after)}, kept)],
    the figures of the kept set"""
    ce = VA.store_cell(G, *cell)[0]
    if not ce:
        raise SystemExit(f"no cell {cell[0]} {cell[1]} in the store")
    alts = [x for x in ce.get("alternatives", []) if x.get("value") not in forms]   # a form tried again: from without it
    saved = list(ce.get("alternatives", []))

    def lift(extra, tm):
        ce["alternatives"] = alts + [{"value": f} for f in extra]
        try:
            n, k, nb, kb = human_rates(P, G, tm).get(cell, [0, 0, 0, 0])
        finally:
            ce["alternatives"] = saved
        return (n, k, nb, kb, (k / n if n else 0) - (kb / nb if nb else 0))

    tms = [tm for tm in ("ot", "nt") if lift([], tm)[0] >= 10]
    base = {tm: lift([], tm) for tm in tms}
    res = []
    for f in forms:
        r = {tm: (base[tm], lift([f], tm)) for tm in tms}
        res.append((f, r, bool(tms) and all(a[4] - b[4] >= min_gain for b, a in r.values())))
    kept = [f for f, _, k in res if k]
    return res, ({tm: (base[tm], lift(kept, tm)) for tm in tms} if kept else {})


METHOD = "cell_check 2"   # the checking method's version: a change to the matching bumps it, and retest reruns


def write_tried(f, G, cell, res, by, where=None):
    """the result into the store: kept forms as alternatives of the cell (method `tested`; a form a rerun no longer
    keeps is taken out), and one claim per form tried, kept or not (verdict confirmed or contradicted), so that no later
    agent tries it again unseen. Each claim records its `rerun` command and its `basis` (grammar.basis): when the store
    settings it depended on change, `grammar.py retest` reruns it"""
    import datetime, json
    d = json.load(open(f, encoding="utf-8"))
    ce0 = VA.store_cell(G, *cell)[0]
    affixes = show({"value": ce0.get("value"), "alternatives": [x for x in ce0.get("alternatives", [])
                                                                if not free_form(x.get("value")) and x.get("method") != "tested"]})
    today = datetime.date.today().isoformat()
    fig = lambda r: "; ".join(f"{tm.upper()}: pass {b[1]}/{b[0]} -> {a[1]}/{a[0]}, background {b[3]}/{b[2]} -> "
                              f"{a[3]}/{a[2]}, lift {b[4]:+.2f} -> {a[4]:+.2f}" for tm, (b, a) in r.items())
    cid = f"c:{cell[0]}:{cell[1].lower()}"
    for e in d["entries"]:
        if e.get("id") == cid:
            tried = {form for form, _, _ in res}
            e["alternatives"] = [x for x in e.get("alternatives", []) if x.get("value") not in tried or x.get("method") != "tested"]
            have = {x.get("value") for x in e["alternatives"]}
            for form, r, k in res:
                if k and form not in have:
                    e["alternatives"].append({"value": form, "n": sum(a[1] - b[1] for b, a in r.values()), "method": "tested"})
    ids = {e.get("id") for e in d["entries"]}
    for form, r, k in res:
        e = {"id": f"claim:{cell[0]}.{cell[1].lower()}.{form.strip('-')}", "kind": "claim",
             "value": f"{form} marks {cell[1]} ({cell[0]}) where the human translation has none of {affixes} on the verb",
             "area": cell[0], "source": "drafting agents' unmarked notes", "tests": ["corpus"], "figures": fig(r),
             "verdict": "confirmed" if k else "contradicted",
             "next": "kept in the cell's alternatives" if k else "not added: no gain over the background",
             "confidence": "medium" if k else "low", "method": "corpus-derived", "by": by, "date": today,
             "status": "observed", "rerun": ["cell_check.py", "try", cell[0], cell[1], form], "rerun_method": METHOD}
        old = next((x for x in d["entries"] if x.get("id") == e["id"]), None)
        if old and old.get("source"):
            e["source"] = old["source"]
        if e["id"] in ids:
            d["entries"] = [e if x.get("id") == e["id"] else x for x in d["entries"]]
        else:
            d["entries"].append(e)
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(f, "a").write("\n")
    b = grammar.basis(where or os.path.dirname(f), cell, METHOD)   # after the write: the store as the test now leaves it
    for e in d["entries"]:
        if e.get("rerun", [None])[:4] == ["cell_check.py", "try", cell[0], cell[1]] and e["rerun"][4] in {x for x, _, _ in res}:
            e["basis"], e["basis_corpus"] = b, grammar.corpus(where) if where else None
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(f, "a").write("\n")
    return f


def show(ce):
    return " / ".join(tn or w or (p + "-" if p else "") + ("…" if p and sf else "") + ("-" + sf if sf else "")
                      for p, sf, w, tn in patterns(ce))


def main(a):
    if len(a) > 1 and a[1] == "unmarked":
        for b, rows in sorted(unmarked_notes(a[0]).items()):
            words = collections.Counter(w for *_, ws in rows for w in ws)
            print(f"{b}: {len(rows)} unmarked; words cited: " + (", ".join(f"{w} ({n})" for w, n in words.most_common()) or "none"))
            for ch, cv, why, _ in rows:
                print(f"  {ch} {cv}: {why}")
        return
    if len(a) > 4 and a[1] == "try":
        P, G = LT.Project(a[0]), grammar.load(a[0])
        cell = (a[2], a[3])
        forms = [x for i, x in enumerate(a[4:], 4) if not x.startswith("--") and a[i - 1] != "--by"]
        res, together = try_forms(P, G, cell, forms)
        fig = lambda b, x: f"pass {x[1]}/{x[0]} ({x[1] / max(1, x[0]):.0%}), background {x[3]}/{x[2]} ({x[3] / max(1, x[2]):.0%}), lift {b[4]:+.2f} -> {x[4]:+.2f}"
        for form, r, k in res:
            print(f"{form}: " + ("KEEP" if k else "no gain") + "".join(f"\n  {tm.upper()} {fig(b, x)}" for tm, (b, x) in r.items()))
        if together:
            print("kept together:" + "".join(f"\n  {tm.upper()} {fig(b, x)}" for tm, (b, x) in together.items()))
        if "--write" in a:
            by = a[a.index("--by") + 1] if "--by" in a else "script:cell_check.py"
            from project import project_dir
            f = os.path.join(project_dir(a[0]), "profile", "observations.json")
            print("written:", os.path.relpath(write_tried(f, G, cell, res, by, a[0]), ROOT))
        return
    files = [x for i, x in enumerate(a[1:], 1) if not x.startswith("--") and a[i - 1] not in ("--human", "--min-ceiling")]
    if not a or not files:
        print(__doc__); sys.exit(2)
    P, G = LT.Project(a[0]), grammar.load(a[0])
    human = a[a.index("--human") + 1] if "--human" in a else None
    floor = float(a[a.index("--min-ceiling") + 1]) if "--min-ceiling" in a else 0.5
    tot, hum, misses = collections.defaultdict(lambda: [0, 0, 0, 0]), collections.defaultdict(lambda: [0, 0]), []
    for f in files:
        tg = f[:-4] + ".tagged" if f.endswith(".txt") else f
        word = "--verse" not in a and tg.endswith(".tagged") and os.path.exists(tg)
        r, m = check_tagged(P, G, tg) if word else check(P, G, f)
        for c, x in r.items():
            for i in range(4):
                tot[c][i] += x[i]
        misses += m
        hf = os.path.join(human, os.path.basename(f)) if human else None
        if hf and os.path.exists(hf):
            for c, x in check(P, G, hf)[0].items():
                hum[c][0] += x[0]; hum[c][1] += x[1]
    base = lambda c: tot[c][3] / tot[c][2] if tot[c][2] else 0.0
    judged = {c for c in tot if tot[c][0] and (not human or (hum[c][0] and hum[c][1] / hum[c][0] >= floor))
              and base(c) <= 0.5}
    word = any(f.endswith(".txt") and os.path.exists(f[:-4] + ".tagged") for f in files) and "--verse" not in a
    how = ("word level: the words tagged with each verb; background = the pattern on the unmarked verbs' words" if word
           else "verse level; background = the pattern in verses with no such verb")
    print(f"{len(files)} files ({how}); cells the store has an observed pattern for"
          + (f" (judged: human pass rate >= {floor:.0%})" if human else ""))
    for c in sorted((c for c in tot if tot[c][0]), key=lambda c: -tot[c][0]):
        n, k = tot[c][:2]
        h = f"; human {hum[c][1]}/{hum[c][0]} ({hum[c][1] / hum[c][0]:.0%})" if hum[c][0] else ""
        print(f"  {c[0]} {c[1]:10} {show(VA.store_cell(G, *c)[0]):12}"
              f" draft {k}/{n} ({k / n:.0%}){h}; background {base(c):.0%}"
              + ("" if c in judged else "  (not judged: " + ("the pattern is common anyway" if base(c) > 0.5 else
                                                             "the human text rarely shows it") + ")"))
    jn = sum(tot[c][0] for c in judged); jk = sum(tot[c][1] for c in judged)
    jh = sum(hum[c][0] for c in judged); jhk = sum(hum[c][1] for c in judged)
    print(f"judged cells: draft {jk}/{jn} ({jk / max(1, jn):.0%})" + (f", human {jhk}/{jh} ({jhk / max(1, jh):.0%})" if human else ""))
    if "--list" in a:
        for ref, c, n, p in misses:
            if c in judged:
                print(f"REVIEW {ref}: {c[0]} {c[1]}: {n} verb(s), the draft has no {show(VA.store_cell(G, *c)[0])}")


if __name__ == "__main__":
    main(sys.argv[1:])
