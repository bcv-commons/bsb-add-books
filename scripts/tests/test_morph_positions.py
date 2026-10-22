#!/usr/bin/env python3
"""Regression test: a `position` on some affixes (an affix chain) must not stop the store's other affixes from coming off.
Synthetic store and vocabulary, no project files. Run: python3 scripts/tests/test_morph_positions.py (or with pytest)."""
import collections, os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import morphs  # noqa: E402

VOCAB = {w: 5 for w in """kasolu solu kabemi bemi rasolu rabemi ramitu mitu katiro tiro
         mokasolu mosolu mokabemi mobemi rapelo pelo kapelo""".split()}
# the NT's word classes (Greek class -> linked tokens, "" all): verbs and nouns
CLASSES = {w: collections.Counter({"": 4, "verb": 4}) for w in ("kasolu", "solu", "mokasolu", "mosolu", "kabemi", "bemi",
                                                                   "mokabemi", "mobemi", "katiro", "tiro")}
CLASSES.update({w: collections.Counter({"": 4, "noun": 4}) for w in ("rasolu", "rabemi", "ramitu", "mitu", "rapelo",
                                                                        "pelo", "kapelo")})


def store(with_position):
    ms = [dict(id="m:ka-", slot="prefix", form="ka-", host="verb", value="PST"),
          dict(id="m:ra-", slot="prefix", form="ra-", host="poss", value="1SG.POSS"),
          dict(id="m:mo-", slot="prefix", form="mo-", host="verb", value="NEG")]
    if with_position:                       # switch the chain on for mo- (and ka- after it) only
        ms[2]["position"] = 1
    return types.SimpleNamespace(morphs=ms)


def parts(S, w):
    return [(m.slot, m.form, m.position) for m in S.split(w) if m.slot != "stem"]


def run():
    off = morphs.Segmenter(store(False), {}, VOCAB, CLASSES)
    on = morphs.Segmenter(store(True), {}, VOCAB, CLASSES)
    assert on.chain and not off.chain
    for w in ("rasolu", "rabemi", "ramitu", "rapelo", "kasolu", "kabemi"):
        # an affix without a position comes off with the position switched on as it does without: any host, position 0
        assert parts(off, w), (w, "baseline")
        assert parts(on, w) == [(s, f, 0) for s, f, _ in parts(off, w)], (w, parts(on, w), parts(off, w))
    assert parts(on, "mosolu") == [("prefix", "mo-", 1)], parts(on, "mosolu")
    for w in VOCAB:                          # every word rebuilt exactly
        assert on.rebuild(on.split(w)) == w and off.rebuild(off.split(w)) == w, w
    split_off = sum(bool(parts(off, w)) for w in VOCAB)
    split_on = sum(bool(parts(on, w)) for w in VOCAB)
    assert split_on >= split_off, (split_on, split_off)


def test_positions_keep_other_affixes():
    run()


if __name__ == "__main__":
    run()
    print("ok")
