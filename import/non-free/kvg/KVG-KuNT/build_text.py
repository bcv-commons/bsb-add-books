#!/usr/bin/env python3
"""Build this edition's text from the Paratext SFM files in source/ (the Kuni NT and its glossary).

- text/<code>NNN.txt: one file per chapter, in the repo's chapter format (scripts/convert_usj.py):
  '===Book, chapter N===', '==heading==', inline 'vN' markers, cross references as {H: …}.
  The text is normalised to NFC (the SFM files are NFD), so that words can be counted and matched.
- glossary.tsv: the glossary book (A9GLO) as term, English equivalent, explanation (Kuni).
- OT books in source/ (since 2026-10-15: Genesis 1-30, Ruth, Jonah, newer than eBible's) are renumbered to the
  Hebrew verses (repo rule, orig/vrs).
- --ot: Ruth and Jonah from eBible's edition 'kvg' (the same translation, © 2015 Wycliffe Switzerland, an
  older state), into text/<code>NNN.txt, only where source/ doesn't have them.
  (Until 2026-10-14 they were held out in holdout/ as the test set of the Ruth drafting test.) The
  eBible NT is compared with source/ and the number of differing verses reported.
- Without source/ (a fresh clone: the working copy is not in git), the whole text and the glossary
  are built from eBible's published edition instead: the same books, an older state of the NT.

Usage: python3 import/non-free/kvg/KVG-KuNT/build_text.py [--ot]
"""
import glob, io, os, re, sys, unicodedata, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from books import BY_CODE                      # noqa: E402
from convert_usj import chapter_text, split_chapters, render  # noqa: E402
from usfm_usj import usfm_to_usj               # noqa: E402

NAME = "Mbumbukiam-qa Manqat Mbomambaqape (Kuni NT)"
SOURCE = "Kuni/Boazi [kvg], Kuni dialect, Paratext SFM files in source/"
EBIBLE_SOURCE = "https://ebible.org/kvg/ (© 2015 Wycliffe Switzerland)"
NFC = lambda s: unicodedata.normalize("NFC", s)


def book_of(usfm):
    m = re.match(r"\\id (\w+)", usfm)
    return m[1] if m else None


def title_of(content, code):
    for c in content:
        if c.get("type") == "para" and c.get("marker") == "h":
            return re.sub(r"\s+", " ", render(c.get("content", []))).strip()
    return code


def write_chapters(usfm, out_dir, name, source):
    content = usfm_to_usj(NFC(usfm))["content"]
    code = book_of(usfm).lower()
    title = title_of(content, code)
    n = 0
    for number, items in split_chapters(content):
        text = chapter_text(name, source, code.upper(), title, number, items)
        open(os.path.join(out_dir, f"{code}{number:03d}.txt"), "w", encoding="utf-8").write(text)
        n += 1
    return code, n


def verses(usfm):
    """{(chapter, verse): text} from raw USFM, markup removed, NFC, whitespace collapsed."""
    out, ch, cur = {}, 0, None
    usfm = NFC(usfm)
    usfm = re.sub(r"\\x .*?\\x\*|\\f .*?\\f\*", "", usfm, flags=re.S)
    for part in re.split(r"(\\c \d+|\\v \d+[-\d]*)", usfm):
        m = re.match(r"\\c (\d+)", part)
        if m:
            ch = int(m[1]); cur = None; continue
        m = re.match(r"\\v (\d+)", part)
        if m:
            cur = (ch, int(m[1])); out[cur] = ""; continue
        if ch and out and cur in out:
            body = part.split("\\s", 1)[0] if "\\s " in part else part
            out[cur] += re.sub(r"\\\+?\w+\*?", " ", body)
    return {k: re.sub(r"\s+", " ", v).strip() for k, v in out.items()}


def glossary(usfm):
    rows, cur = [], None
    for line in NFC(usfm).splitlines():
        m = re.match(r"\\li1 \\k (.+?)\\k\*\s*(?:\\tl \((.*?)\)\\tl\*)?", line)
        if m:
            cur = [m[1].strip(), (m[2] or "").strip(), ""]
            rows.append(cur)
        elif cur and re.match(r"\\(pi1|mi1|p|m)\b", line):
            t = re.sub(r"\\\+?\w+\*?", " ", line.split(" ", 1)[1] if " " in line else "")
            cur[2] = (cur[2] + " " + re.sub(r"\s+", " ", t)).strip()
    return rows


def main():
    text_dir = os.path.join(HERE, "text")
    os.makedirs(text_dir, exist_ok=True)
    total = 0
    local = {}
    sfm = sorted(glob.glob(os.path.join(HERE, "source", "KVG-*.sfm")))
    if not sfm:
        return from_ebible(text_dir)
    for path in sfm:
        usfm = open(path, encoding="utf-8-sig").read()
        bid = book_of(usfm)
        if bid == "GLO":
            rows = glossary(usfm)
            with open(os.path.join(HERE, "glossary.tsv"), "w", encoding="utf-8") as f:
                f.write("term\tenglish\texplanation\n")
                f.writelines("\t".join(r) + "\n" for r in rows)
            print(f"glossary.tsv: {len(rows)} terms")
            continue
        if not bid or bid.lower() not in BY_CODE:
            print(f"skipped {os.path.basename(path)} (book {bid})")
            continue
        code, n = write_chapters(usfm, text_dir, NAME, SOURCE)
        local[code] = verses(usfm)
        total += n
    print(f"text/: {total} chapters of {len(local)} books")
    for code in sorted(local):
        if BY_CODE[code][2] == "ot":
            hebrew_numbering(text_dir, code)

    if "--ot" in sys.argv:
        from fetch_edition import get, EBIBLE, DL
        z = ebible_zip()
        diff = same = 0
        for n in sorted(z.namelist()):
            if not n.endswith(".usfm"):
                continue
            usfm = z.read(n).decode("utf-8-sig")
            code = (book_of(usfm) or "").lower()
            if code in ("rut", "jon") and code not in local:
                _, k = write_chapters(usfm, text_dir, "Kuni (eBible kvg)", EBIBLE_SOURCE)
                print(f"text/: {code} {k} chapters (eBible)")
            elif code in local:
                ev = verses(usfm)
                for key, t in local[code].items():
                    if key in ev:
                        same += ev[key] == t
                        diff += ev[key] != t
        print(f"eBible NT against source/: {same} verses the same, {diff} different")
        for code in ("rut", "jon"):
            if code not in local:
                hebrew_numbering(text_dir, code)


def ebible_zip():
    from fetch_edition import get, EBIBLE, DL
    return zipfile.ZipFile(io.BytesIO(get(f"{EBIBLE}/kvg_usfm.zip", os.path.join(DL, "kvg", "kvg_usfm.zip"))))


def from_ebible(text_dir):
    """No working copy in source/: every book and the glossary from eBible's published text."""
    print("source/ has no SFM files: building text/ and glossary.tsv from eBible 'kvg' (the published text)")
    z, total, books = ebible_zip(), 0, 0
    for n in sorted(z.namelist()):
        if not n.endswith(".usfm"):
            continue
        usfm = z.read(n).decode("utf-8-sig")
        bid = book_of(usfm) or ""
        if bid == "GLO":
            rows = glossary(usfm)
            with open(os.path.join(HERE, "glossary.tsv"), "w", encoding="utf-8") as f:
                f.write("term\tenglish\texplanation\n")
                f.writelines("\t".join(r) + "\n" for r in rows)
            print(f"glossary.tsv: {len(rows)} terms")
        elif bid.lower() in BY_CODE:
            _, k = write_chapters(usfm, text_dir, NAME, EBIBLE_SOURCE)
            total += k; books += 1
    print(f"text/: {total} chapters of {books} books (eBible)")
    for code in ("rut", "jon"):
        hebrew_numbering(text_dir, code)


def hebrew_numbering(text_dir, code):
    """Renumber an OT book from eBible's English numbering to the Hebrew (repo rule), by orig/vrs.
    A verse that moves to another chapter is cut out of its chapter with its text and put at the
    start (or end) of the Hebrew chapter; verse markers within a chapter are renumbered."""
    import vrs
    from books import heb_chapters
    files = {c: os.path.join(text_dir, f"{code}{c:03d}.txt") for c in range(1, heb_chapters(code) + 1)}
    texts = {c: open(f, encoding="utf-8").read() for c, f in files.items() if os.path.exists(f)}
    marker = lambda v: re.compile(rf"(?<![\w>.])v{v}(?=\s)")
    def cut(c, v):                       # the text of verse v of English chapter c, removed from it
        t = texts[c]
        m = marker(v).search(t)
        n = re.compile(r"(?<![\w>.])v\d+(?=\s)").search(t, m.end())
        seg = t[m.end():n.start() if n else len(t)]
        texts[c] = t[:m.start()] + (t[n.start():] if n else "").rstrip() + ("\n" if not n else "")
        return re.sub(r"\s+", " ", seg).strip()
    moved, renames = {}, {}
    for c in texts:
        for hv in vrs.heb_verses(code, c):
            ec, ev = vrs.to_bsb(code, c, hv)
            if ec != c:
                moved.setdefault(c, []).append((hv, cut(ec, ev)))
            elif ev != hv:
                renames.setdefault(c, {})[ev] = hv
    for c, ren in renames.items():
        texts[c] = re.sub(r"(?<![\w>.])v(\d+)(?=\s)", lambda m: f"v{ren.get(int(m[1]), int(m[1]))}", texts[c])
    for c, items in moved.items():
        t = texts[c]
        first = int(re.search(r"(?<![\w>.])v(\d+)(?=\s)", t)[1]) if re.search(r"(?<![\w>.])v(\d+)(?=\s)", t) else 0
        pre = "".join(f"v{hv} {seg} " for hv, seg in items if hv < first).strip()
        post = "".join(f" v{hv} {seg}" for hv, seg in items if hv >= first)
        if pre:
            t = re.sub(r"(===.*===\n)", lambda m: m[1] + "\n" + pre + "\n", t, count=1)
        texts[c] = t.rstrip() + post + "\n"
    for c, t in texts.items():
        open(files[c], "w", encoding="utf-8").write(re.sub(r"\n{3,}", "\n\n", t))
    if moved or renames:
        print(f"text/: {code} renumbered to the Hebrew verses ({sum(len(v) for v in moved.values())} moved across chapters)")


if __name__ == "__main__":
    main()
