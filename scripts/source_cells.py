"""The source-to-cell table: for each Greek or Hebrew token, the grammatical features a translation has to carry, as a
feature bundle and as the paradigm cells it falls into (the cell ids a language's store uses: `verb.subject: 2.PL.IMP`).
Language-neutral: it reads only the source (orig/grc.sqlite, orig/heb.sqlite, MACULA's morphology and clauses); a
language's store says which of these cells it marks and how (the verse analysis, the packs, the draft check).

Per token: pos, person (1 2 3), number (SG PL DU), gender (M F N C), case, mood (IND SBJV IMP OPT INF PTCP; Hebrew
also JUSS COH), tense (Greek PRS AOR IPFV.PST FUT PRF PLPRF; Hebrew the conjugation: QATAL YIQTOL WAYYIQTOL WEQATAL),
voice (Greek), stem (Hebrew binyan), polarity (NEG when a negation goes with the verb: the nearest verb after it in
its clause; Q.NEG for Hebrew הֲלֹא, a rhetorical "haven't you …?"; POS otherwise) with the negation's lemma, proh for a
prohibition (MH: Greek μή with an imperative or a 2nd-person subjunctive; AL: Hebrew אַל with a jussive, yiqtol or
cohortative; LO: Hebrew לֹא with a 2nd-person yiqtol, a prohibition or a statement), and for pronouns the role: subject (a free nominative pronoun), object, possessor, oblique
(Greek by case and the word before; Hebrew suffixes by their host: verb, noun, preposition; inf on an infinitive,
where the suffix is the subject or the object).

Cells (paradigm: bundle):
  verb.subject           person.number.mood              2.PL.IMP
  verb.subject.gender    person.number.gender (Hebrew)   2.SG.F
  verb.polarity          polarity.mood                   NEG.IND
  verb.polarity.tense    polarity.tense.mood             NEG.AOR.SBJV, NEG.YIQTOL.IND
  verb.prohibitive       person.number (MH, AL)          2.SG
  verb.prohibitive.lo    person.number (LO)              2.PL
  pronoun.<role>         person.number[.gender]          pronoun.possessor: 3.SG.M
A language's store names its verb and pronoun cells with these ids, so the store and this table speak the same
language.

Usage: python3 scripts/source_cells.py show <code> <c>:<v>        the verse, token by token
       python3 scripts/source_cells.py stats [--nt | --ot] [paradigm]   cell counts
As a library: cells_of(book) -> {key: Token}; Token.feats (dict), Token.cells ([(paradigm, bundle)]).
"""
import collections, os, sqlite3, sys

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
PERSON = {"first": "1", "second": "2", "third": "3"}
NUMBER = {"singular": "SG", "plural": "PL", "dual": "DU"}
GENDER = {"masculine": "M", "feminine": "F", "common": "C", "both": "C"}
MOOD = {"indicative": "IND", "subjunctive": "SBJV", "imperative": "IMP", "optative": "OPT", "infinitive": "INF",
        "participle": "PTCP"}
TENSE = {"present": "PRS", "aorist": "AOR", "imperfect": "IPFV.PST", "future": "FUT", "perfect": "PRF",
         "pluperfect": "PLPRF"}
HEB_TYPE = {"qatal": ("QATAL", "IND"), "yiqtol": ("YIQTOL", "IND"), "wayyiqtol": ("WAYYIQTOL", "IND"),
            "weqatal": ("WEQATAL", "IND"), "imperative": ("", "IMP"), "jussive": ("", "JUSS"),
            "cohortative": ("", "COH"), "infinitive construct": ("", "INF"), "infinitive absolute": ("", "INF"),
            "participle active": ("", "PTCP"), "participle passive": ("", "PTCP")}
GRC_NEG = {"οὐ", "μή", "οὐδέ", "μηδέ", "οὐκέτι", "μηκέτι", "οὐδείς", "μηδείς", "οὔτε", "μήτε", "οὐχί", "οὔπω", "μήποτε",
           "μηδαμῶς", "οὐδαμῶς", "μήπω", "οὐθείς", "μηθείς"}
HEB_NEG = {"3808": "לֹא", "3809": "לָא", "0408": "אַל", "0369": "אַיִן", "1077": "בַּל", "1097": "בְּלִי",
           "1115": "בִּלְתִּי", "2962": "טֶרֶם", "6435": "פֶּן"}
PROHIBITIVE = {"μή", "μηδέ", "μηδείς", "μήτε", "μηκέτι", "μηθείς", "אַל"}


def _scope(rows, is_neg, is_verb):
    """{verb row index: [negation row indexes]}: a negation goes with the nearest verb after it in its clause (the one
    before it when none follows), not with every verb of the clause (a participle used as a noun stays positive)"""
    by_clause = collections.defaultdict(list)
    for i, r in enumerate(rows):
        if r["clause"]:
            by_clause[r["clause"]].append(i)
    out = collections.defaultdict(list)
    for idx in by_clause.values():
        verbs = [i for i in idx if is_verb(rows[i])]
        for i in idx:
            if is_neg(rows[i]) and verbs:
                after = [j for j in verbs if j > i]
                out[after[0] if after else verbs[-1]].append(i)
    return out


class Token:
    __slots__ = ("key", "text", "lemma", "feats", "cells")

    def __init__(self, key, text, lemma, feats):
        self.key, self.text, self.lemma, self.feats, self.cells = key, text, lemma, feats, []

    def __repr__(self):
        return f"{self.key} {self.text} {self.feats} {self.cells}"


def _db(testament):
    con = sqlite3.connect(os.path.join(ROOT, "orig", "grc.sqlite" if testament == "nt" else "heb.sqlite"))
    con.row_factory = sqlite3.Row
    return con


def _bundle(*parts):
    return ".".join(p for p in parts if p)


def _cells(f):
    out = []
    if f["pos"] == "verb":
        p, n, m = f.get("person", ""), f.get("number", ""), f["mood"]
        if p and n:
            out.append(("verb.subject", _bundle(p, n, m)))
            if f.get("gender"):
                out.append(("verb.subject.gender", _bundle(p, n, f["gender"])))
        out.append(("verb.polarity", _bundle(f["polarity"], m)))
        if f.get("tense"):
            out.append(("verb.polarity.tense", _bundle(f["polarity"], f["tense"], m)))
        if f.get("proh") in ("MH", "AL") and p and n:
            out.append(("verb.prohibitive", _bundle(p, n)))
        elif f.get("proh") == "LO" and p and n:
            out.append(("verb.prohibitive.lo", _bundle(p, n)))
    elif f["pos"] == "pron" and f.get("role") and f.get("person"):
        out.append((f"pronoun.{f['role']}", _bundle(f["person"], f.get("number", ""), f.get("gender", ""))))
    return out


def _grc(rows):
    scope = _scope(rows, lambda r: r["lemma"] in GRC_NEG, lambda r: r["class"] == "verb")
    out, prev = {}, None
    for i, r in enumerate(rows):
        f = {"pos": r["class"] or ""}
        if r["class"] == "verb":
            m = MOOD.get(r["mood"] or "", "")
            f.update(mood=m, tense=TENSE.get(r["tense"] or "", ""), voice=(r["voice"] or "")[:3].upper(),
                     person=PERSON.get(r["person"] or "", ""), number=NUMBER.get(r["number"] or "", ""))
            ng = {rows[j]["lemma"] for j in scope.get(i, ())}
            f["polarity"] = "NEG" if ng else "POS"
            if ng:
                f["neg"] = ",".join(sorted(ng))
                if ng & PROHIBITIVE and (m == "IMP" or (m == "SBJV" and f["person"] == "2")):
                    f["proh"] = "MH"
        elif r["class"] == "pron" and r["type"] == "personal":
            mo = r["morph"] or ""                     # P-2DP (ἐγώ, σύ), P-GSM (αὐτός: third, with gender)
            f.update(person=mo[2] if len(mo) > 2 and mo[2] in "123" else "3", number=NUMBER.get(r["number"] or "", ""),
                     gender={"M": "M", "F": "F", "N": "N"}.get(mo[-1:], "") if not mo[2:3].isdigit() else "",
                     case=(r["gcase"] or "")[:3].upper())
            c = r["gcase"]
            f["role"] = ("subject" if c == "nominative" else "object" if c == "accusative" else
                         "possessor" if c == "genitive" and prev is not None and prev["class"] in ("noun", "adj") else
                         "oblique")
        out[r["key"]] = Token(r["key"], r["text"], r["lemma"], f)
        if r["class"] != "det":
            prev = r
    return out


def _heb(rows):
    scope = _scope(rows, lambda r: r["lexeme"] in HEB_NEG, lambda r: r["class"] == "verb")

    def neg_of(j):
        """the negation's lemma; הֲלֹא (the interrogative he on לֹא: "haven't you …?") apart, a rhetorical question"""
        q = j > 0 and rows[j - 1]["word"] == rows[j]["word"] and rows[j - 1]["lemma"] == "הֲ"
        return "הֲלֹא" if q and rows[j]["lexeme"] == "3808" else HEB_NEG[rows[j]["lexeme"]]
    out = {}
    for i, r in enumerate(rows):
        f = {"pos": "verb" if r["class"] == "verb" else "pron" if r["class"] == "pron" else r["class"] or ""}
        g = GENDER.get(r["gender"] or "", "")
        if f["pos"] == "verb":
            tense, m = HEB_TYPE.get(r["type"] or "", ("", ""))
            f.update(mood=m, tense=tense, stem=r["stem"] or "", person=PERSON.get(r["person"] or "", ""),
                     number=NUMBER.get(r["number"] or "", ""), gender=g)
            ng = {neg_of(j) for j in scope.get(i, ())}
            f["polarity"] = "NEG" if ng - {"הֲלֹא"} else "Q.NEG" if ng else "POS"
            if ng:
                f["neg"] = ",".join(sorted(ng))
                if ng & PROHIBITIVE and (m in ("JUSS", "COH") or tense == "YIQTOL"):
                    f["proh"] = "AL"
                elif "לֹא" in ng and tense == "YIQTOL" and f["person"] == "2":
                    f["proh"] = "LO"              # לֹא תִרְצָח: often a prohibition (Ruth 2:15-16), often a statement
        elif f["pos"] == "pron" and (r["pos"] == "suffix" or r["type"] == "personal"):
            f.update(person=PERSON.get(r["person"] or "", ""), number=NUMBER.get(r["number"] or "", ""), gender=g)
            if r["pos"] == "suffix":
                host = rows[i - 1] if i and rows[i - 1]["word"] == r["word"] and rows[i - 1]["v"] == r["v"] else None
                hc = host["class"] if host is not None else ""
                inf = hc == "verb" and (host["type"] or "").startswith("infinitive")
                f["role"] = ("inf" if inf else "object" if hc == "verb" else "possessor" if hc in ("noun", "adj")
                             else "oblique")    # on an infinitive (בְּבֹאוֹ "when he came") subject or object
            else:
                f["role"] = "subject"
        out[r["key"]] = Token(r["key"], r["text"], r["lemma"], f)
    return out


def cells_of(book, testament=None, con=None):
    """{key: Token} for a book (BSB code or the databases' upper-case code), cells filled"""
    b = book.upper()
    if testament is None:
        sys.path.insert(0, os.path.join(CODE, "scripts"))
        from books import BY_CODE
        testament = BY_CODE[book.lower()][2]
    con = con or _db(testament)
    cols = ("key, book, ch, v, word, text, lemma, class, type, morph, mood, tense, voice, person, number, gcase, clause"
            if testament == "nt" else
            "key, book, ch, v, word, text, lemma, lexeme, class, pos, type, stem, person, gender, number, clause")
    rows = con.execute(f"select {cols} from tokens where book = ? order by key", (b,)).fetchall()
    toks = _grc(rows) if testament == "nt" else _heb(rows)
    for t in toks.values():
        t.cells = _cells(t.feats)
    return toks


def verse(book, ch, v):
    """[Token] of one verse, in order"""
    sys.path.insert(0, os.path.join(CODE, "scripts"))
    from books import BY_CODE
    testament = BY_CODE[book.lower()][2]
    con = _db(testament)
    keys = [k for (k,) in con.execute("select key from tokens where book = ? and ch = ? and v = ? order by key",
                                      (book.upper(), ch, v))]
    toks = cells_of(book, testament, con)
    return [toks[k] for k in keys]


def main(a):
    if a[:1] == ["show"] and len(a) == 3:
        c, v = (int(x) for x in a[2].split(":"))
        for t in verse(a[1], c, v):
            f = {k: x for k, x in t.feats.items() if x and k != "pos"}
            print(f"{t.key}  {t.text:14} {t.feats['pos']:6} {' '.join(f'{k}={x}' for k, x in f.items()):60} "
                  f"{'; '.join(f'{p}: {b}' for p, b in t.cells)}")
    elif a[:1] == ["stats"]:
        sys.path.insert(0, os.path.join(CODE, "scripts"))
        from books import BY_CODE
        want = [x for x in a[1:] if not x.startswith("--")]
        tests = [t for t in ("nt", "ot") if f"--{t}" in a] or ["nt", "ot"]
        for testament in tests:
            n = collections.Counter()
            con = _db(testament)
            for code, (_, _, tt, *_) in BY_CODE.items():
                if tt != testament:
                    continue
                for t in cells_of(code, testament, con).values():
                    for p, b in t.cells:
                        if not want or p == want[0]:
                            n[(p, b)] += 1
            print(f"== {testament.upper()}")
            for (p, b), k in sorted(n.items(), key=lambda x: (x[0][0], -x[1])):
                print(f"{k:7}  {p}: {b}")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
