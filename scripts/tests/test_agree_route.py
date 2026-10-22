#!/usr/bin/env python3
"""The agreement route (scripts/agree_route.py, morphs.py audit --route agree) on a synthetic store and synthetic
verb-noun pairs (no project files): class-7 nouns (eki-) with ki- verbs and class-2 nouns (aba-) with ba- verbs ->
both concords hold and confirm; a concord claiming the wrong class fails and retires; a gender claim (by: gender) is
read from the source noun's gender; without noun classes in the store a class claim is untestable and said so.
Run: python3 scripts/tests/test_agree_route.py (or pytest)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import agree_route as AR, grammar, morphs  # noqa: E402

VSTEMS = "lya genda kola sinza tema wona".split()
NSTEMS = "tabo ntu ti me".split()
VERBS = [p + s for p in ("ki", "ba", "gu") for s in VSTEMS] + VSTEMS
NOUNS = [p + s for p in ("eki", "aba") for s in NSTEMS] + NSTEMS
VOCAB = {w: 5 for w in VERBS + NOUNS}


def m(id_, form, host, **kw):
    return dict(id=id_, kind="morph", slot="prefix", form=form, host=host, value=id_, status="observed", **kw)


NOUN = [m("m:eki:noun", "eki-", "noun", position=1, **{"class": "7"}),
        dict(m("m:aba:noun", "aba-", "noun", position=1), value="CL2")]     # the class read from a CLn value
KI = m("m:ki:verb", "ki-", "verb", position=1, agree={"role": "subject", "class": "7"})
BA = m("m:ba:verb", "ba-", "verb", position=1, agree={"role": "subject", "class": ["2"]})
GU = m("m:gu:verb", "gu-", "verb", position=1, agree={"role": "subject", "class": "7"})      # wrong: gu- goes with 2
SHE = m("m:gu-f:verb", "gu-", "verb", position=1, agree={"role": "subject", "class": "feminine", "by": "gender"})


def pairs():
    """(role, verb, noun, number, gender, ref, source, proper): ki- with eki- nouns 9 of 10 times, ba- with aba- 9 of
    10, gu- with aba- (and feminine nouns), bare verbs with either; a name pair left out of the class test"""
    out, i = [], 0
    for s in VSTEMS:
        for k in range(10):
            i += 1
            ref = f"MAT {1 + i // 30}:{i % 30 + 1}"
            ki_n = "eki" + NSTEMS[k % 4] if k < 9 else "aba" + NSTEMS[k % 4]
            ba_n = "aba" + NSTEMS[k % 4] if k < 9 else "eki" + NSTEMS[k % 4]
            out.append(("subject", "ki" + s, ki_n, "singular", "neuter", ref, "nt", False))
            out.append(("subject", "ba" + s, ba_n, "plural", "masculine", ref, "nt", False))
            out.append(("subject", "gu" + s, "aba" + NSTEMS[k % 4], "plural", "feminine" if k < 8 else "masculine",
                        ref, "nt", False))
            out.append(("subject", s, ("eki" if k % 2 else "aba") + NSTEMS[k % 4], "singular", "masculine", ref, "nt",
                        False))
    out.append(("subject", "kilya", "Maria", "singular", "feminine", "MAT 9:9", "nt", True))
    return out


def run(entries, routes=("agree",)):
    G = grammar.Grammar(entries)
    S = morphs.Segmenter(G, {}, VOCAB)
    old = morphs.affix_tokens
    morphs.affix_tokens = lambda pname, S_: []
    try:
        return {r["entry"]["id"]: r for r in morphs.audit("x", [], None, S, G=G, routes=routes,
                                                         route_toks={"agree": pairs(), "nt": []})}
    finally:
        morphs.affix_tokens = old


def test_concords_hold():
    r = run(NOUN + [KI, BA])
    for i in ("m:ki:verb", "m:ba:verb"):
        x = r[i]["routes"]["agree"]
        assert morphs.route_state(x) == "holds", (i, x)
        assert x["share_with"] > 0.8 and x["odds"] >= 2 and x["odds_all"] >= 2, x
        assert x["pairs"]["names"] == 1, x["pairs"]          # the name pair is not counted against
        assert r[i]["verdict"] in ("confirm", "protect-words"), r[i]["verdict"]


def test_wrong_class_fails():
    r = run(NOUN + [GU])
    x = r["m:gu:verb"]["routes"]["agree"]
    assert morphs.route_state(x) == "fails" and r["m:gu:verb"]["verdict"] == "retire", x


def test_combined_with_nt():
    r = run(NOUN + [KI, GU], routes=("nt", "agree"))
    assert r["m:ki:verb"]["combined"][0] == "confirm", r["m:ki:verb"]["combined"]
    assert r["m:gu:verb"]["combined"][0] == "retire", r["m:gu:verb"]["combined"]


def test_gender():
    r = run([SHE])                                    # no noun classes needed for a gender claim
    x = r["m:gu-f:verb"]["routes"]["agree"]
    assert morphs.route_state(x) == "holds" and x["share_with"] == 0.8, x


def test_no_classes():
    r = run([KI])
    assert r["m:ki:verb"]["routes"]["agree"]["untestable"].startswith("the store has no noun-class"), r
    assert "can't be tested" in AR.summary(grammar.Grammar([KI]))
    assert "nothing to test" in AR.summary(grammar.Grammar(NOUN))


def test_class_specs():
    assert AR.resolve({"singular": "9", "plural": "10"}, "plural") == {"10"}
    assert AR.resolve({"singular": "9", "plural": "10"}, None) == {"9", "10"}
    assert AR.resolve({"default": "1/3", "stems": {"ti": "3"}}, "singular", "ti") == {"3"}
    assert AR.resolve({"default": "1/3", "stems": {"ti": "3"}}, "singular", "ntu") == {"1", "3"}


if __name__ == "__main__":
    for t in (test_concords_hold, test_wrong_class_fails, test_combined_with_nt, test_gender, test_no_classes,
              test_class_specs):
        t()
    print("ok")
