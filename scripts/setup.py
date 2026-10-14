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
                        Hugging Face bcv-commons/hebrew-clause-layout v0.22. For everything
                        published that carries clause structure (sidecars, clause-line editions);
                        also writes orig/heb-bcv-query-keys/ (MACULA word keys).
    --heb macula        MACULA Hebrew + UHB via the shoresh scaffold API (CC BY / CC BY-SA).
                        Slow: one API call per chapter (929), the first call of a chapter can
                        take over a minute. Responses are cached in download/scaffold/.
    --drafting LAYOUT   copy orig/heb-LAYOUT to orig/heb (default: the first --heb layout when
                        orig/heb doesn't exist yet). An existing orig/heb is replaced only with --force.
scripts/relayout.py moves a clause-line draft from one layout to another.

Imported editions with a fetch recipe (a 'fetch:' block in their edition.yaml) are fetched
only on request, with --only editions (scripts/fetch_edition.py --all).

Usage: python3 scripts/setup.py [--heb bhsa,bcv-query,macula] [--drafting LAYOUT] [--force] [--only bsb,msb,bgb,rp,vrs,editions]
  --force   download again even if the file is already in download/
  --only    build only the named sources
Details and licences: docs/sources.md.
"""
import json, functools, hashlib, os, shutil, subprocess, sys, urllib.request, zipfile

print = functools.partial(print, flush=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DL = os.path.join(ROOT, "download")
UA = {"User-Agent": "bsb-add-books-setup/1.0"}

LAYOUTS = {"bhsa": "ETCBC BHSA 2021; CC BY-NC: consulted for drafting, never published",
           "bcv-query": "bcv-query Hebrew clause layout v0.22; CC BY-SA 4.0",
           "macula": "MACULA Hebrew + UHB via the shoresh API; this takes long"}
HCL_TAG = "v0.22"                                         # bcv-commons/hebrew-clause-layout
HCL_URL = f"https://huggingface.co/datasets/bcv-commons/hebrew-clause-layout/resolve/{HCL_TAG}/hebrew-clause-layout-{HCL_TAG}.tar.gz"
RP_COMMIT = "27a45ff1b7be6c17ccbfeac414f3f55732ae8e28"     # byztxt/byzantine-majority-text, 2024-12-31
SOURCES = {
    "bsb": ("https://github.com/BSB-publishing/bsb2usfm/releases/download/v5.16/BSB_usj.zip", "BSB_usj.zip"),
    "msb": ("https://github.com/BSB-publishing/bsb2usfm/releases/download/v5.16/MSB_usj.zip", "MSB_usj.zip"),
    "bgb": ("https://greekbible.org/bgb.docx", "berean/bgb.docx"),
    "hcl": (HCL_URL, f"hebrew-clause-layout/hebrew-clause-layout-{HCL_TAG}.tar.gz"),
    "rp": (f"https://github.com/byztxt/byzantine-majority-text/archive/{RP_COMMIT}.zip", f"rp-{RP_COMMIT[:12]}.zip"),
}
SHA256 = {
    "bgb": "56eb9ba026316e6d66d675a4f1812deae362d46244541b9071e937d77d21eac7",
    "hcl": "624990dd9113d9309300e7755588569a6808774d49f969ecafb2f7c271166640",
}


def fetch(key, force):
    url, name = SOURCES[key]
    path = os.path.join(DL, name)
    if force or not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"  downloading {url}")
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(path + ".part", "wb") as f:
            shutil.copyfileobj(r, f)
        os.replace(path + ".part", path)
    digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if key == "hcl" and digest != SHA256[key]:          # a pinned release: never build from another file
        raise SystemExit(f"  {name}: sha256 {digest} is not the pinned {SHA256[key]}; delete it and run again.")
    if key in SHA256 and digest != SHA256[key]:
        print(f"  WARNING: {name} differs from the version this repo was built with (sha256 {digest}).")
        print("           Check the result before relying on it; see docs/sources.md.")
    return path


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
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", args[0]), *args[1:]], check=True, cwd=ROOT)


def main():
    argv = sys.argv[1:]
    force = "--force" in argv
    hebs = argv[argv.index("--heb") + 1].split(",") if "--heb" in argv else []
    drafting = argv[argv.index("--drafting") + 1] if "--drafting" in argv else None
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else {"bsb", "msb", "bgb", "rp", "vrs"}
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
        print("\nNo orig/heb/ yet. OT drafting needs it: run again with --heb bhsa (and --heb bcv-query for published structure).")
    print("\nDone.")


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    main()
