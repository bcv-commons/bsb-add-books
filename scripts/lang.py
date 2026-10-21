#!/usr/bin/env python3
"""The project's target-language database: export/<project>/_learn/lang.sqlite,
local and git-ignored, built from the imported NT, its alignment to the Greek and the source structures in orig/.

v1 holds the occurrence index: every NT token of the style corpus, and its links to MACULA Greek tokens, from
align.py's links_grc_pos.tsv (eflomal, target <-> the Greek of the project's nt_basis) and the BGB/RP -> MACULA
mapping in orig/grc.sqlite (scripts/src.py). With orig/heb.sqlite's LXX equivalents this answers "how does the NT
say this Hebrew word?": Hebrew lexeme -> Greek lemmas (the LXX bridge) -> their NT tokens -> the target words,
with counts, and the verses.

Tables:
  nt_tokens(book, ch, v, pos, surface, form)        form = lowercased token
  nt_links(book, ch, v, pos, key, src)              target token -> MACULA Greek key; src = eflomal

    python3 scripts/lang.py build <project> [--links FILE]
    python3 scripts/lang.py hbo <project> <lexeme> [--verses N]   via the LXX bridge (e.g. 2617 or H2617)
    python3 scripts/lang.py grc <project> <strong> [--verses N]   a Greek lemma by Strong's number (e.g. 1656)
    python3 scripts/lang.py derive <project>                     the derived products: d_* tables
    python3 scripts/lang.py report <project>                     their summary
    python3 scripts/lang.py stats <project>
    python3 scripts/lang.py layers <project> [--write]          the alignment layers of bcv-commons built on exactly
        our text of the style edition (compact-alignments, full-alignments-llm, full-alignments-manual; matched by the
        file names' text fingerprint), best first; --write sets the best as `lexeme_aligner` in project.yaml where it
        has none, so that build adds its links
The listings show the edition's words for the agents' and the team's own use; what goes into the store or the wiki
keeps to the quotation limits (docs/licensing.md).
"""
import collections, os, re, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import langtools as LT  # noqa: E402
from books import BY_CODE  # noqa: E402

HEB, GRC = os.path.join(ROOT, "orig", "heb.sqlite"), os.path.join(ROOT, "orig", "grc.sqlite")
EDITION = {"critical": "bgb", "majority": "rp", "tr": "rp"}
SCHEMA = """
create table if not exists nt_tokens(book text, ch int, v int, pos int, surface text, form text, raw text);
create index if not exists nt_tokens_ref on nt_tokens(book, ch, v);
create index if not exists nt_tokens_form on nt_tokens(form);
create table if not exists nt_links(book text, ch int, v int, pos int, key text, src text);
create index if not exists nt_links_key on nt_links(key);
create index if not exists nt_links_ref on nt_links(book, ch, v, pos);
create table if not exists meta(name text primary key, value text);
"""


def db_path(P):
    return os.path.join(P.learn, "lang.sqlite")


def build(pname, links=None):
    P = LT.Project(pname)
    links = links or os.path.join(P.learn, "links_grc_pos.tsv")
    if not os.path.exists(links):
        raise SystemExit(f"no {links}: run python3 scripts/align.py {pname} --sides grc")
    ed = EDITION[P.p["nt_basis"]]
    con = sqlite3.connect(db_path(P))
    con.executescript(SCHEMA)
    con.execute("delete from nt_tokens")
    con.execute("delete from nt_links")
    con.execute("attach database ? as g", (GRC,))
    toks = {}
    # the same tokens with every mark kept (the project's tokenizer drops the ignored tone marks): `raw`, for the marks test
    import unicodedata
    raw_rx = re.compile(rf"[\w{re.escape(P.tok.extra)}{LT.WORD_MARKS}]+")
    mismatch = 0
    for ref, code, key, _, text in P.corpus():
        if BY_CODE[code][2] != "nt":
            continue
        t = P.tok.tokens(text)
        toks[ref] = t
        raw = []
        for w in raw_rx.findall(unicodedata.normalize("NFD", text.lower())):
            parts = ([w] if not (P.tok.split and "-" in w) else w.split("-"))
            raw += [x for x in parts if x and not x.isdigit()]
        raw = [unicodedata.normalize("NFC", x) for x in raw]
        if len(raw) != len(t):
            mismatch += 1
            raw = [None] * len(t)
        con.executemany("insert into nt_tokens values(?,?,?,?,?,?,?)",
                        [(code.upper(), key[0], key[1], i, w, w.lower(), raw[i]) for i, w in enumerate(t)])
    gmap = {}
    for book, ch, v, pos, key in con.execute("select book, ch, v, pos, key from g.map where edition=?", (ed,)):
        gmap[(book, ch, v, pos)] = key
    rows, miss = [], 0
    for l in open(links, encoding="utf-8"):
        if l.startswith(("#", "ref\t")):
            continue
        ref, tpos, spos = l.rstrip("\n").split("\t")
        m = re.match(r"(\w+) (\d+):(\d+)", ref)
        k = gmap.get((m[1], int(m[2]), int(m[3]), int(spos)))
        if k is None:
            miss += 1
            continue
        rows.append((m[1], int(m[2]), int(m[3]), int(tpos), k, "eflomal"))
    con.executemany("insert into nt_links values(?,?,?,?,?,?)", rows)
    if P.p.get("lexeme_aligner"):
        have = {r[:5] for r in rows}                    # a link both alignments found counts once
        la = [r for r in lexeme_aligner_links(con, P, P.p["lexeme_aligner"]) if r[:5] not in have]
        con.executemany("insert into nt_links values(?,?,?,?,?,?)", la)
        print(f"  + {len(la)} links from lexeme-aligner's layer {P.p['lexeme_aligner']} (compact-alignments, CC0)")
    con.executemany("insert or replace into meta values(?,?)", [("nt_basis", P.p["nt_basis"]), ("links", os.path.relpath(links, ROOT)),
                                                               ("raw_mismatch_verses", str(mismatch))])
    con.commit()
    n = con.execute("select count(*) from nt_tokens").fetchone()[0]
    linked = con.execute("select count(*) from (select distinct book, ch, v, pos from nt_links)").fetchone()[0]
    print(f"{pname}: {n} NT tokens, {linked} linked to a MACULA Greek token ({100 * linked / max(n, 1):.0f}%); "
          f"{len(rows)} links, {miss} on Greek tokens without a MACULA key (variants)")


CA = "https://huggingface.co/datasets/bcv-commons/compact-alignments"
HF = "https://huggingface.co/datasets/bcv-commons"
# the alignment datasets of bcv-commons, in one format (compact-alignments' paths, _index and tokenizer): a layer id
# with +manual+ is hand-made, with +llm+ checked by a language model, else lexeme-aligner's statistical layer
DATASETS = ("full-alignments-manual", "full-alignments-llm", "compact-alignments")


def dataset_of(layer):
    return ("full-alignments-manual" if "+manual+" in layer else "full-alignments-llm" if "+llm+" in layer
            else "compact-alignments")


def hf_tree(ds, path, cache, max_age=24 * 3600):
    """the entries of a folder of a bcv-commons dataset ([] where it has none), cached for a day: names change with the text"""
    from fetch_edition import getjson
    try:
        x = getjson(f"https://huggingface.co/api/datasets/bcv-commons/{ds}/tree/main/{path}", cache, False, max_age)
    except Exception:                              # a folder the dataset doesn't have answers 404
        return []
    return x if isinstance(x, list) else []


def layer_names(ds, iso, layer):
    """{book: {hash in the file name: path in the dataset}} of a layer's main files"""
    d = os.path.join(ROOT, "download", ds, iso[0], iso, layer)
    os.makedirs(d, exist_ok=True)
    names = collections.defaultdict(dict)
    for x in hf_tree(ds, f"{iso[0]}/{iso}/{layer}", os.path.join(d, "_listing.json")):
        name = os.path.basename(x["path"])
        if name.endswith(".json") and not name.endswith(".meta.json") and "_" in name and not name.startswith("_"):
            names[name.split("_")[0]][name[:-5].split("_", 1)[1]] = x["path"]
    return names


def iso3(P):
    """the language's ISO 639-3 code, the datasets' folder: the style edition's (its language, or the folder it is
    filed in, import/<licence>/<iso>/), else the project's"""
    for e in P.editions:
        for c in (e.get("language") or "", os.path.basename(os.path.dirname(os.path.normpath(e.get("dir") or "")))):
            if re.fullmatch(r"[a-z]{3}", c):
                return c
    return P.p.get("language") or ""


def local_verses(P):
    """{BOOK: [(ch, v, text)]} of the style corpus in the edition's own numbering"""
    out = collections.defaultdict(list)
    for ref, code, key, _, t in P.corpus():
        out[code.upper()].append((key[0], key[1], t))
    return out


def matching(names, verses):
    """the layer file of exactly this text: its text fingerprint (8 hex) in the name, or until 2026-12-20 the old name
    (the last 5 hex of the raw-text hash); None: the text differs from the one the layer was made on"""
    import full_align as FA
    return names.get(FA.text_fingerprint(verses)[0][:8]) or names.get(FA.book_hash(verses)[-5:])


def find_layers(P):
    """[(dataset, layer, NT books matched, NT books of the layer, OT books matched)] of the alignment layers of the
    project's language built on exactly our text of the style edition (by the text fingerprint), best first: most NT
    books, then hand-made before model-checked before statistical"""
    iso = iso3(P)
    ours = local_verses(P)
    out = []
    for rank, ds in enumerate(DATASETS):
        cache = os.path.join(ROOT, "download", ds, iso[:1], iso, "_listing.json")
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        for x in hf_tree(ds, f"{iso[:1]}/{iso}", cache):
            if x.get("type") != "directory":
                continue
            layer = os.path.basename(x["path"])
            names = layer_names(ds, iso, layer)
            nt = [b for b in names if BY_CODE.get(b.lower(), (0, 0, ""))[2] == "nt"]
            m_nt = sum(1 for b in nt if b in ours and matching(names[b], ours[b]))
            m_ot = sum(1 for b in names if b not in nt and b in ours and matching(names[b], ours[b]))
            out.append((ds, layer, m_nt, len(nt), m_ot, rank))
    out.sort(key=lambda r: (-r[2], r[5]))
    return [r[:5] for r in out]


def lexeme_aligner_links(con, P, layer):
    """A second NT alignment: a bcv-commons layer for this language (compact-alignments, or full-alignments-llm /
    -manual for a layer id with +llm+ / +manual+; CC0: token positions only) decoded onto our NT tokens ->
    [(book, ch, v, pos, MACULA key, 'lexeme-aligner')]. Their positions count the words of the layer's source text
    (its tokenizer: runs of letters and marks) in that text's verses. A book whose text is ours exactly (the file name's
    text fingerprint, find_layers) is read on our text; else, for a compact layer from helloAO, on helloAO's text,
    words matched verse by verse onto our copy (it may be newer) and a word our copy lacks left out."""
    import difflib, json, unicodedata, urllib.request
    import full_align as FA
    from fetch_edition import getjson, HELLOAO, DL
    iso = iso3(P) or layer.split("_")[0]
    ds = dataset_of(layer)
    d = os.path.join(ROOT, "download", ds, iso[0], iso, layer)
    names = layer_names(ds, iso, layer)
    if not names:
        raise SystemExit(f"lexeme_aligner: no layer {layer} for {iso} in {ds} (lang.py layers {P.name} lists them)")
    src = {}
    if ds == "compact-alignments":
        man = getjson(f"{CA}/resolve/main/manifest.json", os.path.join(ROOT, "download", "compact-alignments", "manifest.json"),
                      False, 7 * 24 * 3600)
        src = (man["languages"].get(iso, {}).get("editions", {}).get(layer) or {}).get("source", {})
    files = {}

    def fetch(path):
        f = os.path.join(d, os.path.basename(path))
        for attempt in range(4):                         # Hugging Face resets connections now and then
            if os.path.exists(f):
                break
            try:
                req = urllib.request.Request(f"{HF}/{ds}/resolve/main/{path}", headers={"User-Agent": "bsb-add-books"})
                body = urllib.request.urlopen(req, timeout=120).read()
                open(f + ".part", "wb").write(body)
                os.replace(f + ".part", f)
            except OSError:
                if attempt == 3:
                    raise
                import time
                time.sleep(5 * (attempt + 1))
        return f
    mine = local_verses(P)
    data = {"books": []}
    if src.get("provider") == "bible.helloao.org" and not all(matching(names[b], mine[b]) for b in names if b in mine):
        data = getjson(f"{HELLOAO}/{src['edition']}/complete.json", os.path.join(DL, src["edition"], "complete.json"), False)
    fold = lambda s: "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))
    ours = collections.defaultdict(list)
    for b, c, v, pos, surf in con.execute("select book, ch, v, pos, surface from nt_tokens order by book, ch, v, pos"):
        for sub in FA.tokenize(surf) or [surf]:        # their tokenizer splits at hyphens and other marks; ours may not
            ours[(b, c, v)].append((pos, fold(sub)))
    out = []
    theirs = {}
    for book in data["books"]:
        verses = []
        for ch in book["chapters"]:
            c = ch["chapter"]
            for blk in c["content"]:
                if blk.get("type") == "verse":
                    parts = [x if isinstance(x, str) else x["text"] for x in blk["content"] if isinstance(x, str) or "text" in x]
                    verses.append((c["number"], blk["number"], re.sub(r"\s+", " ", " ".join(parts)).strip()))
        theirs[book["id"]] = sorted(verses)
    for b in sorted(names):
        if BY_CODE.get(b.lower(), (None, None, None))[2] != "nt":
            continue
        # the file for exactly this text: our copy, else the provider's; neither: the text changed since the layer
        # was made
        verses = mine.get(b) if b in mine and matching(names[b], mine[b]) else theirs.get(b)
        path = matching(names[b], verses) if verses else None
        if not path:
            if b in mine:
                print(f"  lexeme_aligner: {b}: no layer file for this text (fingerprint "
                      f"{FA.text_fingerprint(mine[b])[0][:8]}); the text changed since the layer was made; skipped")
            continue
        files[b] = fetch(path)
        keys = FA.index(b, "keys")
        # row i of the layer is the i-th verse of the index (_index/<BOOK>_lexemes.json), not of the source text: a
        # verse the source lacks (or adds) would otherwise shift every later row onto the wrong verse
        text = {(c, v): t for c, v, t in verses}
        for ref, s in zip(FA.index(b, "lexemes"), json.load(open(files[b], encoding="utf-8"))):
            c, v = (int(x) for x in ref.split(" ")[1].split(":"))
            mine, t = ours.get((b, c, v), []), text.get((c, v))
            if not s or not mine or t is None:
                continue
            sm = difflib.SequenceMatcher(None, [fold(x) for x in FA.tokenize(t)], [m[1] for m in mine], autojunk=False)
            pmap = {}
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == "equal":
                    pmap.update({i1 + k: mine[j1 + k][0] for k in range(i2 - i1)})
            ks = keys.get(f"{b} {c}:{v}", [])
            for o, ids in FA.parse(s.split("|")[0]).items():
                if o < len(ks) and ks[o]:
                    out += [(b, c, v, pmap[i], key, "lexeme-aligner") for i in ids if i in pmap for key in ks[o].split("+")]
    return list(dict.fromkeys(out))


def connect(pname):
    P = LT.Project(pname)
    con = sqlite3.connect(db_path(P))
    con.execute("attach database ? as g", (GRC,))
    con.execute("attach database ? as h", (HEB,))
    return P, con


def renderings(con, strongs):
    """{strong: Counter(target form)} and example refs, for Greek Strong's numbers."""
    out, ex = {}, collections.defaultdict(list)
    for s in strongs:
        c = collections.Counter()
        for book, ch, v, pos, form in con.execute(
                """select l.book, l.ch, l.v, l.pos, t.form from g.tokens gt
                   join nt_links l on l.key = gt.key
                   join nt_tokens t on t.book = l.book and t.ch = l.ch and t.v = l.v and t.pos = l.pos
                   where gt.strong = ?""", (s,)):
            c[form] += 1
            ex[(s, form)].append((book, ch, v, pos))
        out[s] = c
    return out, ex


def show_verses(con, P, refs, n):
    texts = {}
    for book, ch, v, pos in refs[:n]:
        if (book, ch, v) not in texts:
            texts[(book, ch, v)] = [w for (w,) in con.execute(
                "select surface from nt_tokens where book=? and ch=? and v=? order by pos", (book, ch, v))]
        w = list(texts[(book, ch, v)])
        if pos < len(w):
            w[pos] = f"[{w[pos]}]"
        lo = max(0, pos - 8)
        print(f"      {book} {ch}:{v}  {'… ' if lo else ''}{' '.join(w[lo:pos + 9])}{' …' if pos + 9 < len(w) else ''}")


def grc(pname, strong, nverses=2):
    P, con = connect(pname)
    lemma = con.execute("select lemma, gloss, count(*) from g.tokens where strong=? group by lemma", (strong,)).fetchone()
    occ = lemma[2] if lemma else 0
    r, ex = renderings(con, [strong])
    print(f"G{strong} {lemma[0] if lemma else '?'} ({lemma[1] if lemma else ''}): {occ} NT tokens")
    tot = sum(r[strong].values())
    for form, c in r[strong].most_common(8):
        print(f"  {form} ×{c} ({100 * c / max(tot, 1):.0f}%)")
        show_verses(con, P, ex[(strong, form)], nverses)


def hbo(pname, lex, nverses=1):
    P, con = connect(pname)
    lex = lex.lstrip("Hh")
    occ = con.execute("select count(*), max(lemma), max(gloss) from h.tokens where lexeme=?", (lex,)).fetchone()
    bridge = con.execute("select greekstrong, greek, n from h.lxx where lexeme=? order by n desc", (lex,)).fetchall()
    with_eq = sum(b[2] for b in bridge)
    print(f"H{lex} {occ[1] or ''} ({occ[2] or ''}): {occ[0]} OT tokens, {with_eq} with an LXX equivalent")
    agg = collections.defaultdict(int)
    for g, w, n in bridge:
        agg[g] += n
    for g, n in sorted(agg.items(), key=lambda x: -x[1])[:5]:
        lemma = con.execute("select lemma, count(*) from g.tokens where strong=? group by lemma", (g,)).fetchone()
        r, ex = renderings(con, [g])
        tot = sum(r[g].values())
        print(f"  LXX G{g} {lemma[0] if lemma else '?'} ×{n} ({100 * n / max(with_eq, 1):.0f}% of the bridge); "
              f"in the NT {lemma[1] if lemma else 0} tokens, {tot} linked")
        for form, c in r[g].most_common(4):
            print(f"    {form} ×{c} ({100 * c / max(tot, 1):.0f}%)")
            show_verses(con, P, ex[(g, form)], nverses)


# --- derived products -------------------------------------------------------

DERIVED = """
create table if not exists d_renderings(strong text, lemma text, context text, form text, n int, share real);
create table if not exists d_function(class text, lemma text, form text, n int, share real, dropped real);
create table if not exists d_affix(affix text, feature text, value text, n int, rate real, lift real);
create table if not exists d_order(pattern text, n int, greek_pattern text);
create table if not exists d_names(lemma text, form text, n int);
create table if not exists d_letters(greek text, target text, n int);
create table if not exists d_formulas(lemmas text, n int, form text, k int);
create table if not exists d_discourse(lemma text, form text, n int, share real, dropped real);
create table if not exists d_gaps(lexeme text, lemma text, gloss text, ot_n int, nt_linked int);
"""
FUNCTION = ("det", "conj", "prep", "ptcl", "pron")
ONE_WORD = 0.4  # an affix candidate is dropped when one word makes up this share of its occurrences,
TWO_WORDS = 0.65  # or its two most frequent words this share (measured)
STOP_EN = set("a an the and or but of to in on at by for with from as is are was were be been his her their him them "
              "he she they it its this that these those who which what will shall not no all one".split())
CONNECTORS = ("καί", "δέ", "γάρ", "οὖν", "τότε", "ἀλλά", "ὅτι", "ἵνα", "ὡς", "ἰδού")
GREEK_LATIN = dict(zip("αβγδεζηθικλμνξοπρστυφχψως", ["a", "b", "g", "d", "e", "z", "e", "th", "i", "k", "l", "m", "n",
                                                     "x", "o", "p", "r", "s", "t", "u", "f", "ch", "ps", "o", "s"]))


def merge_fragments(rows, counts, share=0.8):
    """One real affix shows up as nested candidates (-sch, -h; gsch-, gsc-, gc-). When a candidate makes up most
    (≥ share) of the cases of its one-letter-shorter form, that shorter form is only its tail and goes. Longer
    'subset' candidates (-get of -et) are not dropped: that would cost real affixes whose one-letter tails are
    meaningless, so subsets stay for the agent to judge."""
    best = {}
    for a, f, v, n, rate, lift in rows:
        best[a] = max(best.get(a, 0), lift)
    drop = set()

    def shorter(a):
        if a.startswith("-"):
            return "-" + a[2:] if len(a) > 2 else None
        return a[:-2] + "-" if len(a) > 2 else None
    for a in sorted(best, key=len, reverse=True):
        s = shorter(a)
        if s and s in best and a not in drop and counts[a] >= share * counts[s]:
            drop.add(s)
    return [r for r in rows if r[0] not in drop]


def context(t):
    if t["class"] == "verb":
        return ".".join(x for x in (t["tense"], t["voice"], t["mood"], (t["person"] or "")[:1] + (t["number"] or "")[:1]) if x)
    if t["class"] in ("noun", "adj", "pron", "det"):
        return ".".join(x for x in (t["gcase"], (t["number"] or "")[:1], t["degree"]) if x)
    return ""


def latin(s):
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))
    return "".join(GREEK_LATIN.get(c, c) for c in s)


def greek_features(con, gtok=None):
    """features(row) -> {(feature, value)} of a linked Greek token (a row of g.tokens): person, number, tense, mood,
    gcase, voice, and in pairs (person+number "fs", tense+mood "aorist.indicative", person+number+mood "fp.subjunctive"),
    degree, and for verbs three clause-level ones: negated "yes" (οὐ / μή in the Greek clause), object (the clause's
    object pronoun, "3s") and subject_gender (through the subject referent). The names lang.py report shows, which a
    morph entry's `greek` names (scripts/morphs.py try)"""
    gtok = gtok or {r["key"]: r for r in con.execute("select * from g.tokens")}
    NEG = {"οὐ", "μή", "οὐδέ", "μηδέ", "οὐχί", "οὐκέτι", "μηκέτι"}
    neg_clause = {t["clause"] for t in gtok.values() if t["lemma"] in NEG and t["clause"]}
    obj_of = {}
    for t in gtok.values():
        if t["role"] in ("o", "io") and t["class"] == "pron" and t["clause"]:
            m_ = re.match(r"P-(\d)?", t["morph"] or "")
            if m_:
                obj_of.setdefault(t["clause"], f"{m_[1] or '3'}{(t['number'] or '')[:1]}")
    subj_gender = {}
    for k, kind, target in con.execute("select key, kind, target from g.refs where kind='subjref'"):
        tg = gtok.get(target)
        if tg and tg["gender"]:
            subj_gender.setdefault(k, tg["gender"])

    def features(r):
        out = {(f, r[f]) for f in ("person", "number", "tense", "mood", "gcase", "voice") if r[f]}
        if r["person"] and r["number"]:
            out.add(("person+number", f"{r['person'][:1]}{r['number'][:1]}"))
        if r["tense"] and r["mood"]:
            out.add(("tense+mood", f"{r['tense']}.{r['mood']}"))
        if r["person"] and r["number"] and r["mood"] in ("subjunctive", "imperative", "optative"):
            out.add(("person+number+mood", f"{r['person'][:1]}{r['number'][:1]}.{r['mood']}"))  # 1p subjunctive = 'let us'
        if r["degree"]:
            out.add(("degree", r["degree"]))
        if r["class"] == "verb":
            if r["clause"] in neg_clause:  # only the marked value: "not negated" is every other verb and says nothing
                out.add(("negated", "yes"))
            if r["clause"] in obj_of:
                out.add(("object", obj_of[r["clause"]]))
            if r["key"] in subj_gender:
                out.add(("subject_gender", subj_gender[r["key"]]))
        return out
    features.neg_clause = neg_clause           # the Greek clauses with a negation, for derive's own counts
    return features


def derive(pname, quiet=False):
    import difflib, math
    P, con = connect(pname)
    con.row_factory = sqlite3.Row
    con.executescript(DERIVED)
    for t in ("d_renderings", "d_function", "d_affix", "d_order", "d_names", "d_letters", "d_formulas", "d_discourse", "d_gaps"):
        con.execute(f"delete from {t}")
    # every link with its Greek token and target form
    rows = con.execute("""select l.book, l.ch, l.v, l.pos, t.form, t.raw, g.* from nt_links l
        join nt_tokens t on t.book=l.book and t.ch=l.ch and t.v=l.v and t.pos=l.pos
        join g.tokens g on g.key=l.key""").fetchall()
    by_key = collections.defaultdict(list)
    for r in rows:
        by_key[r["key"]].append(r)
    gtok = {r["key"]: r for r in con.execute("select * from g.tokens")}
    # 1. renderings by context (content lemmas)
    ren = collections.defaultdict(collections.Counter)
    for r in rows:
        if r["class"] not in FUNCTION:
            ren[(r["strong"], r["lemma"], "")][r["form"]] += 1
            ren[(r["strong"], r["lemma"], context(r))][r["form"]] += 1
    con.executemany("insert into d_renderings values(?,?,?,?,?,?)",
                    [(s, l, c, f, n, n / sum(cnt.values())) for (s, l, c), cnt in ren.items() for f, n in cnt.most_common(5)])
    # 2. function words: renderings and how often they have no target word
    occ = collections.Counter((t["class"], t["lemma"]) for t in gtok.values() if t["class"] in FUNCTION)
    linked = collections.Counter((gtok[k]["class"], gtok[k]["lemma"]) for k in by_key if gtok[k]["class"] in FUNCTION)
    fm = collections.defaultdict(collections.Counter)
    for r in rows:
        if r["class"] in FUNCTION:
            fm[(r["class"], r["lemma"])][r["form"]] += 1
    con.executemany("insert into d_function values(?,?,?,?,?,?)",
                    [(c, l, f, n, n / sum(cnt.values()), 1 - linked[(c, l)] / occ[(c, l)])
                     for (c, l), cnt in fm.items() if occ[(c, l)] >= 30 for f, n in cnt.most_common(4)])
    # 3. affixes: endings and beginnings of the target word (accents folded, so tone doesn't split the counts), against
    #    the Greek features of the linked token, single and in pairs (person+number, tense+mood), and two clause-level
    #    features: negation (οὐ / μή in the Greek clause) and the object's person+number (the clause's object pronoun);
    #    for verbs also the subject's gender (through the subject referent)
    import unicodedata
    fold = lambda w: "".join(c for c in unicodedata.normalize("NFD", w) if not unicodedata.combining(c))
    features = greek_features(con, gtok)
    neg_clause = features.neg_clause
    import priors
    prior_affixes = priors.inflection_affixes(pname)  # tested as themselves, whatever their length (-schte)
    base, joint, cnt_aff = collections.Counter(), collections.Counter(), collections.Counter()
    words_of = collections.defaultdict(collections.Counter)  # an affix only if it occurs on several different words,
    # and not mostly on one of them (nøfuap, ndigu, nøten: a frequent word's ending is not an affix)
    total = 0
    for r in rows:
        if r["class"] not in ("verb", "noun", "pron", "adj"):
            continue
        total += 1
        f_ = fold(r["form"])
        affs = {f_} if f_.startswith("-") else ({"-" + f_[-k:] for k in (1, 2, 3) if len(f_) > k + 1}
                                               | {f_[:k] + "-" for k in (1, 2, 3, 4) if len(f_) > k + 2}
                                               | {a for a in prior_affixes if len(f_) > len(a) and (
                                                   f_.endswith(a[1:]) if a.startswith("-") else f_.startswith(a[:-1]))})
        fv = features(r)
        for fvv in fv:
            base[fvv] += 1
        for a_ in affs:
            cnt_aff[a_] += 1
            for fvv in fv:
                joint[(a_, fvv)] += 1
                words_of[(a_, fvv)][fold(r["form"])] += 1
    out = []
    for (a_, (f, val)), n in joint.items():
        w = words_of[(a_, (f, val))]
        top = w.most_common(2)
        min_n = 10 if f in ("person+number+mood", "degree") else 30  # rare features (1p subjunctive, comparative)
        if (n >= min_n and cnt_aff[a_] >= 50 and len(w) >= 5 and top[0][1] / n < ONE_WORD
                and sum(c for _, c in top) / n < TWO_WORDS):
            rate = n / base[(f, val)]
            lift = rate / (cnt_aff[a_] / total)
            if lift >= 1.5:
                out.append((a_, f, val, n, rate, lift))
    out = merge_fragments(out, cnt_aff)
    # word-forming affixes named in profile/priors.yaml carry no grammar: not hypotheses
    wf = priors.word_forming(pname)
    # ...unless the priors also list it as inflection, or the statistics tie it strongly to a grammatical value (lift
    # ≥ 5): then it stays, and the priors check reports the contradiction (the model listed an inflection ending as word-forming)
    strong = {r[0] for r in out if r[5] >= 5}
    keep = priors.inflection_affixes(pname) | strong
    out = [r for r in out if r[0] not in wf or r[0] in keep]
    con.executemany("insert into d_affix values(?,?,?,?,?,?)", out)
    # 3b. tone and other marks: each combining mark on a verb against the same features, and the last word of a verse
    #     against a Greek question mark (;) ending the verse
    #     and, where the store says how tone is written (orthography.tone, scripts/morphs.py), the tone pattern by position
    #     from the word's end: '@-1:U+1DC4' (the mark on the last tone-bearing unit), '@-2:U+0300 @-1:U+1DC4' (the last
    #     two): the candidates for a grammatical tone morph's tone_pattern
    import json, morphs
    pf = os.path.join(P.profile, "observations.json")
    spec = morphs.ToneSpec(json.load(open(pf, encoding="utf-8")).get("orthography") if os.path.exists(pf) else {})

    def tone_sig(raw):
        cl = morphs.clusters((raw or "").lower())
        u = spec.units(cl)
        if spec.written not in ("marks", "digits") or not u:
            return set()
        at = {k: sorted(spec.marks_at(cl, u[k])) for k in (-1, -2, -3) if len(u) >= -k}
        out = {f"@{k}:U+{ord(m):04X}" for k, ms_ in at.items() for m in ms_}
        out |= {f"@-2:U+{ord(a):04X} @-1:U+{ord(b):04X}" for a in at.get(-2, []) for b in at.get(-1, [])}
        return out
    marks, mbase, mjoint = collections.Counter(), collections.Counter(), collections.Counter()
    nv = 0
    for r in rows:
        if r["class"] != "verb":
            continue
        nv += 1
        ms = {f"U+{ord(c):04X}" for c in unicodedata.normalize("NFD", r["raw"] or "") if unicodedata.combining(c)}
        ms |= tone_sig(r["raw"])
        fv = features(r)
        neg_mood = ("negated+mood", f"{'neg' if r['clause'] in neg_clause else 'pos'}.{r['mood']}")
        fv.add(neg_mood)
        for fvv in fv:
            mbase[fvv] += 1
        for m_ in ms:
            marks[m_] += 1
            for fvv in fv:
                mjoint[(m_, fvv)] += 1
    # questions: a verse with a Greek question mark (;) anywhere against the marks anywhere in the target verse
    q_ends, q_last = collections.Counter(), collections.Counter()
    verse_marks = collections.defaultdict(set)
    for (book, ch, v, form) in con.execute("select book, ch, v, coalesce(raw, form) from nt_tokens"):
        verse_marks[(book, ch, v)] |= {f"U+{ord(c):04X}" for c in unicodedata.normalize("NFD", form) if unicodedata.combining(c)}
    is_q = {(t["book"], t["ch"], t["v"]) for t in gtok.values() if (t["after"] or "").strip() == ";"}
    for ref, ms in verse_marks.items():
        q = "question" if ref in is_q else "statement"
        q_ends[q] += 1
        for m_ in ms:
            q_last[(m_, q)] += 1
    con.execute("create table if not exists d_marks(mark text, feature text, value text, n int, rate real, lift real)")
    con.execute("delete from d_marks")
    mo = []
    for (m_, (f, val)), n in mjoint.items():
        if n >= 20:
            lift = (n / mbase[(f, val)]) / (marks[m_] / nv)
            if lift >= 1.5:
                mo.append((m_, f, val, n, n / mbase[(f, val)], lift))
    allq = sum(q_ends.values())
    for (m_, q), n in q_last.items():
        tot_m = sum(c for (mm, _), c in q_last.items() if mm == m_)
        lift = (n / q_ends[q]) / (tot_m / allq) if tot_m else 0
        if n >= 20 and lift >= 1.5:
            mo.append((m_, "verse", q, n, n / q_ends[q], lift))
    con.executemany("insert into d_marks values(?,?,?,?,?,?)", mo)
    # 4. constituent order: S, V, O of a Greek clause by the target positions of their linked words
    pat, gpat = collections.Counter(), {}
    clause_words = collections.defaultdict(list)
    for t in gtok.values():
        if t["role"] in ("s", "v", "o") and t["clause"]:
            clause_words[t["clause"]].append(t)
    for cl, ws in clause_words.items():
        roles = {w["role"] for w in ws}
        if not {"s", "v", "o"} <= roles and not ({"v", "o"} <= roles):
            continue
        pos = []
        for w in ws:
            tp = [(r["book"], r["ch"], r["v"], r["pos"]) for r in by_key.get(w["key"], [])]
            if tp:
                pos.append((min(tp), w["role"], w["key"]))
        if len({p[1] for p in pos}) < len(roles) or len({p[0][:3] for p in pos}) > 1:
            continue
        first = {}
        for p in sorted(pos):
            first.setdefault(p[1], p)
        tp_ = "".join(x[1].upper() for x in sorted(first.values()))
        gp_ = "".join(x[1].upper() for x in sorted(first.values(), key=lambda x: x[2]))
        pat[(tp_, gp_)] += 1
    con.executemany("insert into d_order values(?,?,?)", [(t, n, g) for (t, g), n in pat.items()])
    # 5. names and letters
    nm = collections.defaultdict(collections.Counter)
    for r in rows:
        if r["type"] == "proper":
            nm[r["lemma"]][r["form"]] += 1
    con.executemany("insert into d_names values(?,?,?)", [(l, f, n) for l, c in nm.items() for f, n in c.most_common(2)])
    let = collections.Counter()
    for l, c in nm.items():
        f, n = c.most_common(1)[0]
        a, b = latin(l), f.lower()
        own = None
        if any(ch.isalpha() and "LATIN" not in unicodedata.name(ch, "") for ch in b):   # another script: lined up
            b_, own = LT.romanise(b)                     # through a Latin reading, the letters kept in the target's script
            b, orig = b_, b
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "replace" and (i2 - i1) <= 2 and (j2 - j1) <= 3:
                tl = b[j1:j2] if own is None else orig[min(own[j1:j2]):max(own[j1:j2]) + 1]
                let[(a[i1:i2], tl)] += n
    con.executemany("insert into d_letters values(?,?,?)", [(g, t, n) for (g, t), n in let.most_common(60) if n >= 5])
    # 6. formulas: Greek lemma trigrams of a verse, frequent, with the target words linked to them
    seq = collections.defaultdict(list)
    for t in sorted(gtok.values(), key=lambda t: t["key"]):
        seq[(t["book"], t["ch"], t["v"])].append(t)
    tri = collections.defaultdict(list)
    for ref, ts in seq.items():
        for i in range(len(ts) - 2):
            tri[tuple(x["lemma"] for x in ts[i:i + 3])].append(ts[i:i + 3])
    fo = []
    for lem, occs in tri.items():
        if len(occs) < 15 or all(gtok[o[0]["key"]]["class"] in FUNCTION for o in occs[:1]) and sum(1 for x in occs[0] if x["class"] in FUNCTION) == 3:
            continue
        renders = collections.Counter()
        for o in occs:
            ps = sorted({(r["pos"], r["form"]) for x in o for r in by_key.get(x["key"], [])})
            if ps:
                renders[" ".join(f for _, f in ps)] += 1
        for f, k in renders.most_common(2):
            fo.append((" ".join(lem), len(occs), f, k))
    con.executemany("insert into d_formulas values(?,?,?,?)", fo)
    # 7. discourse connectors at clause or verse start
    first_of = {}
    for ref, ts in seq.items():
        for i, t in enumerate(ts):
            if t["lemma"] in CONNECTORS and (i == 0 or t["clause"] != ts[i - 1]["clause"] or i < 2):
                first_of[t["key"]] = t
    dc, dn = collections.defaultdict(collections.Counter), collections.Counter()
    for k, t in first_of.items():
        dn[t["lemma"]] += 1
        for r in by_key.get(k, []):
            dc[t["lemma"]][r["form"]] += 1
    con.executemany("insert into d_discourse values(?,?,?,?,?)",
                    [(l, f, n, n / max(sum(c.values()), 1), 1 - sum(1 for k, t in first_of.items() if t["lemma"] == l and k in by_key) / dn[l])
                     for l, c in dc.items() for f, n in c.most_common(4)])
    # 8. gaps: frequent Hebrew content lexemes whose LXX equivalents the NT hardly has
    nt_by_strong = collections.Counter()
    for r in rows:
        nt_by_strong[r["strong"]] += 1
    gaps = []
    eng_nt = collections.Counter()  # the BSB NT's words: a gap whose English word the NT has is not a gap
    for code in BY_CODE:
        if BY_CODE[code][2] == "nt":
            for f in sorted(__import__("glob").glob(os.path.join(ROOT, "reference", "BSB", f"{code}[0-9][0-9][0-9].txt"))):
                for vt in LT.verses_of(f).values():
                    eng_nt.update(w.lower() for w in re.findall(r"[^\W\d_]+", vt))
    bsb_ot = {}

    def english_of(lex):
        """The lexeme's most frequent BSB word (through the BSB tables), stopwords left out."""
        import full_align as FA
        c = collections.Counter()
        for key, book, ch, v in con.execute("select key, book, ch, v from h.tokens where lexeme=? limit 60", (lex,)):
            pos = con.execute("select positions from h.bsb where key=?", (key,)).fetchone()
            if not pos:
                continue
            import vrs as V
            c2, v2 = V.to_bsb(book.lower(), ch, v)
            f = os.path.join(ROOT, "reference", "BSB", f"{book.lower()}{c2:03d}.txt")
            if f not in bsb_ot:
                bsb_ot[f] = LT.verses_of(f) if os.path.exists(f) else {}
            toks = FA.tokenize(bsb_ot[f].get((c2, v2), ""))
            for i in map(int, pos[0].split()):
                if i < len(toks) and toks[i].lower() not in STOP_EN:
                    c[toks[i].lower()] += 1
        return [w for w, _ in c.most_common(2)]
    for lex, n in con.execute("""select lexeme, count(*) from h.tokens where kind='c' and class in ('noun','verb','adj')
            and coalesce(type, '') <> 'proper' and lexeme is not null group by lexeme having count(*) >= 20""").fetchall():
        lemma, gloss = con.execute("""select lemma, coalesce(english, gloss) from h.tokens where lexeme=?
            group by lemma, coalesce(english, gloss) order by count(*) desc limit 1""", (lex,)).fetchone()
        eq = con.execute("select greekstrong, sum(n) from h.lxx where lexeme=? group by greekstrong order by 2 desc limit 3", (lex,)).fetchall()
        nt = sum(nt_by_strong.get(g.lstrip("0"), 0) + nt_by_strong.get(g, 0) for g, _ in eq)
        if nt < 3:
            eng = english_of(lex)
            stem = lambda w: w[:-1] if w.endswith("s") else w
            in_nt = sum(c for w in eng for ww, c in eng_nt.items() if stem(ww) == stem(w))
            if in_nt < 3:  # neither the LXX route nor the English one finds it in the NT
                gaps.append((lex, lemma, gloss, n, nt))
    con.executemany("insert into d_gaps values(?,?,?,?,?)", gaps)
    con.commit()
    if not quiet:
        for t in ("d_renderings", "d_function", "d_affix", "d_marks", "d_order", "d_names", "d_letters", "d_formulas", "d_discourse", "d_gaps"):
            print(f"  {t}: {con.execute(f'select count(*) from {t}').fetchone()[0]} rows")
    return con


def report(pname, top=8):
    """A readable summary of the derived products (to the terminal; bulk stays in the database)."""
    P, con = connect(pname)
    print(f"# Derived from {pname}'s NT aligned to the Greek\n")
    print("## Constituent order (S, V, O of Greek clauses, ordered by the target words)")
    tot = sum(n for (n,) in con.execute("select n from d_order"))
    for t, n in con.execute("select pattern, sum(n) from d_order group by pattern order by 2 desc limit 6"):
        print(f"  {t}: {n} ({100 * n / max(tot, 1):.0f}%)")
    print("\n## Function words (rendering share; how often the Greek word has no target word)")
    for c, l in con.execute("select class, lemma from d_function group by class, lemma order by sum(n) desc limit 14"):
        rs = con.execute("select form, share, dropped from d_function where class=? and lemma=? order by n desc limit 3", (c, l)).fetchall()
        print(f"  {c} {l}: " + ", ".join(f"{f} {100 * sh:.0f}%" for f, sh, _ in rs) + f"; none {100 * rs[0][2]:.0f}%")
    print("\n## Discourse connectors at clause start")
    for l, in con.execute("select lemma from d_discourse group by lemma order by sum(n) desc"):
        rs = con.execute("select form, share, dropped from d_discourse where lemma=? order by n desc limit 3", (l,)).fetchall()
        print(f"  {l}: " + ", ".join(f"{f} {100 * sh:.0f}%" for f, sh, _ in rs) + f"; none {100 * rs[0][2]:.0f}%")
    print("\n## Affixes and the Greek features they go with (lift ≥ 1.5)")
    for label, cond in (("endings", "affix like '-%'"), ("beginnings", "affix like '%-' and affix not like '-%'")):
        print(f"  {label}:")
        best = {}  # one line per affix: its strongest feature, then the next ones in brief
        for a, f, v, n, rate, lift in con.execute(f"select * from d_affix where {cond} order by lift * min(n, 300) desc"):
            best.setdefault(a, []).append((f, v, n, lift))
        for a, fs in list(best.items())[:24]:
            f, v, n, lift = fs[0]
            more = "; also " + ", ".join(f"{x[0]}={x[1]} ({x[3]:.1f})" for x in fs[1:3]) if len(fs) > 1 else ""
            print(f"    {a} with {f}={v}: n {n}, lift {lift:.1f}{more}")
    print("\n## Constructions (rarer Greek forms, and how the target renders them)")
    hort = con.execute("select affix, n, lift from d_affix where feature='person+number+mood' and value='fp.subjunctive' "
                       "order by lift * min(n, 300) desc limit 3").fetchall()
    print("  'let us' (1st plural subjunctive): " + (", ".join(f"{a} (n {n}, lift {l:.0f})" for a, n, l in hort) or "nothing"))
    cmp = con.execute("select form, sum(n) from d_renderings where context like '%comparative%' group by form "
                      "order by 2 desc limit 8").fetchall()
    print("  Greek comparatives rendered with: " + ", ".join(f"{f} ×{n}" for f, n in cmp)
          + " (lexicalised comparatives such as 'elders' included)")
    print("\n## Marks (tone and other combining marks) and what they go with (lift ≥ 1.5)")
    names = {"U+0300": "grave", "U+0301": "acute", "U+0302": "circumflex", "U+0304": "macron", "U+1DC4": "macron-acute"}
    for m_, f, v, n, rate, lift in con.execute("select * from d_marks order by lift * min(n, 300) desc limit 12"):
        print(f"  {names.get(m_, m_)} with {f}={v}: n {n}, lift {lift:.1f}")
    print("\n## Letters in names (Greek → target)")
    print("  " + ", ".join(f"{g}→{t} ×{n}" for g, t, n in con.execute("select * from d_letters order by n desc limit 20")))
    print("\n## Names (most frequent)")
    print("  " + ", ".join(f"{l} {f}" for l, f, n in con.execute(
        "select lemma, form, max(n) from d_names group by lemma order by max(n) desc limit 16")))
    print("\n## Formulas (Greek lemma trigrams ≥ 15×, top rendering)")
    for lem, n, f, k in con.execute("select lemmas, n, form, max(k) from d_formulas group by lemmas order by n desc limit 10"):
        print(f"  {lem} ×{n}: {f} ({k})")
    print(f"\n## Gaps: frequent Hebrew content words the NT hardly has ({con.execute('select count(*) from d_gaps').fetchone()[0]})")
    print("  " + ", ".join(f"{g} ({l}) ×{n}" for l, g, n in con.execute(
        "select lemma, gloss, ot_n from d_gaps order by ot_n desc limit 25")))
    import priors
    if priors.load(pname):
        print()
        priors.check(pname)


def stats(pname):
    P, con = connect(pname)
    for t in ("nt_tokens", "nt_links"):
        print(t, con.execute(f"select count(*) from {t}").fetchone()[0])
    print(con.execute("select * from meta").fetchall())


def layers(pname, write=False):
    import langtools as LT
    from project import project_dir
    P = LT.Project(pname)
    rows = find_layers(P)
    if not rows:
        print(f"{pname}: no alignment layer for {iso3(P)} in bcv-commons")
        return None
    print(f"{pname}: alignment layers for {iso3(P)} (NT books on exactly our text / the layer's NT books; OT books)")
    for ds, layer, m, n, mo in rows:
        print(f"  {layer:40} {ds:24} NT {m}/{n}" + (f", OT {mo}" if mo else ""))
    best = rows[0] if rows[0][2] else None
    have = P.p.get("lexeme_aligner")
    if not best:
        print("  none is built on our text (another copy or another numbering): lexeme_aligner left as it is")
    elif have:
        print(f"  project.yaml has lexeme_aligner: {have}" + ("" if have == best[1] else f" (the best match is {best[1]})"))
    elif write:
        pf = os.path.join(project_dir(pname), "project.yaml")
        open(pf, "a", encoding="utf-8").write(
            f"# the alignment layer built on our text (lang.py layers): its links go into lang.py build\nlexeme_aligner: {best[1]}\n")
        print(f"  written: lexeme_aligner: {best[1]} (lang.py build adds its links)")
    else:
        print(f"  --write sets lexeme_aligner: {best[1]}")
    return best


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    nv = int(a[a.index("--verses") + 1]) if "--verses" in a else None
    if a[0] == "build":
        build(a[1], a[a.index("--links") + 1] if "--links" in a else None)
    elif a[0] == "hbo":
        hbo(a[1], a[2], nv or 1)
    elif a[0] == "grc":
        grc(a[1], a[2], nv or 2)
    elif a[0] == "derive":
        derive(a[1])
    elif a[0] == "report":
        report(a[1])
    elif a[0] == "stats":
        stats(a[1])
    elif a[0] == "layers":
        layers(a[1], "--write" in a)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
