#!/usr/bin/env python3
"""Correct the OCR misreadings in text/ (the publisher's .docx files came from a scan).

Bern German writes c only in ch and ck (and in names: Cäsarea, Crispus), so a c before anything else is a misread e
(hct het, gscit gseit, scch sech, cm em). A word is corrected only when the corrected form also occurs in the corpus
as written (the evidence that it's a word); the rest are listed for a person to look at. Böll is a misread söll.
Look-alike letters (Cyrillic е, о) become Latin, and the text is NFC (two umlauts were decomposed). Verses too scrambled
to repair (QUARANTINE_VERSES) move out of text/ to quarantined/verses/<book>.txt, as a quarantined book does: no tool's
corpus has them, nothing is lost.
Idempotent: run it again after rebuilding text/ from source/ (study test 2 found the errors, 2026-10-15).

Usage: python3 import/non-free/ch-de-be/bietenhard/fix_ocr.py [--dry-run]
"""
import collections, glob, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
WORD = re.compile(r"[^\W\d_]+")
STRAY = re.compile(r"c(?![hk])", re.I)
FIXED = {"Böll": "söll"}
# Reviewed by hand (2026-10-15): stray-c forms whose corrected form isn't in the corpus, or misreads the c→e rule
# can't reach (an extra c, ch read as c, o read as c, h read as li); each checked against its verse and the corpus.
MANUAL = {
    "Prophetce": "Prophete", "Proschtituicrte": "Proschtituierte", "gsoffc": "gsoffe", "brummlct": "brummlet",
    "Familicvatter": "Familievatter", "tötclige": "tötelige", "öictwäge": "öietwäge", "Abcrysse": "Abrysse",
    "unct": "und", "yncsitzt": "ynesitzt", "zämcsueche": "zämesueche", "loswärdc": "loswärde",
    "ctschlosse": "etschlosse", "Ussagc": "Ussage", "reschpekticret": "reschpektieret",
    "Priestcrklass": "Priesterklass", "Gcsicht": "Geischt", "härcbschickt": "härebschickt", "gsichcret": "gsicheret",
    "Füessc": "Füess", "esc": "eso", "Chriegsheerc": "Chriegsheere", "etrünnc": "etrünne", "hect": "het",
    "Zeice": "Zeiche", "würkclech": "würklech", "ufcerweckt": "uferweckt", "umcgsi": "umegsi", "schc": "scho",
    "stücnde": "stüende", "Schwöscliter": "Schwöschter",
    # e read as o, h as b, li as lf (2026-10-15 split review): every occurrence checked
    "noch": "nech", "beige": "heige", "beseht": "bescht", "Israelfite": "Israelite",
}
# Exact strings (stray marks around a word), applied to the whole text before the word pass; keep these few.
MANUAL_TEXT = [("Mönsc«:.", "Mönsch"), ("e V starche", "e starche"),
    # Stray spaces, fragments and misread short words, reviewed verse by verse (2026-10-15); context keeps each unique
    ("st ärbe", "stärbe"), ("E H uuffe", "E Huuffe"), ("sö lle mir", "sölle mir"), ("R ychi", "Rychi"),
    ("Bärgl and", "Bärgland"), ("Grächtig keit", "Grächtigkeit"), ("A ber Gott", "Aber Gott"), ("I hm ghört", "Ihm ghört"),
    ("R.uef", "Ruef"), ("der R.ych", "der Rych"), ("A m andere Tag", "Am andere Tag"), ("un d si hei", "und si hei"),
    ("Dörfer z ringsetum", "Dörfer zringsetum"), ("z standbringe", "zstandbringe"), ("underw yse", "underwyse"),
    ("bbra cht", "bbracht"), ("gf lüchtet", "gflüchtet"), ("zm itts", "zmitts"), ("Ratsherr e und", "Ratsherre und"),
    ("hö ch Rat", "höch Rat"), ("gä ge di", "gäge di"), ("ufet reit", "ufetreit"), ("Himlen sch und", "Himlen isch und"),
    ("Chöpf zäme zha", "Chöpf zäme z ha"), ("grächt zsy", "grächt z sy"), ("het erz zwöuf", "het er zwöuf"),
    ("dass an: (Grichts", "dass am (Grichts"), ("mv Lohn", "my Lohn"), ("me dt o merkt", "me de o merkt"), ("Mazedonie une i", "Mazedonie und i"), ("Drum alo,", "Drum also,"),
    ("chunt, ür di", "chunt, dür di"), ("dasume nd geit", "dasume und geit"), ("wi si ins drööje", "wi si is drööje"),
    ("nüüt mch ha", "nüüt meh ha"), ("Paulus at tödt", "Paulus tödt"),
    ("zunenand gs gseit", "zunenand gseit"), ("het ser: öffetlech", "het se öffetlech"), ("het is esi Verfählige", "het is üsi Verfählige"),
    ("Rächt zgä", "Rächt ggä"), ("ihm ibe,", "ihm gibe,"), ("seit gen ihm", "seit zuen ihm"),
    ("Vatter ui Toten urerweckt", "Vatter di Toten uferweckt"), ("Mir vei wider", "Mir wei wider"),
    ("und aei ne gfragt", "und hei ne gfragt"), ("Wort, on ig", "Wort, won ig"), ("la k schicke", "la schicke"),
    ("mit äim i der", "mit ihm i der"), ("besucht iüs", "besucht üüs"), ("sogar äsi Synagoge", "sogar üsi Synagoge"),
    ("ggässe li und", "ggässe und"), ("uni de wei", "und de wei"), ("vor de üit", "vor de Lüt"), ("vom i’ald hei", "vom Fäld hei"), ("gseejen rn es", "gseejen es"),
    ("so gum da", "so gump da"), ("steit uff und", "steit uuf und"), ("Mönsch zun ihm", "Mönsch zuen ihm"),
    ("söll öi Friede", "söll öie Friede"), ("zwe Blindi", "zwee Blindi"), ("Was wet dihr", "Was weit dihr"),
    ("Erb üis!", "Erb üüs!"), ("Änderenaa mei si", "Änderenaa hei si"), ("la ligg und", "la lige und"),
    ("ihm gsange.", "ihm ggange."), ("wäg dme Glychnis", "wäg däm Glychnis"),
    ("Am Wägand", "Am Wägrand"), ("se ich gsäiit", "se isch gsäiit"), ("See gsy und", "See gsi und"),
    ("des Wäsche", "ds Wäsche"), ("die heu e Chraft", "die hei e Chraft"), ("Gott eha wüsse", "Gott cha wüsse"),
    ("ohni las Gsetz", "ohni ds Gsetz"), ("S0 ", "So "), ("Gät vne Glüscht", "Gät syne Glüscht"),
    ("ds Urteil. p", "ds Urteil."),
    # verse text across a line break (a hyphenated word; the verse number left inside the next line)
    ("Was sö\n3:11\te mir jitz mache?“ 11 Er", "Was sölle mir jitz mache?“\n3:11\tEr"),
    ("für z\n4:10\tse, söll lose!“, het er gseit. 10 Won", "für z lose, söll lose!“, het er gseit.\n4:10\tWon"),
]
LOOKALIKE = str.maketrans({"е": "e", "о": "o", "Е": "E", "О": "O"})   # Cyrillic letters in Latin words
# Scrambled beyond repair without the printed book (2026-10-15): (book, chapter, verse)
QUARANTINE_VERSES = [("luk", 24, 28), ("luk", 24, 29),
    # damaged in ways only a guess could repair, or with a heading or another verse's text inside (the user: quarantine
    # rather than guess, 2026-10-15)
    ("mrk", 6, 48), ("act", 13, 1), ("1co", 9, 21), ("act", 26, 32), ("act", 27, 3), ("jhn", 4, 15), ("jhn", 5, 2),
    ("luk", 16, 13), ("mrk", 3, 32), ("luk", 20, 26), ("gal", 1, 5), ("act", 19, 10), ("luk", 24, 20), ("mat", 10, 21),
    ("act", 10, 38), ("act", 10, 41), ("act", 10, 46), ("luk", 13, 7), ("luk", 13, 29), ("mat", 13, 11),
    ("jhn", 11, 29), ("rom", 2, 15)]


def quarantine_verses(files, dry):
    """Move the QUARANTINE_VERSES lines out of text/ into quarantined/verses/<book>.txt. -> how many moved now."""
    moved = 0
    for book in sorted({b for b, _, _ in QUARANTINE_VERSES}):
        f = os.path.join(HERE, "text", f"{book}.txt")
        if f not in files:
            continue
        keys = {f"{c}:{v}" for b, c, v in QUARANTINE_VERSES if b == book}
        lines = open(f, encoding="utf-8").read().split("\n")
        out = [l for l in lines if l.split("\t", 1)[0] in keys and "\t" in l]
        if not out:
            continue
        moved += len(out)
        if dry:
            continue
        q = os.path.join(HERE, "quarantined", "verses")
        os.makedirs(q, exist_ok=True)
        with open(os.path.join(q, f"{book}.txt"), "a", encoding="utf-8") as w:
            w.write("\n".join(out) + "\n")
        open(f, "w", encoding="utf-8").write("\n".join(l for l in lines if l not in out))
    return moved


def candidate(w):
    """w with every stray c as e, keeping a word-initial capital C (names)."""
    head, rest = (w[0], w[1:]) if w[0] == "C" else ("", w)
    return head + STRAY.sub(lambda m: "e" if m[0] == "c" else "E", rest)


def main():
    files = sorted(glob.glob(os.path.join(HERE, "text", "*.txt")))
    dry = "--dry-run" in sys.argv
    moved = quarantine_verses(files, dry)
    texts = {f: unicodedata.normalize("NFC", open(f, encoding="utf-8").read()).translate(LOOKALIKE) for f in files}
    raw = {f: open(f, encoding="utf-8").read() for f in files}
    known = collections.Counter(w for t in texts.values() for w in WORD.findall(t) if not STRAY.search(w[1:] if w[0] == "C" else w))
    fixes, unsure = collections.Counter(), collections.Counter()

    def fix(m):
        w = m[0]
        if w in MANUAL:
            fixes[(w, MANUAL[w])] += 1
            return MANUAL[w]
        if w in FIXED:
            fixes[(w, FIXED[w])] += 1
            return FIXED[w]
        if not STRAY.search(w[1:] if w[0] == "C" else w):
            return w
        c = candidate(w)
        if known[c] or known[c.lower()] or known[c[:1].upper() + c[1:]]:
            fixes[(w, c)] += 1
            return c
        unsure[w] += 1
        return w
    for f, t in texts.items():
        new = t
        for old, rep in MANUAL_TEXT:
            if old in new:
                fixes[(old, rep)] += new.count(old)
                new = new.replace(old, rep)
        new = WORD.sub(fix, new)
        if new != raw[f] and not dry:
            open(f, "w", encoding="utf-8").write(new)
    print(f"{sum(fixes.values())} words corrected ({len(fixes)} forms); {sum(unsure.values())} left for a person "
          f"({len(unsure)} forms); {moved} scrambled verses moved to quarantined/verses/" + (" [dry run]" if dry else ""))
    print("  most frequent: " + ", ".join(f"{a}→{b} {n}" for (a, b), n in fixes.most_common(15)))
    if unsure:
        print("  left: " + ", ".join(f"{w} {n}" for w, n in unsure.most_common()))


if __name__ == "__main__":
    main()
