#!/usr/bin/env python3
"""Convert a Berean USJ export (BSB or MSB, from github.com/BSB-publishing/bsb2usfm
releases) into the per-chapter plain-text format of this repo.

Input:  download/<ED>/<BOOKID>.usj   (USJ 3.0 JSON, one file per book)
Output: reference/<ED>/<code><chapter>.txt     (e.g. reference/BSB/gen001.txt, reference/MSB/jhn003.txt)

Format: header lines '!!<…>!!', '===Book, chapter N===', '==headings==',
inline 'vN' verse markers, poetry lines '//1 …', footnotes inline as '{T: …}', cross references
as '{H: …}'.

Unlike older plain-text converters, verse markers and footnotes nested inside
character styles (e.g. \\wj, the words of Jesus) are kept.

Usage: python3 scripts/convert_usj.py BSB
       python3 scripts/convert_usj.py MSB --nt
"""
import glob, json, os, re, sys
from books import BY_CODE, ROOT

EDITIONS = {
    "BSB": ("Berean Standard Bible (BSB)", "https://bereanbible.com (public domain)"),
    "MSB": ("Majority Standard Bible (MSB)", "https://majoritybible.com (public domain)"),
}
HEADING_MARKERS = {"s", "s1", "s2", "s3", "ms", "qa"}
POETRY_MARKERS = {"q": 1, "q1": 1, "q2": 2, "q3": 3, "q4": 4, "qr": 1}
SKIP_MARKERS = {"toc1", "toc2", "toc3", "mt1", "mt2", "mt3", "h", "r"}
BLANK_MARKERS = {"b"}


def note_text(note):
    parts = []
    for sub in note.get("content", []):
        if isinstance(sub, str):
            parts.append(sub)
        elif isinstance(sub, dict) and sub.get("type") == "char" and sub.get("marker") not in ("fr", "xo"):
            parts.append(render(sub.get("content", []), in_note=True))
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def render(content, in_note=False):
    """Flatten inline content, recursing into char/ref spans."""
    out = []
    for sub in content:
        if isinstance(sub, str):
            out.append(sub)
        elif isinstance(sub, dict):
            t = sub.get("type")
            if t == "verse" and not in_note:
                out.append(" v%s " % sub.get("number"))
            elif t == "note" and not in_note:
                text = note_text(sub)
                if text:      # cross references (\\x) as {H: …}, other notes as {T: …}
                    out.append(("{H: %s}" if sub.get("marker") == "x" else "{T: %s}") % text)
            elif t in ("char", "ref"):
                out.append(render(sub.get("content", []), in_note))
    return "".join(out)


def para_text(item):
    return re.sub(r"[ \t]+", " ", render(item.get("content", []))).strip()


def chapter_title(book_id, title, number):
    return "Psalm %d" % number if book_id == "PSA" else "%s, chapter %d" % (title, number)


def split_chapters(content):
    number, items = None, []
    for item in content:
        if item.get("type") == "chapter":
            if number is not None:
                yield number, items
            number, items = int(item["number"]), []
        elif number is not None:
            items.append(item)
    if number is not None:
        yield number, items


def convert_chapter(ed, book_id, title, number, items):
    return chapter_text(*EDITIONS[ed], book_id, title, number, items)


def bracket_to_next(text):
    """an opening [ printed before a verse number (a traditional verse a critical text keeps in brackets) belongs to
    that verse, not to the end of the one before: "… X. [ v21 Y]" -> "… X. v21 [Y]"."""
    return re.sub(r"[ \t]*\[(\s*)(v\d+) ", lambda m: (m[1] or " ") + m[2] + " [", text)


def chapter_text(name, source, book_id, title, number, items):
    """One chapter file from USJ paragraph items (also used by fetch_edition.py)."""
    lines = ["!!<Translation: %s>!!" % name, "!!<Source: %s>!!" % source, "",
             "===%s===" % chapter_title(book_id, title, number), ""]
    paragraph = []

    def flush():
        if paragraph:
            lines.extend([" ".join(paragraph).strip(), ""])
            paragraph.clear()

    for item in items:
        if item.get("type") != "para":
            continue
        marker = item.get("marker")
        if marker in SKIP_MARKERS:
            continue
        if marker in BLANK_MARKERS:
            flush()
            continue
        text = para_text(item)
        if marker in HEADING_MARKERS:
            flush()
            if text:
                lines.extend(["==%s==" % text, ""])
        elif marker in POETRY_MARKERS:
            flush()
            if text:
                lines.extend(["//%d %s" % (POETRY_MARKERS[marker], text), ""])
        elif text:
            paragraph.append(text)
    flush()
    while lines and lines[-1] == "":
        lines.pop()
    return bracket_to_next("\n".join(lines) + "\n")


def main():
    ed = sys.argv[1]
    nt_only = "--nt" in sys.argv
    out_dir = os.path.join(ROOT, "reference", ed)
    os.makedirs(out_dir, exist_ok=True)
    count = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "download", ed, "*.usj"))):
        data = json.load(open(path, encoding="utf-8"))
        content = data["content"]
        book_id = next((i.get("code") for i in content if i.get("type") == "book"), None)
        if not book_id or book_id.lower() not in BY_CODE:
            continue
        if nt_only and BY_CODE[book_id.lower()][2] != "nt":
            continue
        title = next((para_text(i) for i in content if i.get("type") == "para" and i.get("marker") == "h"), book_id)
        for number, items in split_chapters(content):
            with open(os.path.join(out_dir, "%s%03d.txt" % (book_id.lower(), number)), "w", encoding="utf-8") as f:
                f.write(convert_chapter(ed, book_id, title, number, items))
            count += 1
    print("%s: %d chapter files" % (ed, count))


if __name__ == "__main__":
    main()
