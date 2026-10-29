#!/usr/bin/env python3
"""The reading orders (books.ORDERS): each has all 66 books once, the NT the same in all, the numbering order kept;
book ranges and STATUS.md's chapters follow a project's book_order. No project files.
Run: python3 scripts/tests/test_book_order.py (or pytest)."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import books, onboard, status  # noqa: E402


def test_orders():
    nt = [b[0] for b in books.BOOKS if b[2] == "nt"]
    for name, o in books.ORDERS.items():
        assert sorted(o) == sorted(books.BY_CODE) and len(o) == 66, name
        assert o[39:] == nt, name
    assert books.order() == books.ORDERS["tanakh"]
    assert books.order("protestant") == [b[0] for b in books.BOOKS]     # the numbering order, unchanged
    t = books.order("tanakh")
    assert t[:5] == ["gen", "exo", "lev", "num", "deu"] and t[38] == "2ch" and t.index("mal") < t.index("psa")
    s = books.order("septuagint")
    assert s.index("job") < s.index("hos") < s.index("isa") and s[38] == "dan"


def test_ranges_follow_the_order():
    assert onboard.books_of("gen-deu") == onboard.books_of("gen-deu", "protestant")      # the Torah: one order
    assert onboard.books_of("rut-est") == ["rut", "sng", "ecc", "lam", "est"]           # tanakh: the Megillot
    assert onboard.books_of("rut-est", "protestant")[:3] == ["rut", "1sa", "2sa"]
    assert onboard.books_of("dan jos gen") == ["gen", "jos", "dan"]
    try:
        books.order("vulgate")
        assert False, "an unknown order must stop"
    except SystemExit:
        pass


def test_status_order():
    d = tempfile.mkdtemp()
    for code in ("isa", "psa", "gen"):
        os.makedirs(os.path.join(d, code))
        open(os.path.join(d, code, f"{code}001.txt"), "w").write("v1 x\n")
    assert list(status.chapter_files(d)) == ["gen001", "isa001", "psa001"]               # tanakh: Prophets first
    assert list(status.chapter_files(d, "protestant")) == ["gen001", "psa001", "isa001"]


if __name__ == "__main__":
    test_orders(); test_ranges_follow_the_order(); test_status_order(); print("ok")
