#!/usr/bin/env python3
"""The verse analysis: for each word of a source verse, what the target language has for it, per grammatical cell.
Built on the source-to-cell table (scripts/source_cells.py), the store's grammar (scripts/grammar.py: morph and cell
entries) and the project's occurrence index (scripts/lang.py build: every NT token of the style corpus linked to a
Greek token). NT verses (the index links Greek); for the OT the same through the LXX is planned.

Per source word:
  lemma, gloss, the cells it requires (verb.subject 3.SG.IND, verb.polarity NEG.IND, ...)
  forms     the lemma's target forms in the corpus, with counts
  per cell  the store's pattern for the cell (ge-, -eav, Ø) and its status;
            attested: the lemma's forms where its source word had this cell (evidence to read, not a ranking: on
            held-out books they predict the human form no better than the lemma's most frequent forms)
The cell's pattern is the guidance a draft needs: on held-out books the marked cells' patterns show on the human
forms well above the paradigm's other cells (NEG -eav x10, møz- 2.PL, te- 3.SG.SBJV x6); the default cells' (-m) are
not distinctive. Composing forms from stems and patterns was tried and dropped: none matched a held-out form.

The pack's grammar block (pack v4, scripts/verse_pack.py --grammar): grammar_block(project, code, ch) -> (header,
{verse: lines}): the store's verb paradigm once, and per verse the verbs with a marked cell (negated, or a subject other
than 3rd singular), each with its pattern, count and share; NT verses add the lemma's frequent forms (the book being
drafted left out of the lexicon). Hebrew moods the store lacks go to its nearest cell: jussive and cohortative to the
subjunctive (Hebrew אַל + jussive is the Greek μή + subjunctive).

As a library:
  L = Lexicon(project, exclude={"PHP"})     the index without the excluded books (a held-out test)
  analyse(project, code, ch, v, L) -> [Word]  Word.key, .surface, .lemma, .gloss, .cells, .forms, .per_cell
                                             (per_cell: {(paradigm, bundle): {pattern, status, attested}})
Usage: python3 scripts/verse_analysis.py <project> <code> <c:v> [--exclude BOOK,BOOK] [--top N]
"""
import collections, os, re, sqlite3, sys

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
import grammar  # noqa: E402
import source_cells as SC  # noqa: E402
from books import BY_CODE  # noqa: E402

PARADIGMS = ("verb.subject", "verb.polarity", "verb.prohibitive")   # the cells a draft must carry


NT_NUM = {f"{40 + i:02d}": code for i, code in enumerate(c for c, b in BY_CODE.items() if b[2] == "nt")}  # MACULA's book numbers


class Lexicon:
    """lemma -> target forms, overall and per cell, from lang.sqlite's links (books in `exclude` left out)"""
    def __init__(self, pname, exclude=()):
        import langtools as LT
        db = os.path.join(LT.Project(pname).learn, "lang.sqlite")
        if not os.path.exists(db):
            raise SystemExit(f"no {os.path.relpath(db, ROOT)}: python3 scripts/lang.py build {pname}")
        self.exclude = {b.lower() for b in exclude}
        links = collections.defaultdict(set)
        q = ("select l.key, t.form from nt_links l join nt_tokens t on t.book = l.book and t.ch = l.ch and t.v = l.v "
             "and t.pos = l.pos")
        for key, form in sqlite3.connect(db).execute(q):
            if NT_NUM.get(key[:2]) and NT_NUM[key[:2]] not in self.exclude:
                links[key].add(form)
        self.forms = collections.defaultdict(collections.Counter)            # lemma -> forms
        self.cell = collections.defaultdict(collections.Counter)             # (lemma, paradigm, bundle) -> forms
        toks = {}
        for code in sorted({NT_NUM[k[:2]] for k in links}):
            toks.update(SC.cells_of(code, "nt"))
        for key, forms in links.items():
            t = toks.get(key)
            if not t or not t.lemma:
                continue
            for f in forms:
                self.forms[t.lemma][f] += 1
                for par, bundle in t.cells:
                    self.cell[(t.lemma, par, bundle)][f] += 1


class Word:
    def __init__(self, tok, gloss=""):
        self.key, self.surface, self.lemma, self.gloss = tok.key, tok.text, tok.lemma, gloss
        self.cells = [(p, b) for p, b in tok.cells if p in PARADIGMS]
        self.forms, self.per_cell = [], {}


def parts(pattern):
    """a cell's form pattern -> (prefix, suffix): 'ge-' -> ('ge', ''), '-eav' -> ('', 'eav'), 'z…-ap' -> ('z', 'ap')"""
    pre = suf = ""
    for p in re.split(r"[…\s]+|\.\.\.", pattern or ""):
        p = p.strip()
        if p.endswith("-") and not p.startswith("-"):
            pre = p[:-1]
        elif p.startswith("-") and not p.endswith("-"):
            suf = p[1:]
    return pre, suf


def stems(forms, G):
    """the lemma's forms without the store's verb affixes, with counts: an affix is stripped only where what is left
    is attested among the lemma's forms (as a form, or inside one), as scripts' segmenters do (zøkhaneam keeps its zø)"""
    out = collections.Counter()
    pre, suf = G.affixes("verb", "prefix"), G.affixes("verb", "suffix")
    seen = set(forms)
    ok = lambda r, f: len(r) >= 3 and any(r in g for g in seen if g != f)   # in another form of the lemma
    for f, n in forms.items():
        s = f
        for p in pre:
            if s.startswith(p) and ok(s[len(p):], f):
                s = s[len(p):]; break
        for x in suf:
            if s.endswith(x) and ok(s[:-len(x)], f):
                s = s[:-len(x)]; break
        out[s] += n
    return out


def analyse(pname, code, ch, v, L=None, G=None, top=5):
    L = L or Lexicon(pname)
    G = G or grammar.load(pname)
    out = []
    gloss = dict(sqlite3.connect(os.path.join(ROOT, "orig", "grc.sqlite")).execute(
        "select key, gloss from tokens where book = ? and ch = ? and v = ?", (code.upper(), ch, v)))
    for tok in SC.verse(code.upper(), ch, v):
        w = Word(tok, gloss.get(tok.key) or "")
        w.forms = L.forms.get(w.lemma, collections.Counter()).most_common(top)
        for par, bundle in w.cells:
            ce = G.cell(par, bundle)
            att = L.cell.get((w.lemma, par, bundle), collections.Counter()).most_common(top)
            w.per_cell[(par, bundle)] = {"pattern": ce.get("value") if ce else None,
                                         "status": (ce.get("status") + ("/gap" if ce.get("gap") else "")) if ce else "not in the store",
                                         "attested": att}
        out.append(w)
    return out


HEB_MOOD = {"JUSS": "SBJV", "COH": "SBJV"}
VERB_PARADIGMS = ("verb.subject", "verb.polarity")


def store_cell(G, par, bundle):
    """the store's cell for a source cell, with the Hebrew moods mapped: (entry, bundle used) or (None, bundle)"""
    ce = G.cell(par, bundle)
    if ce:
        return ce, bundle
    parts_ = bundle.split(".")
    if parts_[0] == "Q":                                      # a question's negation: the plain one
        parts_ = parts_[1:]
    b2 = ".".join(HEB_MOOD.get(x, x) for x in parts_)
    return G.cell(par, b2), b2


def marked(par, bundle):
    return bundle.startswith(("NEG", "Q.NEG")) if par == "verb.polarity" else not bundle.startswith("3.SG")


def pattern(ce):
    st = ce.get("stats", {})
    return (f"{ce.get('value') or '—'} ({ce.get('status')}{', gap' if ce.get('gap') else ''}"
            + (f"; {st['count']}×, {st['share']:.0%} of the cell's verbs" if "count" in st and "share" in st else "") + ")")


def grammar_block(pname, code, ch, top=4):
    G = grammar.load(pname)
    if not G.cells:
        return [], {}
    nt = BY_CODE[code][2] == "nt"
    head = ["Verb marking (the store's paradigm cells; a share is how often the corpus's verbs of the cell show the "
            "pattern, so a pattern is a tendency, not a rule; on held-out books the marked cells' patterns show far more "
            "in their cell than elsewhere, the defaults (-m) everywhere):", ""]
    for par in VERB_PARADIGMS:
        cells = G.paradigm(par)
        if cells:
            head.append(f"- {par}: " + "; ".join(f"{b} {cells[b].get('value') or '—'}" + (" (open)" if cells[b].get("status") == "open" else "")
                                                for b in sorted(cells)))
    head.append("")
    L = Lexicon(pname, exclude={code}) if nt else None
    db = sqlite3.connect(os.path.join(ROOT, "orig", "grc.sqlite" if nt else "heb.sqlite"))
    gloss = dict(db.execute("select key, gloss from tokens where book = ? and ch = ?", (code.upper(), ch)))
    verses = collections.defaultdict(list)
    keys = db.execute("select key, v from tokens where book = ? and ch = ? order by key", (code.upper(), ch)).fetchall()
    toks = SC.cells_of(code.upper(), "nt" if nt else "ot")
    for key, v in keys:
        t = toks.get(key)
        if not t:
            continue
        rows = []
        for par, bundle in t.cells:
            if par not in VERB_PARADIGMS or not marked(par, bundle):
                continue
            ce, used = store_cell(G, par, bundle)
            rows.append(f"{par.split('.')[1]} {bundle}" + (f" (as {used})" if used != bundle else "") + ": "
                        + (pattern(ce) if ce else "not in the store"))
        if rows:
            forms = ""
            if L:
                fs = L.forms.get(t.lemma, collections.Counter()).most_common(top)
                forms = "; forms of the lemma: " + ", ".join(f"{f} {n}" for f, n in fs) if fs else ""
            line = f"- {t.text} ({(gloss.get(key) or '').replace('.', ' ')}): " + "; ".join(rows) + forms
            if line not in verses[v]:
                verses[v].append(line)
    return head, verses


def main(a):
    if len(a) < 3:
        print(__doc__); sys.exit(2)
    pname, code = a[0], a[1].lower()
    ch, v = (int(x) for x in a[2].split(":"))
    if BY_CODE[code][2] != "nt":
        sys.exit("NT verses for now (the occurrence index links Greek)")
    ex = a[a.index("--exclude") + 1].split(",") if "--exclude" in a else ()
    top = int(a[a.index("--top") + 1]) if "--top" in a else 5
    L = Lexicon(pname, ex)
    for w in analyse(pname, code, ch, v, L, top=top):
        if not w.forms and not w.cells:
            continue
        print(f"{w.surface} ({w.lemma}, {w.gloss}): " + ", ".join(f"{f} {n}" for f, n in w.forms))
        for (par, bundle), c in w.per_cell.items():
            att = ", ".join(f"{f} {n}" for f, n in c["attested"]) or "-"
            print(f"    {par} {bundle}: store {c['pattern'] or '-'} ({c['status']}); attested {att}")


if __name__ == "__main__":
    main(sys.argv[1:])
