#!/usr/bin/env python3
"""decide_text (morphs.py decide) on a synthetic store and corpus: a prefix z- confirmed on five stems that occur
often -> a split share above the minimum, a low tokens/type ratio and an exact decode -> morphs; the same corpus
without morph entries -> words; a corpus of few repeated words (high ratio) -> words. Run: python3
scripts/tests/test_decide_text.py (or pytest)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import decide_text, grammar, morphs  # noqa: E402
from nllb import model_text as MT  # noqa: E402

STEMS = "kabi tolu mesa nibo rako".split()
ENT = dict(id="m:z-", kind="morph", slot="prefix", form="z-", host="any", value="2PL", status="observed")
RARE = [f"w{i}" for i in range(400)]                 # many types: tokens per type low


def corpus():
    return [w for s in STEMS for w in (s, "z" + s) * 5] + RARE


def seg(toks):
    import collections
    return morphs.Segmenter(grammar.Grammar([ENT]), {}, {w: n for w, n in collections.Counter(toks).items() if n >= 2})


def codec():
    return MT.Codec({"mode": "morphs", "join": "+", "tone": "~", "written": "none", "marks": [], "vowels": "",
                     "codes": {}, "tones": {}})


def test_morphs():
    t = corpus()
    S = seg(t)
    f = decide_text.figures(t, S, morphs.affix_entries(grammar.Grammar([ENT])), codec())
    assert f["split_tokens"] == 25 / 450, f
    assert f["decode_bad"] == [], f["decode_bad"]
    assert f["forms_per_stem"] == 2.0, f
    t2 = [w for s in STEMS for w in (s, "z" + s) * 50] + RARE
    f2 = decide_text.figures(t2, seg(t2), morphs.affix_entries(grammar.Grammar([ENT])), codec())
    assert f2["split_tokens"] > decide_text.SPLIT_MIN and f2["ratio"] <= decide_text.RATIO_MAX, f2
    assert decide_text.suggest(f2)[0] == "morphs", decide_text.suggest(f2)


def test_words():
    t = corpus()
    f = decide_text.figures(t, None)
    assert decide_text.suggest(f) == ("words", "the store has no morph entries")
    t3 = [w for s in STEMS for w in (s, "z" + s) * 50]  # ten types only: ratio 50
    f3 = decide_text.figures(t3, seg(t3), morphs.affix_entries(grammar.Grammar([ENT])), codec())
    m, why = decide_text.suggest(f3)
    assert m == "words" and "tokens per type" in why, why


if __name__ == "__main__":
    test_morphs(); test_words(); print("ok")
