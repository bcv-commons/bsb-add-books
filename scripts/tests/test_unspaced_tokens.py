#!/usr/bin/env python3
"""Regression test: for scripts without spaces the tokeniser cuts words as tokenizer v2 does (compact-alignments, bibles'
tools/verse-text bcv_tokenize; our copy full_align.tokenize), and leaves every other script as it was. Synthetic text,
no project files. Run: python3 scripts/tests/test_unspaced_tokens.py (or with pytest)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import full_align as FA, langtools as L  # noqa: E402


def test_spaced_unchanged():
    for text, script in [("Kalo ka-tamu sòpì ma, nqovotáz.", "Latn"), ("ଆଦିରେ ବାକ୍ୟ ଥିଲେ", "Orya"),
                         ("في البدء كان الكلمة", "Arab")]:
        for cfg in ({}, {"split_hyphens": True}):
            a, b = L.Tokeniser(cfg), L.Tokeniser(cfg, script=script)
            assert b.segment is None
            for ex in (False, True):
                assert a.tokens(text, exact=ex) == b.tokens(text, exact=ex)


def test_unspaced():
    t = L.Tokeniser({}, script="Hani")
    assert t.tokens("太初有道，道与神同在。") == list("太初有道道与神同在")
    assert L.Tokeniser({}, script="Jpan").tokens("神の子イエス") == ["神", "の", "子", "イエス"]
    # Thai: zero-width spaces already break words; nothing more is cut
    th = "ใน​สมัย​ที่ ผู้วินิจฉัย"
    assert L.Tokeniser({}, script="Thai").tokens(th) == L.Tokeniser({}).tokens(th) == ["ใน", "สมัย", "ที่", "ผู้วินิจฉัย"]
    # Myanmar: tokenizer v2's syllables; our tokens keep the marks it drops (U+1037), the cuts are the same
    my = "ယနေ့ည အာဗြဟံ"
    toks = L.Tokeniser({}, script="Mymr").tokens(my, exact=True)
    assert ["".join(c for c in x if not FA.dropped(c)) for x in toks] == FA.tokenize(my)
    assert "".join(toks) == my.replace(" ", "")
    # turned off by the project
    assert L.Tokeniser({"segment": "none"}, script="Hani").tokens("太初有道") == ["太初有道"]


if __name__ == "__main__":
    test_spaced_unchanged(); test_unspaced(); print("ok")
