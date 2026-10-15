#!/usr/bin/env python3
"""The project's target-language database (internal-docs plan, sections 14.1b and 15): export/<project>/_learn/lang.sqlite,
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
    python3 scripts/lang.py derive <project>                     the derived products (plan 14.2): d_* tables
    python3 scripts/lang.py report <project>                     their summary
    python3 scripts/lang.py stats <project>
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
create table if not exists nt_tokens(book text, ch int, v int, pos int, surface text, form text);
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
    for ref, code, key, _, text in P.corpus():
        if BY_CODE[code][2] != "nt":
            continue
        t = P.tok.tokens(text)
        toks[ref] = t
        con.executemany("insert into nt_tokens values(?,?,?,?,?,?)",
                        [(code.upper(), key[0], key[1], i, w, w.lower()) for i, w in enumerate(t)])
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
    con.executemany("insert or replace into meta values(?,?)", [("nt_basis", P.p["nt_basis"]), ("links", os.path.relpath(links, ROOT))])
    con.commit()
    n = con.execute("select count(*) from nt_tokens").fetchone()[0]
    linked = con.execute("select count(*) from (select distinct book, ch, v, pos from nt_links)").fetchone()[0]
    print(f"{pname}: {n} NT tokens, {linked} linked to a MACULA Greek token ({100 * linked / max(n, 1):.0f}%); "
          f"{len(rows)} links, {miss} on Greek tokens without a MACULA key (variants)")


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


# --- derived products (internal-docs plan, section 14.2) -------------------------------------------------------

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
CONNECTORS = ("καί", "δέ", "γάρ", "οὖν", "τότε", "ἀλλά", "ὅτι", "ἵνα", "ὡς", "ἰδού")
GREEK_LATIN = dict(zip("αβγδεζηθικλμνξοπρστυφχψως", ["a", "b", "g", "d", "e", "z", "e", "th", "i", "k", "l", "m", "n",
                                                     "x", "o", "p", "r", "s", "t", "u", "f", "ch", "ps", "o", "s"]))


def context(t):
    if t["class"] == "verb":
        return ".".join(x for x in (t["tense"], t["voice"], t["mood"], (t["person"] or "")[:1] + (t["number"] or "")[:1]) if x)
    if t["class"] in ("noun", "adj", "pron", "det"):
        return ".".join(x for x in (t["gcase"], (t["number"] or "")[:1]) if x)
    return ""


def latin(s):
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))
    return "".join(GREEK_LATIN.get(c, c) for c in s)


def derive(pname, quiet=False):
    import difflib, math
    P, con = connect(pname)
    con.row_factory = sqlite3.Row
    con.executescript(DERIVED)
    for t in ("d_renderings", "d_function", "d_affix", "d_order", "d_names", "d_letters", "d_formulas", "d_discourse", "d_gaps"):
        con.execute(f"delete from {t}")
    # every link with its Greek token and target form
    rows = con.execute("""select l.book, l.ch, l.v, l.pos, t.form, g.* from nt_links l
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
    # 3. affixes: hyphenated target tokens and word-final strings, against the Greek features of the linked token
    feats = ("person", "number", "tense", "mood", "gcase", "voice")
    base, joint, cnt_aff = collections.Counter(), collections.Counter(), collections.Counter()
    words_of = collections.defaultdict(set)  # an ending is an affix only if it ends several different words
    total = 0
    for r in rows:
        if r["class"] not in ("verb", "noun", "pron", "adj"):
            continue
        total += 1
        affs = {r["form"]} if r["form"].startswith("-") else {"-" + r["form"][-k:] for k in (1, 2, 3) if len(r["form"]) > k + 1}
        fv = {(f, r[f]) for f in feats if r[f]}
        for fvv in fv:
            base[fvv] += 1
        for a in affs:
            cnt_aff[a] += 1
            for fvv in fv:
                joint[(a, fvv)] += 1
                words_of[(a, fvv)].add(r["form"])
    out = []
    for (a, (f, val)), n in joint.items():
        if n >= 30 and cnt_aff[a] >= 50 and len(words_of[(a, (f, val))]) >= 5:
            rate = n / base[(f, val)]
            lift = rate / (cnt_aff[a] / total)
            if lift >= 1.5:
                out.append((a, f, val, n, rate, lift))
    con.executemany("insert into d_affix values(?,?,?,?,?,?)", out)
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
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "replace" and (i2 - i1) <= 2 and (j2 - j1) <= 3:
                let[(a[i1:i2], b[j1:j2])] += n
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
    for lex, n in con.execute("""select lexeme, count(*) from h.tokens where kind='c' and class in ('noun','verb','adj')
            and coalesce(type, '') <> 'proper' and lexeme is not null group by lexeme having count(*) >= 20""").fetchall():
        lemma, gloss = con.execute("""select lemma, coalesce(english, gloss) from h.tokens where lexeme=?
            group by lemma, coalesce(english, gloss) order by count(*) desc limit 1""", (lex,)).fetchone()
        eq = con.execute("select greekstrong, sum(n) from h.lxx where lexeme=? group by greekstrong order by 2 desc limit 3", (lex,)).fetchall()
        nt = sum(nt_by_strong.get(g.lstrip("0"), 0) + nt_by_strong.get(g, 0) for g, _ in eq)
        if nt < 3:
            gaps.append((lex, lemma, gloss, n, nt))
    con.executemany("insert into d_gaps values(?,?,?,?,?)", gaps)
    con.commit()
    if not quiet:
        for t in ("d_renderings", "d_function", "d_affix", "d_order", "d_names", "d_letters", "d_formulas", "d_discourse", "d_gaps"):
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
    for a, f, v, n, rate, lift in con.execute("select * from d_affix order by lift * min(n, 300) desc limit 16"):
        print(f"  {a} with {f}={v}: n {n}, lift {lift:.1f}")
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


def stats(pname):
    P, con = connect(pname)
    for t in ("nt_tokens", "nt_links"):
        print(t, con.execute(f"select count(*) from {t}").fetchone()[0])
    print(con.execute("select * from meta").fetchall())


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
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
