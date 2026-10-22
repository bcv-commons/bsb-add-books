#!/usr/bin/env python3
"""Regression test: Greek quoted in notes (quotes.original_runs). A run of more than 6 words must be the BGB word for
word; a reading the BGB lacks passes when it is Robinson-Pierpont word for word and its line names it as a Majority Text
variant (RP / BYZ / Majority Text); unmarked, or TR-only, it stays a problem; Greek punctuation (U+0387) and a `…` gap
don't break the check. Needs orig/grc and orig/grc-rp (scripts/setup.py). Run: python3 scripts/tests/test_quotes_rp.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import quotes  # noqa: E402

RP_ONLY = "διελθὼν διὰ μέσου αὐτῶν· καὶ παρῆγεν οὕτως"          # JHN 8:59, Majority Text only
BGB = "Ἐγώ εἰμι ἡ ὁδὸς καὶ ἡ ἀλήθεια καὶ ἡ ζωή"                  # JHN 14:6, ends before the ano teleia
INVENTED = "καὶ ἐγὼ ὑπάγω πρὸς τὸν πατέρα μου σήμερον ταχέως"


def runs(text):
    return quotes.original_runs(text)


def test_bgb_with_ano_teleia():
    assert runs(f"| 6 | {BGB}· οὐδεὶς |") == []


def test_rp_variant_marked():
    for mark in ("BYZ, TR +", "RP:", "Majority Text:"):
        assert runs(f"8,59 {mark} {RP_ONLY}") == [], mark


def test_rp_variant_unmarked():
    assert runs(f"8,59 {RP_ONLY}") != []


def test_not_rp_stays_problem():
    assert runs(f"TR: {INVENTED}") != []
    assert runs(f"BYZ: {INVENTED}") != []


def test_mark_only_on_its_line():
    assert runs(f"BYZ\n{RP_ONLY}") != []


def test_gap_ends_run():
    assert runs("ὁ δὲ ἔφη Πιστεύω κύριε … καὶ εἶπεν ὁ Ἰησοῦς") == []


if __name__ == "__main__":
    if not (quotes.open_text("grc") and quotes.open_text("rp")):
        print("skip: no orig/grc or orig/grc-rp (scripts/setup.py)")
        raise SystemExit
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
    print("ok")
