#!/usr/bin/env python3
"""Two checks on synthetic data:
- cell_check.carries: a prefix written with a hyphen (ká-bonà: tokens ka, -bona) and a reduplicated prefix (kaka- for
  ka-) carry the cell's prefix, in the morph view and as strings;
- rough_check.features: a word's beginnings are negation-marker candidates (a negative verb prefix, Zinza ti-/tii-).
Run: python3 scripts/tests/test_check_fixes.py (or with pytest)."""
import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import cell_check as C  # noqa: E402
import rough_check as R  # noqa: E402

PAT = [("ka", "", "", "")]                     # the cell's prefix ka-


class Seg:                                     # a stand-in morph view: ka- and kaka- are store prefixes
    pre, suf = ["kaka", "ka"], ["ni"]

    def labels(self, w):
        w = w.lower().replace("á", "a").replace("à", "a")
        if "-" in w or len(w) < 4:
            return set()
        if w.startswith("kaka"):
            return {"kaka-"}
        return {"ka-"} if w.startswith("ka") else set()


def test_has_prefix():
    assert C.has_prefix({"ka-"}, "ka") and C.has_prefix({"kaka-"}, "ka")
    assert not C.has_prefix({"kaku-"}, "ka") and not C.has_prefix({"ka-"}, "kaka")


def test_hyphen_morph_view():
    toks, ex = ["ka", "-bona"], ["ká", "-bonà"]
    assert C.carries(toks, PAT, ex, Seg()) == 1          # before the fix: 0 (the agent had to write kábonà)
    assert C.carries(["kabona"], PAT, ["kábonà"], Seg()) == 1


def test_reduplicated_morph_view():
    assert C.carries(["kakarumi"], PAT, ["kakarumi"], Seg()) == 1   # before the fix: 0 (label kaka-)
    assert C.carries(["kaka", "-tolu"], PAT, ["kaka", "-tolu"], Seg()) == 1


def test_strings():
    assert C.carries(["ka", "-bona"], PAT) == 1         # as strings: before the fix 0 (ka alone is too short)
    assert C.carries(["ka"], PAT) == 0                   # a word ka alone is still not the prefix


def test_negation_beginnings():
    P = types.SimpleNamespace(name="t", tok=types.SimpleNamespace(tokens=lambda s, exact=False: s.lower().split(),
                                                                  plain=lambda w: w.replace("í", "i")))
    R._SEG[P.name] = (None, False)
    f = R.features(P, "Tiínkumanya kandi")
    assert "^ti-" in f and "^tii-" in f and "-nya" in f, sorted(f)


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
    print("ok")
