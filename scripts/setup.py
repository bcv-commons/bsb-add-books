#!/usr/bin/env python3
"""Download the source texts and build the folders this repo works from.

The repo keeps no outside source content in git. This script fetches every source
into download/ (pinned versions, checked by SHA-256) and builds from it:

    reference/BSB/ Berean Standard Bible           bsb2usfm v5.16, BSB_usj.zip   -> convert_usj.py BSB
    reference/MSB/ Majority Standard Bible, NT     bsb2usfm v5.16, MSB_usj.zip   -> convert_usj.py MSB --nt
    orig/grc/      Berean Greek Bible (BGB)        greekbible.org/bgb.docx       -> extract_bgb.py
    orig/grc-rp/   Robinson-Pierpont 2018          byztxt/byzantine-majority-text (pinned commit) -> extract_rp.py
    orig/vrs/      Hebrew -> BSB verse maps        cdn.bibel.wiki/_vrs/map/      -> vrs.py --fetch
    orig/heb-<layout>/  Hebrew/Aramaic OT clause layouts   only with --heb (see below)
    orig/heb/      the layout the drafting agents read     a copy of one of them (--drafting)

The Hebrew clause layout can be built three ways, side by side (--heb a,b builds several):
    --heb bhsa          the ETCBC BHSA 2021 clause atoms and levels (CC BY-NC 4.0). The deepest
                        hierarchy; the drafting layout. Agents consult it like a reference work: the
                        drafts stay free, but the files and their levels are never published.
                        Needs text-fabric; downloads BHSA on first use (build_heb_bhsa.py).
    --heb bcv-query     the bcv-query Hebrew clause layout release (MACULA Hebrew + UHB, with the
                        text-level hierarchy; CC BY-SA 4.0), pinned by tag and SHA-256:
                        Hugging Face bcv-commons/hebrew-clause-layout v0.37. For everything
                        published that carries clause structure (sidecars, clause-line editions);
                        also writes orig/heb-bcv-query-keys/ (MACULA word keys).
    --heb macula        MACULA Hebrew + UHB via the shoresh scaffold API (CC BY / CC BY-SA).
                        Slow: one API call per chapter (929), the first call of a chapter can
                        take over a minute. Responses are cached in download/scaffold/.
    --drafting LAYOUT   copy orig/heb-LAYOUT to orig/heb (default: the first --heb layout when
                        orig/heb doesn't exist yet). An existing orig/heb is replaced only with --force.
scripts/relayout.py moves a clause-line draft from one layout to another.

The prepared source structures (orig/heb.sqlite, orig/grc.sqlite: MACULA Hebrew and Greek with the numbering, the BSB
tables, referents, frames, speakers; scripts/src.py) come from bcv-query's published cache (v1, pinned SHA-256: three
downloads instead of about a thousand); the BHSA layout rows and the BGB/RP mapping are added here and never published
(`src`; `python3 scripts/src.py build` builds them from MACULA instead, with the UBS columns). The speaker layer
(bcv-commons/hebrew-speaker-layer, CC BY 4.0, pinned tag and SHA-256: who speaks where, quotations inside quotations, frames)
is added to orig/heb.sqlite after them (`spk`; scripts/src.py speaker-layer); the clause packages show it.

Imported editions with a fetch recipe (a 'fetch:' block in their edition.yaml) are fetched
only on request, with --only editions (scripts/fetch_edition.py --all).

Grambank v1.0.3 (CC BY 4.0, pinned tag and SHA-256): the feature questions and their value codes, for the language
store's typology (scripts/grammar.py plan|run), into download/grambank/v1.0.3/; only on request, with --only grambank.

Glottolog v5.3 (glottolog-cldf, CC BY 4.0, pinned tag and SHA-256): the family tree, for the relatives of a language the
model doesn't know (scripts/donor.py), into download/glottolog/v5.3/; only on request, with --only glottolog.

STEPBible TIPNR (proper names with their referents, CC BY 4.0, STEPBible.org / Tyndale House; pinned commit and SHA-256):
one participant per named person or place for scripts/participants.py, into download/stepbible/; with --only names (also
in the default set: one 8 MB file).

The Greek NT clause layout (bcv-commons/greek-nt-clause-layout, CC BY 4.0, pinned tag and SHA-256): the NT's clauses and
speeches (who speaks, quotation spans) on MACULA Greek's word ids, for scripts/alternations.py's speech context, into
download/greek-nt-clause-layout/<tag>/clauses.parquet (read with pyarrow); only on request, with --only gntl.

The Vamvas alignment (bcv-commons/full-alignments-llm, layer ell_GreVamvas+llm+jev-v4, CC0; pinned commit and the
SHA-256 of its files' SHA256SUMS): the modern Greek of each OT Hebrew word, for the affix audit's Vamvas route
(scripts/morphs.py audit --route vamvas; needs import/CC0/ell/vamvas/text/), into download/full-alignments-llm/; only on
request, with --only vamvas-align.

Usage: python3 scripts/setup.py [--heb bhsa,bcv-query,macula] [--drafting LAYOUT] [--force] [--only bsb,msb,bgb,rp,vrs,src,spk,names,editions,grambank,glottolog,vamvas-align,gntl]
  --force   download again even if the file is already in download/
  --only    build only the named sources
Details and licences: docs/sources.md.
"""
import json, functools, hashlib, os, shutil, subprocess, sys, urllib.request, zipfile

print = functools.partial(print, flush=True)

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
DL = os.path.join(ROOT, "download")
UA = {"User-Agent": "make-tanakh-setup/1.0"}

LAYOUTS = {"bhsa": "ETCBC BHSA 2021; CC BY-NC: consulted for drafting, never published",
           "bcv-query": "bcv-query Hebrew clause layout v0.37; CC BY-SA 4.0",
           "macula": "MACULA Hebrew + UHB via the shoresh API; this takes long"}
HCL_TAG = "v0.37"                                         # bcv-commons/hebrew-clause-layout
HCL_URL = f"https://huggingface.co/datasets/bcv-commons/hebrew-clause-layout/resolve/{HCL_TAG}/hebrew-clause-layout-{HCL_TAG}.tar.gz"
SPK_TAG = "v0.15"                                          # bcv-commons/hebrew-speaker-layer
SPK_URL = f"https://huggingface.co/datasets/bcv-commons/hebrew-speaker-layer/resolve/{SPK_TAG}/hebrew-speaker-layer-{SPK_TAG}.tar.gz"
GNTL_TAG = "v0.5"                                          # bcv-commons/greek-nt-clause-layout
GNTL_URL = f"https://huggingface.co/datasets/bcv-commons/greek-nt-clause-layout/resolve/{GNTL_TAG}/data/clauses.parquet"
RP_COMMIT = "27a45ff1b7be6c17ccbfeac414f3f55732ae8e28"     # byztxt/byzantine-majority-text, 2024-12-31
GB_TAG = "v1.0.3"                                         # grambank/grambank (Skirgård et al. 2023)
GB_URL = f"https://raw.githubusercontent.com/grambank/grambank/{GB_TAG}/cldf/{{f}}.csv"
GL_TAG = "v5.3"                                           # glottolog/glottolog-cldf (Hammarström et al.), CC BY 4.0
GL_URL = f"https://raw.githubusercontent.com/glottolog/glottolog-cldf/{GL_TAG}/cldf/{{f}}.csv"
TIPNR_COMMIT = "1f3423d42400f59f1f30fe08f74e38fcd3bbf7bc"  # STEPBible/STEPBible-Data, 2026-10-05
TIPNR_URL = (f"https://raw.githubusercontent.com/STEPBible/STEPBible-Data/{TIPNR_COMMIT}/Proper%20Nouns/"
             "TIPNR%20-%20Translators%20Individualised%20Proper%20Names%20with%20all%20References%20-%20STEPBible.org%20CC%20BY.txt")
VAMVAS_COMMIT = "49f2972c6201f39ccc90f2a9bcf236a8272362d0"   # bcv-commons/full-alignments-llm, 2026-10-21
VAMVAS_LAYER = "ell_GreVamvas+llm+jev-v4"                  # Vamvas (1850) aligned to MACULA, model-checked; CC0
VAMVAS_URL = f"https://huggingface.co/datasets/bcv-commons/full-alignments-llm/resolve/{VAMVAS_COMMIT}/{{f}}"
VAMVAS_SHA256 = "5ab99b6fd66e346550c11d83afd0903518a1e771698c76bb3125b80d1462e75a"  # the SHA-256 of the SHA256SUMS lines of the fetched files (manifest, _layer, OT books)
SRC_V = "v1"  # the prepared source structures, published by bcv-query (built by scripts/src.py; verified row by row)
SRC_URL = "https://files.qombi.com/files/source-structure-{v}-{f}"
SOURCES = {
    "bsb": ("https://github.com/BSB-publishing/bsb2usfm/releases/download/v5.16/BSB_usj.zip", "BSB_usj.zip"),
    "msb": ("https://github.com/BSB-publishing/bsb2usfm/releases/download/v5.16/MSB_usj.zip", "MSB_usj.zip"),
    "bgb": ("https://greekbible.org/bgb.docx", "berean/bgb.docx"),
    "hcl": (HCL_URL, f"hebrew-clause-layout/hebrew-clause-layout-{HCL_TAG}.tar.gz"),
    "spk": (SPK_URL, f"hebrew-speaker-layer/hebrew-speaker-layer-{SPK_TAG}.tar.gz"),
    "gntl": (GNTL_URL, f"greek-nt-clause-layout/{GNTL_TAG}/clauses.parquet"),
    "rp": (f"https://github.com/byztxt/byzantine-majority-text/archive/{RP_COMMIT}.zip", f"rp-{RP_COMMIT[:12]}.zip"),
    **{f"gb-{f}": (GB_URL.format(f=f), f"grambank/{GB_TAG}/{f}.csv") for f in ("parameters", "codes")},
    **{f"gl-{f}": (GL_URL.format(f=f), f"glottolog/{GL_TAG}/{f}.csv") for f in ("languages", "values")},
    "names": (TIPNR_URL, f"stepbible/TIPNR-{TIPNR_COMMIT[:12]}.txt"),
    **{f"src-{f}": (SRC_URL.format(v=SRC_V, f=f), f"source-structure-{SRC_V}/source-structure-{SRC_V}-{f}")
       for f in ("heb-open.sqlite.gz", "grc-open.sqlite.gz", "heb-bcv-query.sqlite.gz")},
}
SHA256 = {
    "bgb": "56eb9ba026316e6d66d675a4f1812deae362d46244541b9071e937d77d21eac7",
    "hcl": "02f90e95caf01b941136fe2f03826f6dcdb93551dd6a78d86aa792235a864791",
    "spk": "ec616e931b6348dd232080230f86403fcc5a18c238ac62faf3aa574e1e5c73c0",
    "gntl": "f70a0cb287a0cb4f15bfc06f73253b0b2b9face8221c97ef1dbdc35ad3ad208f",
    "gb-parameters": "ff5a675e6e2417b6e1746230b6649429be688f4e16df0da99bbabe4eff52dc80",
    "gb-codes": "cdcf17f53d56c6b58d52a76cb82c77fe6fd919abb3b9ac836c80f97c537f3263",
    "gl-languages": "1a50a393bc81568b656f9522be18aa4f80f38e94309ba6c863d583234adfbb89",
    "gl-values": "a8601cb04ccc6a310538217f772d2461853aa0ea49e3bfe24c7396570fc4ea25",
    "names": "aaec5b0af6e539b74536bd3b8b93e3acbe344290865c5e0728252787d0a8358e",
    "src-heb-open.sqlite.gz": "7a3613f19c450746afb304c02f688963c556e3e74fd469caaf27d44e7d70e543",
    "src-grc-open.sqlite.gz": "d707cd1f7ef3e25a0cd6d3008f5ef74d13f7e29bb96e7177b2fa5f281a743611",
    "src-heb-bcv-query.sqlite.gz": "00e3ab016ca5537d66b6a0a2a245428c71c425a3abb6e2d191474b3776c14efc",
}
PINNED = {"hcl", "spk", "gntl", "gb-parameters", "gb-codes", "gl-languages", "gl-values", "names", "src-heb-open.sqlite.gz", "src-grc-open.sqlite.gz", "src-heb-bcv-query.sqlite.gz"}  # never another file


def fetch(key, force):
    url, name = SOURCES[key]
    path = os.path.join(DL, name)
    for attempt in range(3):  # a download can break off (it did for bcv-query's build): retry before giving up
        if force or attempt or not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            print(f"  downloading {url}")
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=900) as r, open(path + ".part", "wb") as f:
                    shutil.copyfileobj(r, f)
                os.replace(path + ".part", path)
            except OSError as e:
                print(f"  download failed ({e}); retrying")
                continue
        digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if key not in PINNED or digest == SHA256[key]:
            break
        print(f"  {name}: sha256 {digest[:16]}… is not the pinned one; downloading again")
    if key in PINNED and digest != SHA256[key]:          # a pinned release: never build from another file
        raise SystemExit(f"  {name}: sha256 {digest} is not the pinned {SHA256[key]}; delete it and run again.")
    if key in SHA256 and digest != SHA256[key]:
        print(f"  WARNING: {name} differs from the version this repo was built with (sha256 {digest}).")
        print("           Check the result before relying on it; see docs/sources.md.")
    return path


def fetch_vamvas_align(force):
    """bcv-commons/full-alignments-llm, layer ell_GreVamvas+llm+jev-v4 at the pinned commit: manifest.json, the layer's
    _layer.json and its OT book files (<BOOK>_<fingerprint>.json and .meta.json) into
    download/full-alignments-llm/e/ell/<layer>/, with SHA256SUMS; the SHA-256 of those lines is pinned (VAMVAS_SHA256).
    The files are data (JSON), read by scripts/ot_routes.py; their names carry the fingerprint of the Vamvas text they
    were made on (the module's KJV numbering; ot_routes.py checks our import/CC0/ell/vamvas/ copy against it)."""
    from books import BY_CODE
    d = os.path.join(DL, "full-alignments-llm", "e", "ell", VAMVAS_LAYER)
    os.makedirs(d, exist_ok=True)

    def get(rel, dest):
        if force or not os.path.exists(dest):
            print(f"  downloading {rel}")
            for attempt in range(4):                    # Hugging Face resets connections now and then
                try:
                    with urllib.request.urlopen(urllib.request.Request(VAMVAS_URL.format(f=urllib.request.quote(rel)),
                                                                       headers=UA), timeout=300) as r:
                        open(dest + ".part", "wb").write(r.read())
                    os.replace(dest + ".part", dest)
                    break
                except OSError as e:
                    if attempt == 3:
                        raise
                    print(f"  download failed ({e}); retrying")
        return dest
    man = json.load(open(get("manifest.json", os.path.join(d, "manifest.json")), encoding="utf-8"))
    get(f"e/ell/{VAMVAS_LAYER}/_layer.json", os.path.join(d, "_layer.json"))
    books = man["languages"]["ell"]["layers"][VAMVAS_LAYER]["books"]
    names = ["manifest.json", "_layer.json"]
    for b, f in sorted(books.items()):
        if BY_CODE.get(b.lower(), (0, 0, ""))[2] != "ot":
            continue
        for name in (f, f[:-5] + ".meta.json"):
            get(f"e/ell/{VAMVAS_LAYER}/{name}", os.path.join(d, name))
            names.append(name)
    sums = "".join(f"{hashlib.sha256(open(os.path.join(d, n), 'rb').read()).hexdigest()}  {n}\n" for n in sorted(names))
    open(os.path.join(d, "SHA256SUMS"), "w").write(sums)
    digest = hashlib.sha256(sums.encode()).hexdigest()
    if digest != VAMVAS_SHA256:
        raise SystemExit(f"  {d}: SHA256SUMS digest {digest} is not the pinned {VAMVAS_SHA256}; delete the folder and run "
                         "again (or check what changed)")
    print(f"  {len(names) - 2} Tanakh files of {VAMVAS_LAYER} at {VAMVAS_COMMIT[:12]} (SHA256SUMS digest {digest[:16]}…)")


def unzip_flat(zpath, dest):
    """Extract all files of a zip into dest, without their folders (like unzip -j)."""
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            if not info.is_dir():
                with z.open(info) as src, open(os.path.join(dest, os.path.basename(info.filename)), "wb") as out:
                    shutil.copyfileobj(src, out)


def unzip_strip(zpath, dest):
    """Extract a GitHub archive into dest, dropping its top folder (<repo>-<commit>/)."""
    if os.path.exists(dest):
        shutil.rmtree(dest)
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            rel = info.filename.split("/", 1)[1] if "/" in info.filename else ""
            if not rel or info.is_dir():
                continue
            target = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def run(*args):
    print(f"  python3 scripts/{' '.join(args)}")
    subprocess.run([sys.executable, os.path.join(CODE, "scripts", args[0]), *args[1:]], check=True, cwd=ROOT)


def install_src(force):
    """The published cache: download (pinned SHA-256), unpack to orig/, then add what stays local: the BHSA layout rows
    (if orig/heb-bhsa exists; never published) and our BGB/RP -> MACULA mapping (needs orig/grc, orig/grc-rp).
    The UBS columns (SDBH, Louw-Nida) stay empty; `python3 scripts/src.py build` builds everything from MACULA instead."""
    import gzip, sqlite3
    out = {"heb": os.path.join(ROOT, "orig", "heb.sqlite"), "grc": os.path.join(ROOT, "orig", "grc.sqlite")}
    if all(os.path.exists(p) for p in out.values()) and not force:
        print("  orig/heb.sqlite and orig/grc.sqlite exist (--force replaces them)")
        return
    files = {f: fetch(f"src-{f}", force) for f in ("heb-open.sqlite.gz", "grc-open.sqlite.gz", "heb-bcv-query.sqlite.gz")}
    os.makedirs(os.path.join(ROOT, "orig"), exist_ok=True)
    for lang in ("heb", "grc"):
        with gzip.open(files[f"{lang}-open.sqlite.gz"]) as g, open(out[lang] + ".part", "wb") as f:
            shutil.copyfileobj(g, f)
        os.replace(out[lang] + ".part", out[lang])
    lay = os.path.join(DL, f"source-structure-{SRC_V}", "heb-bcv-query.sqlite")
    with gzip.open(files["heb-bcv-query.sqlite.gz"]) as g, open(lay, "wb") as f:
        shutil.copyfileobj(g, f)
    con = sqlite3.connect(out["heb"])
    con.execute("attach database ? as l", (lay,))
    con.execute("delete from layout")
    con.execute("insert into layout select * from l.layout")
    con.commit()
    con.close()
    if os.path.isdir(os.path.join(ROOT, "orig", "heb-bhsa")):
        run("src.py", "layouts", "--layout", "bhsa")
    if os.path.isdir(os.path.join(ROOT, "orig", "heb-bcv-query")):  # the cache's rows have v0.22's levels: take the pinned release's
        run("src.py", "layouts", "--layout", "bcv-query")
    if os.path.isdir(os.path.join(ROOT, "orig", "grc")):
        run("src.py", "map")
    print("  done: the structures are here; the BHSA rows and the mapping were added locally")


def main():
    argv = sys.argv[1:]
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return
    force = "--force" in argv
    hebs = argv[argv.index("--heb") + 1].split(",") if "--heb" in argv else []
    drafting = argv[argv.index("--drafting") + 1] if "--drafting" in argv else None
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else {"bsb", "msb", "bgb", "rp", "vrs", "src", "spk", "names"}
    for h in hebs + ([drafting] if drafting else []):
        if h not in LAYOUTS:
            raise SystemExit(f"--heb / --drafting: expected one of {', '.join(LAYOUTS)}, got {h!r}")
    if "bsb" in only:
        print("reference/BSB/")
        unzip_flat(fetch("bsb", force), os.path.join(DL, "BSB"))
        run("convert_usj.py", "BSB")
    if "msb" in only:
        print("reference/MSB/")
        unzip_flat(fetch("msb", force), os.path.join(DL, "MSB"))
        run("convert_usj.py", "MSB", "--nt")
    if "bgb" in only:
        print("orig/grc/ (BGB)")
        fetch("bgb", force)
        run("extract_bgb.py")
    if "rp" in only:
        print("orig/grc-rp/ (Robinson-Pierpont)")
        unzip_strip(fetch("rp", force), os.path.join(DL, "rp"))
        run("extract_rp.py")
    if "vrs" in only:
        print("orig/vrs/")
        run("vrs.py", "--fetch")
    if "grambank" in only:
        print(f"download/grambank/{GB_TAG}/ (Grambank: the feature questions and codes)")
        for f in ("parameters", "codes"):
            fetch(f"gb-{f}", force)
    if "gntl" in only:
        print(f"download/greek-nt-clause-layout/{GNTL_TAG}/ (the Greek NT clause layout: speeches, for scripts/alternations.py;"
              " orig/grc-gntl/, the website's Greek clause view)")
        fetch("gntl", force)
        try:
            import pyarrow  # noqa: F401
            run("build_grc_gntl.py")
        except ImportError:
            print("  orig/grc-gntl/ not built: needs pyarrow (pip install pyarrow), then python3 scripts/build_grc_gntl.py")
    if "names" in only:
        print("download/stepbible/ (STEPBible TIPNR: proper names, for scripts/participants.py)")
        fetch("names", force)
    if "glottolog" in only:
        print(f"download/glottolog/{GL_TAG}/ (Glottolog: the family tree, for a language's relatives; scripts/donor.py)")
        for f in ("languages", "values"):
            fetch(f"gl-{f}", force)
    if "vamvas-align" in only:
        print(f"download/full-alignments-llm/ (the Vamvas alignment {VAMVAS_LAYER}, CC0: the audit's Tanakh Vamvas route)")
        fetch_vamvas_align(force)
    if "editions" in only:
        print("import/: editions with a fetch recipe")
        run("fetch_edition.py", "--all", *(["--force"] if force else []))
    for h in hebs:
        out = os.path.join(ROOT, "orig", f"heb-{h}")
        print(f"orig/heb-{h}/ ({LAYOUTS[h]})")
        if h == "bcv-query":
            import tarfile
            path = fetch("hcl", force)
            dest = os.path.join(DL, "hebrew-clause-layout")
            with tarfile.open(path) as t:
                t.extractall(dest, filter="data")
            run("build_heb_bcvquery.py", os.path.join(dest, f"hebrew-clause-layout-{HCL_TAG}"), "--out", out)
        elif h == "macula":
            from books import BOOKS
            run("fetch_heb_macula.py", *[b[0] for b in BOOKS if b[2] == "ot"], "--out", out)
        else:
            run("build_heb_bhsa.py", "--out", out)
    heb_dir = os.path.join(ROOT, "orig", "heb")
    if drafting is None and hebs and not os.path.isdir(heb_dir):
        drafting = hebs[0]
    if drafting:
        src = os.path.join(ROOT, "orig", f"heb-{drafting}")
        if not os.path.isdir(src):
            raise SystemExit(f"--drafting {drafting}: no orig/heb-{drafting}/ yet; build it with --heb {drafting}")
        if os.path.isdir(heb_dir) and not force:
            raise SystemExit(f"orig/heb/ exists; --drafting {drafting} replaces it only with --force")
        import shutil
        shutil.rmtree(heb_dir, ignore_errors=True)
        shutil.copytree(src, heb_dir)
        info = os.path.join(heb_dir, "_source.json")
        meta = json.load(open(info, encoding="utf-8")) if os.path.exists(info) else {}
        meta["drafting_copy_of"] = f"orig/heb-{drafting}"
        json.dump(meta, open(info, "w", encoding="utf-8"), indent=1)
        print(f"orig/heb/ = orig/heb-{drafting}/ (the drafting layout)")
    elif not os.path.isdir(heb_dir):
        print("\nNo orig/heb/ yet. Drafting the Tanakh needs it: run again with --heb bhsa (and --heb bcv-query for published structure).")
    if "src" in only:  # last: the BHSA layout rows need orig/heb-bhsa, the mapping orig/grc and orig/grc-rp
        print(f"orig/heb.sqlite, orig/grc.sqlite (prepared source structures {SRC_V}, published by bcv-query)")
        install_src(force)
    if "spk" in only:  # after src: its segments are the bcv-query layout rows of orig/heb.sqlite
        print(f"orig/heb.sqlite: the speaker layer (bcv-commons/hebrew-speaker-layer {SPK_TAG}; CC BY 4.0)")
        if not os.path.exists(os.path.join(ROOT, "orig", "heb.sqlite")):
            print("  no orig/heb.sqlite yet: run with --only src first")
        else:
            import tarfile
            path = fetch("spk", force)
            dest = os.path.join(DL, "hebrew-speaker-layer")
            with tarfile.open(path) as t:
                t.extractall(dest, filter="data")
            run("src.py", "speaker-layer", os.path.join(dest, f"hebrew-speaker-layer-{SPK_TAG}"))
    print("\nDone.")


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(CODE, "scripts"))
    main()
