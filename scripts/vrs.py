"""Hebrew (orig/heb) to BSB verse numbering, from the bcv-commons/bibles verse maps.

Two files in orig/vrs/, published by bcv-commons/bibles at cdn.bibel.wiki/_vrs/map/
(see its doc/vrs-maps.md), derived from STEPBible TVTMS (CC BY 4.0):

- `org-to-eng.json`: `map` lists the single verses whose number differs
  (`JOL 3:1 -> JOL 2:28`); every other verse keeps its number. `PSA 3:title` is a
  superscription, which the BSB prints as part of its verse 1.
- `org-to-eng.multiverse.json`: `map` lists verses that are merged or split, with a
  range on one side (`1SA 20:42-21:1 -> 1SA 20:42`, `ISA 63:19 -> ISA 63:19-64:1`).

Read together, every Hebrew verse of orig/heb maps to a BSB verse, and every BSB verse
is reached except NEH 7:68, which the Hebrew lacks (checked 2026-10-12).

Usage:
    python3 scripts/vrs.py --fetch           # (re)download both files to orig/vrs/
    python3 scripts/vrs.py <code> <chapter>  # print the mapping of one Hebrew chapter
"""
import json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "orig", "vrs")
URL = "https://cdn.bibel.wiki/_vrs/map/"
FILES = ["org-to-eng.json", "org-to-eng.multiverse.json"]

# Facts about the BSB text, not about numbering, that a translator should see.
NOTES = {
    ("neh", 7): "BSB 7:68 is missing in most Hebrew manuscripts and in orig/heb.",
}

_single = _multi = None


def parse_range(ref):
    """'NUM 25:19-26:1' -> ('NUM', (25, 19), (26, 1)); 'PSA 13:5-6' -> ('PSA', (13, 5), (13, 6))."""
    book, cv = ref.split()
    a, _, b = cv.partition("-")
    c0, v0 = map(int, a.split(":"))
    if not b:
        return book, (c0, v0), (c0, v0)
    c1, v1 = map(int, b.split(":")) if ":" in b else (c0, int(b))
    return book, (c0, v0), (c1, v1)


def load():
    global _single, _multi
    if _single is None:
        _single = {r["s"]: r["t"] for r in json.load(open(os.path.join(DIR, FILES[0]), encoding="utf-8"))["map"]}
        _multi = [(parse_range(r["s"]), parse_range(r["t"]), r["s"], r["t"])
                  for r in json.load(open(os.path.join(DIR, FILES[1]), encoding="utf-8"))["map"]]
    return _single, _multi


def relation(code, ch, v):
    """The multiverse relation whose Hebrew side contains this verse, or None."""
    for rel in load()[1]:
        (book, start, end), _, _, _ = rel
        if book == code.upper() and start <= (ch, v) <= end:
            return rel
    return None


def to_bsb(code, ch, v):
    """BSB (chapter, verse) of a Hebrew verse; verse is 'title' for a superscription.
    A Hebrew verse that is part of a merged BSB verse maps to that verse."""
    t = load()[0].get(f"{code.upper()} {ch}:{v}")
    if not t:
        rel = relation(code, ch, v)
        return rel[1][1] if rel else (ch, v)
    c, vv = t.split()[1].split(":")
    return int(c), (vv if vv == "title" else int(vv))


def heb_verses(code, ch):
    vs = []
    for line in open(os.path.join(ROOT, "orig", "heb", f"{code}{ch:03d}.txt"), encoding="utf-8").read().splitlines()[1:]:
        m = re.match(r"(\d+):", line)
        if m and (not vs or vs[-1] != int(m.group(1))):
            vs.append(int(m.group(1)))
    return vs


def chapter(code, ch):
    """(BSB chapters to consult, list of 'Hebrew x = BSB y' notes) for a Hebrew chapter."""
    verses = heb_verses(code, ch)
    pairs = [(v, to_bsb(code, ch, v)) for v in verses]
    bsb_chapters = {c for _, (c, _) in pairs}
    rels = []
    for v in verses:
        rel = relation(code, ch, v)
        if rel and rel not in rels:
            rels.append(rel)
            (_, (t0, _), (t1, _)) = rel[1]
            bsb_chapters |= set(range(t0, t1 + 1))
    # group shifted verses into runs with a constant offset in the same BSB chapter;
    # verses of a merge/split relation are described by the relation instead
    runs = []
    for v, (c, bv) in pairs:
        if (c, bv) == (ch, v) or relation(code, ch, v):
            continue
        r = runs[-1] if runs else None
        title = bv == "title" and r and r["bv1"] == "title"
        step = bv != "title" and r and r["bv1"] != "title" and bv == r["bv1"] + 1
        if r and r["c"] == c and v == r["v1"] + 1 and (title or step):
            r["v1"], r["bv1"] = v, bv
        else:
            runs.append(dict(v0=v, v1=v, c=c, bv0=bv, bv1=bv))
    notes = []
    for r in runs:
        h = f"{ch}:{r['v0']}" + (f"–{r['v1']}" if r["v1"] != r["v0"] else "")
        if r["bv0"] == "title":
            notes.append(f"Hebrew {h} (superscription) = the start of BSB {r['c']}:1")
        else:
            b = f"{r['c']}:{r['bv0']}" + (f"–{r['bv1']}" if r["bv1"] != r["bv0"] else "")
            notes.append(f"Hebrew {h} = BSB {b}")
    for _, _, s, t in rels:
        notes.append(f"Hebrew {s.split()[1].replace('-', '–')} = BSB {t.split()[1].replace('-', '–')} (verses divided differently)")
    if (code, ch) in NOTES:
        notes.append(NOTES[(code, ch)].rstrip("."))
    return sorted(bsb_chapters), notes


def fetch():
    os.makedirs(DIR, exist_ok=True)
    for f in FILES:
        req = urllib.request.Request(URL + f, headers={"User-Agent": "bsb-add-books"})
        data = urllib.request.urlopen(req).read()
        n = len(json.loads(data)["map"])
        open(os.path.join(DIR, f), "wb").write(data)
        print(f"orig/vrs/{f}: {n} rows")


if __name__ == "__main__":
    if sys.argv[1:] == ["--fetch"]:
        fetch()
    else:
        cs, notes = chapter(sys.argv[1], int(sys.argv[2]))
        print("BSB chapters:", ", ".join(map(str, cs)))
        for n in notes:
            print(" ", n)
