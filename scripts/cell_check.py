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

Usage: python3 scripts/cell_check.py <project> <chapter file> ... [--list] [--verse] [--min-ceiling R]
  --list           the verses that miss a cell (REVIEW lines), for a draft
  --min-ceiling R  with a human file given as --human DIR: only cells whose human pass rate is at least R (default 0.5)
  --human DIR      the human translation's folder (files named as the drafts): its pass rate per cell beside the draft's
"""
import collections, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import grammar  # noqa: E402
import langtools as LT  # noqa: E402
import source_cells as SC  # noqa: E402
import verse_analysis as VA  # noqa: E402
from books import BY_CODE  # noqa: E402


def patterns(ce):
    """(prefix, suffix) pairs of a cell entry: its value and its alternatives of two letters or more"""
    out = []
    alts = [a.get("value") for a in ce.get("alternatives", [])]
    for v in [ce.get("value")] + alts:
        pre, suf = VA.parts(v)
        if (pre or suf) and (v == ce.get("value") or len(pre + suf) >= 2):    # a one-letter alternative passes anything
            out.append((pre, suf))
    return out


def carries(tokens, pats):
    """the number of tokens that carry one of the patterns"""
    n = 0
    for i, t in enumerate(tokens):
        for pre, suf in pats:
            if pre and suf:
                ok = t.startswith(pre) and (t.endswith(suf) or (i + 1 < len(tokens) and tokens[i + 1] == "-" + suf))
            elif pre:
                ok = t.startswith(pre) and len(t) > len(pre) + 1
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
    req, pats = required(G, code, ch)
    res = collections.defaultdict(lambda: [0, 0, 0, 0])     # verses needing, passing; verses not needing, with it
    miss = []
    allpats = dict(pats)
    for (c_, v), t in text.items():                          # the pattern where the source has no such verb
        if c_ != ch:
            continue
        toks = P.tok.tokens(t)
        for cell, ps in allpats.items():
            if not req.get(v, {}).get(cell):
                res[cell][2] += 1; res[cell][3] += carries(toks, ps) > 0
    for v, cells in sorted(req.items()):
        if (ch, v) not in text:
            continue
        toks = P.tok.tokens(text[(ch, v)])
        for cell, n in cells.items():
            ok = carries(toks, pats[cell]) >= n
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
    for i in range(1, len(parts) - 1, 2):
        v, body = int(parts[i]), parts[i + 1]
        ref = f"{code.upper()} {ch}:{v}"
        num = {n: keys for n, _, _, keys in F.numbering(code.upper(), ref)}
        words = collections.defaultdict(list)            # source key -> the target tokens of the words tagged with it
        for w, ns in re.findall(r"(\S+?)\^(\d+(?:,\d+)*)", body):
            toks = P.tok.tokens(w)
            for n in ns.split(","):
                for k in num.get(int(n), []):
                    words[k].append(toks)
        for k, tl in words.items():
            t = cells.get(k)
            if not t:
                continue
            toks = [x for tt in tl for x in tt]
            for par, bundle in t.cells:
                if par not in VA.VERB_PARADIGMS:
                    continue
                if VA.marked(par, bundle):
                    ce, used = VA.store_cell(G, par, bundle)
                    if not (ce and ce.get("status") in ("observed", "decided") and not ce.get("gap") and patterns(ce)):
                        continue
                    pats[(par, used)] = patterns(ce)
                    ok = carries(toks, pats[(par, used)]) > 0
                    res[(par, used)][0] += 1; res[(par, used)][1] += ok
                    if not ok:
                        miss.append((ref, (par, used), 1, pats[(par, used)]))
                else:
                    unmarked[par].append(toks)
    for cell, ps in pats.items():                        # the background: the pattern on the unmarked verbs' words
        tl = unmarked.get(cell[0], [])
        res[cell][2] = len(tl); res[cell][3] = sum(carries(t, ps) > 0 for t in tl)
    return res, miss


def human_rates(P, G):
    """per cell: [verses required, passed, not required, with the pattern anyway] in the style corpus's OT chapters
    (verse level): the human ceiling and its background"""
    by = collections.defaultdict(dict)
    for _, code, (c, v), _, t in P.corpus():
        if BY_CODE[code][2] == "ot":
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


def show(ce):
    return " / ".join((p + "-" if p else "") + ("…" if p and s else "") + ("-" + s if s else "") for p, s in patterns(ce))


def main(a):
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
