#!/usr/bin/env python3
"""The SFM profile of an edition: how the team's own Paratext files are written, read from the books themselves (their
Settings.xml is not needed), so that what we send back (scripts/export_usfm.py) is in the same form.

Reads <edition dir>/source/*.sfm (not the Earlier Attempts files) and detects:
  encoding, bom            UTF-8 or not; a byte-order mark
  normalization            NFD or NFC (a team's files may be NFD; Paratext's word list compares code points)
  line_endings             crlf or lf
  versification            english or hebrew: in every chapter of theirs where the Hebrew and the English (BSB)
                           verse counts differ (Joel 2-4, Malachi 3-4, Jonah 1-2, the Psalm titles, Genesis 31-32, ...),
                           which one their last verse matches; with the evidence, and a guess where no such chapter is
  id_line, ide             the \\id line ({BOOK} for the code) and whether a \\ide line follows it
  file_pattern             the file names ({nn}{BOOK}: Paratext's book number and code)
  heading                  the section heading marker (s or s1)
  paragraphs               the paragraph and poetry markers they use (p, m, b, q1, q2, pi1, li1, ...)
  divine_name              the words they mark \\nd ...\\nd*
  footnotes                the parts of their footnotes (fr fk ft)
  also                     markup we don't produce, recorded only (cross references, glossary words, figures)
Where books disagree, the profile follows the newest book: the latest year in the \\id lines when every book has one,
else the book whose \\id form the fewest books share (a team's current work beside its published set: a guess, said so;
--newest BOOK settles it), and lists what the older books do differently (`differs_in_older_books`).

Without --write it prints the profile, its evidence and what is uncertain, and the differences from the edition's
stored `sfm:` block; --write puts the block into edition.yaml (the rest of the file kept as it is).

Usage: python3 scripts/sfm_profile.py <edition id | edition dir> [--newest BOOK] [--write]
"""
import collections, datetime, glob, os, re, sys, unicodedata

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
from books import BOOKS, BY_CODE  # noqa: E402

PARAS = ("p", "m", "b", "nb", "pi", "pi1", "pi2", "mi", "pmo", "q", "q1", "q2", "q3", "qr", "qc", "li", "li1", "li2")
ALSO = {"x": "cross references", "r": "parallel passages", "k": "glossary words", "w": "glossary words",
        "fig": "figures", "tl": "transliterations", "it": "italics", "bk": "book titles", "qs": "selah"}
YEAR = re.compile(r"\b(19|20)\d\d\b")


def edition_dir(arg):
    if os.path.isdir(arg):
        return os.path.abspath(arg)
    from project import edition
    return os.path.join(ROOT, edition(arg)["dir"])


def sfm_files(d):
    return [f for f in sorted(glob.glob(os.path.join(d, "source", "*.[sS][fF][mM]")))
            if "Earlier" not in os.path.basename(f)]


def read(f):
    """one file's conventions"""
    raw = open(f, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        text, enc = raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        text, enc = raw.decode("latin-1"), "not utf-8"
    nfd, nfc = text == unicodedata.normalize("NFD", text), text == unicodedata.normalize("NFC", text)
    first = text.lstrip().splitlines()[0] if text.strip() else ""
    m = re.match(r"\\id (\w{3})\b", first)
    code = m[1].lower() if m else None
    lines = text.splitlines()
    i = next((k for k, l in enumerate(lines) if l.startswith("\\id")), -1)
    markers = collections.Counter(re.findall(r"\\\+?([a-z]+\d?)(?![a-z*])", text))
    chapters, c = collections.defaultdict(int), 0
    for mk, n in re.findall(r"\\(c|v) (\d+)", text):
        if mk == "c":
            c = int(n)
        else:
            chapters[c] = max(chapters[c], int(n))
    nd = collections.Counter(unicodedata.normalize("NFC", w).strip(" ,.;:!?") for w in re.findall(r"\\nd (.*?)\\nd\*", text))
    fns = re.findall(r"\\f (.*?)\\f\*", text, re.S)
    parts = collections.Counter(p for x in fns for p in set(re.findall(r"\\(fr|fk|fq|fqa|fl|ft|fv)\b", x)))
    return {"file": os.path.basename(f), "code": code, "encoding": enc, "bom": bom,
            "normalization": "NFD" if nfd and not nfc else "NFC" if nfc and not nfd else "either" if nfc else "mixed",
            "line_endings": "crlf" if b"\r\n" in raw else "lf",
            "id_line": re.sub(rf"^\\id {code.upper()}\b", "\\\\id {BOOK}", first) if code else first,
            "ide": i >= 0 and i + 1 < len(lines) and lines[i + 1].startswith("\\ide"),
            "year": max(map(int, (m_.group(0) for m_ in YEAR.finditer(first))), default=None),
            "markers": markers, "chapters": dict(chapters), "nd": nd,
            "footnotes": len(fns), "footnote_parts": parts}


def file_pattern(name, code):
    """XYZ-01GEN-Name 1-30.sfm -> XYZ-{nn}{BOOK}-Name.sfm (a chapter range in the name dropped)"""
    if not code:
        return None
    pat = re.sub(rf"\d\d{code.upper()}", "{nn}{BOOK}", name, count=1, flags=re.I)
    if pat == name:
        pat = re.sub(code.upper(), "{BOOK}", name, count=1, flags=re.I)
    return re.sub(r" [\d-]+(?=\.\w+$)", "", pat)


def versification(books):
    """(english|hebrew|None, evidence): the chapters where the Hebrew and the English verse counts differ"""
    import vrs
    sys.path.insert(0, os.path.join(CODE, "scripts"))
    import langtools as LT
    votes, ev = collections.Counter(), []
    for b in books:
        code = b["code"]
        if not code or code not in BY_CODE or BY_CODE[code][2] == "nt":
            continue
        for c, last in sorted(b["chapters"].items()):
            if not c:
                continue
            try:
                heb = max(vrs.heb_verses(code, c) or [0])
            except Exception:  # noqa: BLE001 - a chapter Hebrew doesn't have (Malachi 4)
                heb = 0
            f = os.path.join(ROOT, "reference", "BSB", f"{code}{c:03d}.txt")
            eng = max((v for (_, v) in LT.verses_of(f)), default=0) if os.path.exists(f) else 0
            if heb == eng or last not in (heb, eng):
                continue
            side = "english" if last == eng else "hebrew"
            votes[side] += 1
            if len(ev) < 6:
                ev.append(f"{code.upper()} {c}: {last} verses ({side}; {'Hebrew' if side == 'english' else 'English'} "
                          f"{heb if side == 'english' else eng})")
    if not votes:
        return None, "no chapter of theirs where the Hebrew and English counts differ"
    side = votes.most_common(1)[0][0]
    return side, f"{votes[side]} of {sum(votes.values())} chapters: " + "; ".join(ev)


def footnote_form(books, new):
    """the parts most of their footnotes have, in Paratext's order ('fr fk ft'); the newest book's, else all books'"""
    src = [new] if new["footnotes"] else books
    n = sum(b["footnotes"] for b in src)
    if not n:
        return "fr ft"
    parts = collections.Counter()
    for b in src:
        parts.update(b["footnote_parts"])
    return " ".join(p for p in ("fr", "fk", "fq", "fqa", "fl", "fv", "ft") if parts[p] >= 0.2 * n)


def newest(books, pick=None):
    """(the newest book, how it was chosen)"""
    if pick:
        b = next((b for b in books if b["code"] == pick.lower()), None)
        if not b:
            raise SystemExit(f"--newest {pick}: no file of that book in source/")
        return b, "--newest"
    if all(b["year"] for b in books) and len({b["year"] for b in books}) > 1:
        return max(books, key=lambda b: b["year"]), "the latest year in the \\id lines"
    forms = collections.Counter(b["id_line"] for b in books)
    if len(forms) == 1:
        return books[0], "one \\id form in every book"
    b = min(books, key=lambda b: (forms[b["id_line"]], -(b["year"] or 0)))
    return b, (f"a guess: its \\id form is the rarest ({forms[b['id_line']]} of {len(books)} books; the dates don't "
               "settle it); confirm it or give --newest BOOK")


def profile(d, pick=None):
    """(the sfm block, notes for the person)"""
    files = sfm_files(d)
    if not files:
        return None, [f"no SFM files in {os.path.relpath(d, ROOT)}/source/"]
    books = [read(f) for f in files]
    canon = [b for b in books if b["code"] in BY_CODE] or books
    new, how = newest(canon, pick)
    notes = [f"{len(books)} files; newest book {(new['code'] or '?').upper()} ({how})"]
    one = lambda k: collections.Counter(b[k] for b in books)
    most = lambda k: one(k).most_common(1)[0][0]
    m = new["markers"]
    heading = max(("s", "s1"), key=lambda s: m.get(s, 0)) if m.get("s") or m.get("s1") else "s1"
    paras = [p for p in PARAS if m.get(p)]
    vers, vev = versification(canon)
    norm = most("normalization")
    block = {"detected": datetime.date.today().isoformat(), "files": len(books), "newest": (new["code"] or "").upper(),
             "encoding": most("encoding"), "bom": most("bom"),
             "normalization": "NFC" if norm == "either" else norm, "line_endings": most("line_endings"),
             "versification": vers or "english", "id_line": new["id_line"], "ide": new["ide"],
             "file_pattern": file_pattern(new["file"], new["code"]) or "{nn}{BOOK}.SFM",
             "heading": heading, "paragraphs": paras or ["p"],
             "divine_name": sorted(new["nd"]), "footnotes": footnote_form(canon, new),
             "also": sorted({ALSO[k] for k in ALSO if any(b["markers"].get(k) or b["markers"].get(k + "o")
                                                          for b in books)})}
    block["evidence"] = {"versification": vev if vers else f"a guess (english): {vev}"}
    for k in ("encoding", "bom", "normalization", "line_endings"):
        if len(one(k)) > 1:
            notes.append(f"{k}: the files differ ({dict(one(k))}); the profile takes the most common")
    if not vers:
        notes.append(f"versification: {vev}; english assumed (give `versification:` in the project's sfm: to change it)")
    older = {}
    others = [b for b in canon if b is not new]
    if others:
        if any(b["id_line"] != new["id_line"] for b in others):
            older["id_line"] = collections.Counter(b["id_line"] for b in others if b["id_line"] != new["id_line"]).most_common(1)[0][0]
        if any(b["ide"] != new["ide"] for b in others):
            older["ide"] = not new["ide"]
        oh = collections.Counter()
        for b in others:
            oh.update({s: b["markers"].get(s, 0) for s in ("s", "s1")})
        if oh and oh.most_common(1)[0][1] and oh.most_common(1)[0][0] != heading:
            older["heading"] = oh.most_common(1)[0][0]
        ond = sorted({w for b in others for w in b["nd"]})
        if ond != block["divine_name"]:
            older["divine_name"] = ond or "none"
    if older:
        block["differs_in_older_books"] = older
    return block, notes


def dump(block):
    """the sfm: block as YAML lines (values in JSON form, which YAML reads)"""
    import json
    out = [f"sfm:                                  # scripts/sfm_profile.py, from the team's own files in source/"]
    for k, v in block.items():
        if isinstance(v, dict):
            out.append(f"  {k}:")
            out += [f"    {a}: {json.dumps(b, ensure_ascii=False)}" for a, b in v.items()]
        else:
            out.append(f"  {k}: {json.dumps(v, ensure_ascii=False)}")
    return out


def stored(d):
    import yaml
    f = os.path.join(d, "edition.yaml")
    return (yaml.safe_load(open(f, encoding="utf-8")) or {}).get("sfm") if os.path.exists(f) else None


def write(d, block):
    """replace (or append) the top-level sfm: block of edition.yaml, every other line kept"""
    f = os.path.join(d, "edition.yaml")
    lines = open(f, encoding="utf-8").read().splitlines() if os.path.exists(f) else []
    out, skip = [], False
    for l in lines:
        if re.match(r"^sfm:", l):
            skip = True
            continue
        if skip and (l.startswith((" ", "\t")) or not l.strip()):
            continue
        skip = False
        out.append(l)
    while out and not out[-1].strip():
        out.pop()
    open(f, "w", encoding="utf-8").write("\n".join(out + [""] + dump(block)) + "\n")


SKIP = ("detected", "evidence", "files")


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        raise SystemExit(__doc__)
    d = edition_dir(a[0])
    block, notes = profile(d, a[a.index("--newest") + 1] if "--newest" in a else None)
    for n in notes:
        print("  " + n)
    if not block:
        return
    print("\n".join(dump(block)))
    old = stored(d)
    changed = {k: (old.get(k), v) for k, v in block.items() if k not in SKIP and old.get(k) != v} if old else {}
    if old and changed:
        print(f"changed since the stored block ({old.get('detected')}):")
        for k, (o, n) in changed.items():
            print(f"  {k}: {o!r} -> {n!r}")
    elif old:
        print(f"the same as the stored block ({old.get('detected')})")
    if "--write" in a:
        if old and not changed:
            print("edition.yaml left as it is")
            return
        write(d, block)
        print(f"{os.path.relpath(os.path.join(d, 'edition.yaml'), ROOT)}: sfm: block written")
    else:
        print("(not written: --write puts the block into edition.yaml)")


if __name__ == "__main__":
    main()
