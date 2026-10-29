"""Build orig/heb/<code>NNN.txt from the ETCBC BHSA (2021) with Text-Fabric.

BHSA (Biblia Hebraica Stuttgartensia Amstelodamensis, Eep Talstra Centre for Bible and
Computer) is CC BY-NC 4.0: fine for private, non-commercial drafting; never publish the
files or their levels. Cite DOI 10.17026/dans-z6y-skyh.

One file per chapter, Hebrew verse numbering. First line '<code> <chapter>', then one line
per BHSA clause atom: '<verse>:<tab> <text>', where tab is the atom's level in BHSA's text
hierarchy and the text is the pointed surface text with its trailing characters
(g_word_utf8 + trailer_utf8).

Needs text-fabric (pip install text-fabric). Without --tf it downloads BHSA 2021 from
github.com/ETCBC/bhsa into ~/text-fabric-data on first use.

Usage: python3 scripts/build_heb_bhsa.py [--tf <dir with BHSA 2021 .tf files>] [--out DIR] [code ...]
"""
import os, sys
from books import BOOKS, ROOT

LATIN = dict(zip(
    "gen exo lev num deu jos jdg 1sa 2sa 1ki 2ki isa jer ezk hos jol amo oba jon mic nam hab zep hag zec mal "
    "psa job pro rut sng ecc lam est dan ezr neh 1ch 2ch".split(),
    "Genesis Exodus Leviticus Numeri Deuteronomium Josua Judices Samuel_I Samuel_II Reges_I Reges_II Jesaia "
    "Jeremia Ezechiel Hosea Joel Amos Obadia Jona Micha Nahum Habakuk Zephania Haggai Sacharia Maleachi Psalmi "
    "Iob Proverbia Ruth Canticum Ecclesiastes Threni Esther Daniel Esra Nehemia Chronica_I Chronica_II".split()))
FEATURES = "book chapter verse tab g_word_utf8 trailer_utf8"


def load(tf_dir):
    if tf_dir:
        from tf.fabric import Fabric
        api = Fabric(locations=tf_dir, silent="deep").load(FEATURES, silent="deep")
    else:
        from tf.app import use
        api = use("ETCBC/bhsa", version="2021", hoist=False, silent="deep").api
        api.TF.load(FEATURES, add=True, silent="deep")
    if not api:
        raise SystemExit("could not load BHSA 2021")
    return api


def main():
    argv = sys.argv[1:]
    tf_dir = argv[argv.index("--tf") + 1] if "--tf" in argv else None
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(ROOT, "orig", "heb")
    skip = {tf_dir, out}
    codes = [a for a in argv if not a.startswith("--") and a not in skip] or [b[0] for b in BOOKS if b[2] == "ot"]
    api = load(tf_dir)
    F, L, T = api.F, api.L, api.T
    os.makedirs(out, exist_ok=True)
    n = 0
    by_name = {F.book.v(b): b for b in F.otype.s("book")}   # BHSA's own (Latin) book names
    for code in codes:
        book = by_name[LATIN[code]]
        for ch in L.d(book, otype="chapter"):
            c = F.chapter.v(ch)
            lines = [f"{code} {c}"]
            for a in L.d(ch, otype="clause_atom"):
                text = "".join(F.g_word_utf8.v(w) + F.trailer_utf8.v(w) for w in L.d(a, otype="word"))
                lines.append(f"{F.verse.v(L.u(a, otype='verse')[0])}:{F.tab.v(a)} {text}")
            open(os.path.join(out, f"{code}{c:03d}.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
            n += 1
    import json
    json.dump({"source": "bhsa", "version": "2021", "licence": "CC BY-NC 4.0 (ETCBC): consult for drafting; never publish "
               "these files or their levels", "doi": "10.17026/dans-z6y-skyh", "levels": "tab"},
              open(os.path.join(out, "_source.json"), "w", encoding="utf-8"), indent=1)
    print(f"orig/heb: {n} chapters written to {out}")


if __name__ == "__main__":
    main()
