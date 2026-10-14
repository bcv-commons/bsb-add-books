#!/usr/bin/env python3
"""Find Bible editions in a language, and fetch one into import/ from its fetch recipe.

    python3 scripts/fetch_edition.py --find <iso>      # what exists for a language, with licences
    python3 scripts/fetch_edition.py <edition>         # fetch the edition named in its edition.yaml
    python3 scripts/fetch_edition.py --all             # fetch every edition that has a recipe

Sources, in the order --find lists them:

    helloao    bible.helloao.org (bcv-commons/bibles source 'h')   whole translation as JSON
    openbible  cdn.bibel.wiki/openbible/ (bcv-commons/bibles 'o')  per book as USJ
    ebible     ebible.org/Scriptures/                               per book as USFM (zip), parsed with usfmtc
                                                                    as bcv-commons/bibles does (usfm_usj.py)

bcv-commons/bibles (cdn.bibel.wiki/catalog/) is the official discovery layer; eBible comes
after it for texts the catalogue doesn't carry yet. Two catalogue sources are listed but
not fetched: DBT ('d', needs your own API key) and PKF ('p', needs the Node decoder in
bcv-commons/bibles/tools/pkf-decode/).

The recipe is a 'fetch:' block in import/<licence>/<language>/<edition>/edition.yaml:

    fetch:
      source: helloao      # helloao | openbible | ebible
      id: dan_det          # helloAO translation id | openbible '<iso>/<edition>' | eBible id
      books: [mat, mrk]    # optional: only these books (BSB codes)

The fetched text goes to the edition's text/, one file per chapter (<code>NNN.txt) in the
format of the BSB files, with the source's own verse numbering. text/ is git-ignored (the
script writes a .gitignore next to it); the recipe, and fetch.lock.json with the source
version and a SHA-256 per file, are kept in git, so a later fetch shows whether the source
changed. Raw downloads are cached in download/editions/<edition>/.

The source's licence is checked against the licence folder: an edition can't sit in a
more open folder than its licence allows (e.g. a CC BY-NC text in CC-BY/). Where the
licence can't be read from the source, pass --licence-checked after checking it yourself.

Options: --force (download again), --update (accept a changed source and rewrite the lock),
--licence-checked.
"""
import csv, datetime, functools, hashlib, io, json, os, re, shutil, sys, urllib.request, zipfile
from books import BY_CODE, ROOT
from convert_usj import chapter_text, para_text, split_chapters
from usfm_usj import usfm_to_usj
from project import edition_dir, load_yaml

print = functools.partial(print, flush=True)
UA = {"User-Agent": "bsb-add-books-fetch/1.0"}      # cdn.bibel.wiki (Cloudflare) rejects urllib's default
DL = os.path.join(ROOT, "download", "editions")
CATALOG = "https://cdn.bibel.wiki/catalog/index.json"
HELLOAO = "https://bible.helloao.org/api"
OPENBIBLE = "https://cdn.bibel.wiki"
EBIBLE = "https://ebible.org/Scriptures"
OPEN = ["CC0", "CC-BY", "CC-BY-SA", "non-free"]      # most open first; a folder may be less open than the licence


def get(url, cache=None, force=False):
    if cache and os.path.exists(cache) and not force:
        return open(cache, "rb").read()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r:
        data = r.read()
    if cache:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        open(cache, "wb").write(data)
    return data


def getjson(url, cache=None, force=False):
    return json.loads(get(url, cache, force))


# ---------- licences ----------

def class_from_helloao(lic):
    if not lic:
        return None
    if lic.get("publicDomain"):
        return "CC0"
    if lic.get("commercialUse") == "not-allowed" or lic.get("derivatives") == "not-allowed":
        return "non-free"
    return "CC-BY-SA" if lic.get("copyleft") else "CC-BY"


def helloao_statement(lic):
    if not lic:
        return "no licence given"
    if lic.get("publicDomain"):
        return "public domain"
    parts = ["attribution required" if lic.get("attribution") == "required" else "no attribution required"]
    parts += ["no commercial use"] if lic.get("commercialUse") == "not-allowed" else []
    parts += ["no derivatives"] if lic.get("derivatives") == "not-allowed" else []
    parts += ["share alike"] if lic.get("copyleft") else []
    return ", ".join(parts)


def flat(x):
    """USJ content with its line breaks (inside strings) turned into spaces."""
    if isinstance(x, str):
        return x.replace("\n", " ")
    if isinstance(x, list):
        return [flat(y) for y in x]
    if isinstance(x, dict):
        return {k: flat(v) for k, v in x.items()}
    return x


def class_from_text(text):
    """A licence class from a licence name or statement; None if it can't be read."""
    t = text.lower().replace("_", "-")
    if re.search(r"\b(nc|nd)\b|non-?commercial|no-?deriv|creativecommons\.org/licenses/by-(nc|nd)", t):
        return "non-free"
    if re.search(r"cc0|public domain|publicdomain", t):
        return "CC0"
    if re.search(r"by-sa|cc by-sa|sharealike|share alike", t):
        return "CC-BY-SA"
    if re.search(r"cc by\b|creativecommons\.org/licenses/by/|attribution 4\.0", t):
        return "CC-BY"
    return None


def ebible_class(row, page):
    """Conservative: only an explicit Creative Commons link on the copyright page, or 'public domain' in the
    catalogue's Copyright field with no © in it; anything else (e.g. a public-domain NT with a © OT) is None."""
    if row["Redistributable"] != "True":
        return "non-free"
    cc = set(re.findall(r"creativecommons\.org/(?:licenses/([a-z-]+)|publicdomain/(zero))", page.lower()))
    kinds = {k or z for k, z in cc}
    if any("nc" in k.split("-") or "nd" in k.split("-") for k in kinds):
        return "non-free"
    copyright = row["Copyright"].lower()
    if "public domain" in copyright and "©" not in copyright and "copyright" not in copyright.replace("public domain", ""):
        return "CC0"
    if kinds == {"by-sa"}:
        return "CC-BY-SA"
    if kinds == {"by"}:
        return "CC-BY"
    if kinds == {"zero"}:
        return "CC0"
    return None


def check_licence(folder, found, statement, checked):
    print(f"  licence: {statement}  -> {found or 'not readable'}; folder {folder}")
    if folder not in OPEN:
        raise SystemExit(f"  unknown licence folder {folder!r}")
    if found is None:
        if not checked and folder != "non-free":
            raise SystemExit("  the licence can't be read from the source: check it, then run again with --licence-checked")
    elif OPEN.index(folder) < OPEN.index(found):
        raise SystemExit(f"  the licence ({found}) doesn't allow folder {folder}: move the edition to import/{found}/")


# ---------- helloAO JSON -> USJ-like paragraphs ----------

def helloao_books(tid, force):
    data = getjson(f"{HELLOAO}/{tid}/complete.json", os.path.join(DL, tid, "complete.json"), force)
    for book in data["books"]:
        items = []
        for ch in book["chapters"]:
            c = ch["chapter"]
            notes = {n["noteId"]: n.get("text", "") for n in c.get("footnotes", [])}
            items.append({"type": "chapter", "number": str(c["number"])})
            para = None

            def new(marker):
                nonlocal para
                para = {"type": "para", "marker": marker, "content": []}
                items.append(para)

            for block in c["content"]:
                t = block.get("type")
                if t == "heading":
                    items.append({"type": "para", "marker": "s1", "content": [" ".join(x for x in block["content"] if isinstance(x, str))]})
                    para = None
                elif t == "hebrew_subtitle":
                    items.append({"type": "para", "marker": "d", "content": [" ".join(x if isinstance(x, str) else x.get("text", "") for x in block["content"])]})
                    para = None
                elif t == "line_break":
                    items.append({"type": "para", "marker": "b", "content": []})
                    para = None
                elif t == "verse":
                    first = True
                    for x in block["content"]:
                        if isinstance(x, str) or "text" in x:
                            text = x if isinstance(x, str) else x["text"]
                            poem = None if isinstance(x, str) else x.get("poem")
                            marker = f"q{min(poem, 4)}" if poem else "p"
                            if para is None or poem or para["marker"] != marker:
                                new(marker)
                            if first:
                                para["content"].append({"type": "verse", "number": str(block["number"])})
                                first = False
                            para["content"].append(text + " ")
                        elif "noteId" in x and para is not None:
                            para["content"].append({"type": "note", "content": [re.sub(r"^\d+\.\d+\s*", "", notes.get(x["noteId"], ""))]})
                        elif x.get("lineBreak"):
                            para = None
        yield book["id"], book.get("commonName") or book.get("name") or book["id"], items


def para_title(item):
    return para_text(item).strip() or None


# ---------- sources ----------

def fetch_source(rec, force):
    """-> (name, url, licence statement, licence class, version, [(BOOK, title, items)])"""
    src, sid = rec["source"], rec["id"]
    if src == "helloao":
        listing = getjson(f"{HELLOAO}/available_translations.json", os.path.join(DL, "_helloao", "available_translations.json"), True)
        t = next((x for x in listing["translations"] if x["id"] == sid), None)
        if not t:
            raise SystemExit(f"  helloAO has no translation {sid!r}")
        books = list(helloao_books(sid, force))
        return (t.get("englishName") or t["name"], t.get("website") or f"{HELLOAO}/{sid}", helloao_statement(t.get("license")),
                class_from_helloao(t.get("license")), t.get("sha256"), books)
    if src == "openbible":
        meta = getjson(f"{OPENBIBLE}/openbible/{sid}/_meta.json", os.path.join(DL, sid.replace("/", "_"), "_meta.json"), force)
        lics = meta.get("licenses") or []
        statement = "; ".join(f"{l.get('type')} {l.get('url', '')}".strip() for l in lics)
        classes = [class_from_text(f"{l.get('type')} {l.get('url', '')}") for l in lics]
        found = min((c for c in classes if c), key=OPEN.index, default=None)
        books = []
        for b in meta.get("books", []):
            code = b if isinstance(b, str) else b.get("code") or b.get("id")
            usj = getjson(f"{OPENBIBLE}/openbible/{sid}/{code}.usj.json", os.path.join(DL, sid.replace("/", "_"), f"{code}.usj.json"), force)
            title = next((c.get("content", [code])[0] for c in usj["content"] if c.get("marker") == "h"), code)
            books.append((code, title, flat(usj["content"])))
        return meta.get("name") or sid, f"{OPENBIBLE}/openbible/{sid}/", statement, found, meta.get("version") or meta.get("updated"), books
    if src == "ebible":
        rows = list(csv.DictReader(io.StringIO(get(f"{EBIBLE}/translations.csv", os.path.join(DL, "_ebible", "translations.csv"), True).decode("utf-8-sig"))))
        row = next((r for r in rows if r["translationId"] == sid), None)
        if not row:
            raise SystemExit(f"  eBible has no translation {sid!r}")
        z = zipfile.ZipFile(io.BytesIO(get(f"{EBIBLE}/{sid}_usfm.zip", os.path.join(DL, sid, f"{sid}_usfm.zip"), force)))
        about = get(f"https://ebible.org/{sid}/copyright.htm", os.path.join(DL, sid, "copyright.htm"), force).decode("utf-8", "replace")
        statement = f"{row['Copyright']} (redistributable: {row['Redistributable']})"
        found = ebible_class(row, re.sub(r"<[^>]+>", " ", about))
        books = []
        for n in sorted(z.namelist()):
            if n.endswith(".usfm"):
                content = usfm_to_usj(z.read(n).decode("utf-8-sig"))["content"]
                code = next((c.get("code") for c in content if c.get("type") == "book"), None)
                title = next((para_title(c) for c in content if c.get("type") == "para" and c.get("marker") == "h"), code)
                books.append((code, title, content))
        return row["title"], row["publicationURL"] or f"https://ebible.org/{sid}/", statement, found, row["UpdateDate"], books
    raise SystemExit(f"  unknown source {src!r} (helloao, openbible, ebible)")


def fetch_edition(name, force=False, update=False, checked=False):
    rel = edition_dir(name)
    path = os.path.join(ROOT, rel)
    ed = load_yaml(os.path.join(path, "edition.yaml"))
    rec = ed.get("fetch")
    if not rec:
        raise SystemExit(f"{name}: edition.yaml has no fetch: block")
    print(f"{rel}: {rec['source']} {rec['id']}")
    title, url, statement, found, version, books = fetch_source(rec, force)
    check_licence(rel.split(os.sep)[1], found, statement, checked)
    want = set(rec.get("books") or [])
    tmp = os.path.join(path, ".text.new")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    files = {}
    for book_id, btitle, items in books:
        code = (book_id or "").lower()
        if code not in BY_CODE or (want and code not in want):
            continue
        for number, chapter in split_chapters(items):
            fname = "%s%03d.txt" % (code, number)
            text = chapter_text(ed.get("name") or title, f"{url} ({statement})", book_id, btitle, number, chapter)
            open(os.path.join(tmp, fname), "w", encoding="utf-8").write(text)
            files[fname] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    lock_path = os.path.join(path, "fetch.lock.json")
    lock = {"source": rec["source"], "id": rec["id"], "url": url, "licence": statement, "version": version,
            "fetched": datetime.date.today().isoformat(), "files": dict(sorted(files.items()))}
    old = json.load(open(lock_path, encoding="utf-8")) if os.path.exists(lock_path) else None
    if old and old["files"] != lock["files"] and not update:
        changed = sum(old["files"].get(k) != v for k, v in files.items()) + len(set(old["files"]) - set(files))
        shutil.rmtree(tmp)
        raise SystemExit(f"  the source changed since {old['fetched']} (files differing: {changed}; version {old.get('version')} -> {version}).\n"
                         "  Kept the old text. Run again with --update to take the new one.")
    shutil.rmtree(os.path.join(path, "text"), ignore_errors=True)
    os.replace(tmp, os.path.join(path, "text"))
    open(os.path.join(path, ".gitignore"), "w").write("# written by scripts/fetch_edition.py: the text is fetched, not kept in git\ntext/\n.text.new/\n")
    if not old or old["files"] != lock["files"] or update:
        json.dump(lock, open(lock_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  {len(files)} chapter files in {rel}/text/")


# ---------- --find ----------

def candidates(iso):
    """Every edition of a language the sources list, best first: [{source, id, title, cls, licence, books,
    nt, ot, note}]; cls is the licence class (CC0 / CC-BY / CC-BY-SA / non-free) or None if it can't be read
    from the listing (eBible: decided from its copyright page when fetched). Also {"catalog": [...]}: the
    bcv-commons/bibles catalogue's coverage rows for the language (nt / ot / otp = part of the OT)."""
    out, catalog = [], []
    try:
        catalog = [(cov, src) for e in getjson(CATALOG)["entries"] if e[0] == iso for _, cov, src in [e[:3]]]
    except Exception as e:  # the listings below still work
        catalog = [("unreachable", str(e))]
    for t in getjson(f"{HELLOAO}/available_translations.json")["translations"]:
        if t.get("language") == iso:
            nb = t.get("numberOfBooks") or 0
            out.append({"source": "helloao", "id": t["id"], "title": t.get("englishName") or t["name"],
                        "cls": class_from_helloao(t.get("license")), "licence": helloao_statement(t.get("license")),
                        "books": nb, "nt": nb >= 27 or None, "ot": nb > 27 or None, "url": t.get("licenseUrl") or t.get("website") or "",
                        "language_name": t.get("languageEnglishName") or t.get("languageName")})
    for e in getjson(f"{OPENBIBLE}/catalog/openbible-editions.json")["entries"].values():
        if e.get("iso") == iso:
            lics = e.get("licenses", [])
            classes = [class_from_text(f"{l.get('type')} {l.get('url', '')}") for l in lics]
            books = [b if isinstance(b, str) else b.get("code") or b.get("id") for b in e.get("books", [])]
            codes = {str(b).lower() for b in books}
            out.append({"source": "openbible", "id": f"{iso}/{e['abbr']}", "title": e.get("name") or e["abbr"],
                        "cls": min((c for c in classes if c), key=OPEN.index, default=None),
                        "licence": "; ".join(l.get("type", "") for l in lics), "books": len(books),
                        "nt": any(BY_CODE.get(c, ("", "", ""))[2] == "nt" for c in codes) or None,
                        "ot": any(BY_CODE.get(c, ("", "", ""))[2] == "ot" for c in codes) or None,
                        "note": "" if e.get("published") else "not published: " + e.get("reason", ""), "url": ""})
    for r in csv.DictReader(io.StringIO(get(f"{EBIBLE}/translations.csv").decode("utf-8-sig"))):
        if r["languageCode"] == iso:
            cls = "non-free" if r["Redistributable"] != "True" else class_from_text(r["Copyright"])
            ot, nt = int(r["OTbooks"] or 0), int(r["NTbooks"] or 0)
            out.append({"source": "ebible", "id": r["translationId"], "title": f"{r['title']} ({r['description']})",
                        "cls": cls, "licence": f"{r['Copyright']}; redistributable {r['Redistributable']}",
                        "books": ot + nt, "nt": nt > 0, "ot": ot > 0, "ot_books": ot, "nt_books": nt,
                        "url": f"https://ebible.org/{r['translationId']}/"})
    return out, catalog


def find(iso):
    print(f"Editions for {iso!r}. Check the licence on the source before importing (import/README.md).\n")
    found, catalog = candidates(iso)
    print("bcv-commons/bibles catalogue:", ", ".join(f"{s}:{c}" for c, s in catalog) or "nothing",
          "  (h = helloAO, o = openbible, d = DBT: needs an API key, p = PKF: needs the Node decoder)")
    for c in found:
        print(f"  {c['source']:10} {c['id']:24} {c['title']}  [{c['cls'] or '?'}: {c['licence']}] {c['books']} books"
              + (f"  {c['note']}" if c.get("note") else ""))
    print("\nCrossWire (SWORD modules) isn't searched; see https://www.crosswire.org/sword/modules/")


def main():
    argv = sys.argv[1:]
    flags = {a for a in argv if a.startswith("--")}
    args = [a for a in argv if not a.startswith("--")]
    if "--find" in flags:
        return find(args[0])
    names = args
    if "--all" in flags:
        names = [d for lic in sorted(os.listdir(os.path.join(ROOT, "import"))) if not lic.startswith(("_", "."))
                 and os.path.isdir(os.path.join(ROOT, "import", lic))
                 for lang in sorted(os.listdir(os.path.join(ROOT, "import", lic))) if os.path.isdir(os.path.join(ROOT, "import", lic, lang))
                 for d in sorted(os.listdir(os.path.join(ROOT, "import", lic, lang)))
                 if (load_yaml(p) if os.path.isfile(p := os.path.join(ROOT, "import", lic, lang, d, "edition.yaml")) else {}).get("fetch")]
    if not names:
        if "--all" in flags:
            return print("No edition in import/ has a fetch recipe.")
        raise SystemExit(__doc__)
    failed = []
    for n in names:
        try:
            fetch_edition(n, "--force" in flags, "--update" in flags, "--licence-checked" in flags)
        except SystemExit as e:
            if len(names) == 1:
                raise
            print(e); failed.append(n)
    if failed:
        raise SystemExit(f"\nNot fetched: {', '.join(failed)}")


if __name__ == "__main__":
    main()
