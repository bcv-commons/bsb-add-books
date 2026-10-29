#!/usr/bin/env python3
"""package.participant_ids on GEN 24 (needs orig/heb.sqlite; skipped without it):
- "my son" (3:3 בְנִי, token 17) is Isaac, "my" (18) Abraham, the implicit subject of תִקַּח (14) the servant;
- the servant's chain: the same participant id for the imperative שִׂים (2:16), "you" (2:19) and his later verbs;
- a name itself gets no `who:` entry; no resolver (NT, missing data) -> ({}, "", {}, set()) and no error.
Run: python3 scripts/tests/test_package_pids.py (or with pytest)."""
import os, sqlite3, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import package as PK  # noqa: E402

HAVE = os.path.exists(PK.HEB)


def gen24():
    con = sqlite3.connect(PK.HEB)
    con.row_factory = sqlite3.Row
    toks = con.execute("select * from tokens where book='GEN' and ch=24 order by key").fetchall()
    lines = {r["key"]: r["line"] for r in con.execute(
        "select l.key, l.line from layout l join tokens t on t.key=l.key where t.book='GEN' and t.ch=24 and l.layout='bhsa'")}
    who, legend, *_ = PK.participant_ids("gen", 24, toks, lines)
    at = {}
    for t in toks:
        for n, name in who.get(t["key"], []):
            at[(t["v"], n)] = name
    return at, legend, toks, who


def test_gen24():
    if not HAVE:
        print("skip: no orig/heb.sqlite")
        return
    at, legend, toks, who = gen24()
    assert at[(3, "17")].startswith("Isaac("), at.get((3, "17"))
    assert at[(3, "18")].startswith("Abraham(")
    servant = at[(2, "16s")]
    assert "servant" in servant and at[(2, "19")] == servant and at[(3, "14s")] == servant
    assert sum(1 for v in at.values() if v == servant) > 20          # the chain runs through the chapter
    assert not any(who.get(t["key"]) for t in toks if t["type"] == "proper")
    assert legend.startswith("p1 Abraham")


def test_off_without_resolver():
    import participants as P
    real = P.resolve
    try:
        P.resolve = lambda *a: (_ for _ in ()).throw(FileNotFoundError("no data"))
        assert PK.participant_ids("gen", 24, [], {}) == ({}, "", {}, set())
    finally:
        P.resolve = real


if __name__ == "__main__":
    test_gen24()
    test_off_without_resolver()
    print("ok")
