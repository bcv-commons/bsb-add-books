#!/usr/bin/env python3
"""Protected words (store kind `word`): the morph view leaves them whole, they are no evidence for a split, and the
validator checks the field. Synthetic store and vocabulary. Run: python3 scripts/tests/test_protected_words.py (or pytest)."""
import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import grammar, morphs  # noqa: E402

VOCAB = {w: 5 for w in "zundo undo zabelo abelo zomitu omitu zelani elani zakari akari".split()}
M = [dict(id="m:z-", kind="morph", slot="prefix", form="z-", host="verb", value="2PL", status="observed")]
W = [dict(id="w:zundo", kind="word", form="zundo", value="WORD", status="observed"),
     dict(id="w:zelani", kind="word", form="Zelani", value="NAME", status="observed")]


def split(G, w):
    S = morphs.Segmenter(G, {}, VOCAB)
    return [(m.slot, m.form) for m in S.split(w)]


def test_words_stay_whole():
    bare = grammar.Grammar(M)
    assert ("prefix", "z") in split(bare, "zundo") or ("prefix", "z-") in split(bare, "zundo"), split(bare, "zundo")
    G = grammar.Grammar(M + W)
    assert [x[0] for x in split(G, "zundo")] == ["stem"], split(G, "zundo")
    assert [x[0] for x in split(G, "Zelani")] == ["stem"]
    assert any(x[0] == "prefix" for x in split(G, "zabelo")), split(G, "zabelo")   # the prefix still comes off others


def test_superseded_word_is_not_live():
    G = grammar.Grammar(M + [dict(W[0], status="superseded")])
    assert G.words == []


def test_validator_form():
    import json, subprocess, tempfile
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "text"))
    open(os.path.join(d, "text", "jhn001.txt"), "w").write("v1 Zundo abelo zabelo.\nv2 Omitu.\n")
    base = dict(confidence="high", method="corpus-derived", by="script:morphs.py audit", date="2026-10-22")
    es = [dict(W[0], **base, evidence=[{"ref": "JHN 1:1"}]),
          dict(W[0], **base, id="w:bad", form="z-undo-", evidence=[{"ref": "JHN 1:1"}]),
          dict(W[0], **base, id="w:absent", form="zomitu", evidence=[{"ref": "JHN 1:2"}]),
          dict(W[0], **base, id="w:none", form="abelo")]
    json.dump({"iso": "xxx", "edition": "test", "partition": "observations", "entries": es},
              open(os.path.join(d, "observations.json"), "w"))
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "language_profile.py"),
                        "check", d, "--text-dir", os.path.join(d, "text")], capture_output=True, text=True)
    out = r.stdout + r.stderr
    assert "w:bad: form 'z-undo-' is one whole word" in out, out
    assert "w:absent: word 'zomitu' not found as a whole word" in out, out
    assert "w:none: no evidence" in out, out
    assert "w:zundo:" not in out, out


if __name__ == "__main__":
    test_words_stay_whole(); test_superseded_word_is_not_live(); test_validator_form(); print("ok")
