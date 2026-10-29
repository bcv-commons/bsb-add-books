#!/usr/bin/env python3
"""Fetch the Vamvas Bible (1850, modern Greek, public domain) from CrossWire's SWORD module GreVamvas and write text/.

    python3 import/CC0/ell/vamvas/fetch_vamvas.py [--root REPO]

Downloads the module zip (pinned SHA-256) to download/editions/vamvas/, reads it with pysword (pip install
pysword==0.2.8) and writes one book file per book, text/<code>.txt, lines 'chapter:verse<TAB>text'.
The module has the KJV versification: the OT is renumbered to the Hebrew verses (repo rule) by orig/vrs, so
build orig/ first (scripts/setup.py). Where several Hebrew verses map to one English verse, the text goes to the
first of them; an English verse that no Hebrew verse starts (ISA 64:1, NEH 7:68, PSA 13:6) goes with the Hebrew verse
that holds the English verse before it, so no text is lost; a psalm superscription, which Vamvas prints in «…» at the start of verse 1, goes to the Hebrew title
verse (the first, where the Hebrew has two). The NT keeps its numbering. text/_fingerprints.json records each book's text
fingerprint in the module's own numbering (as alignment layers on this text name their files) and the SHA-256 of the
book file written (scripts/ot_routes.py). text/ is git-ignored: the text comes from the source.
"""
import hashlib, json, os, re, sys, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv else os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import vrs  # noqa: E402
from books import BY_CODE, heb_chapters  # noqa: E402

URL = "https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/GreVamvas.zip"
SHA256 = "3e1593fab993ad189fcaa8a848280f70337d11d5dd154b9bda6d0087a7bf3b5d"   # module 1.0.3
OSIS = ("Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer "
        "Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph "
        "Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev").split()


def module():
    d = os.path.join(ROOT, "download", "editions", "vamvas")
    z = os.path.join(d, "GreVamvas.zip")
    if not os.path.exists(z):
        os.makedirs(d, exist_ok=True)
        urllib.request.urlretrieve(URL, z)
    if hashlib.sha256(open(z, "rb").read()).hexdigest() != SHA256:
        sys.exit(f"{z}: SHA-256 differs from the pinned module 1.0.3")
    mod = os.path.join(d, "mod")
    if not os.path.isdir(mod):
        zipfile.ZipFile(z).extractall(mod)
    return mod


def main():
    from pysword.modules import SwordModules
    m = SwordModules(module()); m.parse_modules()
    bible = m.get_bible_from_module("GreVamvas")
    st = bible.get_structure().get_books()
    books = st["ot"] + st["nt"]
    codes = list(BY_CODE)                                  # books.tsv order = the KJV order
    assert len(books) == len(codes) == len(OSIS), (len(books), len(codes))
    out = os.path.join(HERE, "text"); os.makedirs(out, exist_ok=True)
    total, fps = 0, {}
    import full_align as FA
    for code, bk in zip(codes, books):
        get = lambda c, v: bible.get(books=[bk.name], chapters=[c], verses=[v], clean=True).strip()
        eng = {(c, v): get(c, v) for c in range(1, bk.num_chapters + 1) for v in range(1, bk.chapter_lengths[c - 1] + 1)}
        lines, used, last = [], set(), {}
        # the book's text fingerprint in the module's own numbering, as alignment layers on this text name their files
        fp = FA.text_fingerprint([(c, v, t) for (c, v), t in eng.items()])[0]
        if BY_CODE[code][2] == "ot":
            titles = {}
            for c in range(1, heb_chapters(code) + 1):
                if any(vrs.to_bsb(code, c, hv)[1] == "title" for hv in vrs.heb_verses(code, c)):
                    m = re.match(r"«[^»]*»\s*", eng.get((c, 1), ""))
                    if m:
                        titles[c] = m[0].strip()
                        eng[(c, 1)] = eng[(c, 1)][m.end():]
            for c in range(1, heb_chapters(code) + 1):
                for hv in vrs.heb_verses(code, c):
                    ec, ev = vrs.to_bsb(code, c, hv)
                    t = titles.pop(c, "") if ev == "title" else "" if (ec, ev) in used else eng.get((ec, ev), "")
                    used.add((ec, ev))
                    lines.append(f"{c}:{hv}\t{t}")
                    last[(ec, ev)] = len(lines) - 1
            # an English verse no Hebrew verse starts (a Hebrew verse that spans two, a verse missing in the Hebrew:
            # ISA 64:1, NEH 7:68, PSA 13:6) goes with the Hebrew verse that holds the English verse before it
            prev = None
            for k in sorted(eng):
                if k in last:
                    prev = last[k]
                elif eng[k] and prev is not None:
                    cv, _, t = lines[prev].partition("\t")
                    lines[prev] = f"{cv}\t{(t + ' ' + eng[k]).strip()}"
        else:
            lines = [f"{c}:{v}\t{t}" for (c, v), t in eng.items()]
        total += sum(1 for l in lines if l.split("\t", 1)[1])
        body = "\n".join(lines) + "\n"
        open(os.path.join(out, f"{code}.txt"), "w", encoding="utf-8").write(body)
        # with the SHA-256 of the file written from it: the fingerprint holds for that file only, unchanged
        fps[code.upper()] = {"module": fp, "text_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}
    json.dump(fps, open(os.path.join(out, "_fingerprints.json"), "w"), indent=0, sort_keys=True)
    print(f"text/: {len(codes)} books, {total:,} verses with text")


if __name__ == "__main__":
    main()
