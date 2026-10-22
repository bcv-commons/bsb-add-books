#!/usr/bin/env python3
"""Regression test: parts written with a hyphen (a morph's `written`: hyphen | both). A word with an internal hyphen is one
word with a boundary inside: a hyphen prefix is the whole first piece (x-stem), a hyphen suffix the whole last piece (a
clitic), the inside segmented as a word; grammatical tone is read on the whole word, across the hyphen; a "hyphen" part
never comes off a fused word; every word rebuilds and the model text decodes back exactly. Synthetic store, no project
files. Run: python3 scripts/tests/test_hyphen_words.py (or with pytest)."""
import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nllb"))
import morphs  # noqa: E402
import model_text  # noqa: E402

VOCAB = {w: 5 for w in "kalo kaloma tamu kamu sopi sopima -omu -sopi -ko ri rito lame".split()}
ORTH = {"ignore_marks": ["U+0300", "U+1DC4"],
        "tone": {"written": "marks", "marks": ["U+0300", "U+1DC4"], "vowels": "aeiou"}}


def store(hyphen=True):
    ms = [dict(id="m:ka-", slot="prefix", form="ka-", host="verb", value="3SG"),
          dict(id="m:-ma", slot="suffix", form="-ma", host="verb", value="PST"),
          dict(id="m:tone-proh", slot="tone", form="tone-proh", host="verb", value="PROH",
               tone_pattern=[{"at": "<-1", "mark": "U+0300"}, {"at": "-1", "mark": "U+1DC4"}])]
    if hyphen:
        ms += [dict(id="m:geto-", slot="prefix", form="geto-", host="verb", value="3SG", written="hyphen"),
               dict(id="m:ri-", slot="prefix", form="ri-", host="verb", value="1SG", written="hyphen"),
               dict(id="m:-ko", slot="suffix", form="-ko", host="any", value="LOC", written="hyphen")]
    return types.SimpleNamespace(morphs=ms, words=[])


def parts(S, w):
    return [(m.slot, m.form, m.text) for m in S.split(w)]


def run():
    S = morphs.Segmenter(store(), ORTH, VOCAB)
    off = morphs.Segmenter(store(False), ORTH, VOCAB)
    assert S.hyphen and not off.hyphen
    # the first piece is the pre-stem part, the inside is segmented as a word
    assert parts(S, "geto-sopima") == [("prefix", "geto-", "geto-"), ("stem", "sopi", "sopi"), ("suffix", "-ma", "ma")], \
        parts(S, "geto-sopima")
    # a clitic after a hyphen; both at once
    assert parts(S, "lame-ko") == [("stem", "lame", "lame"), ("suffix", "-ko", "-ko")], parts(S, "lame-ko")
    assert [m.form for m in S.split("geto-kalo-ko")][0] == "geto-" and S.split("geto-kalo-ko")[-1].form == "-ko"
    # a hyphen part never comes off a fused word (rito stays whole: ri- is written with a hyphen only)
    assert [m.slot for m in S.split("rito")] == ["stem"], parts(S, "rito")
    # the prohibitive across the hyphen: grave on the first piece, the rising on the last vowel of the whole word
    w = "rì-omu᷄"
    ms = S.split(w)
    assert any(m.slot == "tone" and m.form == "tone-proh" for m in ms), parts(S, w)
    assert ms[0].form == "ri-"
    # without hyphen parts the old behaviour: no tone across, no prefix from the piece
    assert all(m.form != "ri-" for m in off.split(w))
    # an unknown first piece and no clitic: segmented as before
    assert S.split("zumo-lame") == off.split("zumo-lame")
    for x in list(VOCAB) + ["geto-sopima", "lame-ko", "geto-kalo-ko", w, "rì-sopìma᷄", "zumo-lame", "Geto-Kalo"]:
        assert S.rebuild(S.split(x)) == morphs.unicodedata.normalize("NFC", x.lower()), x
    # the model text: the hyphen is kept inside its part (geto-+, +-ko); decoded back exactly
    spec = {"mode": "morphs", "join": "+", "tone": "~", "written": "marks", "marks": ["U+0300", "U+1DC4"],
            "vowels": "aeiou", "codes": {"U+0300": "L", "U+1DC4": "MH"},
            "tones": {"PROH": {"form": "tone-proh", "pattern": [["<-1", "U+0300"], ["-1", "U+1DC4"]]}}}
    C = model_text.Codec(spec)
    C.names = {"lame"}
    line = "Geto-sopima lame-ko rì-omu᷄, zumo-lame geto-kalo-ko."
    e = C.encode(line, S)
    assert "geto-+" in e.lower() and "+-ko" in e and "~PROH" in e, e
    assert C.decode(e) == model_text.NFC(line), (e, C.decode(e))
    assert "lame +-ko" in e, e                    # a name stays whole; its clitic comes off


def test_hyphen_words():
    run()


if __name__ == "__main__":
    run()
    print("ok")
