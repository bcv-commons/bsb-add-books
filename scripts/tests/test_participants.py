#!/usr/bin/env python3
"""participants.py: chapter ranges, and the speaker self-test on PHP 1 (needs orig/grc.sqlite; skipped without it).
Run: python3 scripts/tests/test_participants.py (or with pytest)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import participants as P  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))


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


if __name__ == "__main__":
    test_chapter_list(); test_php1_self_test(); print("ok")
