#!/usr/bin/env python3
"""Measure a draft against the style of the human translations in the target language, and show what to
change (docs/onboarding.md). Nothing here knows a language: every figure comes from the corpus.

How a draft is judged:
  - Expected values. Each draft verse is compared with the 30 corpus verses whose assisting text (BSB) is
    most like it (rare shared words weigh more), never from the drafted book. What the human translators wrote
    in those verses gives the expected count of every frequent word and word pair, and the expected shape
    (words per BSB word, sentences per BSB sentence). A story about women may say "woman" often; a chapter
    full of dialogue may say "you" often.
  - Human spread. The same is done for every chapter of the corpus, as if it were a draft: how far do the
    human translators' own chapters stray from what their other books predict? (`calibrate`; cached in
    _learn/style_norms*.json, rebuilt when the corpus changes.) A draft is flagged only where it strays further
    than 95% of the human chapters, and the count is large enough to mean something (Poisson |z| >= 2,
    4 or more expected or seen). Further than 80% (|z| >= 1.5) is listed under Watch.
  - Style items only: words and pairs that occur in most books of the corpus (names and topic words don't)
    and are not simply the rendering of one English content word.

For each flag the report gives the draft's verses to look at, and from the human verses most like them what
the translators wrote. Word forms found nowhere in the corpus are listed too (built or invented: check each).

Usage: python3 scripts/style.py <project> <draft> [<draft> ...] [--brief] [--out FILE]
       python3 scripts/style.py <project> --calibrate [--exclude CODES]
       --brief   the flags only (for a drafting or revising agent)
"""
import collections, json, math, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import langtools as LT  # noqa: E402
import vrs  # noqa: E402
from books import BY_CODE  # noqa: E402

K = 30
COMMON_ENG = set("the a an of to and in that it is was for on with as his he her she they them their be by at "
                 "from this not but have had were are you your i me my we us our will all which who so said "
                 "him then there when what one no do did would been has into up out if".split())
SHAPE = ("words per BSB word", "sentences per BSB sentence", "marks per 100 words")


def sentences(v):
    return [s for s in re.split(r"(?<=[.!?;])[”’\"»«)]*\s+", v) if re.search(r"\w", s)]


def marks(v):
    return sum(1 for c in unicodedata.normalize("NFD", v) if unicodedata.combining(c))


class Verses:
    """Counts over verses [(ref, book, chapter, assisting text, target text)]."""

    def __init__(self, P, rows):
        self.rows = rows
        self.toks = [P.tok.tokens(r[4]) for r in rows]
        self.eng = [set(LT.eng_tokens(r[3])) for r in rows]
        self.items = [collections.Counter(ts) + collections.Counter(" ".join(b) for b in zip(ts, ts[1:])) for ts in self.toks]
        self.shape = [(len(ts), len(LT.eng_tokens(r[3])), len(sentences(r[4])), len(sentences(r[3])) or 1, marks(r[4]))
                      for ts, r in zip(self.toks, rows)]


class Index:
    """BSB-text similarity over the corpus verses: tf-idf cosine over all words (so "you" and "said" count, and
    a dialogue verse finds dialogue verses), proper names left out (they would match by story, not by style)."""

    def __init__(self, C):
        import numpy as np
        from scipy import sparse
        self.np, self.C = np, C
        caps, alls = collections.Counter(), collections.Counter()
        for r in C.rows:
            for m in re.finditer(r"(?<![.!?“‘\"]\s)(?<!^)\b([A-Za-z]+)", r[3]):
                alls[m[1].lower()] += 1
                caps[m[1].lower()] += m[1][0].isupper()
        self.names = {w for w, n in alls.items() if n >= 2 and caps[w] / n > 0.8}
        self.vocab = {}
        for s_ in C.eng:
            for w in s_:
                if w not in self.names:
                    self.vocab.setdefault(w, len(self.vocab))
        df = collections.Counter(w for s_ in C.eng for w in s_)
        self.idf = {w: math.log(len(C.eng) / (1 + df[w])) + 1 for w in self.vocab}
        self.M = self.matrix(C.eng).T.tocsc()
        self.book = np.array([r[1] for r in C.rows])

    def matrix(self, sets):
        from scipy import sparse
        rows, cols, vals = [], [], []
        for i, s_ in enumerate(sets):
            ws = [w for w in s_ if w in self.vocab]
            norm = math.sqrt(sum(self.idf[w] ** 2 for w in ws)) or 1
            for w in ws:
                rows.append(i); cols.append(self.vocab[w]); vals.append(self.idf[w] / norm)
        return sparse.csr_matrix((vals, (rows, cols)), shape=(len(sets), len(self.vocab)), dtype="float32")

    def near_many(self, sets, not_book):
        np = self.np
        S = (self.matrix(sets) @ self.M).toarray()
        S[:, self.book == not_book] = -1
        top = np.argpartition(-S, K, axis=1)[:, :K]
        return [list(t[np.argsort(-S[i, t])]) for i, t in enumerate(top)]

    def near(self, eng, not_book):
        return self.near_many([eng], not_book)[0]


def expected(C, near_lists, items):
    """Expected item counts and shape for a unit of verses, from each verse's neighbours."""
    exp = collections.Counter()
    sh = [0.0, 0.0]                                   # expected words, expected sentences
    for i_tok, i_eng, i_bsent, ns in near_lists:
        words = sum(C.shape[j][0] for j in ns) or 1
        eng = sum(C.shape[j][1] for j in ns) or 1
        bs = sum(C.shape[j][3] for j in ns) or 1
        sents = sum(C.shape[j][2] for j in ns)
        cnt = collections.Counter()
        for j in ns:
            cnt.update({it: C.items[j][it] for it in items if it in C.items[j]})
        for it in items:
            exp[it] += cnt[it] / words * i_tok
        sh[0] += words / eng * i_eng
        sh[1] += sents / bs * i_bsent
    return exp, sh


def lr(obs, exp):
    return math.log((obs + 1) / (exp + 1))


def pick_items(P, C):
    """Style items of the corpus: frequent, in most books, not the rendering of one English content word."""
    uni = collections.Counter(t for ts in C.toks for t in ts)
    bi = collections.Counter(" ".join(b) for ts in C.toks for b in zip(ts, ts[1:]))
    cand = [w for w, _ in uni.most_common(150)] + [b for b, n in bi.most_common(120) if n >= 20]
    books = collections.defaultdict(set)
    for r, its in zip(C.rows, C.items):
        books[r[1]].update(its)
    big = [c for c in books if sum(1 for r in C.rows if r[1] == c) >= 20]
    edf = collections.Counter(w for s in C.eng for w in s)
    out = []
    for it in cand:
        if sum(1 for c in big if it in books[c]) < 0.6 * len(big):
            continue
        have = [i for i, its in enumerate(C.items) if it in its]
        co = collections.Counter(w for i in have for w in C.eng[i] if w not in COMMON_ENG)
        best = max((min(k / len(have), k / edf[w]) for w, k in co.items() if edf[w] >= 5), default=0)
        if best < 0.35:
            out.append(it)
    return out


def corpus_side(P, exclude=()):
    rows = [(r[0], r[1], r[2][0], r[3], r[4]) for r in P.corpus(exclude=set(exclude)) if r[3] and r[4]]
    return Verses(P, rows)


def calibrate(P, exclude=()):
    C = corpus_side(P, exclude)
    idx = Index(C)
    items = pick_items(P, C)
    units = collections.defaultdict(list)
    for i, r in enumerate(C.rows):
        units[(r[1], r[2])].append(i)
    per_item = collections.defaultdict(list)
    shape = collections.defaultdict(list)
    for (book, ch), vs in units.items():
        if len(vs) < 8:
            continue
        nn = idx.near_many([C.eng[i] for i in vs], book)
        nl = [(C.shape[i][0], C.shape[i][1], C.shape[i][3], n_) for i, n_ in zip(vs, nn)]
        exp, sh = expected(C, nl, items)
        obs = collections.Counter()
        for i in vs:
            obs.update({it: C.items[i][it] for it in items if it in C.items[i]})
        for it in items:
            per_item[it].append(lr(obs[it], exp[it]))
        words = sum(C.shape[i][0] for i in vs) or 1
        shape[SHAPE[0]].append(math.log(words / max(sh[0], 1)))
        shape[SHAPE[1]].append(math.log(max(sum(C.shape[i][2] for i in vs), 1) / max(sh[1], 1)))
        shape[SHAPE[2]].append(100 * sum(C.shape[i][4] for i in vs) / words)

    def band(xs):
        xs = sorted(xs)
        q = lambda p: xs[min(len(xs) - 1, max(0, int(round(p * (len(xs) - 1)))))]
        return {"lo": q(0.025), "p10": q(0.1), "mid": q(0.5), "p90": q(0.9), "hi": q(0.975), "n": len(xs)}
    norms = {"books": sorted({r[1] for r in C.rows}), "verses": len(C.rows), "excluded": sorted(exclude), "k": K,
             "items": {it: band(v) for it, v in per_item.items()}, "shape": {k: band(v) for k, v in shape.items()}}
    f = norms_file(P, exclude)
    json.dump(norms, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    return norms, f


def norms_file(P, exclude):
    os.makedirs(P.learn, exist_ok=True)
    return os.path.join(P.learn, "style_norms" + ("-no-" + "-".join(sorted(exclude)) if exclude else "") + ".json")


def get_norms(P, code):
    """Norms with the drafted book left out when the corpus has it (so its human text can't set the bands)."""
    books = {r[1] for r in P.corpus()}
    exclude = (code,) if code in books else ()
    f = norms_file(P, exclude)
    if os.path.exists(f):
        n = json.load(open(f, encoding="utf-8"))
        if n["verses"] == len([r for r in P.corpus(exclude=set(exclude)) if r[3] and r[4]]) and n.get("k") == K:
            return n
    print(f"building {os.path.relpath(f, ROOT)} (once per corpus) …", file=sys.stderr)
    return calibrate(P, exclude)[0]


def load_draft(P, paths):
    rows = []
    for p in paths:
        code = os.path.basename(p)[:3]
        ot = BY_CODE[code][2] != "nt"
        for key, t in sorted(LT.verses_of(p).items()):
            c, v = vrs.to_bsb(code, *key) if ot else key
            f = os.path.join(ROOT, P.assist_dir(code), f"{code}{c:03d}.txt")
            e = LT.verses_of(f).get((c, v), "") if os.path.exists(f) else ""
            rows.append((f"{code.upper()} {key[0]}:{key[1]}", code, key[0], e, t))
    return Verses(P, rows), code


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    P = LT.Project(a[0])
    if "--calibrate" in a:
        ex = a[a.index("--exclude") + 1].split(",") if "--exclude" in a else ()
        n, f = calibrate(P, ex)
        print(f"{os.path.relpath(f, ROOT)}: {len(n['items'])} style items, {n['items'] and next(iter(n['items'].values()))['n']} "
              f"human chapters, {len(n['books'])} books")
        return
    drafts = [x for i, x in enumerate(a[1:], 1) if not x.startswith("--") and a[i - 1] != "--out"]
    D, code = load_draft(P, drafts)
    norms = get_norms(P, code)
    C = corpus_side(P, (code,))
    idx = Index(C)
    items = list(norms["items"])
    label = (P.p.get("language_name") or "target").split(" (")[0]
    brief = "--brief" in a
    near = idx.near_many(D.eng, code)
    nl = [(D.shape[i][0], D.shape[i][1], D.shape[i][3], near[i]) for i in range(len(D.rows))]
    exp, sh = expected(C, nl, items)
    obs = collections.Counter()
    for its in D.items:
        obs.update({it: its[it] for it in items if it in its})
    words = sum(s[0] for s in D.shape) or 1

    L = [f"# Style check: {', '.join(os.path.basename(d) for d in drafts)}", "",
         f"Measured against the human {label} text ({len(norms['books'])} books, {norms['verses']} verses; "
         f"{code.upper()} left out). Draft: {len(D.rows)} verses, {words} words. A flag means the draft strays further "
         f"than 95% of the human chapters do.", ""]

    # shape
    sobs = {SHAPE[0]: math.log(words / max(sh[0], 1)),
            SHAPE[1]: math.log(max(sum(s[2] for s in D.shape), 1) / max(sh[1], 1)),
            SHAPE[2]: 100 * sum(s[4] for s in D.shape) / words}
    sflags = []
    for k, v in sobs.items():
        b = norms["shape"][k]
        if not b["lo"] <= v <= b["hi"]:
            sflags.append(k)
    show = lambda k, v: f"{v:.1f}" if k == SHAPE[2] else f"{math.exp(v):.2f}x"
    if not brief:
        L += ["## Shape", "", "| | draft | human chapters: middle | 95% range |", "|---|---|---|---|"]
        for k, v in sobs.items():
            b = norms["shape"][k]
            L.append(f"| {k}{' (against expected)' if k != SHAPE[2] else ''} | {show(k, v)}{' **flag**' if k in sflags else ''} | "
                     f"{show(k, b['mid'])} | {show(k, b['lo'])} – {show(k, b['hi'])} |")
        L.append("")

    # items
    flags, watch = [], []
    for it in items:
        o, e, b = obs[it], exp[it], norms["items"][it]
        r = lr(o, e)
        z = (o - e) / math.sqrt(max(e, 1))
        if max(o, e) >= 4 and abs(z) >= 2 and not b["lo"] <= r <= b["hi"]:
            flags.append((it, o, e, "more" if o > e else "fewer", (r - b["hi"]) if r > b["hi"] else (b["lo"] - r)))
        elif max(o, e) >= 4 and abs(z) >= 1.5 and not b.get("p10", b["lo"]) <= r <= b.get("p90", b["hi"]):
            watch.append((it, o, e, "more" if o > e else "fewer"))
    pairs = [f for f in flags if " " in f[0]]
    flags = [f for f in flags if " " in f[0] or not any(f[0] in p[0].split() and f[3] == p[3] for p in pairs)]
    flags.sort(key=lambda f: -f[4] * math.sqrt(max(f[1], f[2])))

    L += ["## Flags", ""]
    if not flags and not sflags:
        L += ["None: the draft is within the human translators' range.", ""]
    for k in sflags:
        b = norms["shape"][k]
        L.append(f"- **{k}**: {show(k, sobs[k])}; human chapters {show(k, b['lo'])} – {show(k, b['hi'])}"
                 + (" (fewer marks: copy them from the model verses)" if k == SHAPE[2] and sobs[k] < b["lo"] else
                    " (shorter sentences than the translators write: join some)" if k == SHAPE[1] and sobs[k] > b["hi"] else
                    " (longer sentences: split some)" if k == SHAPE[1] else ""))
    if sflags:
        L.append("")
    for it, o, e, f, _ in flags[:10]:
        L += [f"### *{it}*: {o} in the draft, about {e:.0f} expected ({'more' if f == 'more' else 'fewer'} than the human translators)", ""]
        if f == "more":
            vs = sorted(((D.items[i][it], i) for i in range(len(D.rows)) if it in D.items[i]), reverse=True)
            L.append(f"- draft verses with it: {', '.join(D.rows[i][0] + (f' ×{n}' if n > 1 else '') for n, i in vs[:24])}"
                     f"{' …' if len(vs) > 24 else ''}")
            ex = []
            for _, i in vs:
                for j in near[i]:
                    if it not in C.items[j] and j not in ex:
                        ex.append(j)
                        break
                if len(ex) == 3:
                    break
            if ex:
                L.append(f"- what the translators wrote in verses like these, without *{it}*:")
        else:
            gap = []
            for i in range(len(D.rows)):
                if it not in D.items[i]:
                    share = sum(1 for j in near[i] if it in C.items[j]) / len(near[i])
                    gap.append((share, i))
            gap.sort(reverse=True)
            L.append(f"- draft verses where the human verses most like them often have it: "
                     f"{', '.join(f'{D.rows[i][0]} ({s:.0%})' for s, i in gap[:12])}")
            ex = []
            for _, i in gap:
                for j in near[i]:
                    if it in C.items[j] and j not in ex:
                        ex.append(j)
                        break
                if len(ex) == 3:
                    break
            L.append(f"- the translators with *{it}* in verses like these:")
        L += [f"  - {C.rows[j][0]} BSB: {C.rows[j][3]}\n    {label}: {C.rows[j][4]}" for j in ex]
        L.append("")

    if watch:
        L += ["## Watch", "", "Further than 80% of the human chapters (weaker signs; look at them if the verse allows):", "",
              ", ".join(f"*{it}* {o} for about {e:.0f} ({f})" for it, o, e, f in sorted(watch, key=lambda w: -abs(w[1] - w[2]))), ""]

    # unknown forms
    known = {t for ts in C.toks for t in ts}
    new = collections.Counter(t for ts in D.toks for t in ts if t not in known and not t.startswith("-"))
    L += ["## Word forms found nowhere in the corpus", "",
          (f"{len(new)} forms ({sum(new.values())} tokens, {100 * sum(new.values()) / words:.1f}% of the draft). Names and "
           "built forms are expected; each should follow a pattern the corpus shows: "
           + ", ".join(w + (f" ×{n}" if n > 1 else "") for w, n in new.most_common(60))) if new else "None.", ""]

    if not brief:
        L += ["## Style items", "", "Per 1000 words; expected from the human verses most like the draft's; the range is "
              "the human chapters' 95% range of draft/expected.", "",
              "| item | draft | expected | human range | |", "|---|---|---|---|---|"]
        fl = {f[0] for f in flags}
        for it in sorted(items, key=lambda x: -exp[x])[:80]:
            b = norms["items"][it]
            L.append(f"| {it} | {obs[it] * 1000 / words:.1f} | {exp[it] * 1000 / words:.1f} | "
                     f"{math.exp(b['lo']):.2f}x – {math.exp(b['hi']):.2f}x | {'flag' if it in fl else ''} |")
        L.append("")
    text = "\n".join(L)
    if "--out" in a:
        f = a[a.index("--out") + 1]
        open(f, "w", encoding="utf-8").write(text + "\n")
        print(f"{f}: {len(sflags)} shape flags, {len(flags)} word flags, {len(watch)} to watch, {len(new)} new forms")
    else:
        print(text)


if __name__ == "__main__":
    main()
