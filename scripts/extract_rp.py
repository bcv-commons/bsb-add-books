"""Extract the Robinson-Pierpont Byzantine Textform 2018 (public domain,
github.com/byztxt/byzantine-majority-text, cloned to download/rp/) into
orig/grc-rp/<code>NNN.txt, one verse per line: '<chapter>:<verse> <greek>'.

Source: csv-unicode/ccat/no-variants/<RP>.csv (chapter,verse,text).
- The paragraph sign ¶ is removed from the text.
- John 7,53-8,11 (Pericope Adulterae) is part of JOH.csv; it is kept.
- The alternative form of Acts 24,6-8 (ACT24.csv) goes to act024_notes.txt.
- Differences against Nestle-Aland, marked in csv-unicode/ccat/with-variants
  as '{NA <RP words> > <NA words> }', go to <code>NNN_notes.txt as
  '<verse> NA: <RP> > <NA>'.

Usage: python3 scripts/extract_rp.py
"""
import csv, os, re
from collections import defaultdict
from books import BOOKS, ROOT

SRC = os.path.join(ROOT, "download", "rp", "csv-unicode", "ccat")
OUT = os.path.join(ROOT, "orig", "grc-rp")


def rows(path):
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            yield int(r["chapter"]), int(r["verse"]), r["text"]


def clean(t):
    return re.sub(r"\s+", " ", t.replace("¶", "")).strip()


def main():
    os.makedirs(OUT, exist_ok=True)
    nchap = nverse = 0
    for code, name, t, rp in BOOKS:
        if t != "nt":
            continue
        text, notes = defaultdict(dict), defaultdict(list)
        for c, v, s in rows(os.path.join(SRC, "no-variants", f"{rp}.csv")):
            text[c][v] = clean(s)
        for c, v, s in rows(os.path.join(SRC, "with-variants", f"{rp}.csv")):
            for m in re.finditer(r"\{NA ([^>}]*)>([^}]*)\}", s):
                notes[c].append(f"{v} NA: {clean(m.group(1))} > {clean(m.group(2))}")
        if code == "act":
            for c, v, s in rows(os.path.join(SRC, "no-variants", "ACT24.csv")):
                notes[c].append(f"{v} RP alternative form (ACT24.csv): {clean(s)}")
        for c in sorted(text):
            lines = [f"{code} {c}"] + [f"{c}:{v} {text[c][v]}" for v in sorted(text[c])]
            open(os.path.join(OUT, f"{code}{c:03d}.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
            if notes[c]:
                open(os.path.join(OUT, f"{code}{c:03d}_notes.txt"), "w", encoding="utf-8").write("\n".join(notes[c]) + "\n")
            nchap += 1
            nverse += len(text[c])
    print(f"orig/grc-rp: {nchap} chapters, {nverse} verses")


if __name__ == "__main__":
    main()
