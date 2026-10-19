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
    dbt        4.dbt.io (Digital Bible Platform, bcv-commons/bibles 'd') per chapter: the Sofria document (text_json,
               paragraphs, headings, footnotes; decoded here) where the text has one, else plain verses; needs your own API
               key (free to register at https://4.dbt.io): the environment variable DBT_API_KEY, or a line
               DBT_API_KEY=... in .env in the working copy (git-ignored). The key is read only to make a
               request: it is never printed, logged, cached or written into a file name.

bcv-commons/bibles (cdn.bibel.wiki/catalog/) is the official discovery layer; eBible comes
after it for texts the catalogue doesn't carry yet. Two catalogue sources are listed but
not fetched: PKF ('p', needs the Node decoder in bcv-commons/bibles/tools/pkf-decode/). DBT ('d') is fetched when
a key is set (see dbt above); without one, --find says that the catalogue has the language on DBT.

The recipe is a 'fetch:' block in import/<licence>/<language>/<edition>/edition.yaml:

    fetch:
      source: helloao      # helloao | openbible | ebible | dbt | local (the team's files in the edition's source/)
      id: dan_det          # helloAO translation id | openbible '<iso>/<edition>' | eBible id | DBT text fileset id

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


def get(url, cache=None, force=False, max_age=None):
    """The URL's body, from the cache when it is there (and younger than max_age seconds, if given)."""
    import time
    if cache and os.path.exists(cache) and not force and (max_age is None or time.time() - os.path.getmtime(cache) < max_age):
        return open(cache, "rb").read()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r:
        data = r.read()
    if cache:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        open(cache, "wb").write(data)
    return data


def getjson(url, cache=None, force=False, max_age=None):
    return json.loads(get(url, cache, force, max_age))


DAY = 24 * 3600            # the listings --find reads are cached for a day (download/editions/_listings/)
LISTINGS = os.path.join(DL, "_listings")


# ---------- DBT (Digital Bible Platform) ----------

def dbt_base():
    import localenv
    return (localenv.key("DBT_API_BASE_URL") or "https://4.dbt.io/api").rstrip("/")
def dbt_key():
    """The user's DBT key: DBT_API_KEY from the environment, else from .env (git-ignored; scripts/localenv.py)."""
    import localenv
    return localenv.key("DBT_API_KEY")


def dbt_get(path, cache=None, force=False, **params):
    """GET {dbt_base()}/{path} as JSON. The key goes only into the request; errors are reported without the URL."""
    if cache and os.path.exists(cache) and not force:
        return json.load(open(cache, encoding="utf-8"))
    key = dbt_key()
    if not key:
        raise SystemExit("  DBT needs your API key: set DBT_API_KEY, or put DBT_API_KEY=... in .env (git-ignored); "
                         "a key is free at https://4.dbt.io")
    import urllib.parse, time
    q = urllib.parse.urlencode({**params, "v": "4", "key": key})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{dbt_base()}/{path}?{q}", headers=UA), timeout=120) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (401, 403):
                raise SystemExit(f"  DBT refused the key for {path} (HTTP {e.code}): check the key, or whether it covers this text")
            err = f"HTTP {e.code}"
        except (urllib.error.URLError, OSError) as e:
            err = type(e).__name__
        if attempt == 3:
            raise SystemExit(f"  DBT {path}: {err} after 4 tries")
        time.sleep(3 * (attempt + 1))
    if cache:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        json.dump(data, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return data


def dbt_bibles(iso):
    """DBT's bibles of a language with a plain-text fileset: [{id (the fileset), bible, title, books}]."""
    out = []
    for b in (dbt_get("bibles", language_code=iso) or {}).get("data", []):
        sets = (b.get("filesets") or {}).get("dbp-prod", [])
        sofria = {fs["id"] for fs in sets if fs.get("type") == "text_json"}
        for fs in sets:
            if fs.get("type") == "text_plain":
                out.append({"id": fs["id"], "bible": b.get("abbr"), "size": fs.get("size"),
                            "title": b.get("vname") or b.get("name") or b.get("abbr"),
                            "sofria": fs["id"] + "-json" if fs["id"] + "-json" in sofria else None})
    return out


def sofria_items(doc):
    """A Proskomma Sofria document (DBT's text_json filesets) -> the item shape of the other sources: chapter items,
    paragraphs with their USFM marker, verse markers, text, footnotes (grafts of type footnote) and headings (title and
    heading grafts as paragraphs of their own). Cross references are left out, as in the other sources."""
    items = []

    def kind(g):                                       # a graft's kind: its subtype, or its sequence's type (DBT)
        return g.get("subtype") or (g.get("sequence") or {}).get("type")

    def text_of(seq):
        out = []
        for b in (seq or {}).get("blocks", []):
            walk(b.get("content", []), out, notes=None)
        return re.sub(r"\s+", " ", "".join(x for x in out if isinstance(x, str))).strip()

    def walk(content, out, notes):
        for x in content:
            if isinstance(x, str):
                out.append(x)
            elif x.get("type") == "mark" and x.get("subtype") == "chapter_label":
                items.append({"type": "chapter", "number": str(x["atts"]["number"])})
            elif x.get("type") == "mark" and x.get("subtype") == "verses_label":
                out.append({"type": "verse", "number": str(x["atts"]["number"])})
            elif x.get("type") == "wrapper":
                walk(x.get("content", []), out, notes)
            elif x.get("type") == "graft" and kind(x) == "footnote" and notes is not None:
                t = text_of(x.get("sequence"))
                if t:
                    out.append({"type": "note", "content": [t]})
    for b in doc["sequence"]["blocks"]:
        if b.get("type") == "graft":
            if kind(b) == "heading":                   # a book title (kind "title") is not part of the chapter text
                t = text_of(b.get("sequence"))
                if t:
                    items.append({"type": "para", "marker": "s1", "content": [t]})
            continue
        marker = (b.get("subtype") or "usfm:p").split(":")[-1]
        content = []
        walk(b.get("content", []), content, notes=True)
        items.append({"type": "para", "marker": marker if re.fullmatch(r"(p|m|pi\d?|q\d?|li\d?|nb|pc|mi)", marker) else "p",
                "content": content})
    return items


def dbt_books(fileset, bible, force, sofria=None, workers=6):
    """[(BOOK, title, items)] of a DBT text fileset, in the item shape of the other sources. With a Sofria fileset
    (`<fileset>-json`), its documents (paragraphs, headings, footnotes); else the plain verses. Downloads run six at a
    time (DBT answers in 1-13 s): chapter 1 of every book first (which books the text has), then the rest. Every answer
    is cached in download/editions/<fileset>/, a missing chapter too, so a stopped run continues where it stopped."""
    from books import chapters as n_chapters
    from concurrent.futures import ThreadPoolExecutor
    import urllib.request as UR
    set_id = sofria or fileset
    cache = os.path.join(DL, set_id)
    os.makedirs(cache, exist_ok=True)
    print(f"  downloading {set_id} ({'Sofria: paragraphs, headings, footnotes' if sofria else 'plain verses'}) "
          f"into {os.path.relpath(cache, ROOT)}/; a stopped run continues from there")

    def path(book, c):
        return os.path.join(cache, f"{book}_{c:03d}.json")

    def fetch(task):
        """Download one chapter into the cache (or mark it missing). -> True if it exists."""
        book, c = task
        f = path(book, c)
        if not force and (os.path.exists(f) or os.path.exists(f[:-5] + ".none")):
            return os.path.exists(f)
        r = dbt_get(f"bibles/filesets/{set_id}/{book}/{c}")
        rows = (r or {}).get("data") or []
        tf = os.path.join(cache, f"{book}.title")
        if rows and rows[0].get("book_name") and not os.path.exists(tf):          # the book's own name (Matyu)
            open(tf, "w", encoding="utf-8").write(rows[0]["book_name"])
        data = rows or None
        if sofria and rows and rows[0].get("path"):
            try:              # a signed, short-lived link to the chapter's document (never printed or kept)
                with UR.urlopen(UR.Request(rows[0]["path"], headers=UA), timeout=120) as resp:
                    data = json.loads(resp.read())
            except Exception as e:
                raise SystemExit(f"  {book} {c}: the Sofria document could not be downloaded ({type(e).__name__}); "
                                 "run again to continue")
        if data:
            json.dump(data, open(f + ".part", "w", encoding="utf-8"), ensure_ascii=False)
            os.replace(f + ".part", f)
        else:
            open(f[:-5] + ".none", "w").close()
        return bool(data)

    books = [(code, code.upper(), title) for code, (_, title, _p, _u) in BY_CODE.items()]   # always every book
    with ThreadPoolExecutor(workers) as pool:
        first = dict(zip([b for _, b, _ in books], pool.map(fetch, [(b, 1) for _, b, _ in books])))
        rest = [(b, c) for code, b, _ in books if first[b] for c in range(2, n_chapters(code) + 1)]
        done = 0
        for _ in pool.map(fetch, rest):
            done += 1
            if done % 25 == 0:
                print(f"  {done + sum(first.values())} of {len(rest) + sum(first.values())} chapters")
    out = []
    for code, book, title in books:
        if not first[book]:
            continue
        tf = os.path.join(cache, f"{book}.title")
        if os.path.exists(tf):
            title = open(tf, encoding="utf-8").read().strip() or title
        items, got = [], 0
        for c in range(1, n_chapters(code) + 1):
            if not os.path.exists(path(book, c)):
                continue
            data = json.load(open(path(book, c), encoding="utf-8"))
            got += 1
            if sofria:
                ch_items = sofria_items(data)
                if not any(i["type"] == "chapter" for i in ch_items):
                    ch_items.insert(0, {"type": "chapter", "number": str(c)})
                items += ch_items
            else:
                items.append({"type": "chapter", "number": str(c)})
                para = {"type": "para", "marker": "p", "content": []}
                for v in data:
                    para["content"] += [{"type": "verse", "number": str(v["verse_start"])}, (v.get("verse_text") or "").strip() + " "]
                items.append(para)
        out.append((book, title, items))
        print(f"  {book}: {got} chapters")
    return out


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

def local_books(folder):
    """The team's own USFM / SFM files in an edition's source/ -> [(BOOK, title, items)] (NFC; usfm_usj.py)."""
    import unicodedata
    if not os.path.isdir(folder):
        raise SystemExit(f"  no folder {os.path.relpath(folder, ROOT)}: copy the files (.usfm, .sfm, one per book) there")
    books = []
    for f in sorted(os.listdir(folder)):
        if f.lower().endswith((".usfm", ".sfm")):
            raw = open(os.path.join(folder, f), encoding="utf-8-sig", errors="replace").read()
            content = usfm_to_usj(unicodedata.normalize("NFC", raw))["content"]
            code = next((c.get("code") for c in content if c.get("type") == "book"), None)
            title = next((para_title(c) for c in content if c.get("type") == "para" and c.get("marker") == "h"), code)
            if code:
                books.append((code, title, content))
    if not books:
        raise SystemExit(f"  no .usfm or .sfm files in {os.path.relpath(folder, ROOT)}: copy them there and run again")
    return books


def fetch_source(rec, force, edition_path=None):
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
    if src == "local":
        folder = os.path.join(edition_path or ROOT, rec.get("id") or "source")
        return ("", "the team's own files", None, None, None, local_books(folder))
    if src == "dbt":
        iso = rec.get("language") or sid[:3].lower()
        fs = next((b for b in dbt_bibles(iso) if b["id"] == sid), None)
        if not fs:
            raise SystemExit(f"  DBT has no plain-text fileset {sid!r} for {iso!r}")
        cp = dbt_get(f"bibles/{fs['bible']}/copyright", os.path.join(DL, sid, "copyright.json"), force)
        lines = [x.get("copyright", {}).get("copyright") for x in (cp if isinstance(cp, list) else [cp])
                 if isinstance(x, dict) and str(x.get("type", "text")).startswith("text")]      # not the audio / video
        statement = "; ".join(dict.fromkeys(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", l)).strip() for l in lines if l)) or "see DBT"
        # DBT texts are licensed for display in apps: kept local (non-free) unless the copyright says otherwise
        return (fs["title"], f"https://www.bible.is/bible/{fs['bible']}", statement, "non-free", fs.get("size"),
                dbt_books(sid, fs["bible"], force, fs.get("sofria")))
    raise SystemExit(f"  unknown source {src!r} (helloao, openbible, ebible, dbt, local)")


def set_licence(yaml_path, ed, statement, url):
    """licence and credit from the source's own copyright line, in an edition.yaml marked `licence_source: fetched`
    (the wizard's editions; a hand-written licence is never touched). Only those two lines change; comments stay."""
    name = ed.get("name") or ""
    credit = f"{name}, {statement}" + (f" ({url})" if url and url not in statement else "")
    text = open(yaml_path, encoding="utf-8").read()
    for key, value in (("licence", statement), ("credit", credit)):
        text = re.sub(rf"^{key}:.*(?:\n[ \t]+.*)*$", f"{key}: {json.dumps(value, ensure_ascii=False)}", text, count=1, flags=re.M)
    if ed.get("attribution"):
        text = re.sub(r"^attribution:.*(?:\n[ \t]+.*)*$", f"attribution: {json.dumps(credit, ensure_ascii=False)}", text, count=1, flags=re.M)
    open(yaml_path, "w", encoding="utf-8").write(text)
    print(f"  licence from the source: {statement}")


def fetch_edition(name, force=False, update=False, checked=False):
    rel = edition_dir(name)
    path = os.path.join(ROOT, rel)
    ed = load_yaml(os.path.join(path, "edition.yaml"))
    rec = ed.get("fetch")
    if not rec:
        raise SystemExit(f"{name}: edition.yaml has no fetch: block")
    print(f"{rel}: {rec['source']} {rec['id']}")
    title, url, statement, found, version, books = fetch_source(rec, force, path)
    if rec["source"] != "local":          # the team's own files: their licence is what edition.yaml states
        check_licence(rel.split(os.sep)[1], found, statement, checked)
    statement = statement or ed.get("licence", "")
    if ed.get("licence_source") == "fetched" and statement:
        set_licence(os.path.join(path, "edition.yaml"), ed, statement, url)
    if rec.get("books"):
        raise SystemExit(f"{name}: the recipe limits the books (books: ...); an edition is always fetched whole: every book "
                         "the source has is corpus for the drafts. Remove the line.")
    tmp = os.path.join(path, ".text.new")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    files = {}
    for book_id, btitle, items in books:
        code = (book_id or "").lower()
        if code not in BY_CODE:
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
        catalog = [(cov, src) for e in getjson(CATALOG, os.path.join(LISTINGS, "catalog.json"), max_age=DAY)["entries"]
                   if e[0] == iso for _, cov, src in [e[:3]]]
    except Exception as e:  # the listings below still work
        catalog = [("unreachable", str(e))]
    for t in getjson(f"{HELLOAO}/available_translations.json", os.path.join(LISTINGS, "helloao.json"), max_age=DAY)["translations"]:
        if t.get("language") == iso:
            nb = t.get("numberOfBooks") or 0
            out.append({"source": "helloao", "id": t["id"], "title": t.get("englishName") or t["name"],
                        "cls": class_from_helloao(t.get("license")), "licence": helloao_statement(t.get("license")),
                        "books": nb, "nt": nb >= 27 or None, "ot": nb > 27 or None, "url": t.get("licenseUrl") or t.get("website") or "",
                        "language_name": t.get("languageEnglishName") or t.get("languageName")})
    for e in getjson(f"{OPENBIBLE}/catalog/openbible-editions.json", os.path.join(LISTINGS, "openbible.json"), max_age=DAY)["entries"].values():
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
    for r in csv.DictReader(io.StringIO(get(f"{EBIBLE}/translations.csv", os.path.join(LISTINGS, "ebible.csv"), max_age=DAY).decode("utf-8-sig"))):
        if r["languageCode"] == iso:
            cls = "non-free" if r["Redistributable"] != "True" else class_from_text(r["Copyright"])
            ot, nt = int(r["OTbooks"] or 0), int(r["NTbooks"] or 0)
            out.append({"source": "ebible", "id": r["translationId"], "title": f"{r['title']} ({r['description']})",
                        "cls": cls, "licence": f"{r['Copyright']}; redistributable {r['Redistributable']}",
                        "books": ot + nt, "nt": nt > 0, "ot": ot > 0, "ot_books": ot, "nt_books": nt,
                        "url": f"https://ebible.org/{r['translationId']}/"})
    if any(src == "d" for _, src in catalog) or dbt_key():
        if dbt_key():
            for b in dbt_bibles(iso):
                size = str(b.get("size") or "")
                out.append({"source": "dbt", "id": b["id"], "title": b["title"], "cls": "non-free",
                            "licence": "DBT: licensed for display; kept local", "books": None,
                            "nt": size in ("NT", "NTP", "C") or None, "ot": size in ("OT", "OTP", "C") or None,
                            "coverage": {"NT": "New Testament", "NTP": "part of the New Testament", "OT": "Old Testament",
                                         "OTP": "part of the Old Testament", "C": "whole Bible"}.get(size),
                            "url": "https://www.bible.is/", "language": iso})
        else:
            out.append({"source": "dbt", "id": None, "title": "on the Digital Bible Platform (DBT)", "cls": "non-free",
                        "licence": "needs your API key", "books": None, "nt": None, "ot": None, "url": "https://4.dbt.io",
                        "note": "set DBT_API_KEY, or DBT_API_KEY=... in .env (git-ignored), to list and fetch it"})
    return out, catalog


def find(iso):
    print(f"Editions for {iso!r}. Check the licence on the source before importing (import/README.md).\n")
    found, catalog = candidates(iso)
    print("bcv-commons/bibles catalogue:", ", ".join(f"{s}:{c}" for c, s in catalog) or "nothing",
          "  (h = helloAO, o = openbible, d = DBT: needs an API key, p = PKF: needs the Node decoder)")
    for c in found:
        print(f"  {c['source']:10} {c['id'] or '(no key)':24} {c['title']}  [{c['cls'] or '?'}: {c['licence']}] "
              f"{str(c['books']) + ' books' if c.get('books') else 'books: read when fetched'}"
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
