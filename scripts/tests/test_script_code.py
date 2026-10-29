#!/usr/bin/env python3
"""Regression test: the target script (ISO 15924) from synthetic text, the NLLB code built on it, and the init chosen in
the same script. No project files. Run: python3 scripts/tests/test_script_code.py (or with pytest)."""
import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import script_code as SC  # noqa: E402

LANGS = ["eng_Latn", "tpi_Latn", "hin_Deva", "ory_Orya", "rus_Cyrl", "arb_Arab", "tha_Thai", "khm_Khmr"]


def test_dominant():
    cases = {"Kalo ka-tamu sòpì ma.": "Latn", "Ὁ λόγος σὰρξ ἐγένετο": "Grek", "В начале было Слово": "Cyrl",
             "ଆଦିରେ ବାକ୍ୟ ଥିଲେ": "Orya", "आदि में वचन था": "Deva", "في البدء كان الكلمة": "Arab", "בְּרֵאשִׁית בָּרָא": "Hebr",
             "ในปฐมกาลพระวาทะดำรงอยู่": "Thai", "ពីដើមដំបូង": "Khmr", "အစအဦး၌": "Mymr", "ཐོག་མར་": "Tibt",
             "ቃል ነበረ": "Ethi", "태초에 말씀이": "Hang", "太初有道": "Hani", "": "Latn", "123 ...": "Latn"}
    for text, code in cases.items():
        assert SC.dominant_script([text]) == code, (text, SC.dominant_script([text]), code)
    # majority wins over a few Latin names inside Odia text
    assert SC.dominant_script(["ଯୀଶୁ Jesus ଖ୍ରୀଷ୍ଟ ଙ୍କ ବାକ୍ୟ"]) == "Orya"


def proj(text, p=None, eds=()):
    return types.SimpleNamespace(p=p or {}, editions=list(eds), corpus=lambda: [("GEN 1:1", "gen", (1, 1), "", text)])


def test_recorded_wins():
    assert SC.target_script(proj("Kalo tamu")) == ("Latn", "corpus")
    assert SC.target_script(proj("Kalo tamu", eds=[{"script": "orya"}])) == ("Orya", "recorded")
    assert SC.target_script(proj("ଆଦିରେ", p={"script": "Latn"})) == ("Latn", "recorded")
    assert SC.nllb_code("bdv", "Orya") == "bdv_Orya"


def test_init():
    assert SC.init_for_script("tpi_Latn", "Latn", LANGS) == ("tpi_Latn", None)       # Latin: unchanged
    assert SC.init_for_script("eng_Latn", "Orya", LANGS)[0] == "ory_Orya"           # the only Odia language
    assert SC.init_for_script("eng_Latn", "Deva", LANGS)[0] == "hin_Deva"
    assert SC.init_for_script("eng_Latn", "Cyrl", LANGS)[0] == "rus_Cyrl"
    init, why = SC.init_for_script("eng_Latn", "Tibt", LANGS)                         # none in the list: kept, said why
    assert init == "eng_Latn" and "no NLLB language" in why


if __name__ == "__main__":
    for f in (test_dominant, test_recorded_wins, test_init):
        f()
    print("ok")
