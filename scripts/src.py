#!/usr/bin/env python3
"""The prepared source structure (internal-docs plan, sections 4, 10, 13): one local SQLite file per original
language, built from published sources at pinned versions, never published (orig/ is git-ignored).

Hebrew, orig/heb.sqlite, from:
  - MACULA Hebrew lowfat XML (Clear-Bible/macula-hebrew, WLC, CC BY 4.0, pinned MACULA_HEB): every token with
    morphology, glosses, transliteration, the LXX equivalent, SDBH sense and domain codes (© UBS, used with
    permission inside MACULA: local use only), semantic frames and participant referents; the syntax tree (word
    groups and clauses, with rule, role, head);
  - compact-alignments' _index (CC0): the content / function ordinals (cN / fN) and the tagged format's verse-local
    numbers (scripts/full_align.py);
  - the BSB Translation Tables (full-alignments-manual eng_BSB+manual+bsb-tables, CC0): which BSB words render each
    token (positions in the BSB verse);
  - the two clause layouts on this machine: orig/heb-bhsa (BHSA 2021, CC BY-NC: local only) and orig/heb-bcv-query
    (+ -keys; hebrew-clause-layout v0.22, CC BY-SA): the line of each token in each layout.

Tables:
  tokens(key, book, ch, v, word, n, kind, ord, text, after, lemma, lexeme, strong, class, pos, morph, type, stem,
         person, gender, number, state, role, gloss, english, translit, greek, greekstrong, sdbh, lexdomain,
         coredomain, sensenumber, lang, node, clause)
      key = the MACULA word id without its 'o' (12 digits, as in the scaffold and compact-alignments); word = the
      orthographic word's number in the verse (lowfat ref `!N`); n = the tagged format's number, kind/ord = c|f and
      the compact ordinal (NULL for an elided article, which has no index entry); node = the token's word group,
      clause = its nearest clause (class cl)
  nodes(id, book, ch, v, parent, class, rule, role, head, clausetype, first, last)
  refs(key, kind, target)          participantref / subjref / frame roles (A0, A1, AA): who a token refers to
  bsb(key, positions)              BSB token positions ("3 4")
  layout(key, layout, line, level) the token's line in a clause layout (line = the chapter's line number, 0-based)
  lxx(lexeme, greekstrong, greek, n)   the per-token LXX equivalents counted over the whole build (the bridge)
  meta(name, value)

Greek, orig/grc.sqlite, from MACULA Greek lowfat (Clear-Bible/macula-greek, Nestle 1904, CC BY 4.0, pinned
MACULA_GRC): tokens (lemma, Strong's, morphology, Louw-Nida domain and sense (UBS data: local use only), role,
referents, frames), the tree, compact-alignments' NT numbering, the BSB tables' NT part, and the token mapping from
our two Greek texts to MACULA's keys: map(edition, book, ch, v, pos, key, how) for orig/grc (BGB, the BSB's) and
orig/grc-rp (RP 2018, the MSB's); how = same | spelling | moved, a variant token has no row.

    python3 scripts/src.py build [code ...]          build or update (default: every OT book; NT codes -> Greek)
    python3 scripts/src.py speakers                  who speaks where: Clear Bible's MACULA Quotation and Speaker Data
                                                     (CC BY 4.0; with SIL Glyssen / FCBH character data, MIT), one span
                                                     per quotation with its first and last MACULA word, via shoresh
    python3 scripts/src.py layouts [code ...] [--layout bhsa|bcv-query]   (re)build the layout rows from the layouts here
    python3 scripts/src.py map [code ...]            (re)build the BGB/RP -> MACULA mapping in orig/grc.sqlite
    python3 scripts/src.py export-open DIR           the publishable cache: no UBS columns, no BHSA (manifest.json)
    python3 scripts/src.py show <code> <ch>:<v>      one verse: tokens, numbers, clause, referents, LXX, BSB words
    python3 scripts/src.py bridge <lexeme>           the LXX equivalents of a Hebrew lexeme (e.g. 2617 or H2617)
    python3 scripts/src.py stats                     what the file holds
"""
import json, os, re, sqlite3, sys, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from books import BY_CODE, heb_chapters  # noqa: E402

MACULA_HEB = "47db250bd55d0d8577f2a94fba114ef16c35b23c"  # Clear-Bible/macula-hebrew main, 2026-04-24
RAW = f"https://raw.githubusercontent.com/Clear-Bible/macula-hebrew/{MACULA_HEB}/WLC/lowfat"
LISTING = f"https://api.github.com/repos/Clear-Bible/macula-hebrew/contents/WLC/lowfat?ref={MACULA_HEB}"
CACHE = os.path.join(ROOT, "download", "macula-hebrew", MACULA_HEB[:12])
DB = os.path.join(ROOT, "orig", "heb.sqlite")
MACULA_GRC = "8423afe47b9e8f24b7772e808af45c7159a6fe7e"  # Clear-Bible/macula-greek main, 2026-07-07
RAW_GRC = f"https://raw.githubusercontent.com/Clear-Bible/macula-greek/{MACULA_GRC}/Nestle1904/lowfat"
CACHE_GRC = os.path.join(ROOT, "download", "macula-greek", MACULA_GRC[:12])
DB_GRC = os.path.join(ROOT, "orig", "grc.sqlite")
GRC_FILES = ("matthew mark luke john acts romans 1corinthians 2corinthians galatians ephesians philippians colossians "
             "1thessalonians 2thessalonians 1timothy 2timothy titus philemon hebrews james 1peter 2peter 1john 2john "
             "3john jude revelation").split()
GRC_ATTRS = ("lemma", "normalized", "strong", "class", "type", "morph", "case", "number", "gender", "tense", "voice",
             "mood", "person", "degree", "role", "gloss", "domain", "ln", "discontinuous")
UA = {"User-Agent": "bsb-add-books/1.0"}
XID = "{http://www.w3.org/XML/1998/namespace}id"
TOKEN_ATTRS = ("lemma", "strongnumberx", "stronglemma", "class", "pos", "morph", "type", "stem", "person", "gender",
               "number", "state", "role", "gloss", "english", "transliteration", "greek", "greekstrong", "sdbh",
               "lexdomain", "coredomain", "sensenumber", "lang")
SCHEMA = """
create table if not exists tokens(key text primary key, book text, ch int, v int, word int, n int, kind text, ord int,
  text text, after text, lemma text, lexeme text, stronglemma text, class text, pos text, morph text, type text, stem text,
  person text, gender text, number text, state text, role text, gloss text, english text, translit text, greek text,
  greekstrong text, sdbh text, lexdomain text, coredomain text, sensenumber text, lang text, node text, clause text);
create index if not exists tokens_ref on tokens(book, ch, v);
create index if not exists tokens_lexeme on tokens(lexeme);
create table if not exists nodes(id text primary key, book text, ch int, v int, parent text, class text, rule text,
  role text, head text, clausetype text, first text, last text);
create table if not exists refs(key text, kind text, target text);
create index if not exists refs_key on refs(key);
create index if not exists refs_target on refs(target);
create table if not exists bsb(key text primary key, positions text);
create table if not exists layout(key text, layout text, line int, level int);
create index if not exists layout_key on layout(key);
create table if not exists lxx(lexeme text, greekstrong text, greek text, n int);
create table if not exists meta(name text primary key, value text);
"""


def get(url, path, timeout=300):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                    data = r.read()
                break
            except Exception:
                if attempt == 2:
                    raise
        open(path + ".part", "wb").write(data)
        os.replace(path + ".part", path)
    return path


def lowfat_names():
    """{BOOK: file name prefix} from the pinned listing (e.g. GEN -> 01-Gen, HOS -> 28-HOS)."""
    listing = json.load(open(get(LISTING, os.path.join(CACHE, "listing.json")), encoding="utf-8"))
    out = {}
    for x in listing:
        m = re.match(r"(\d\d-(\w+))-\d{3}-lowfat\.xml$", x["name"])
        if m:
            out[m[2].upper()] = m[1]
    alias = {"SNG": "SNG", "EZK": "EZK", "JOL": "JOL", "NAM": "NAM"}
    return {**out, **{k: out[v] for k, v in alias.items() if v in out}}


def lowfat(book, ch, names):
    name = f"{names[book]}-{ch:03d}-lowfat.xml"
    return ET.parse(get(f"{RAW}/{name}", os.path.join(CACHE, name))).getroot()


def chapter_rows(book, ch, root):
    """tokens, nodes, refs of one chapter from its lowfat tree."""
    tokens, nodes, refs = [], [], []
    counter = [0]

    def walk(e, parent, clause, v):
        for c in e:
            if c.tag == "milestone" and c.get("unit") == "verse":
                v = int(c.get("id").split(":")[1])
            if c.tag == "w":
                key = c.get(XID)[1:]
                m = re.match(r"\w+ (\d+):(\d+)!(\d+)", c.get("ref"))
                row = {"key": key, "book": book, "ch": int(m[1]), "v": int(m[2]), "word": int(m[3]),
                       "text": c.text or "", "after": c.get("after") or "", "node": parent, "clause": clause}
                for a in TOKEN_ATTRS:
                    row[a] = c.get(a)
                tokens.append(row)
                for kind in ("participantref", "subjref"):
                    for t in (c.get(kind) or "").split():
                        refs.append((key, kind, t))
                for part in (c.get("frame") or "").split():
                    role, _, ts = part.partition(":")
                    for t in ts.split(";"):
                        if t:
                            refs.append((key, role, t))
            elif c.tag in ("wg", "c"):
                counter[0] += 1
                nid = f"{book}{ch:03d}.{counter[0]}"
                nodes.append({"id": nid, "book": book, "ch": ch, "v": v, "parent": parent, "class": c.get("class") or c.tag,
                              "rule": c.get("rule"), "role": c.get("role"), "head": c.get("head"),
                              "clausetype": c.get("clausetype")})
                v = walk(c, nid, nid if c.get("class") == "cl" else clause, v)
            else:
                v = walk(c, parent, clause, v)
        return v
    walk(root, None, None, None)
    # first / last token of each node
    span = {}
    by_node = {n["id"]: n for n in nodes}
    for t in tokens:
        nid = t["node"]
        while nid:
            a, b = span.get(nid, (t["key"], t["key"]))
            span[nid] = (min(a, t["key"]), max(b, t["key"]))
            nid = by_node[nid]["parent"]
    for n in nodes:
        n["first"], n["last"] = span.get(n["id"], (None, None))
    return tokens, nodes, refs


def layouts(con, code, ch, by_v=None, which=None):
    """The layout rows of one chapter: each token's line in each clause layout on this machine (orig/heb-bhsa: BHSA,
    local only; orig/heb-bcv-query). by_v = {verse: [token dicts with key, text]}, read from the database if not given."""
    import bridge_align as BA
    from clause_lines import layout_rows, LAYOUTS
    book = code.upper()
    if by_v is None:
        by_v = {}
        for key, v, text in con.execute("select key, v, text from tokens where book=? and ch=? order by key", (book, ch)):
            by_v.setdefault(v, []).append({"key": key, "text": text})
    for lay in which or LAYOUTS:
        path = os.path.join(ROOT, LAYOUTS[lay], f"{code}{ch:03d}.txt")
        con.execute("delete from layout where layout=? and key in (select key from tokens where book=? and ch=?)", (lay, book, ch))
        if not os.path.exists(path):
            continue
        rows = layout_rows(path)
        first = {}
        for i, r in enumerate(rows):
            first.setdefault(r[0], i)
        for v, toks in by_v.items():
            if v not in first:
                continue
            if lay == "bhsa":
                seg, segrows = BA.bhsa_segments(code, ch, v, [t for t in toks if t["text"]])
                levels = [r[1] for r in segrows]
            else:
                seg, _ = BA.bcvq_segments(code, ch, v)
                levels = [r[1] for r in rows if r[0] == v]
            con.executemany("insert into layout values(?,?,?,?)",
                            [(k, lay, first[v] + j, levels[j] if j < len(levels) else None) for k, j in seg.items()])


OPEN = {  # what the published cache leaves out: UBS data (SDBH, Louw-Nida; permission given to MACULA only), BHSA
    "heb": {"null": ("sdbh", "lexdomain", "coredomain"), "layouts_kept": ()},
    "grc": {"null": ("domain", "ln"), "layouts_kept": ()},
}


def speakers():
    """speakers(speaker, divine, start, stop, word_start, word_end, start_partial, end_partial, block_speaker,
    speaker_basis, quote_type): one row per quotation, from shoresh (bcv-query). start/stop are verses in English
    numbering (bbcccvvv); word_start/word_end MACULA word ids without their 'o' / 'n' (so they compare with the token
    keys); *_partial: the span covers only part of that verse. Licence: CC BY 4.0 (Clear Bible) + MIT (Glyssen)."""
    from concurrent.futures import ThreadPoolExecutor
    import urllib.parse
    base = "https://shoresh.qombi.com"
    lst = json.load(urllib.request.urlopen(urllib.request.Request(f"{base}/speakers", headers=UA), timeout=300))["speakers"]

    import time

    def one(sp):
        url = f"{base}/speaker/{urllib.parse.quote(sp['speaker'], safe='')}"  # names may contain '/'
        for attempt in range(6):
            try:
                return sp, json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300))
            except Exception:
                time.sleep(2 ** attempt)
        return sp, None
    with ThreadPoolExecutor(3) as ex:
        got = list(ex.map(one, lst))
    failed = [sp["speaker"] for sp, d in got if d is None]
    # a group name with '/' (Zebah/Zalmunna) was unreachable as /speaker/<name> until bcv-query fixed the route
    # (2026-10-15); should it fail again, those are skipped and listed; any other failure stops the update
    slashed = [n for n in failed if "/" in n]
    if len(failed) > len(slashed):
        raise SystemExit(f"speakers: {len(failed)} of {len(lst)} could not be fetched (e.g. {failed[:3]}); nothing written")
    got = [(sp, d) for sp, d in got if d]
    con = sqlite3.connect(DB)
    con.execute("drop table if exists speakers")
    con.execute("""create table speakers(speaker text, divine int, start int, stop int, word_start text, word_end text,
                   start_partial int, end_partial int, block_speaker text, speaker_basis text, quote_type text)""")
    strip = lambda w: (w or "")[1:] if (w or "")[:1] in ("o", "n") else w
    rows = [(sp["speaker"], int(bool(sp.get("divine"))), r["start_bbcccvvv"], r["end_bbcccvvv"], strip(r.get("word_start")),
             strip(r.get("word_end")), int(bool(r.get("start_partial"))), int(bool(r.get("end_partial"))),
             r.get("block_speaker"), r.get("speaker_basis"), r.get("quote_type")) for sp, d in got for r in d.get("ranges", [])]
    con.executemany("insert into speakers values(?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.execute("create index if not exists speakers_range on speakers(start, stop)")
    src = (got[0][1] or {}).get("source", {}) if got else {}
    con.execute("insert or replace into meta values('speakers', ?)", (
        f"{src.get('attribution', 'MACULA Quotation and Speaker Data, © 2023 Clear Bible, Inc')} ({src.get('license', 'CC-BY-4.0')}); "
        "includes FCBH character data via SIL Glyssen (MIT), Copyright (c) 2014-2020 SIL LSDev and Faith Comes By Hearing; "
        f"via shoresh /speakers, {len(lst)} speakers, fetched {__import__('datetime').date.today()}"
        + (f"; not fetchable (a '/' in the name): {'; '.join(slashed)}" if slashed else ""),))
    con.commit()
    print(f"speakers: {len(lst) - len(slashed)} of {len(lst)} speakers, {len(rows)} quotations"
          + (f"; {len(slashed)} group names with '/' skipped" if slashed else ""))


def export_open(out):
    """The publishable cache (internal-docs plan, setup cache): heb-open.sqlite and grc-open.sqlite without the UBS
    columns and without any layout row, heb-bcv-query.sqlite with the bcv-query layout rows only (CC BY-SA, a file of
    its own), and manifest.json with sources, licences and SHA-256. BHSA rows never leave this machine."""
    import hashlib, shutil
    os.makedirs(out, exist_ok=True)
    files = {}
    for lang, src in (("heb", DB), ("grc", DB_GRC)):
        if not os.path.exists(src):
            continue
        dst = os.path.join(out, f"{lang}-open.sqlite")
        shutil.copy(src, dst)
        con = sqlite3.connect(dst)
        con.execute(f"update tokens set {', '.join(c + '=null' for c in OPEN[lang]['null'])}")
        # speakers stay (CC BY 4.0 + MIT, credited in meta 'speakers')
        if lang == "heb":
            lay = os.path.join(out, "heb-bcv-query.sqlite")
            if os.path.exists(lay):
                os.remove(lay)
            con.execute("attach database ? as o", (lay,))
            con.execute("create table o.layout as select * from layout where layout='bcv-query'")
            con.execute("create table o.meta(name text primary key, value text)")
            con.execute("insert into o.meta values('licence', 'CC BY-SA 4.0: bcv-commons/hebrew-clause-layout v0.22 "
                        "(MACULA Hebrew, UHB); keys are MACULA Hebrew word ids')")
            con.commit()
            con.execute("detach database o")
            files["heb-bcv-query.sqlite"] = lay
            con.execute("delete from layout")
        if lang == "grc":
            con.execute("delete from map")  # ours, built locally from orig/grc and orig/grc-rp (bcv-query has neither)
        assert not con.execute("select count(*) from layout").fetchone()[0] if lang == "heb" else True
        con.execute("insert or replace into meta values('licence', ?)", (
            "CC BY 4.0: MACULA " + ("Hebrew" if lang == "heb" else "Greek") + " Linguistic Datasets, "
            "https://github.com/Clear-Bible/macula-" + ("hebrew" if lang == "heb" else "greek") + "/ (Biblica); with "
            "CC0 data: compact-alignments _index, BSB Translation Tables" + (", the BGB/RP -> MACULA mapping" if lang == "grc" else "")
            + ". UBS data (SDBH / Louw-Nida) left out; the setup adds the layout rows locally.",))
        con.commit()
        con.execute("vacuum")
        con.close()
        files[f"{lang}-open.sqlite"] = dst
    man = {"built_from": {"macula_hebrew": MACULA_HEB, "macula_greek": MACULA_GRC},
           "files": {k: {"sha256": hashlib.sha256(open(p, "rb").read()).hexdigest(), "bytes": os.path.getsize(p)}
                     for k, p in files.items()},
           "left_out": "SDBH and Louw-Nida columns (UBS; added locally if wanted), all BHSA data"}
    json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    for k, v in man["files"].items():
        print(f"{k}: {v['bytes'] / 1e6:.1f} MB  {v['sha256'][:16]}…")


def build(codes):
    import full_align as FULL, bridge_align as BA
    from clause_lines import layout_rows, LAYOUTS
    names = lowfat_names()
    from concurrent.futures import ThreadPoolExecutor
    todo = [(c.upper(), ch) for c in codes if c.upper() in names for ch in range(1, heb_chapters(c) + 1)]
    with ThreadPoolExecutor(8) as ex:  # the downloads, in parallel, once
        list(ex.map(lambda bc: get(f"{RAW}/{names[bc[0]]}-{bc[1]:03d}-lowfat.xml",
                                   os.path.join(CACHE, f"{names[bc[0]]}-{bc[1]:03d}-lowfat.xml")), todo))
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    for code in codes:
        book = code.upper()
        if book not in names:
            print(f"{code}: not in MACULA's listing")
            continue
        T = BA.tables(book)
        for ch in range(1, heb_chapters(code) + 1):
            tokens, nodes, refs = chapter_rows(book, ch, lowfat(book, ch, names))
            for t in ("tokens", "nodes"):
                con.execute(f"delete from {t} where book=? and ch=?", (book, ch))
            keys = [t["key"] for t in tokens]
            con.executemany("delete from refs where key=?", [(k,) for k in keys])
            con.executemany("delete from bsb where key=?", [(k,) for k in keys])
            con.executemany("delete from layout where key=?", [(k,) for k in keys])
            by_v = {}
            for t in tokens:
                by_v.setdefault(t["v"], []).append(t)
            for v, toks in by_v.items():
                ref = f"{book} {ch}:{v}"
                num = {parts[0]: (n, c, o) for n, c, o, parts in FULL.numbering(book, ref)}
                fused = {p: parts[0] for _, _, _, parts in FULL.numbering(book, ref) for p in parts[1:]}
                for t in toks:
                    n, c, o = num.get(fused.get(t["key"], t["key"]), (None, None, None))
                    t.update(n=n, kind=c, ord=o)
                tv = T.get(ref, {})
                con.executemany("insert or replace into bsb values(?,?)",
                                [(k, " ".join(map(str, p))) for k, p in tv.items() if k in {t["key"] for t in toks}])
            cols = ["key", "book", "ch", "v", "word", "n", "kind", "ord", "text", "after"] + list(TOKEN_ATTRS) + ["node", "clause"]
            con.executemany(f"insert into tokens values({','.join('?' * 35)})",
                            [(t["key"], t["book"], t["ch"], t["v"], t["word"], t["n"], t["kind"], t["ord"], t["text"],
                              t["after"], t["lemma"], t["strongnumberx"], t["stronglemma"], t["class"], t["pos"],
                              t["morph"], t["type"], t["stem"], t["person"], t["gender"], t["number"], t["state"],
                              t["role"], t["gloss"], t["english"], t["transliteration"], t["greek"], t["greekstrong"],
                              t["sdbh"], t["lexdomain"], t["coredomain"], t["sensenumber"], t["lang"], t["node"],
                              t["clause"]) for t in tokens])
            con.executemany("insert into nodes values(?,?,?,?,?,?,?,?,?,?,?,?)",
                            [(n["id"], n["book"], n["ch"], n["v"], n["parent"], n["class"], n["rule"], n["role"],
                              n["head"], n["clausetype"], n["first"], n["last"]) for n in nodes])
            con.executemany("insert into refs values(?,?,?)", refs)
            layouts(con, code, ch)  # from the database: tokens in text (key) order, not the tree's document order
            con.commit()
        print(f"{code}: {heb_chapters(code)} chapters", flush=True)
    con.execute("delete from lxx")
    con.execute("""insert into lxx select lexeme, greekstrong, greek, count(*) from tokens
                   where greekstrong is not null group by lexeme, greekstrong""")
    con.executemany("insert or replace into meta values(?,?)", [("macula_hebrew", MACULA_HEB)])
    con.commit()
    return con


SCHEMA_GRC = """
create table if not exists tokens(key text primary key, book text, ch int, v int, word int, n int, kind text, ord int,
  text text, after text, lemma text, normalized text, strong text, class text, type text, morph text, gcase text,
  number text, gender text, tense text, voice text, mood text, person text, degree text, role text, gloss text,
  domain text, ln text, discontinuous text, node text, clause text);
create index if not exists tokens_ref on tokens(book, ch, v);
create index if not exists tokens_strong on tokens(strong);
create table if not exists nodes(id text primary key, book text, ch int, v int, parent text, class text, rule text,
  role text, head text, clausetype text, first text, last text);
create table if not exists refs(key text, kind text, target text);
create index if not exists refs_key on refs(key);
create table if not exists bsb(key text primary key, positions text);
create table if not exists map(edition text, book text, ch int, v int, pos int, key text, how text);
create index if not exists map_ref on map(edition, book, ch, v);
create index if not exists map_key on map(key);
create table if not exists meta(name text primary key, value text);
"""


def fold(s):
    import unicodedata
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c)).replace("ς", "σ")


def fold2(s):
    """spelling variants too: doubled letters (Ἰωάνης / Ἰωάννης), ει / ι, a final ν."""
    s = re.sub(r"(.)\1", r"\1", fold(s)).replace("ει", "ι")
    return s[:-1] if s.endswith("ν") else s


def map_verse(nestle, edition):
    """[(edition position, nestle index, how)] for one verse: equal runs, then spelling variants inside the changed
    blocks, then the same word moved within the verse; the rest are variants (no row)."""
    import difflib
    a, b = [fold(x) for x in nestle], [fold(x) for x in edition]
    out, used_a, used_b = [], set(), set()
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            out += [(j1 + k, i1 + k, "same") for k in range(i2 - i1)]
            used_a |= set(range(i1, i2)); used_b |= set(range(j1, j2))
        else:
            for j in range(j1, j2):
                i = next((i for i in range(i1, i2) if i not in used_a and fold2(nestle[i]) == fold2(edition[j])), None)
                if i is not None:
                    out.append((j, i, "spelling")); used_a.add(i); used_b.add(j)
    for j in range(len(b)):
        if j in used_b:
            continue
        cands = [i for i in range(len(a)) if i not in used_a and fold2(nestle[i]) == fold2(edition[j])]
        if cands:
            i = min(cands, key=lambda i: abs(i / max(len(a), 1) - j / max(len(b), 1)))
            out.append((j, i, "moved")); used_a.add(i); used_b.add(j)
    return sorted(out)


def grc_rows(book, root):
    tokens, nodes, refs = [], [], []
    counter = [0]

    def walk(e, parent, clause):
        for c in e:
            if c.tag == "w":
                key = c.get(XID)[1:]
                m = re.match(r"\w+ (\d+):(\d+)!(\d+)", c.get("ref"))
                row = {"key": key, "book": book, "ch": int(m[1]), "v": int(m[2]), "word": int(m[3]),
                       "text": c.text or "", "after": c.get("after") or "", "node": parent, "clause": clause}
                for a in GRC_ATTRS:
                    row[a] = c.get(a)
                tokens.append(row)
                for kind in ("referent", "subjref"):
                    for t in (c.get(kind) or "").split():
                        refs.append((key, kind, t.lstrip("n")))
                for part in (c.get("frame") or "").split():
                    role, _, ts = part.partition(":")
                    for t in ts.split(";"):
                        if t:
                            refs.append((key, role, t.lstrip("n")))
            elif c.tag == "wg":
                counter[0] += 1
                nid = f"{book}.{counter[0]}"
                nodes.append({"id": nid, "book": book, "parent": parent, "class": c.get("class"), "rule": c.get("rule"),
                              "role": c.get("role"), "head": c.get("head"), "clausetype": c.get("clauseType")})
                walk(c, nid, nid if c.get("class") == "cl" else clause)
            else:
                walk(c, parent, clause)
    walk(root, None, None)
    by_node, span = {n["id"]: n for n in nodes}, {}
    for t in tokens:
        nid = t["node"]
        while nid:
            a, b = span.get(nid, (t, t))
            span[nid] = (a if a["key"] <= t["key"] else t, b if b["key"] >= t["key"] else t)
            nid = by_node[nid]["parent"]
    for n in nodes:
        a, b = span.get(n["id"], (None, None))
        n.update(first=a and a["key"], last=b and b["key"], ch=a and a["ch"], v=a and a["v"])
    return tokens, nodes, refs


def map_editions(con, codes=None):
    """The mapping from our Greek texts (orig/grc: BGB; orig/grc-rp: RP) to MACULA's keys, from the Greek tokens in the
    database (also after the structure came from the published cache, whose `map` is empty: it is ours, built here)."""
    codes = codes or [c for c in BY_CODE if BY_CODE[c][2] == "nt"]
    for code in codes:
        book = code.upper()
        con.execute("delete from map where book=?", (book,))
        by_v = {}
        for key, ch, v, text in con.execute("select key, ch, v, text from tokens where book=? order by key", (book,)):
            by_v.setdefault((ch, v), []).append({"key": key, "text": text})
        for ed, d in (("bgb", "orig/grc"), ("rp", "orig/grc-rp")):
            for ch in sorted({c for c, _ in by_v}):
                path = os.path.join(ROOT, d, f"{code}{ch:03d}.txt")
                if not os.path.exists(path):
                    continue
                for l in open(path, encoding="utf-8").read().splitlines()[1:]:
                    m = re.match(r"(\d+):(\d+)\s+(.*)", l)
                    if not m:
                        continue
                    c, v = int(m[1]), int(m[2])
                    ed_toks = re.findall(r"[^\W\d_]+", m[3])
                    nest = by_v.get((c, v), [])
                    con.executemany("insert into map values(?,?,?,?,?,?,?)",
                                    [(ed, book, c, v, j, nest[i]["key"], how)
                                     for j, i, how in map_verse([t["text"] for t in nest], ed_toks)])
    con.commit()


def build_grc(codes):
    import full_align as FULL, bridge_align as BA
    from concurrent.futures import ThreadPoolExecutor
    nt = [c for c in BY_CODE if BY_CODE[c][2] == "nt"]
    files = {c: f"{i + 1:02d}-{GRC_FILES[i]}.xml" for i, c in enumerate(nt)}
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda c: get(f"{RAW_GRC}/{files[c]}", os.path.join(CACHE_GRC, files[c]), timeout=900), codes))
    con = sqlite3.connect(DB_GRC)
    con.executescript(SCHEMA_GRC)
    for code in codes:
        book = code.upper()
        tokens, nodes, refs = grc_rows(book, ET.parse(os.path.join(CACHE_GRC, files[code])).getroot())
        for t in ("tokens", "nodes", "map"):
            con.execute(f"delete from {t} where book=?", (book,))
        keys = [t["key"] for t in tokens]
        con.executemany("delete from refs where key=?", [(k,) for k in keys])
        con.executemany("delete from bsb where key=?", [(k,) for k in keys])
        by_v = {}
        for t in tokens:
            by_v.setdefault((t["ch"], t["v"]), []).append(t)
        T = BA.tables(book)
        for (ch, v), toks in by_v.items():
            ref = f"{book} {ch}:{v}"
            num = {parts[0]: (n, c, o) for n, c, o, parts in FULL.numbering(book, ref)}
            fused = {p: parts[0] for _, _, _, parts in FULL.numbering(book, ref) for p in parts[1:]}
            for t in toks:
                t["n"], t["kind"], t["ord"] = num.get(fused.get(t["key"], t["key"]), (None, None, None))
            con.executemany("insert or replace into bsb values(?,?)",
                            [(k, " ".join(map(str, p))) for k, p in T.get(ref, {}).items()])
        con.executemany(f"insert into tokens values({','.join('?' * 31)})",
                        [tuple(t[k] for k in ("key", "book", "ch", "v", "word", "n", "kind", "ord", "text", "after"))
                         + tuple(t[a] for a in GRC_ATTRS) + (t["node"], t["clause"]) for t in tokens])
        con.executemany("insert into nodes values(?,?,?,?,?,?,?,?,?,?,?,?)",
                        [(n["id"], n["book"], n["ch"], n["v"], n["parent"], n["class"], n["rule"], n["role"],
                          n["head"], n["clausetype"], n["first"], n["last"]) for n in nodes])
        con.executemany("insert into refs values(?,?,?)", refs)
        con.commit()
        map_editions(con, [code])
        print(f"{code}: {len(tokens)} tokens", flush=True)
    con.execute("insert or replace into meta values(?,?)", ("macula_greek", MACULA_GRC))
    con.commit()


def show(code, cv):
    con = sqlite3.connect(DB)
    ch, v = map(int, cv.split(":"))
    rows = con.execute("select key, n, kind, ord, text, gloss, english, morph, class, role, greek, sdbh, clause, translit "
                       "from tokens where book=? and ch=? and v=? order by key", (code.upper(), ch, v)).fetchall()
    who = lambda k: (con.execute("select text, gloss from tokens where key=?", (k,)).fetchone() or ("?", k))
    clause = None
    for key, n, kind, o, text, gloss, eng, morph, cls, role, greek, sdbh, cl, tr in rows:
        if cl != clause:
            c = con.execute("select rule, role from nodes where id=?", (cl,)).fetchone()
            lay = con.execute("select layout, line, level from layout where key=?", (key,)).fetchall()
            print(f"  clause {cl} {c[0] if c else ''}  " + " ".join(f"{l}:L{ln}/{lv}" for l, ln, lv in lay))
            clause = cl
        r = con.execute("select kind, target from refs where key=?", (key,)).fetchall()
        b = con.execute("select positions from bsb where key=?", (key,)).fetchone()
        print(f"    {'' if n is None else n:>2} {(kind or '') + str('' if o is None else o):<4} {text or '·':<10} {gloss or ''}"
              f"{' / ' + eng if eng and eng != gloss else ''} [{cls} {morph}{' ' + role if role else ''}]"
              f"{' LXX ' + greek if greek else ''}{' bsb ' + b[0] if b else ''}"
              + "".join(f" {k}→{who(t)[0]}({who(t)[1]})" for k, t in r))


def bridge(lex):
    con = sqlite3.connect(DB)
    lex = lex.lstrip("Hh")
    rows = con.execute("select greekstrong, greek, n from lxx where lexeme=? order by n desc", (lex,)).fetchall()
    tot = sum(r[2] for r in rows)
    occ = con.execute("select count(*) from tokens where lexeme=?", (lex,)).fetchone()[0]
    print(f"H{lex}: {occ} occurrences, {tot} with an LXX equivalent")
    for g, w, n in rows[:15]:
        print(f"  G{g} {w} ×{n}")


def stats():
    con = sqlite3.connect(DB)
    for t in ("tokens", "nodes", "refs", "bsb", "layout", "lxx"):
        print(t, con.execute(f"select count(*) from {t}").fetchone()[0])
    print("books", con.execute("select count(distinct book) from tokens").fetchone()[0],
          "chapters", con.execute("select count(distinct book||ch) from tokens").fetchone()[0])
    print("meta", con.execute("select * from meta").fetchall())


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    if a[0] == "build":
        codes = a[1:] or [c for c in BY_CODE if BY_CODE[c][2] == "ot"]
        ot, nt = [c for c in codes if BY_CODE[c][2] == "ot"], [c for c in codes if BY_CODE[c][2] == "nt"]
        if ot:
            build(ot)
        if nt:
            build_grc(nt)
    elif a[0] == "layouts":
        con = sqlite3.connect(DB)
        which = [a[a.index("--layout") + 1]] if "--layout" in a else None
        codes = [x for x in a[1:] if not x.startswith("--") and x not in (which or [])]
        for c in codes or [c for c in BY_CODE if BY_CODE[c][2] == "ot"]:
            for ch in range(1, heb_chapters(c) + 1):
                layouts(con, c, ch, which=which)
            con.commit()
            print(f"{c}: layouts", flush=True)
    elif a[0] == "map":
        map_editions(sqlite3.connect(DB_GRC), a[1:] or None)
        print("orig/grc.sqlite: map (BGB, RP -> MACULA keys) rebuilt")
    elif a[0] == "speakers":
        speakers()
    elif a[0] == "export-open":
        export_open(os.path.abspath(a[1]))
    elif a[0] == "show":
        show(a[1], a[2])
    elif a[0] == "bridge":
        bridge(a[1])
    elif a[0] == "stats":
        stats()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
