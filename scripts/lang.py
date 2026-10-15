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
    elif a[0] == "stats":
        stats(a[1])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
