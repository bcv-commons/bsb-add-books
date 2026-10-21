"""Draft: convert bcv-query's Hebrew clause layout (MACULA + UHB, with the phase-2 text hierarchy)
into a Text-Fabric dataset, loadable by Text-Fabric and Context-Fabric. No BHSA data.

Inputs:
- a clause-layout delivery: <dir>/clauses/<BOOK>_<CCC>.jsonl and <dir>/build.json
  (bcv-query's format, bcv-commons/hebrew-clause-layout on Hugging Face);
- the MACULA word data for the same chapters from the shoresh /scaffold API, cached in
  download/scaffold/<BOOK>/<chapter>.json (scripts/fetch_heb_macula.py fetches them).

Model (node types, from small to large):
  word         slot: one MACULA token (prefixes such as וְ, בְּ, הַ are tokens of their own, as in BHSA)
  phrase       MACULA phrase group the token belongs to (role, function, type)
  clause_atom  a clause segment: a maximal run of a clause's words inside one verse (BHSA's term)
  clause       all segments of one clause (clause_key); may be discontinuous
  verse, chapter, book   sections (Hebrew numbering; verse_ref_en gives the English reference)
Edges:
  mother        clause -> its discourse_parent, valued with the relation (as BHSA's mother edge,
                but our links and relation names)
  macula_parent clause -> the enclosing clause in the MACULA tree (parent_key)
  attach        clause -> the word in the mother clause it depends on (discourse_attach)
Feature names follow MACULA and bcv-query; `mother` is the only BHSA name, because the
meaning is the same. Values are never taken from BHSA.

Usage (needs text-fabric: pip install text-fabric):
  python3 scripts/macula_to_tf.py <delivery dir> [--out DIR] [--version V] [--scaffold DIR]
  --scaffold: folder with <BOOK>/<chapter>.json scaffold responses (default download/scaffold)
  default out: scratch/tf/macula-hebrew-clauses/tf/<version>
"""
import glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WORD_FEATURES = ["key", "lexeme", "lemma", "strong", "gloss", "sp", "role", "stem", "person", "number", "gender",
                 "state", "wtype"]
INT = {"chapter", "verse", "seg", "depth", "tree_depth", "text_depth", "content"}


def load(delivery, scaffold_dir):
    """-> build.json, [(book, chapter, rows, scaffold)] in canonical order of the delivery files."""
    build = json.load(open(os.path.join(delivery, "build.json"), encoding="utf-8"))
    chapters = []
    for f in glob.glob(os.path.join(delivery, "clauses", "*.jsonl")):
        rows = [json.loads(l) for l in open(f, encoding="utf-8")]
        book, ch = rows[0]["book"], rows[0]["chapter"]
        sc = os.path.join(scaffold_dir, book, f"{ch}.json")
        if not os.path.exists(sc):
            raise SystemExit(f"missing {sc}: run scripts/fetch_heb_macula.py {book.lower()}:{ch}")
        chapters.append((book, ch, rows, json.load(open(sc, encoding="utf-8"))))
    chapters.sort(key=lambda c: c[2][0]["first"])        # word keys start with the book number
    return build, chapters


def director_for(chapters):
    def director(cv):
        cur = {"book": None, "chapter": None, "verse": None}
        clause_node, edges = {}, []                       # clause_key -> node; (from key, to key, kind, value)
        word_node = {}
        for book, ch, rows, sc in chapters:
            seg_of, clause_of = {}, {}
            first_row = {}
            for r in rows:
                for k in r["words"]:
                    seg_of[k] = (r["clause_key"], r["seg"])
                    clause_of[k] = r["clause_key"]
                first_row.setdefault(r["clause_key"], r)
            kq = {e["key"]: e for r in rows for e in r["ketiv_qere"]}
            ref_en = {r["verse"]: r["verse_ref_en"] for r in rows}
            if cur["book"] is None or cv.get("book", cur["book"]) != book:
                if cur["book"] is not None:
                    cv.terminate(cur["book"])
                cur["book"] = cv.node("book")
                cv.feature(cur["book"], book=book)
            cur["chapter"] = cv.node("chapter")
            cv.feature(cur["chapter"], book=book, chapter=ch)
            active = {"verse": None, "clause_atom": None, "clause": None, "phrase": None}
            vnum = None
            seg_node, phrase_node = {}, {}

            def switch(kind, ident, make):
                """Keep exactly the node for `ident` of this kind active (resume it if it was seen before)."""
                a = active[kind]
                if a is not None and a[0] == ident:
                    return
                if a is not None:
                    cv.terminate(a[1])
                if ident is None:
                    active[kind] = None
                    return
                n = make(ident)
                active[kind] = (ident, n)

            def make_clause(ck):
                if ck in clause_node:
                    cv.resume(clause_node[ck])
                    return clause_node[ck]
                n = cv.node("clause")
                r = first_row[ck]
                cv.feature(n, clause_key=ck, kind=r["kind"], rule=r["rule"], language=r["language"],
                           relation=r.get("relation"), tree_depth=r.get("tree_depth"), text_depth=r.get("text_depth"),
                           discourse_rule=r.get("discourse_rule"), depth=r["depth"])
                if r.get("discourse_parent"):
                    edges.append((ck, r["discourse_parent"], "mother", r.get("relation")))
                if r.get("parent_key"):
                    edges.append((ck, r["parent_key"], "macula_parent", None))
                if r.get("discourse_attach"):
                    edges.append((ck, r["discourse_attach"], "attach", None))
                clause_node[ck] = n
                return n

            def make_seg(sid):
                n = cv.node("clause_atom")
                cv.feature(n, seg=sid[1], clause_key=sid[0])
                seg_node[sid] = n
                return n

            def make_phrase(pid):
                if pid in phrase_node:
                    cv.resume(phrase_node[pid])
                    return phrase_node[pid]
                n = cv.node("phrase")
                p = sc["phrases"].get(str(pid), {})
                cv.feature(n, role=p.get("role"), function=p.get("function"), typ=p.get("type"))
                phrase_node[pid] = n
                return n

            toks = sc["tokens"]
            for ti, t in enumerate(toks):
                if t["verse"] != vnum:
                    for kind in ("phrase", "clause_atom", "clause"):
                        switch(kind, None, None)
                    if active["verse"] is not None:
                        cv.terminate(active["verse"][1])
                    vnum = t["verse"]
                    vn = cv.node("verse")
                    cv.feature(vn, book=book, chapter=ch, verse=vnum, verse_ref_en=ref_en.get(vnum))
                    active["verse"] = (vnum, vn)
                k = t["key"]
                switch("clause", clause_of.get(k), make_clause)
                switch("clause_atom", seg_of.get(k), make_seg)
                switch("phrase", t["phrase"], make_phrase)
                s = cv.slot()
                word_node[k] = s
                trailer = t["trailer"] or ""
                if trailer == "׀":
                    trailer = " ׀ "
                elif trailer in ("׃פ", "׃ס"):          # an open/closed paragraph after the verse
                    cv.feature(active["verse"][1], paragraph=trailer[1])
                    trailer = "׃ " + trailer[1] + " "
                elif trailer == "׃":
                    trailer = "׃ "
                elif trailer == "" and ti + 1 < len(toks) and toks[ti + 1]["key"][:11] != k[:11]:
                    trailer = " "                          # a new word (key without the part digit) begins
                feats = {f: t.get(f) for f in WORD_FEATURES if t.get(f) not in (None, "")}
                feats.update(g_word_utf8=t["text"], trailer_utf8=trailer, content=int(bool(t.get("content"))))
                if k in kq:
                    feats.update(ketiv=kq[k]["ketiv"], qere=kq[k]["qere"])
                cv.feature(s, **feats)
            for kind in ("phrase", "clause_atom", "clause"):
                switch(kind, None, None)
            cv.terminate(active["verse"][1])
            cv.terminate(cur["chapter"])
        cv.terminate(cur["book"])
        for a, b, kind, val in edges:
            na = clause_node.get(a)
            nb = word_node.get(b) if kind == "attach" else clause_node.get(b)
            if na is None or nb is None:
                continue
            if val is not None:
                cv.edge(na, nb, **{kind: val})
            else:
                cv.edge(na, nb, **{kind: None})
    return director


def main():
    from tf.fabric import Fabric
    from tf.convert.walker import CV
    delivery = sys.argv[1]
    version = sys.argv[sys.argv.index("--version") + 1] if "--version" in sys.argv else "draft"
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(
        ROOT, "scratch", "tf", "macula-hebrew-clauses", "tf", version)
    scaffold_dir = sys.argv[sys.argv.index("--scaffold") + 1] if "--scaffold" in sys.argv else os.path.join(
        ROOT, "download", "scaffold")
    build, chapters = load(delivery, scaffold_dir)
    generic = {
        "name": "MACULA Hebrew clause layout (draft)",
        "source": f"bcv-query clause layout, discourse rules {build.get('discourse_rules')}, segmentation "
                  f"{build.get('segmentation', {}).get('version')}; MACULA Hebrew, UHB ketiv/qere",
        "licence": build.get("licence", "CC BY-SA 4.0"),
        "version": version,
        "chapters": " ".join(f"{b} {c}" for b, c, _, _ in chapters),
        "note": "draft by bsb-add-books; no BHSA data",
    }
    otext = {
        "sectionTypes": "book,chapter,verse",
        "sectionFeatures": "book,chapter,verse",
        "fmt:text-orig-full": "{g_word_utf8}{trailer_utf8}",
        "fmt:lex-orig-full": "{lemma} ",
    }
    meta = {
        "key": {"description": "MACULA word key (BBCCCVVVWWW + part digit), stable across versions"},
        "g_word_utf8": {"description": "surface text of the token"},
        "trailer_utf8": {"description": "text after the token: space, maqaf, sof pasuq, paseq or nothing"},
        "lexeme": {"description": "MACULA lexeme id"}, "lemma": {"description": "MACULA lemma"},
        "strong": {"description": "Strong's number (MACULA)"}, "gloss": {"description": "English gloss (MACULA)"},
        "sp": {"description": "MACULA word class (noun, verb, cj, prep, ...)"},
        "role": {"description": "MACULA role of the word or phrase in its clause (s, v, o, adv, pp, ...)"},
        "function": {"description": "MACULA phrase function (Subject, PrepositionalPhrase, ...)"},
        "typ": {"description": "MACULA phrase type (np, pp, vp, ...)"},
        "stem": {"description": "verb stem"}, "person": {"description": "person"}, "number": {"description": "number"},
        "gender": {"description": "gender"}, "state": {"description": "state"},
        "wtype": {"description": "MACULA word type: verb form (wayyiqtol, qatal, ...) or noun type"},
        "content": {"description": "1 for a content word (MACULA)"},
        "ketiv": {"description": "ketiv (UHB), where the word has a ketiv/qere"},
        "qere": {"description": "qere (UHB), where the word has a ketiv/qere"},
        "book": {"description": "USFM book code"}, "chapter": {"description": "chapter (Hebrew numbering)"},
        "verse": {"description": "verse (Hebrew numbering)"},
        "verse_ref_en": {"description": "the verse in English numbering (TVTMS via bcv-commons/bibles)"},
        "paragraph": {"description": "פ (open, petuha) or ס (closed, setuma) paragraph break after the verse"},
        "seg": {"description": "position of the clause segment in its chapter"},
        "clause_key": {"description": "stable clause id: first word key of the clause's first segment"},
        "kind": {"description": "MACULA clause kind (VC, NC, ...)"}, "rule": {"description": "MACULA constituent rule"},
        "language": {"description": "hbo or arc"},
        "relation": {"description": "type of the link to the mother clause (bcv-query relation names)"},
        "discourse_rule": {"description": "the bcv-query rule that set the mother link"},
        "depth": {"description": "embedding depth in the MACULA tree, within the verse"},
        "tree_depth": {"description": "links up the mother chain, every link counted (BHSA-like)"},
        "text_depth": {"description": "links up the mother chain without the flat relations (flat view)"},
        "mother": {"description": "clause -> the clause it depends on in the text hierarchy; value: the relation"},
        "macula_parent": {"description": "clause -> the enclosing clause in the MACULA tree"},
        "attach": {"description": "clause -> the word in its mother clause that it depends on"},
    }
    os.makedirs(out, exist_ok=True)
    TF = Fabric(locations=out, silent="deep")
    cv = CV(TF)
    ok = cv.walk(director_for(chapters), "word", otext=otext, generic=generic,
                 intFeatures={k for k in INT}, featureMeta=meta, warn=True, force=False)
    print(("written to " if ok else "FAILED; partial output in ") + out)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
