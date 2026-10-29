#!/usr/bin/env python3
"""morphs.audit on a synthetic store and synthetic Greek links (no project files): a person prefix z- that holds on
most stems, and a frequent word zundo that only begins like it -> verdict protect-words, zundo listed against it; with
the word protected (kind word) the prefix is confirmed. Run: python3 scripts/tests/test_morph_audit.py (or pytest)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import grammar, morphs  # noqa: E402

STEMS = "kabi tolu mesa nibo rako".split()
VOCAB = {**{w: 10 for w in STEMS}, **{"z" + w: 10 for w in STEMS}, "zundo": 15, "undo": 3}
ENT = dict(id="m:z-:verb", kind="morph", slot="prefix", form="z-", host="verb", value="2PL", status="observed",
           greek={"person+number": "sp"})
WORD = dict(id="w:zundo", kind="word", form="zundo", value="WORD", status="observed")


def tokens(S):
    """affix_tokens' rows: six Greek links per word; the z- words 2PL on four of them, zundo a noun"""
    out = []
    for w in VOCAB:
        ms = S.split(w)
        labs = {(m.form, m.position) for m in ms if m.slot != "stem"}
        stem = next(m.form for m in ms if m.slot == "stem")
        for i in range(6):
            sp = w.startswith("z") and w != "zundo" and i < 4
            out.append(("noun" if w == "zundo" else "verb", labs, stem, {("person+number", "sp" if sp else "ts")},
                        i % 2 == 0, f"MAT 1:{i + 1}", w, "χείρ" if w == "zundo" else "λέγω"))
    return out


def run(entries):
    G = grammar.Grammar(entries)
    S = morphs.Segmenter(G, {}, VOCAB)
    old = morphs.affix_tokens
    morphs.affix_tokens = lambda pname, S_: tokens(S_)
    try:
        return morphs.audit("x", [], None, S, G=G)[0]
    finally:
        morphs.affix_tokens = old


def test_audit():
    r = run([ENT])
    assert r["tokens"] == 65 and r["stems"] == 6, r
    assert [w for w, _ in r["against"]] == ["zundo"], r["against"]
    assert r["verdict"] == "protect-words", r["verdict"]
    assert r["share_with"] > r["share_without"]


def test_audit_protected():
    r = run([ENT, WORD])
    assert r["tokens"] == 50 and not r["against"] and r["verdict"] == "confirm", r


if __name__ == "__main__":
    test_audit(); test_audit_protected(); print("ok")
