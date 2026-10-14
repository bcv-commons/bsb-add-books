"""Extract the whole Berean Greek Bible NT (download/berean/bgb.docx,
https://greekbible.org/bgb.docx - the Greek text the BSB is translated from)
into orig/grc/<code>NNN.txt, one verse per line: '<chapter>:<verse> <greek>'.
BGB footnotes (text-critical and OT-quote notes) go to orig/grc/<code>NNN_notes.txt.

Footnote markers in the BGB are Latin letters glued to a Greek word ('Ἐφέσῳa');
they are removed from the text and kept only in the notes file. The BGB
signs ‹…› (bracketed/doubtful words) and ⇔ (word-order note) are kept.

Usage: python3 scripts/extract_bgb.py
"""
import html, os, re, zipfile
from books import BOOKS, ROOT

SRC = os.path.join(ROOT, "download", "berean", "bgb.docx")
OUT = os.path.join(ROOT, "orig", "grc")
GREEK = r"[Ͱ-Ͽἀ-῿]"
NT = [(code, name) for code, name, t, _ in BOOKS if t == "nt"]
CHAPTER = re.compile(r"(%s) (\d+)" % "|".join(re.escape(n) for _, n in NT))


def paragraphs():
    x = zipfile.ZipFile(SRC).read("word/document.xml").decode("utf-8")
    return [html.unescape("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)))
            for p in re.findall(r"<w:p[ >].*?</w:p>", x, flags=re.S)]


def is_greek(p):
    return len(re.findall(GREEK, p)) > len(re.findall(r"[A-Za-z]", p))


def main():
    code_of = {name: code for code, name in NT}
    verses, notes = {}, {}          # (code, chapter) -> {verse: text} / [note lines]
    key = None
    for p in paragraphs():
        m = CHAPTER.fullmatch(p.strip())
        if m:
            key = (code_of[m.group(1)], int(m.group(2)))
            verses[key], notes[key] = {}, []
            continue
        if key is None:
            continue
        if re.match(r"^[a-z]{1,2} \d", p):
            # footnote paragraph: 'a 30 text...b 31 text...'
            for fm in re.finditer(r"([a-z]{1,2}) (\d+(?:[-–]\d+)?) (.*?)(?=(?:(?<=[^\s])[a-z]{1,2} \d+ )|$)", p):
                notes[key].append(f"{fm.group(2)} [{fm.group(1)}] {fm.group(3).strip()}")
            continue
        if not is_greek(p):
            continue  # English section heading or book title
        # split on verse numbers 'N\xa0'; text before the first number continues the last verse
        parts = re.split(r"(?:^|\s)(\d+)\xa0", p)
        lead, rest = parts[0], parts[1:]
        cur = max(verses[key]) if verses[key] else None
        if lead.strip() and cur is not None:
            verses[key][cur] += " " + lead.strip()
        for i in range(0, len(rest), 2):
            verses[key][int(rest[i])] = rest[i + 1].strip()
    os.makedirs(OUT, exist_ok=True)
    for (code, c), vs in sorted(verses.items()):
        lines = [f"{code} {c}"]
        for v in sorted(vs):
            # footnote letters sit right after a Greek letter or after closing punctuation
            t = re.sub(rf"(?<=(?:{GREEK}|[,.·;:’”)\]]))[a-z]{{1,2}}(?=[\s,.·;:’”“)]|$)", "", vs[v])
            t = re.sub(r"\s+", " ", t).strip()
            lines.append(f"{c}:{v} {t}")
        open(os.path.join(OUT, f"{code}{c:03d}.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
        if notes[(code, c)]:
            open(os.path.join(OUT, f"{code}{c:03d}_notes.txt"), "w", encoding="utf-8").write("\n".join(notes[(code, c)]) + "\n")
    print(f"orig/grc: {len(verses)} chapters, {sum(len(v) for v in verses.values())} verses")


if __name__ == "__main__":
    main()
