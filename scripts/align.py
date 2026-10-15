#!/usr/bin/env python3
"""Word alignment of a project's style corpus, for the drafting agents' lexicons (docs/proposals/language-toolkit/).

Sides (source -> target-language words):
  eng  the assisting translation (BSB / MSB), every book of the corpus
  hbo  MACULA Hebrew lexemes (hbo:NNNN, the bcv-commons scaffold API, cached in download/scaffold/), OT books
  grc  the NT Greek of the project's nt_basis (orig/grc or orig/grc-rp), accents removed, cut to 6 letters
Models: eflomal (Östling & Tiedemann 2016; GPL, used if the Python package `eflomal` is installed) or the
built-in IBM Model 2 with a diagonal prior (fast_align-style). Both directions, symmetrised by
intersection + grow-diag. Target words come from the project's tokeniser (scripts/langtools.py).

Writes export/<project>/_learn/:
  lexicon_eng.tsv, lexicon_grc.tsv   source, target, count, share (top 8 per source word)
  lexicon_hbo.tsv                    lexeme, lemma, gloss, target, count, share
  links_<side>.tsv                   ref, target token, source token: the symmetrised links of the OT books
  links_grc_pos.tsv                  ref, target position, source position: every NT link (the Greek side), for
                                     scripts/lang.py's occurrence index
  align_report.txt                   the checks: glossary terms, OT names (where the corpus has OT books)
Lexicons are statistics about the edition (words with counts), ours and CC0 for any edition (docs/licensing.md);
the links files list a verse's words in order and stay local (.gitignore). lexicon_hbo's lemmas and glosses are
MACULA Hebrew's (CC BY 4.0, credited in CREDITS.md).

Usage: python3 scripts/align.py <project> [--sides eng,hbo,grc] [--model eflomal|ibm2] [--iter N] [--out DIR]
"""
import collections, difflib, json, math, os, re, sys, tempfile, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import langtools as LT  # noqa: E402
from books import BY_CODE  # noqa: E402

GREEK = {"critical": "orig/grc", "majority": "orig/grc-rp", "tr": "orig/grc-rp"}


# --- models --------------------------------------------------------------------------------------

def ibm2_train(pairs, src_i, tgt_i, iters, tension=4.0, p0=0.08):
    """P(target word | source word) with a diagonal prior; the source side gets a NULL word."""
    t = collections.defaultdict(lambda: 1e-3)
    for _ in range(iters):
        counts, totals = collections.defaultdict(float), collections.defaultdict(float)
        for p in pairs:
            S, T = p[src_i], p[tgt_i]
            m, n = len(T), len(S)
            for j, tw in enumerate(T):
                ws = [p0 * t[(None, tw)]] + [(1 - p0) * t[(sw, tw)] * math.exp(-tension * abs(i / n - j / m))
                                             for i, sw in enumerate(S)]
                z = sum(ws) or 1e-12
                for i, w in enumerate(ws):
                    sw = None if i == 0 else S[i - 1]
                    counts[(sw, tw)] += w / z
                    totals[sw] += w / z
        t = collections.defaultdict(lambda: 1e-6, {k: v / totals[k[0]] for k, v in counts.items()})
    return t


def ibm2_viterbi(p, src_i, tgt_i, t, tension=4.0, p0=0.08):
    S, T = p[src_i], p[tgt_i]
    links, m, n = set(), len(T), len(S)
    for j, tw in enumerate(T):
        best, bi = p0 * t[(None, tw)], None
        for i, sw in enumerate(S):
            w = (1 - p0) * t[(sw, tw)] * math.exp(-tension * abs(i / n - j / m))
            if w > best:
                best, bi = w, i
        if bi is not None:
            links.add((bi, j))
    return links


def ibm2_links(pairs, iters):
    """[(fwd, rev)] per pair, both as sets of (source i, target j)."""
    tA, tB = ibm2_train(pairs, 0, 1, iters), ibm2_train(pairs, 1, 0, iters)
    return [(ibm2_viterbi(p, 0, 1, tA), {(i, j) for j, i in ibm2_viterbi(p, 1, 0, tB)}) for p in pairs]


def eflomal_links(pairs):
    import eflomal
    d = tempfile.mkdtemp()
    src, trg = os.path.join(d, "src"), os.path.join(d, "trg")
    open(src, "w", encoding="utf-8").write("".join(" ".join(p[0]) + "\n" for p in pairs))
    open(trg, "w", encoding="utf-8").write("".join(" ".join(p[1]) + "\n" for p in pairs))
    fwd, rev = os.path.join(d, "fwd"), os.path.join(d, "rev")
    with open(src, encoding="utf-8") as s, open(trg, encoding="utf-8") as t:
        eflomal.Aligner().align(s, t, links_filename_fwd=fwd, links_filename_rev=rev, quiet=True)
    read = lambda fn: [{tuple(map(int, x.split("-"))) for x in l.split()} for l in open(fn).read().splitlines()]
    return list(zip(read(fwd), read(rev)))          # pharaoh 'i-j' = source i, target j, in both files


def symmetrise(fwd, rev):
    """Intersection + grow-diag of two link sets of (source i, target j)."""
    a, union, added = fwd & rev, fwd | rev, True
    while added:
        added = False
        for (i, j) in sorted(union - a):
            if any((i + di, j + dj) in a for di in (-1, 0, 1) for dj in (-1, 0, 1)):
                if not any(x == i for x, _ in a) or not any(y == j for _, y in a):
                    a.add((i, j)); added = True
    return a


# --- corpora -------------------------------------------------------------------------------------

def grc_tokens(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c)).replace("ς", "σ")
    return [w[:6] for w in re.findall(r"[α-ω]+", s)]


def scaffold(code, ch):
    cache = os.path.join(ROOT, "download", "scaffold", code.upper(), f"{ch}.json")
    if not os.path.exists(cache):
        from fetch_heb_macula import fetch, BASE
        return fetch(code.upper(), ch, BASE)
    return json.load(open(cache, encoding="utf-8"))


def side_pairs(P, side):
    """[(source tokens, target tokens, ref, code)]"""
    out, greek = [], {}
    gl = collections.defaultdict(collections.Counter)
    lemma = {}
    heb = {}
    for ref, code, key, assist, text in P.corpus():
        ot = BY_CODE[code][2] != "nt"
        tgt = P.tok.tokens(text)
        if not tgt:
            continue
        if side == "eng":
            src = LT.eng_tokens(assist)
        elif side == "grc":
            if ot:
                continue
            f = os.path.join(ROOT, GREEK[P.p["nt_basis"]], f"{code}{key[0]:03d}.txt")
            if f not in greek:
                greek[f] = {}
                if os.path.exists(f):
                    for l in open(f, encoding="utf-8").read().splitlines()[1:]:
                        m = re.match(r"(\d+):(\d+) (.*)", l)
                        if m:
                            greek[f][(int(m[1]), int(m[2]))] = m[3]
            src = grc_tokens(greek[f].get(key, ""))
        else:
            if not ot:
                continue
            if (code, key[0]) not in heb:
                byv = collections.defaultdict(list)
                for t in scaffold(code, key[0])["tokens"]:
                    if t.get("lexeme"):
                        byv[t["verse"]].append(t["lexeme"])
                        gl[t["lexeme"]][(t.get("gloss") or "").strip("[]")] += 1
                        lemma[t["lexeme"]] = t.get("lemma") or ""
                heb[(code, key[0])] = byv
            src = heb[(code, key[0])].get(key[1], [])
        if src:
            out.append((src, tgt, ref, code))
    return out, gl, lemma


# --- main ----------------------------------------------------------------------------------------

def lexicon(pairs, links):
    lex, sym = collections.Counter(), []
    for p, (f, r) in zip(pairs, links):
        s = {(i, j) for i, j in symmetrise(f, r) if i < len(p[0]) and j < len(p[1])}
        sym.append(s)
        for i, j in s:
            lex[(p[0][i], p[1][j])] += 1
    by = collections.defaultdict(collections.Counter)
    for (s, t), c in lex.items():
        by[s][t] += c
    return by, sym


def glossary_check(P, by_eng):
    ok = tot = 0
    for row in P.glossary():
        if len(row) < 2:
            continue
        e = row[1].split(",")[0].strip().lower()
        if not re.fullmatch(r"[a-z]+", e) or e not in by_eng:
            continue
        term = (P.tok.tokens(row[0]) or [""])[0]
        top = [k for k, _ in by_eng[e].most_common() if not k.startswith("-")][:1]
        tot += 1
        ok += bool(top and top[0] == term)
    return ok, tot


def names_check(P, pairs, by_hbo, gl):
    """Hebrew proper nouns (capitalised gloss) -> is the top rendering the name in the edition's verses?"""
    verses = collections.defaultdict(list)
    for src, tgt, ref, code in pairs:
        for lx in set(src):
            verses[lx].append(tgt)
    ok = n = 0
    for lx, gls in gl.items():
        g = re.sub(r"^(of |to |from |in |the |and )+", "", gls.most_common(1)[0][0])
        if not g[:1].isupper() or g in ("LORD", "God") or lx not in by_hbo:
            continue
        cands = collections.Counter(t for v in verses[lx] for t in v)
        gold = max(cands, key=lambda w: (difflib.SequenceMatcher(None, w, g.lower()).ratio(), cands[w]), default=None)
        if not gold or difflib.SequenceMatcher(None, gold, g.lower()).ratio() < 0.6:
            continue
        n += 1
        ok += by_hbo[lx].most_common(1)[0][0] == gold
    return ok, n


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    P = LT.Project(a[0])
    sides = (a[a.index("--sides") + 1] if "--sides" in a else "eng,hbo,grc").split(",")
    iters = int(a[a.index("--iter") + 1]) if "--iter" in a else 6
    model = a[a.index("--model") + 1] if "--model" in a else None
    if model in (None, "eflomal"):
        try:
            import eflomal  # noqa: F401
            model = "eflomal"
        except ImportError:
            if model == "eflomal":
                raise SystemExit("eflomal is not installed (docs/proposals/language-toolkit/README.md: External tools)")
            model = "ibm2"
    if "--out" in a:
        P.learn = os.path.abspath(a[a.index("--out") + 1])
    os.makedirs(P.learn, exist_ok=True)
    rep = [f"project {P.name}, model {model}, corpus {len(P.corpus())} verses"]
    for side in sides:
        pairs, gl, lemma = side_pairs(P, side)
        if not pairs:
            rep.append(f"{side}: no verse pairs")
            continue
        sp = [(p[0], p[1]) for p in pairs]
        links = eflomal_links(sp) if model == "eflomal" else ibm2_links(sp, iters)
        by, sym = lexicon(sp, links)
        with open(os.path.join(P.learn, f"lexicon_{side}.tsv"), "w", encoding="utf-8") as fh:
            fh.write(("lexeme\tlemma\tgloss\t" if side == "hbo" else "source\t") + "target\tcount\tshare\n")
            for s in sorted(by, key=lambda s: -sum(by[s].values())):
                tot = sum(by[s].values())
                pre = f"{s}\t{lemma.get(s, '')}\t{'; '.join(x for x, _ in gl[s].most_common(3))}" if side == "hbo" else s
                for t, c in by[s].most_common(8):
                    fh.write(f"{pre}\t{t}\t{c}\t{c / tot:.2f}\n")
        ot = [(p, s) for p, s in zip(pairs, sym) if BY_CODE[p[3]][2] != "nt"]
        if ot:
            with open(os.path.join(P.learn, f"links_{side}.tsv"), "w", encoding="utf-8") as fh:
                fh.write("ref\ttarget\tsource\n")
                for p, s in ot:
                    for i, j in sorted(s, key=lambda x: x[1]):
                        fh.write(f"{p[2]}\t{p[1][j]}\t{p[0][i]}\n")
        if side == "grc":  # every NT link by position, for the occurrence index (scripts/lang.py: positions -> MACULA keys)
            with open(os.path.join(P.learn, "links_grc_pos.tsv"), "w", encoding="utf-8") as fh:
                fh.write(f"# nt_basis {P.p['nt_basis']}: source positions in {GREEK[P.p['nt_basis']]} (letters only), "
                         "target positions in the project's tokens\nref\ttarget_pos\tsource_pos\n")
                for p, s in zip(pairs, sym):
                    for i, j in sorted(s, key=lambda x: (x[1], x[0])):
                        fh.write(f"{p[2]}\t{j}\t{i}\n")
        rep.append(f"{side}: {len(pairs)} verse pairs, {len(by)} source words")
        if side == "eng":
            ok, tot = glossary_check(P, by)
            if tot:
                rep.append(f"  glossary: the term is the top rendering of its one-word English equivalent in {ok} of {tot}")
        if side == "hbo":
            ok, n = names_check(P, pairs, by, gl)
            if n:
                rep.append(f"  names: the top rendering of a Hebrew name is the edition's name in {ok} of {n}")
    open(os.path.join(P.learn, "align_report.txt"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
