#!/usr/bin/env python3
"""participants.py: chapter ranges, and the speaker self-test on PHP 1 (needs orig/grc.sqlite; skipped without it).
Run: python3 scripts/tests/test_participants.py (or with pytest)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import participants as P  # noqa: E402

ROOT = P.ROOT   # the data root (books.py)


def test_chapter_list():
    assert P.chapter_list(["1-3", "7"]) == [1, 2, 3, 7]


def test_php1_self_test():
    if not os.path.exists(os.path.join(ROOT, "orig", "grc.sqlite")):
        print("skip: no orig/grc.sqlite")
        return
    r = P.resolve("grc", "PHP", [1])
    assert r.speaker_check["agree"] == 36 and r.speaker_check["differ"] == 0, dict(r.speaker_check)
    pids = {r.pid(k) for k in r.mention_keys}
    assert any((r.name(p) or "").startswith("Paul") for p in pids)


def test_gen24_kinship():
    """"my son" (24:4, Abraham's) is Isaac, named in the same verse; "the son of Milcah" (24:24) Bethuel; "a son" born
    to Abraham (24:36, no possessor) joins neither. The self-test holds at GEN 1-24 319 / 9."""
    if not (os.path.exists(os.path.join(ROOT, "orig", "heb.sqlite")) and P.load_tipnr()[1]):
        print("skip: no orig/heb.sqlite or TIPNR")
        return
    r = P.resolve("hbo", "GEN", list(range(1, 25)))
    assert r.speaker_check["agree"] >= 319 and r.speaker_check["differ"] <= 9, dict(r.speaker_check)
    isaac, bethuel = r.pid("010240040102"), r.pid("010240240061")
    assert r.name(isaac) == "Isaac" and r.name(bethuel) == "Bethuel"
    for k in ("010240030112", "010240040092", "010240370072", "010240440142"):      # my son / the son (of my master)
        assert r.pid(k) == isaac, (k, r.name(r.pid(k)))
    assert r.pid("010240360051") not in (isaac, bethuel)
    assert r.joined_by["kinship"] > 0


if __name__ == "__main__":
    test_chapter_list(); test_php1_self_test(); test_gen24_kinship(); print("ok")
