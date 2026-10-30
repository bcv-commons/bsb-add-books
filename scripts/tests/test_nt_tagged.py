#!/usr/bin/env python3
"""Tagged drafting on the NT (needs orig/grc.sqlite, the Greek NT clause layout and the compact-alignments index;
skipped without them):
- the clause packages of EPH 1 have one block per layout line that holds words of the BGB text, and every number in
  them is one that full_align.numbering gives for its verse;
- a word of the drafting text without a MACULA word is marked `*` (JHN 4:1, BGB Ἰησοῦς where MACULA has Κύριος), and
  the MACULA word the text lacks is `absent`: split doesn't ask for it;
- a tagged chapter split and tagged again gives the same .align.
Run: python3 scripts/tests/test_nt_tagged.py (or with pytest)."""
import collections, os, re, shutil, sqlite3, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import full_align as FA, package as PK  # noqa: E402

ROOT = PK.ROOT
GRC = os.path.join(ROOT, "orig", "grc.sqlite")
HAVE = all(os.path.exists(os.path.join(ROOT, f)) for f in ("orig/grc.sqlite", "orig/grc-gntl-keys/eph001.json",
                                                           "orig/grc/eph001.txt", "export/dan/dan_BSB/project.yaml"))


def numbers(text):
    """{verse: [the numbers of its cells]} and the `*` words, from a package"""
    out, stars, v = collections.defaultdict(list), [], None
    for l in text.splitlines():
        if re.fullmatch(r"v\d+", l):
            v = int(l[1:])
        elif l.startswith("  ") and not l.lstrip().startswith(("BSB:", "who:", "had:")):
            for cell in l.strip().split(" · "):
                head = cell.split(" ")[0]
                (stars.append((v, cell.split(" ")[1])) if head == "*" else out[v].append(int(head)))
    return out, stars


def test_package_numbers():
    if not HAVE:
        print("skip: no Greek NT sources or the Danish demo")
        return
    text = PK.build("dan/dan_BSB", "eph", 1, "known")
    got, stars = numbers(text)
    for v, ns in got.items():
        allowed = {n for n, *_ in FA.numbering("EPH", f"EPH 1:{v}")}
        assert set(ns) <= allowed, (v, set(ns) - allowed)
    assert text.count("\n§") == 50 and (14, "ὅ") in stars          # 1:14 BGB ὅ, MACULA ὅς


def test_star_and_absent():
    if not HAVE:
        print("skip")
        return
    _, stars = numbers(PK.build("dan/dan_BSB", "jhn", 4, "known"))
    assert (1, "Ἰησοῦς") in stars, stars[:5]
    con = sqlite3.connect(GRC)
    kyrios = con.execute("select n from tokens where book='JHN' and ch=4 and v=1 and lemma='κύριος'").fetchone()[0]
    assert kyrios in FA.absent("dan/dan_BSB", "jhn", 4)[1]


def test_round_trip():
    if not HAVE:
        print("skip")
        return
    con = sqlite3.connect(GRC)
    gone = FA.absent("dan/dan_BSB", "eph", 1)
    lines = ["===Ephesians, Chapter 1==="]
    for v in sorted({v for (v,) in con.execute("select v from tokens where book='EPH' and ch=1")}):
        ns = [n for n, *_ in FA.numbering("EPH", f"EPH 1:{v}") if n not in gone.get(v, set())]
        # one made-up word per token, every third one dropped at its place
        lines.append(f"v{v} " + " ".join(f"^-{n}" if n % 3 == 2 else f"w{chr(97 + n % 26)}^{n}" for n in ns) + ".")
    tagged = "\n".join(lines) + "\n"
    d = os.path.join(FA.project_dir("dan/dan_BSB"), "eph")
    made = not os.path.isdir(d)
    try:
        os.makedirs(d, exist_ok=True)
        for x in ("eph001.txt", "eph001.align", "eph001.tagged"):     # never overwrite a real chapter
            assert not os.path.exists(os.path.join(d, x)), f"{x} exists: the test would overwrite it"
        open(os.path.join(d, "eph001.tagged"), "w", encoding="utf-8").write(tagged)
        problems, undecided, rows = FA.split("dan/dan_BSB", "eph", 1)
        assert not problems and not undecided, (problems, undecided)
        again = FA.split("dan/dan_BSB", "eph", 1, write=False, tagged=FA.tag("dan/dan_BSB", "eph", 1)[0])
        assert [r[:3] for r in again[2]] == [r[:3] for r in rows]
    finally:
        for x in ("eph001.txt", "eph001.align", "eph001.tagged"):
            if os.path.exists(os.path.join(d, x)):
                os.remove(os.path.join(d, x))
        if made:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    test_package_numbers(); test_star_and_absent(); test_round_trip(); print("ok")
