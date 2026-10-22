#!/usr/bin/env python3
"""Verse pairs for the second-draft model: a source Bible, the style corpus as target, as Scripture Forge pairs a
major-language Bible with the project. The source is the project's `nllb_source` (scripts/nllb/source.py): by default
the Vamvas Bible in modern Greek (import/CC0/ell/vamvas/; closer to the original than English), or `bsb`, the
assisting translation in English (--source overrides it). The pairs hold edition text, so they stay in the
project's git-ignored `_eval/local/nllb/data/` (and on the machine that trains; never published for a non-free edition).

Splits: test = the held-out book(s) (--test rut,jon; none by default: then the model is trained on everything, as for
triage), val = 250 random verses of the rest, train = the rest (--nt-only: NT verses only in train). Files:
<out>/{train,val,test}.{src,trg,vref} and <out>/meta.json (the source and its NLLB code, the NLLB language code of the
target, and the language its new code starts from, read by train.py and draft.py). A verse the source lacks drops out.

The target side as the store says (analysis.model_text, scripts/nllb/model_text.py): the text as written, or each word as
its parts (prefix, stem, grammatical tone, suffix, lexical tone codes); the spec goes into meta.json, so training and
drafting decode as the data was built.

Usage: python3 scripts/nllb/data.py <project> [--source vamvas|bsb|<edition>] [--test rut[,jon]] [--nt-only]
                                    [--trg-code xxx_Latn] [--init-lang tpi_Latn] [--model-text words|morphs] [--out DIR]
  --model-text overrides the store's analysis.model_text (for a comparison)
  --trg-code  default: the project's language code (ISO 639-3, first part) + _Latn (dan_Latn is NLLB's own; a code NLLB
              lacks is added at training)
  --init-lang the NLLB language a new code starts from (default: the project's donor.nllb_init, else eng_Latn; better a
              related language: tpi_Latn for a language where Tok Pisin is the language of wider communication,
              deu_Latn for a German dialect)
"""
import json, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "nllb"))
import langtools as LT  # noqa: E402
from books import BY_CODE  # noqa: E402
from project import project_dir  # noqa: E402
import model_text as MT  # noqa: E402
from source import Source  # noqa: E402


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        raise SystemExit(__doc__)
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    P = LT.Project(a[0])
    test = set((opt("--test") or "").split(",")) - {""}
    out = opt("--out") or os.path.join(project_dir(a[0]), "_eval", "local", "nllb", "data")
    os.makedirs(out, exist_ok=True)
    src = Source(P, opt("--source"))
    rows = [(r[0], r[1], r[2], src.verse(r[1], *r[2]), r[4]) for r in P.corpus() if r[4].strip()]
    rows = [r for r in rows if r[3]]
    te = [r for r in rows if r[1] in test]
    rest = [r for r in rows if r[1] not in test]
    if "--nt-only" in a:
        rest = [r for r in rest if BY_CODE[r[1]][2] == "nt"]
    C, S = MT.codec_for(a[0], opt("--model-text"), P)
    random.Random(111).shuffle(rest)
    va, tr = rest[:250], rest[250:]
    for name, part in (("train", tr), ("val", va), ("test", te)):
        with open(f"{out}/{name}.src", "w", encoding="utf-8") as s, open(f"{out}/{name}.trg", "w", encoding="utf-8") as t, \
                open(f"{out}/{name}.vref", "w", encoding="utf-8") as v:
            for r in part:
                s.write(" ".join(r[3].split()) + "\n")
                t.write(C.encode(" ".join(r[4].split()), S) + "\n")
                v.write(r[0] + "\n")
    import lang as LG
    lang = LG.iso3(P) or str(P.p.get("language") or a[0].split("/")[0]).split("-")[0].lower()
    meta = {"project": a[0], "source": src.name, "src_code": src.code, "trg_code": opt("--trg-code") or f"{lang}_Latn", "init_lang": opt("--init-lang") or (P.p.get("donor") or {}).get("nllb_init") or "eng_Latn",
            "test": sorted(test), "nt_only": "--nt-only" in a, "model_text": C.spec}
    json.dump(meta, open(os.path.join(out, "meta.json"), "w", encoding="utf-8"), indent=1)
    print({n: len(p) for n, p in (("train", tr), ("val", va), ("test", te))}, f"{src.name} ({src.code}) ->", meta["trg_code"], "target as",
          C.spec["mode"], "->", out)


if __name__ == "__main__":
    main()
