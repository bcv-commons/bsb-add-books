"""The book table shared by all scripts.

Every file in this repo is named with the BSB book code plus a three-digit
chapter number (`gen001.txt`, `jhn003.txt`). This table maps those codes
to the names used by the sources:

    code   BSB code (file names in reference/BSB/, reference/MSB/, orig/heb/, orig/grc/, orig/grc-rp/)
    name   English book name (as in the BGB .docx, e.g. "1 Corinthians")
    t      testament: "ot" or "nt"
    rp     Robinson-Pierpont CSV file name (download/rp/csv-unicode/...), NT only

Run `python3 scripts/books.py` to (re)write books.tsv with chapter counts.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BOOKS = [
    # code, name, testament, rp code
    ("gen", "Genesis", "ot", None),
    ("exo", "Exodus", "ot", None),
    ("lev", "Leviticus", "ot", None),
    ("num", "Numbers", "ot", None),
    ("deu", "Deuteronomy", "ot", None),
    ("jos", "Joshua", "ot", None),
    ("jdg", "Judges", "ot", None),
    ("rut", "Ruth", "ot", None),
    ("1sa", "1 Samuel", "ot", None),
    ("2sa", "2 Samuel", "ot", None),
    ("1ki", "1 Kings", "ot", None),
    ("2ki", "2 Kings", "ot", None),
    ("1ch", "1 Chronicles", "ot", None),
    ("2ch", "2 Chronicles", "ot", None),
    ("ezr", "Ezra", "ot", None),
    ("neh", "Nehemiah", "ot", None),
    ("est", "Esther", "ot", None),
    ("job", "Job", "ot", None),
    ("psa", "Psalms", "ot", None),
    ("pro", "Proverbs", "ot", None),
    ("ecc", "Ecclesiastes", "ot", None),
    ("sng", "Song of Songs", "ot", None),
    ("isa", "Isaiah", "ot", None),
    ("jer", "Jeremiah", "ot", None),
    ("lam", "Lamentations", "ot", None),
    ("ezk", "Ezekiel", "ot", None),
    ("dan", "Daniel", "ot", None),
    ("hos", "Hosea", "ot", None),
    ("jol", "Joel", "ot", None),
    ("amo", "Amos", "ot", None),
    ("oba", "Obadiah", "ot", None),
    ("jon", "Jonah", "ot", None),
    ("mic", "Micah", "ot", None),
    ("nam", "Nahum", "ot", None),
    ("hab", "Habakkuk", "ot", None),
    ("zep", "Zephaniah", "ot", None),
    ("hag", "Haggai", "ot", None),
    ("zec", "Zechariah", "ot", None),
    ("mal", "Malachi", "ot", None),
    ("mat", "Matthew", "nt", "MAT"),
    ("mrk", "Mark", "nt", "MAR"),
    ("luk", "Luke", "nt", "LUK"),
    ("jhn", "John", "nt", "JOH"),
    ("act", "Acts", "nt", "ACT"),
    ("rom", "Romans", "nt", "ROM"),
    ("1co", "1 Corinthians", "nt", "1CO"),
    ("2co", "2 Corinthians", "nt", "2CO"),
    ("gal", "Galatians", "nt", "GAL"),
    ("eph", "Ephesians", "nt", "EPH"),
    ("php", "Philippians", "nt", "PHP"),
    ("col", "Colossians", "nt", "COL"),
    ("1th", "1 Thessalonians", "nt", "1TH"),
    ("2th", "2 Thessalonians", "nt", "2TH"),
    ("1ti", "1 Timothy", "nt", "1TI"),
    ("2ti", "2 Timothy", "nt", "2TI"),
    ("tit", "Titus", "nt", "TIT"),
    ("phm", "Philemon", "nt", "PHM"),
    ("heb", "Hebrews", "nt", "HEB"),
    ("jas", "James", "nt", "JAM"),
    ("1pe", "1 Peter", "nt", "1PE"),
    ("2pe", "2 Peter", "nt", "2PE"),
    ("1jn", "1 John", "nt", "1JO"),
    ("2jn", "2 John", "nt", "2JO"),
    ("3jn", "3 John", "nt", "3JO"),
    ("jud", "Jude", "nt", "JUD"),
    ("rev", "Revelation", "nt", "REV"),
]

BY_CODE = {b[0]: b for b in BOOKS}


def chapters(code):
    """Number of chapters, counted from the BSB files."""
    d = os.path.join(ROOT, "reference", "BSB")
    return len([f for f in os.listdir(d) if f[:3] == code and f[3:6].isdigit()])


# Books whose Hebrew chapter count differs from the BSB's (Joel 2:28-3:21 BSB = 3-4 Hebrew; Mal 4 BSB = 3:19-24 Hebrew).
HEB_CHAPTERS = {"jol": 4, "mal": 3}


def heb_chapters(code):
    """Number of chapters in the Hebrew numbering (orig/heb)."""
    return HEB_CHAPTERS.get(code) or chapters(code)


if __name__ == "__main__":
    rows = ["code\tname\ttestament\tchapters\trp_code"]
    for code, name, t, rp in BOOKS:
        rows.append(f"{code}\t{name}\t{t}\t{chapters(code)}\t{rp or ''}")
    open(os.path.join(ROOT, "books.tsv"), "w", encoding="utf-8").write("\n".join(rows) + "\n")
    print(f"books.tsv: {len(BOOKS)} books")
