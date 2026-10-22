#!/usr/bin/env python3
"""The target language's writing system as an ISO 15924 code (Latn, Cyrl, Orya, ...), and the NLLB code built on it.

    python3 scripts/script_code.py <project>      # the script, where it came from, the NLLB code and init

A script recorded in the project (`script:` in project.yaml) or its style edition (`script:` in edition.yaml) wins; else
the dominant script of the corpus letters, counted by Unicode character name (the same counting as lexeme-aligner's
eval/xedition_verify.dominant_script and probe_language.script_of). Nothing found: Latn, so Latin text behaves as before.
"""
import collections, os, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Unicode character-name prefix -> ISO 15924. Two-word prefixes first (checked before the one-word ones).
ISO15924 = {
    "LATIN": "Latn", "CYRILLIC": "Cyrl", "GREEK": "Grek", "ARABIC": "Arab", "HEBREW": "Hebr", "SYRIAC": "Syrc",
    "DEVANAGARI": "Deva", "BENGALI": "Beng", "ORIYA": "Orya", "TAMIL": "Taml", "TELUGU": "Telu", "KANNADA": "Knda",
    "MALAYALAM": "Mlym", "GUJARATI": "Gujr", "GURMUKHI": "Guru", "SINHALA": "Sinh", "THAI": "Thai", "LAO": "Laoo",
    "KHMER": "Khmr", "MYANMAR": "Mymr", "TIBETAN": "Tibt", "ETHIOPIC": "Ethi", "GEORGIAN": "Geor", "ARMENIAN": "Armn",
    "HANGUL": "Hang", "CJK": "Hani", "HIRAGANA": "Jpan", "KATAKANA": "Jpan", "THAANA": "Thaa", "CHEROKEE": "Cher",
    "CANADIAN": "Cans", "TIFINAGH": "Tfng", "VAI": "Vaii", "NKO": "Nkoo", "OL": "Olck", "MONGOLIAN": "Mong",
    "JAVANESE": "Java", "BALINESE": "Bali", "YI": "Yiii", "COPTIC": "Copt", "ADLAM": "Adlm",
}
RTL = {"Arab", "Hebr", "Syrc", "Thaa", "Nkoo", "Adlm"}
NO_SPACES = {"Thai", "Laoo", "Khmr", "Mymr", "Tibt", "Hani", "Jpan"}   # word segmentation needed (Tibetan: tsheg = syllable)


def char_script(c):
    """ISO 15924 code of one letter, or None (unknown name, or a script not in the table)."""
    try:
        name = unicodedata.name(c)
    except ValueError:
        return None
    return ISO15924.get(name.split()[0])


def dominant_script(texts, sample=20000):
    """The ISO 15924 code of most letters in `texts` (an iterable of strings), counted over up to `sample` letters;
    Latn when there are none."""
    n, seen = collections.Counter(), 0
    for t in texts:
        for c in t:
            if c.isalpha():
                s = char_script(c)
                if s:
                    n[s] += 1
                seen += 1
        if seen >= sample:
            break
    return n.most_common(1)[0][0] if n else "Latn"


def recorded_script(P):
    """`script:` from project.yaml, else from the first style edition that records one (normalised to Xxxx), else None."""
    for d in [P.p] + list(P.editions):
        s = (d or {}).get("script")
        if s and len(str(s)) == 4:
            return str(s).title()
    return None


def target_script(P):
    """(code, source): the recorded script, else the corpus's dominant one."""
    s = recorded_script(P)
    if s:
        return s, "recorded"
    return dominant_script(r[4] for r in P.corpus()), "corpus"


def direction(pname):
    """(script, bcp47 lang) of a project's target text when its script is written right to left, else None: what the
    site, the wiki view and other HTML put on target-language text (dir="rtl" lang=...). Left-to-right: None, so
    nothing changes for them."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import langtools as LT
    try:
        P = LT.Project(pname)
        s, _ = target_script(P)
    except (Exception, SystemExit):   # no project or corpus here (a fresh clone without editions): nothing recorded either
        return None
    if s not in RTL:
        return None
    lang = str(P.p.get("language") or "").strip() or "und"
    return s, f"{lang}-{s}"


def html_dir(pname):
    """' dir="rtl" lang="xx-Arab"' for a right-to-left target, else ''."""
    d = direction(pname)
    return f' dir="rtl" lang="{d[1]}"' if d else ""


def nllb_languages():
    f = os.path.join(ROOT, "scripts", "nllb", "languages.txt")
    return [l.strip() for l in open(f, encoding="utf-8") if l.strip() and not l.startswith("#")]


def nllb_code(iso, script):
    return f"{iso}_{script}"


def init_for_script(init, script, languages=None, prefer=("hin_Deva", "rus_Cyrl", "arb_Arab", "tha_Thai")):
    """(init, why): keep `init` when it is in the target script; else the same language in the target script if NLLB has
    it, else a well-resourced NLLB language of that script (`prefer`), else the first one listed; why is None when
    nothing changed. An init in another script starts the new code's embedding from a model of letters it never writes."""
    if not init or init.endswith("_" + script):
        return init, None
    langs = languages if languages is not None else nllb_languages()
    same = [l for l in langs if l.endswith("_" + script)]
    if not same:
        return init, f"no NLLB language is written in {script}; init {init} kept (another script)"
    iso = init.split("_")[0]
    pick = next((l for l in same if l.split("_")[0] == iso), None) or next((l for l in prefer if l in same), None) or same[0]
    return pick, f"init {init} is not written in {script}; {pick} is (the new code starts from a model of the same letters)"


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        raise SystemExit(__doc__)
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import langtools as LT, lang as LG
    P = LT.Project(sys.argv[1])
    s, src = target_script(P)
    iso = LG.iso3(P) or str(P.p.get("language") or "").split("-")[0].lower()
    init, why = init_for_script((P.p.get("donor") or {}).get("nllb_init") or "eng_Latn", s)
    print(f"{sys.argv[1]}: script {s} ({src}{', right-to-left' if s in RTL else ''}{', no spaces' if s in NO_SPACES else ''})"
          f"; trg_code {nllb_code(iso, s)}; init {init}" + (f" ({why})" if why else ""))
