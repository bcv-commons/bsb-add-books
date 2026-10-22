#!/usr/bin/env python3
"""Regression test for the script at onboarding (onboard.text_script, probe_language.script_of), the script-aware donor
(donor.pick_init) and right-to-left target text (script_code.direction / html_dir, build_site.verse_view's tdir).
Synthetic samples: an Arabic-script, an Odia and a Latin one; no project files.
Run: python3 scripts/tests/test_script_steps.py (or with pytest)."""
import os, sys, tempfile, types
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import script_code as SC  # noqa: E402

ARAB, ORYA, LATN = "في البدء كان الكلمة والكلمة كان عند الله", "ଆଦିରେ ବାକ୍ୟ ଥିଲେ, ପୁଣି ବାକ୍ୟ ପରମେଶ୍ୱରଙ୍କ ସହିତ ଥିଲେ", "Kalo ka-tamu sòpì ma."


def proj(text, p=None):
    return types.SimpleNamespace(p=p or {}, editions=[], corpus=lambda: [("JHN 1:1", "jhn", (1, 1), "", text)])


def test_onboard_records_script():
    import onboard
    for text, code, rtl in ((ARAB, "Arab", ", right-to-left"), (ORYA, "Orya", ""), (LATN, "Latn", "")):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "jhn001.txt"), "w", encoding="utf-8").write(f"1\t{text}\n")
            assert onboard.text_script(d) == (code, rtl), (text, onboard.text_script(d))


def test_probe_names_script():
    import probe_language as PL
    assert PL.script_of(proj(ORYA)) == "Odia"
    assert PL.script_of(proj(ARAB)) == "Arabic"
    assert PL.script_of(proj(LATN)) == "Latin"
    assert PL.script_of(proj(LATN, p={"script": "Deva"})) == "Devanagari"     # recorded wins


def test_donor_same_script():
    import donor
    table = {"hin": ["hin_Deva"], "ory": ["ory_Orya"], "urd": ["urd_Arab"], "pbt": ["pbt_Arab"], "kas": ["kas_Arab", "kas_Deva"],
             "swh": ["swh_Latn"], "lug": ["lug_Latn"]}
    donor.nllb_by_iso = lambda: table
    real = SC.nllb_languages
    SC.nllb_languages = lambda: [c for cs in table.values() for c in cs] + ["arb_Arab", "eng_Latn"]
    try:
        # Latin target: the first relative's code, no note (as before)
        assert donor.pick_init(["lug", "swh"], "Latn") == ("lug_Latn", None)
        # Odia target, nearest relative Hindi (Deva), Odia further: Odia, with the reason
        ni, why = donor.pick_init(["hin", "ory"], "Orya")
        assert ni == "ory_Orya" and "Orya" in why and "hin_Deva" in why
        # Arabic-script target: a relative with an Arabic-script code (kas_Arab) wins without a note
        assert donor.pick_init(["kas", "hin"], "Arab") == ("kas_Arab", None)
        # no relative in the script: script_code.init_for_script moves it to a large language of that script
        ni, why = donor.pick_init(["swh"], "Arab")
        assert ni == "arb_Arab" and "no relative" in why
        assert donor.pick_init([], "Arab") == (None, None)
    finally:
        SC.nllb_languages = real


def test_direction():
    import langtools as LT
    real = LT.Project
    try:
        LT.Project = lambda name: types.SimpleNamespace(p={"language": "ckb"} if name == "a" else {}, editions=[],
                                                        corpus=lambda: [("x", "jhn", (1, 1), "", ARAB if name == "a" else ORYA)])
        assert SC.direction("a") == ("Arab", "ckb-Arab")
        assert SC.html_dir("a") == ' dir="rtl" lang="ckb-Arab"'
        assert SC.direction("o") is None and SC.html_dir("o") == ""
        def boom(name):
            raise SystemExit("no project")
        LT.Project = boom
        assert SC.html_dir("missing") == ""
    finally:
        LT.Project = real


def test_verse_view_tdir():
    import build_site as B
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "jhn001.txt")
        open(f, "w", encoding="utf-8").write(f"1:1\t{ARAB}\n")
        B.source_verses = lambda code, n: {1: "Ἐν ἀρχῇ ἦν ὁ λόγος"}
        B.bsb_verses = lambda p, code, n, vs: {1: ("JHN 1:1", "In the beginning was the Word")}
        notes = "| Verse | Comment |\n|---|---|\n| 1 | a note |\n"
        ui = {"n_verse": "", "notes_more": ""}
        rtl = B.verse_view({}, "jhn", 1, f, notes, ui, ' dir="rtl" lang="ckb-Arab"')
        ltr = B.verse_view({}, "jhn", 1, f, notes, ui)
        assert '<div class="vv-t" dir="rtl" lang="ckb-Arab">' in rtl
        assert '<div class="vv-t">' in ltr and "rtl" not in ltr.split('class="vv-o"')[0]
        assert 'class="vv-e" dir' not in rtl                 # the BSB line stays left to right


def test_wiki_view_span():
    """wiki.py view puts dir/lang on this span for a right-to-left target: it must stay in the template"""
    tpl = open(os.path.join(SC.ROOT, "scripts", "wiki_view.html"), encoding="utf-8").read()
    assert '<span class="val">${esc(v)}</span>' in tpl


if __name__ == "__main__":
    for k, fn in list(globals().items()):
        if k.startswith("test_"):
            fn()
    print("ok")
