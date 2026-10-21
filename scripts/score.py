#!/usr/bin/env python3
"""Score a draft chapter against a human translation of the same chapter (docs/onboarding.md).

For evaluation only: the reference must be kept from the drafting agents (a held-out book). chrF
(character n-grams 1-6, beta 2) over the chapter, on the project tokeniser's plain text (lower case,
ignored marks removed) and as written, and per verse with --verses; beside them chrF3 as SIL reports it
(sacrebleu's corpus_chrf: beta 3, whitespace removed, case and marks kept, counts summed over verses), so our
figures can be read beside Scripture Forge's. Two floors for comparison:
  - retrieval: for each verse, the target text of the corpus verse whose assisting text (BSB) is most like
    the verse's BSB (what copying the nearest known sentence gives); the scored book is left out;
  - lexical: the BSB verse word by word through the project's lexicon_eng.tsv (top rendering, English order).

Usage: python3 scripts/score.py <project> <draft> [--reference FILE] [--verses]
       The reference defaults to the chapter's file in the project's style_from editions (text/ or, for a
       quarantined book, quarantined/<code>/).
"""
import collections, glob, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import langtools as LT  # noqa: E402
import vrs  # noqa: E402
from books import BY_CODE  # noqa: E402


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    P, draft = LT.Project(a[0]), a[1]
    b = os.path.basename(draft)[:6] + ".txt"
    code = b[:3]
    if "--reference" in a:
        ref_file = a[a.index("--reference") + 1]
    else:
        hits = [f for d in P.text_dirs() for f in glob.glob(os.path.join(d, b))]
        hits += [f for e in P.editions for f in glob.glob(os.path.join(LT.ROOT, e["dir"], "quarantined", code, b))]
        if not hits:
            raise SystemExit(f"no reference {b} in the style_from editions; pass --reference FILE")
        ref_file = hits[0]
    ref, hyp = LT.verses_of(ref_file), LT.verses_of(draft)
    ot = BY_CODE[code][2] != "nt"
    eng = {}
    for k in ref:
        c, v = vrs.to_bsb(code, *k) if ot else k
        f = os.path.join(ROOT, P.assist_dir(code), f"{code}{c:03d}.txt")
        eng[k] = LT.verses_of(f).get((c, v), "") if os.path.exists(f) else ""
    rows = P.corpus(exclude={code})
    df = collections.Counter(t for r in rows for t in set(LT.eng_tokens(r[3])))
    lex = {}
    lf = os.path.join(P.learn, "lexicon_eng.tsv")
    if os.path.exists(lf):
        for l in open(lf, encoding="utf-8").read().splitlines()[1:]:
            s, t = l.split("\t")[:2]
            lex.setdefault(s, t)

    def retrieve(e):
        q = set(LT.eng_tokens(e))
        return max(rows, key=lambda r: sum(math.log(len(rows) / (1 + df[t])) for t in set(LT.eng_tokens(r[3])) if t in q))[4]

    def lexical(e):
        return " ".join(lex[t] for t in LT.eng_tokens(e) if t in lex and not lex[t].startswith("-"))

    plain = lambda s: P.tok.plain(s)
    out = {"draft": [], "retrieval": [], "lexical": []}
    per = []
    for k in sorted(ref):
        r, h, e = ref[k], hyp.get(k, ""), eng[k]
        out["draft"].append((h, r)); out["retrieval"].append((retrieve(e), r))
        if lex:
            out["lexical"].append((lexical(e), r))
        per.append((k, LT.chrf(plain(h), plain(r))))
    for name, pairs in out.items():
        if not pairs:
            continue
        H, R = " ".join(plain(h) for h, _ in pairs), " ".join(plain(r) for _, r in pairs)
        Hw, Rw = " ".join(P.tok.exact(h) for h, _ in pairs), " ".join(P.tok.exact(r) for _, r in pairs)
        c3 = LT.chrf3([h for h, _ in pairs], [r for _, r in pairs])
        print(f"{name:10} chrF {LT.chrf(H, R):5.1f} (marks ignored)   {LT.chrf(Hw, Rw):5.1f} (as written)   chrF3 {c3:5.1f} (SIL's)")
    missing = [k for k in sorted(ref) if k not in hyp]
    print(f"verses: {len(ref)} in the reference, {len(missing)} missing in the draft {missing or ''}")
    if "--verses" in a:
        for k, s in per:
            print(f"  {k[0]}:{k[1]:<3} {s:5.1f}")


if __name__ == "__main__":
    main()
