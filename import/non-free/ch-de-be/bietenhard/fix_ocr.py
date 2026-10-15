#!/usr/bin/env python3
"""Correct the OCR misreadings in text/ (the publisher's .docx files came from a scan).

Bern German writes c only in ch and ck (and in names: Cäsarea, Crispus), so a c before anything else is a misread e
(hct het, gscit gseit, scch sech, cm em). A word is corrected only when the corrected form also occurs in the corpus
as written (the evidence that it's a word); the rest are listed for a person to look at. Böll is a misread söll.
Idempotent: run it again after rebuilding text/ from source/ (study test 2 found the errors, 2026-10-15).

Usage: python3 import/non-free/ch-de-be/bietenhard/fix_ocr.py [--dry-run]
"""
import collections, glob, os, re, sys

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
}
# Exact strings (stray marks around a word), applied to the whole text before the word pass; keep these few.
MANUAL_TEXT = [("Mönsc«:.", "Mönsch"), ("e V starche", "e starche")]


def candidate(w):
    """w with every stray c as e, keeping a word-initial capital C (names)."""
    head, rest = (w[0], w[1:]) if w[0] == "C" else ("", w)
    return head + STRAY.sub(lambda m: "e" if m[0] == "c" else "E", rest)


def main():
    files = sorted(glob.glob(os.path.join(HERE, "text", "*.txt")))
    texts = {f: open(f, encoding="utf-8").read() for f in files}
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
        if new != t and "--dry-run" not in sys.argv:
            open(f, "w", encoding="utf-8").write(new)
    print(f"{sum(fixes.values())} words corrected ({len(fixes)} forms); {sum(unsure.values())} left for a person "
          f"({len(unsure)} forms)" + (" [dry run]" if "--dry-run" in sys.argv else ""))
    print("  most frequent: " + ", ".join(f"{a}→{b} {n}" for (a, b), n in fixes.most_common(15)))
    if unsure:
        print("  left: " + ", ".join(f"{w} {n}" for w, n in unsure.most_common()))


if __name__ == "__main__":
    main()
