#!/usr/bin/env python3
"""Two cheap meaning checks for a draft chapter, no model: the verses a reviewer must look at in a rough pass (an NLLB
draft for a team), and useful on any draft.

- negation: the original's negations per verse (Hebrew: the WLC words tagged negative in orig/heb.sqlite; Greek: Louw-Nida
  69.2-69.3 in orig/grc.sqlite) against the project language's negation markers in the draft verse. The markers are learned
  from the style corpus: forms and word endings that occur almost only in verses whose English (the assisting translation)
  is negated. Flagged: the original negates and the draft has no marker ("missing"), or fewer markers than the original
  has negations ("fewer"); the draft has a marker where the original has none ("added", weaker: Hebrew and the language may
  negate in different places). In rough machine drafts a lost negation is a common major error.
  Markers need precision >= 0.6 (--strict: 0.7, which flags more verses, and more of the human translation's too); how
  much of the corpus's negated verses they cover is printed first. A human translation gets some flags as well: a flag
  asks for a look, it is not an error.
  A draft with a .align beside it (OT, scripts/full_align.py) also counts the original's negations its alignment links
  to a draft word, so a marker the corpus can't learn because it is also a common other word (Hebrew אל "do not", also
  "to") is no false "missing" flag; a negation the draft leaves unlinked is counted by the markers alone.
- English: word forms the corpus doesn't have but the assisting English does ("seven", "mules"): text the model copied
  from its English source instead of translating ("mules", Ps 32:9). Capitalised ones may be names spelled the English
  way; an English loanword the corpus has is not flagged.

Both report verse numbers and forms only (no corpus text), so the output may go into a review list. The markers and how
well they cover the corpus's negated verses are printed first (--markers shows them alone).

Usage: python3 scripts/rough_check.py <project> <chapter file> [...] [--markers] [--strict] [--no-added]
       (chapter files with vN markers, named <code>NNN.txt; Hebrew verse numbering in the OT)
"""
import collections, os, re, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import langtools as LT  # noqa: E402
from books import BY_CODE  # noqa: E402

ENG_NEG = re.compile(r"\b(?:not|no|never|nor|neither|none|nothing|nobody|cannot|can't|won't|don't|didn't|isn't|wasn't|"
                     r"aren't|weren't|shouldn't|wouldn't|couldn't|mustn't|hasn't|haven't|hadn't|doesn't)\b", re.I)


def source_negations(code, ch):
    """{verse: number of negations} in the original (Hebrew numbering in the OT)."""
    out = collections.Counter()
    if BY_CODE[code][2] == "nt":
        db = os.path.join(ROOT, "orig", "grc.sqlite")
        q = "select v from tokens where book=? and ch=? and (ln like '69.2%' or ln like '69.3%')"
    else:
        db = os.path.join(ROOT, "orig", "heb.sqlite")
        q = "select v from tokens where book=? and ch=? and morph like 'Tn%'"
    if not os.path.exists(db):
        raise SystemExit(f"{os.path.relpath(db, ROOT)} is missing: python3 scripts/setup.py --only src")
    for (v,) in sqlite3.connect(db).execute(q, (code.upper(), ch)):
        out[v] += 1
    return out


def aligned_negations(path):
    """{verse: number of the original's negations linked to a draft word} from the .align beside an OT draft; {} if none."""
    import full_align as FA
    b = os.path.basename(path)
    code, ch = b[:3], int(b[3:6])
    al = path[:-4] + ".align"
    if BY_CODE[code][2] != "ot" or not os.path.exists(al):
        return {}
    con = sqlite3.connect(os.path.join(ROOT, "orig", "heb.sqlite"))
    neg = {k for (k,) in con.execute("select key from tokens where book=? and ch=? and morph like 'Tn%'", (code.upper(), ch))}
    out = collections.Counter()
    for v, (main, fn, _) in FA.read_chapter(al)[1].items():
        for links, kind in ((main, "keys"), (fn, "fn_keys")):           # content and function tokens (אל is one)
            keys = FA.index(code.upper(), kind).get(f"{code.upper()} {ch}:{v}", [])
            for o, pos in FA.parse(links).items():
                if pos and o < len(keys) and keys[o]:
                    out[v] += sum(1 for k in keys[o].split("+") if k in neg)
    return out


USE_MORPHS = None       # True / False overrides the store's analysis.match (for comparisons)
_SEG = {}


def segmenter(P):
    """the morph view (scripts/morphs.py) when the store sets `analysis.match: morphs`, else None"""
    import json
    import morphs
    if P.name not in _SEG:
        f = os.path.join(P.profile, "observations.json")
        d = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
        _SEG[P.name] = (morphs.load(P.name, P), (d.get("analysis") or {}).get("match") == "morphs")
    S, on = _SEG[P.name]
    return S if (on if USE_MORPHS is None else USE_MORPHS) else None


def features(P, text):
    """The candidate negation markers of a verse: its word forms, the endings of their hyphen parts (2-4 characters,
    as '-ending') and their beginnings (as '^beginning-'), each both as written (every mark kept: a negation may differ from another form only by a tone mark) and
    plain; with the morph view also each word's morphs (as '~-eav', '~tone-proh': a negation that is a suffix or a tone
    pattern, not a word's last letters)."""
    out = set()
    S = segmenter(P)
    for w in P.tok.tokens(text, exact=True):
        if S is not None:
            out |= {"~" + m for m in S.labels(w)}
        for x in {w, P.tok.plain(w)}:
            out.add(x)
            for part in x.split("-")[1:] if "-" in x else [x]:
                for n in (2, 3, 4):
                    if len(part) > n + 1:
                        out.add("-" + part[-n:])
            # and the word's beginnings (2-4 characters, as 'beginning-'): a negation that is a verb prefix (Zinza
            # ti-/tii-: tiínkumanya, titukweésiga) is neither a word of its own nor an ending
            head = x.split("-")[0] if "-" in x else x
            for n in (2, 3, 4):
                if len(head) > n + 1:
                    out.add("^" + head[:n] + "-")
    return out


def learn_markers(P, min_n=15, min_prec=0.6):
    """Markers with precision >= min_prec (share of their verses whose English is negated) and >= min_n verses, chosen
    greedily to cover the negated verses. Returns (markers, coverage of negated corpus verses, number of negated verses)."""
    rows = P.corpus()
    neg = [bool(ENG_NEG.search(r[3])) for r in rows]
    feats = [features(P, r[4]) for r in rows]
    n_f, n_neg = collections.Counter(), collections.Counter()
    for fs, g in zip(feats, neg):
        for f in fs:
            n_f[f] += 1
            n_neg[f] += g
    negated = {i for i, g in enumerate(neg) if g}
    # word beginnings ('^ti-') only where words and endings leave the negated verses poorly covered (a language that
    # negates with a verb prefix, Zinza ti-): elsewhere they only add weak markers and false "added" flags
    for begin in (False, True):
        cand = {f for f in n_f if n_f[f] >= min_n and n_neg[f] / n_f[f] >= min_prec and (begin or not f.startswith("^"))}
        chosen, cov = _greedy(cand, feats, negated)
        if cov >= BEGIN_BELOW:
            break
    return chosen, cov, len(negated)


BEGIN_BELOW = 0.75   # coverage of the negated corpus verses under which word beginnings are learned too


def _greedy(cand, feats, negated):
    cand = set(cand)
    left, chosen = set(negated), []
    while True:
        # the marker that covers most verses still left; a tie by the form, so that the choice doesn't follow the
        # set's order (which changes with PYTHONHASHSEED)
        best = max(sorted(cand), key=lambda f: sum(1 for i in left if f in feats[i]), default=None)
        if best is None:
            break
        gain = {i for i in left if best in feats[i]}
        if len(gain) < max(3, len(negated) // 500):
            break
        chosen.append(best)
        left -= gain
        cand.discard(best)
    cov = 1 - len(left) / max(1, len(negated))
    return chosen, cov


def marker_count(P, text, markers):
    """How many words of the text carry a negation marker."""
    return sum(1 for w in P.tok.tokens(text, exact=True) if features(P, w) & markers)


def english_forms(P):
    """The word forms of the assisting translation, the whole Bible (reference/BSB, or MSB), not only the corpus's books."""
    import glob
    eng = set()
    for r in P.corpus():
        eng.update(LT.eng_tokens(r[3]))
    for d in {os.path.join(ROOT, P.assist_dir(c)) for c in ("gen", "mat")}:
        for f in glob.glob(os.path.join(d, "*.txt")):
            for t in LT.verses_of(f).values():
                eng.update(LT.eng_tokens(t))
    return eng


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        raise SystemExit(__doc__)
    P = LT.Project(a[0])
    files = [x for x in a[1:] if not x.startswith("--")]
    markers, cov, n_neg = learn_markers(P, min_prec=0.7 if "--strict" in a else 0.6)
    print(f"# negation markers ({len(markers)}, from {n_neg} corpus verses with English negation; they cover {cov:.0%}): "
          + ", ".join(markers))
    if "--markers" in a:
        return
    ms, eng = set(markers), english_forms(P)
    sp, store = P.spellings(), P.store_forms()
    for f in files:
        b = os.path.basename(f)
        code, ch = b[:3], int(b[3:6])
        src, linked = source_negations(code, ch), aligned_negations(f)
        flags = []
        for (c, v), text in sorted(LT.verses_of(f).items()):
            n_src, n_tgt = src.get(v, 0), max(marker_count(P, text, ms), linked.get(v, 0))
            if n_src and not n_tgt:
                flags.append((v, f"negation missing: the original negates {n_src}x, the draft has no negation marker"))
            elif n_src > n_tgt:
                flags.append((v, f"negation fewer: the original negates {n_src}x, the draft {n_tgt}x"))
            elif n_tgt and not n_src and "--no-added" not in a:
                flags.append((v, f"negation added? the draft has {n_tgt} marker(s), the original no negation"))
            leak = [w for w in P.tok.tokens(text, exact=True)
                    if w not in store and not sp.get(P.tok.plain(w)) and w.lower() in eng]
            if leak:
                flags.append((v, "English? not in the corpus but in the English: " + ", ".join(dict.fromkeys(leak))))
        print(f"\n## {code} {ch} ({os.path.relpath(f, ROOT) if f.startswith(ROOT) else f}): {len({v for v, _ in flags})} verses flagged")
        for v, msg in flags:
            print(f"{ch}:{v}  {msg}")


if __name__ == "__main__":
    main()
