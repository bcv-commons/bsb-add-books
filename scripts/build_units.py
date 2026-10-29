#!/usr/bin/env python3
"""Translation units of the style corpus: English (the assisting verse) <-> target groups, many-to-one and many-to-many,
from the word links and, in the NT, the Greek route, for the verse packs' lexicon (docs/onboarding.md).

Two kinds of English <-> target links:
  core  align.py's English links (export/<project>/_learn/links_eng_pos.tsv), every verse;
  grc   through the Greek, NT verses with the BSB as the assisting text: the BSB tables (orig/grc.sqlite `bsb`: the
        English words of each MACULA Greek word) joined with the target <-> Greek links of the language DB
        (lang.py build: eflomal and the bcv-commons layers).
Merged by --mode (default grc):
  grc    the Greek route first; a core link only where neither its English word nor its target word has a Greek one;
  fill   core first; a Greek link only where its English or target word has no core link;
  agree  core and the Greek links, without a Greek link that joins two different core units;
  union  both.
A unit is a connected group of links in a verse: English words <-> target words (the sea <-> di sii).

Writes export/<project>/_learn/ (local, like the links: a verse's words in order):
  units_eng.tsv          ref, English positions, English words, target positions, target words, kind (core|grc|both)
  lexicon_units.tsv      source, target, count, share: lexicon_eng.tsv's format, from the merged links (top 8), for
                         verse_pack.py --lexicon units (on trial)
In the packs the units' lexicon covers fewer words than lexicon_eng.tsv (Zinza, Genesis 1-5: 243 words left to search
with --mode fill, 272 with grc, against 227): a Greek word's English and target spans multiply, and fewer renderings
reach the pack's share. So the packs keep lexicon_eng.tsv; the units are for reading a verse's groups and for tests.

Usage: python3 scripts/build_units.py <project> [--mode grc|fill|agree|union]
"""
import collections, os, re, sqlite3, sys

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
import langtools as LT  # noqa: E402
import full_align as FA  # noqa: E402
from books import BY_CODE  # noqa: E402

MODES = ("grc", "fill", "agree", "union")


def read_links(f):
    """{ref: {(source pos, target pos)}} of a links_*_pos.tsv"""
    L = collections.defaultdict(set)
    for l in open(f, encoding="utf-8"):
        x = l.rstrip("\n").split("\t")
        if l.startswith("#") or x[0] == "ref" or len(x) < 3:
            continue
        L[x[0]].add((int(x[2]), int(x[1])))
    return L


def compact_to_eng(text):
    """{compact-alignments token position: langtools.eng_tokens position} of an English verse (john's: one eng token)"""
    E = LT.eng_tokens(text)
    C = [w.lower().replace("’", "'") for w in FA.tokenize(text)]
    m, j = {}, 0
    for i, w in enumerate(E):
        for p in re.findall(r"[a-z]+", w):
            while j < len(C) and C[j] != p:
                j += 1
            if j < len(C):
                m[j] = i
                j += 1
    return m


def greek_route(P):
    """{ref: {(English pos, target pos)}} through the Greek, for NT verses whose assisting text is the BSB"""
    dbf = os.path.join(P.learn, "lang.sqlite")
    gf = os.path.join(ROOT, "orig", "grc.sqlite")
    if not (os.path.exists(dbf) and os.path.exists(gf)):
        return {}, "no Greek route (needs orig/grc.sqlite and lang.py build)"
    bsb = os.path.join(ROOT, "reference", "BSB")
    tgt = collections.defaultdict(lambda: collections.defaultdict(set))       # ref -> MACULA key -> {target pos}
    for b, c, v, pos, key in sqlite3.connect(dbf).execute("select book, ch, v, pos, key from nt_links"):
        tgt[f"{b} {c}:{v}"][key].add(pos)
    g = sqlite3.connect(gf)
    R, skipped = {}, set()
    for ref, code, key, assist, text in P.corpus():
        if BY_CODE[code][2] != "nt" or ref not in tgt:
            continue
        if os.path.abspath(os.path.join(ROOT, P.assist_dir(code))) != os.path.abspath(bsb):
            skipped.add(code)                       # the BSB tables give positions in the BSB, not the MSB
            continue
        m = compact_to_eng(assist)
        keys = tgt[ref]
        s = set()
        for k, poss in g.execute("select key, positions from bsb where key in (%s)" % ",".join("?" * len(keys)),
                                 list(keys)):
            for bp in map(int, poss.split()):
                if bp in m:
                    s |= {(m[bp], t) for t in keys[k]}
        R[ref] = s
    return R, (f"Greek route skipped for {len(skipped)} books with the MSB as the assisting text" if skipped else "")


class Groups:
    """union-find over ('e', i) and ('t', j)"""

    def __init__(self, links):
        self.par = {}
        for i, j in links:
            self.par[self.find(("e", i))] = self.find(("t", j))

    def find(self, x):
        while self.par.setdefault(x, x) != x:
            x = self.par[x]
        return x


def merge(C, G, mode):
    le, lt = {i for i, _ in C}, {j for _, j in C}
    if mode == "union":
        return C | G
    if mode == "fill":
        return C | {(i, j) for i, j in G - C if i not in le or j not in lt}
    if mode == "grc":
        ge, gt = {i for i, _ in G}, {j for _, j in G}
        return G | {(i, j) for i, j in C if i not in ge and j not in gt}
    f = Groups(C).find
    return C | {(i, j) for i, j in G - C if not (i in le and j in lt and f(("e", i)) != f(("t", j)))}


def units(S):
    """[(English positions, target positions)] of a verse's links, by connected group"""
    f = Groups(S).find
    by = collections.defaultdict(lambda: (set(), set()))
    for i, j in S:
        r = f(("e", i))
        by[r][0].add(i)
        by[r][1].add(j)
    return sorted(((sorted(e), sorted(t)) for e, t in by.values()), key=lambda u: (u[1], u[0]))


def span(words, pos):
    """the words at pos in order, a gap as …"""
    out = []
    for k, p in enumerate(pos):
        if k and p != pos[k - 1] + 1:
            out.append("…")
        out.append(words[p])
    return " ".join(out)


def build(pname, mode="grc"):
    P = LT.Project(pname)
    lf = os.path.join(P.learn, "links_eng_pos.tsv")
    if not os.path.exists(lf):
        raise SystemExit(f"{lf} is missing: run python3 scripts/align.py {pname} --sides eng first")
    core = read_links(lf)
    route, note = greek_route(P)
    lex = collections.defaultdict(collections.Counter)
    n, cov = collections.Counter(), collections.Counter()
    with open(os.path.join(P.learn, "units_eng.tsv"), "w", encoding="utf-8") as fh:
        fh.write(f"# mode {mode}: English (assisting verse, langtools.eng_tokens) <-> target (the project's tokens)\n"
                 "ref\teng_pos\teng\ttarget_pos\ttarget\tkind\n")
        for ref, code, key, assist, text in P.corpus():
            E, T = LT.eng_tokens(assist), P.tok.tokens(text)
            if not E or not T:
                continue
            C = {(i, j) for i, j in core.get(ref, ()) if i < len(E) and j < len(T)}
            G = {(i, j) for i, j in route.get(ref, ()) if i < len(E) and j < len(T)}
            S = merge(C, G, mode) if G else C
            cov["eng"] += len(E)
            cov["eng_linked"] += len({i for i, _ in S})
            cov["tgt"] += len(T)
            cov["tgt_linked"] += len({j for _, j in S})
            for e, t in units(S):
                ls = {(i, j) for i, j in S if i in e}
                kind = "both" if ls <= (C & G) else "core" if ls <= C else "grc" if ls <= G else "mixed"
                n[kind] += 1
                n["many"] += len(e) > 1 or len(t) > 1
                tw = span(T, t)
                fh.write(f"{ref}\t{','.join(map(str, e))}\t{span(E, e)}\t{','.join(map(str, t))}\t{tw}\t{kind}\n")
                for i, j in ls:
                    lex[E[i]][T[j]] += 1
    with open(os.path.join(P.learn, "lexicon_units.tsv"), "w", encoding="utf-8") as fh:
        fh.write("source\ttarget\tcount\tshare\n")
        for s in sorted(lex, key=lambda s: -sum(lex[s].values())):
            tot = sum(lex[s].values())
            for t, c in lex[s].most_common(8):
                fh.write(f"{s}\t{t}\t{c}\t{c / tot:.2f}\n")
    tot = sum(n[k] for k in ("both", "core", "grc", "mixed"))
    print(f"{pname}: {tot} units ({n['many']} not one-to-one; by link source: core {n['core']}, grc {n['grc']}, both "
          f"{n['both']}, mixed {n['mixed']}), mode {mode}, {len(route)} verses through the Greek; English words in a unit "
          f"{cov['eng_linked'] / max(cov['eng'], 1):.1%}, target words {cov['tgt_linked'] / max(cov['tgt'], 1):.1%}")
    if note:
        print(" ", note)
    print(f"  {os.path.join(P.learn, 'units_eng.tsv')}, lexicon_units.tsv")


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        raise SystemExit(__doc__)
    mode = a[a.index("--mode") + 1] if "--mode" in a else "grc"
    if mode not in MODES:
        raise SystemExit(f"--mode {mode}: one of {', '.join(MODES)}")
    build(a[0], mode)


if __name__ == "__main__":
    main()
