#!/usr/bin/env python3
"""The OT routes of the affix audit on synthetic data (no project files, no edition's text): the Greek ending table and the
modern auxiliaries, the Hebrew features, which claims a route can test, hyphen words, the combined verdict, and the
audit on synthetic NT and Hebrew rows (re-label, nt-only, ot-only, flat, the all-words fallback for stems never seen
without the affix). Run: python3 scripts/tests/test_ot_routes.py (or pytest)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import grammar, morphs, ot_routes as O  # noqa: E402

O._NT = {}          # no NT lookup: the ending table alone


def test_endings():
    assert O.greek_parse("ἐποίησεν")[:4] == ("aorist", "indicative", "third", "singular")
    assert O.greek_parse("ποιήσουσιν")[:4] == ("future", "indicative", "third", "plural")
    assert O.greek_parse("ἐπορεύθησαν")[:4] == ("aorist", "indicative", "third", "plural")
    assert O.greek_parse("λέγων")[1] == "participle"
    assert O.greek_parse("ἔλεγον")[0] == "past"            # imperfect or second aorist: past, the tense open
    assert O.greek_parse("ακουέτω")[:2] == ("present", "imperative")
    assert O.greek_parse("καί") is None


def test_modern():
    assert O.greek_parse(["θα", "ποιήσω"], modern=True)[:4] == ("future", "indicative", "first", "singular")
    assert O.greek_parse(["θέλει", "ποιήσει"], modern=True)[:4] == ("future", "indicative", "third", "singular")
    assert O.greek_parse(["να", "ποιήσωμεν"], modern=True)[:4] == ("aorist", "subjunctive", "first", "plural")
    p = O.greek_parse(["ας", "ακούση"], modern=True)
    assert p[1] == "imperative" and p[4] == "aux"
    fs = O.greek_feature_set(O.greek_parse("ἐποίησαν"))
    assert {("tense", "aorist"), ("tense_class", "past"), ("aspect", "perfective"), ("person+number", "tp")} <= fs


def test_hebrew_features():
    R = lambda **k: {**dict(key="", lemma="", pos="", type=None, stem=None, person=None, number=None, role=None,
                            clause=None), **k}
    rows = [R(key="1", lemma="לֹא", pos="adverb", clause="c1"),
            R(key="2", lemma="הָלַךְ", pos="verb", type="yiqtol", stem="qal", person="first", number="singular",
              clause="c1"),
            R(key="3", lemma="", pos="suffix", role="o", person="second", number="singular", clause="c1"),
            R(key="4", lemma="אָמַר", pos="verb", type="wayyiqtol", stem="qal", person="third", number="singular",
              clause="c2"),
            R(key="5", lemma="שָׁמַע", pos="verb", type="jussive", stem="qal", person="third", number="plural",
              clause="c3")]
    f = O.heb_features(rows)
    assert {("negated", "yes"), ("object", "2s"), ("person+number", "fs"), ("tense_class", "nonpast")} <= f["2"]
    assert ("tense_class", "past") in f["4"] and ("negated", "yes") not in f["4"]
    assert {("mood", "imperative"), ("modality", "jussive"), ("person+number+mood", "tp.imperative")} <= f["5"]


def test_route_want():
    assert O.route_want("hebrew", {"tense": {"perfect"}}) == ({"tense_class": {"past"}}, True, None)
    assert O.route_want("hebrew", {"mood": {"subjunctive"}})[0] is None
    assert O.route_want("hebrew", {"tense": {"present", "aorist"}})[0] is None
    assert O.route_want("lxx", {"negated": {"yes"}})[0] is None
    assert O.route_want("vamvas", {"person+number": {"ts"}})[0] == {"person+number": {"ts"}}


class Tok:
    def tokens(self, s, exact=False):
        return s.split()


def test_whole_words():
    P = type("P", (), {"tok": Tok()})()
    w = O.whole_words(P, "abo tamu -ko kha", hyphen=True)
    assert w["tamu"] == ["tamu-ko"] and w["-ko"] == ["tamu-ko"] and w["kha"] == ["kha"]
    assert O.whole_words(P, "tamu -ko", hyphen=False)["tamu"] == ["tamu"]


def R(state, odds=3.0, n=30, sw=0.6, so=0.2, weak=False, verdict="confirm"):
    return dict(links=n, odds=None if state == "thin" else odds, share_with=sw, share_without=so, weak=weak,
                verdict=verdict, alt={}, untestable="x" if state == "n.a." else None)


def test_combine():
    hold, fail = R("holds"), R("fails", odds=1.0)
    assert morphs.combine({"nt": hold, "hebrew": hold})[0] == "confirm"
    assert morphs.combine({"nt": hold, "hebrew": hold, "lxx": fail})[0] == "re-label"
    assert morphs.combine({"nt": hold, "hebrew": fail, "lxx": fail})[0] == "nt-only"
    assert morphs.combine({"nt": fail, "hebrew": hold})[0] == "ot-only"
    assert morphs.combine({"nt": R("holds", verdict="protect-words"), "hebrew": R("thin")})[0] == "protect-words"
    assert morphs.combine({"nt": fail, "hebrew": fail})[0] == "retire"
    flat = R("fails", odds=0.8, sw=0.85, so=0.87)          # 3rd singular everywhere: neither holds nor fails
    assert morphs.route_state(flat) == "flat"
    assert morphs.route_state(R("fails", odds=1.0, sw=0.0, so=0.0)) == "thin"   # the feature on none: no evidence
    assert morphs.combine({"nt": hold, "hebrew": flat})[0] == "confirm"
    weak = R("holds", weak=True)                             # tense from the conjugation: counts, named in the note
    v, note = morphs.combine({"nt": hold, "hebrew": weak})
    assert v == "confirm" and "weak" in note


STEMS = "kabi tolu mesa nibo rako".split()
VOCAB = {**{w: 10 for w in STEMS}, **{w + "tez": 10 for w in STEMS}}
ENT = dict(id="m:-tez:verb", kind="morph", slot="suffix", form="-tez", host="verb", value="PRF", status="observed",
           greek={"tense": "perfect"})


def rows(S, feat_on, feat_off, n=6):
    """rows of one route: every word n times, the -tez words with feat_on on their first rows, the bare ones feat_off"""
    out = []
    for w in VOCAB:
        ms = S.split(w)
        labs = {(m.form, m.position) for m in ms if m.slot != "stem"}
        stem = next(m.form for m in ms if m.slot == "stem")
        on = w.endswith("tez")
        for i in range(n):
            fv = (feat_on if on and i < 4 else feat_off if not on and i < 1 else set())
            out.append(("verb", labs, stem, set(fv), i % 2 == 0, f"GEN 1:{i + 1}", w, "x"))
    return out


def test_audit_routes():
    G = grammar.Grammar([ENT])
    S = morphs.Segmenter(G, {}, VOCAB)
    nt = rows(S, {("tense", "perfect")}, {("tense", "perfect")})
    heb = rows(S, {("tense_class", "past")}, {("tense_class", "past")})
    lxx = rows(S, {("tense", "aorist")}, {("tense", "perfect")})       # the LXX: aorist where the affix is
    r = morphs.audit("x", [], None, S, G=G, routes=("nt", "hebrew", "lxx"),
                     route_toks={"nt": nt, "hebrew": heb, "lxx": lxx})[0]
    assert r["routes"]["nt"]["odds"] > 2 and r["routes"]["hebrew"]["weak"]
    assert morphs.route_state(r["routes"]["lxx"]) == "fails"
    assert r["combined"][0] == "re-label", r["combined"]
    assert r["routes"]["lxx"]["alt"]["tense"][0] == "aorist"


def test_all_words_fallback():
    """stems never seen without the affix: the odds against every host word without it, said so"""
    vocab = VOCAB | {"pumo": 10, "sile": 10}               # the bare stems are words, but never linked
    G = grammar.Grammar([ENT])
    S = morphs.Segmenter(G, {}, vocab)
    out = []
    for w in (w for w in vocab if w not in STEMS):
        ms = S.split(w)
        labs = {(m.form, m.position) for m in ms if m.slot != "stem"}
        stem = next(m.form for m in ms if m.slot == "stem")
        for i in range(6):
            fv = {("tense", "perfect")} if (w.endswith("tez") and i < 4) else set()
            out.append(("verb", labs, stem, fv, i % 2 == 0, f"MAT 1:{i + 1}", w, "x"))
    r = morphs.audit("x", [], None, S, G=G, route_toks={"nt": out})[0]
    assert r["odds_basis"] == "all words" and r["links_without"] == 12 and r["odds"] > 2, r


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
    print("ok")
