#!/usr/bin/env python3
"""Alternations (scripts/alternations.py): forms with the same letters and other marks are grouped, cues are kept only
when stable, strong and decisive, and the entry they make is a valid `feature` with an `alternation` block. Synthetic
tokens and study results. Run: python3 scripts/tests/test_alternations.py (or pytest)."""
import collections, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import alternations as A  # noqa: E402


def test_plain_and_groups():
    assert A.plain("Eín") == "ein" and A.plain("ndǿgo") == "ndøgo"
    toks = {("MRK", 1, v): [(0, "ein")] * 30 + [(1, "eín")] * 25 + [(2, "zo")] * 40 for v in (1,)}
    gs = dict(A.groups(toks, min_n=20, share=0.05))
    assert set(gs) == {"ein"} and gs["ein"] == collections.Counter({"ein": 30, "eín": 25})


def row(q, ctx, val, pa, pb, stable=True):
    return (q, (ctx, val), pa, pb, [q, q], stable)


def test_cues_keep_only_decisive_ones():
    res = {"ein": {"n": 100, "rows": [row(60.0, "previous", "gezø", 0.30, 0.0),       # kept
                                      row(60.0, "within 3", "gezø", 0.30, 0.0),       # not a cue context
                                      row(12.0, "previous", "rare", 0.05, 0.0),       # 5 tokens: too few
                                      row(30.0, "previous", "half", 0.30, 0.0, stable=False),
                                      row(11.0, "next", "mixed", 0.20, 0.10)],        # p = 20 / (20 + 10) < 0.8
                       "refs": collections.defaultdict(list, {("previous", "gezø"): ["MRK 1:1"]}),
                       "books": collections.defaultdict(lambda: collections.Counter({"MAT": 10, "MRK": 10, "LUK": 10}))},
           "eín": {"n": 100, "rows": [], "refs": collections.defaultdict(list), "books": {}}}
    cs = A.cues(res, {"ein": 100, "eín": 100})
    assert [(c["form"], c["context"], c["value"]) for c in cs] == [("ein", "previous", "gezø")], cs
    assert cs[0]["p"] == 1.0 and cs[0]["n"] == 30 and cs[0]["books"] == 3
    good = res["ein"]["books"]
    res["ein"]["books"] = collections.defaultdict(lambda: collections.Counter({"REV": 25, "MAT": 3, "LUK": 2}))
    assert A.cues(res, {"ein": 100, "eín": 100}) == []                              # one book's habit: no cue
    res["ein"]["books"] = good
    e = A.entry("x/y", ["ein", "eín"], {"ein": 100, "eín": 100}, res, "2026-10-27")
    assert e["id"] == "alt:ein" and e["kind"] == "feature" and e["status"] == "open"
    assert e["alternation"]["forms"] == {"ein": 100, "eín": 100}
    assert e["evidence"] == [{"ref": "MRK 1:1", "form": "ein", "n": 100}]
    assert all("refs" not in c for c in e["alternation"]["cues"])


def test_no_cues_no_entry():
    res = {"a": {"n": 50, "rows": [], "refs": collections.defaultdict(list)},
           "á": {"n": 50, "rows": [], "refs": collections.defaultdict(list)}}
    assert A.entry("x/y", ["a", "á"], {"a": 50, "á": 50}, res, "2026-10-27") is None


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
    print("ok")
