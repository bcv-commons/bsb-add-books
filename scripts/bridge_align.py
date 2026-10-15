#!/usr/bin/env python3
"""Align a prose draft to the Hebrew by script, with no model: a full word alignment (.align), and the clause lines
for both layouts derived from it (for the website). For drafts whose agents left no alignment.

The bridge, per verse:
  Hebrew token -> BSB words      the BSB Translation Tables (the BSB publisher's interlinear, CC0), as published by
                                 bcv-commons in full-alignments-manual (eng_BSB+manual+bsb-tables), compact format
  BSB word -> draft word         the project's lexicon (_learn/lexicon_eng.tsv, from its style corpus) and spelling
                                 likeness (names, numbers, cognates)
  Hebrew lexeme -> draft word    the project's Hebrew-side lexicon (_learn/lexicon_hbo.tsv) where it has one
  plus a position prior (the drafts follow the Hebrew order closely).
Each draft word links to its best Hebrew token if the evidence reaches a threshold.

Writes <code>NNN.align next to the draft (or into --out DIR): the full alignment in the bcv-commons format
(scripts/full_align.py), profile a = this script.

Clause lines (clauses()): never stored. scripts/build_site.py derives them at build time from the draft, its .align
and the local layout files (orig/heb-bhsa, orig/heb-bcv-query; never published): a monotone split of each verse's
words over the layout's lines, with the saved links as evidence and cut bonuses at punctuation and conjunctions; a
line that gets no words is a merge ('//N ='). The text stays the draft's (scripts/clause_lines.py check).

Usage: python3 scripts/bridge_align.py <project> <code> <ch> [--out DIR] [--compare]
       python3 scripts/bridge_align.py <project> --all       every OT chapter of the project
       --compare: the derived clause lines against an agent's (export/<project>/_eval/local/clauses/, local only)
"""
import difflib, glob, json, os, re, sys, unicodedata, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from clause_sidecar import tokenize  # noqa: E402
import align as AL  # noqa: E402  (scaffold(): MACULA tokens per chapter, cached)
import vrs  # noqa: E402
import langtools as LT  # noqa: E402
import full_align as FULL  # noqa: E402  (the bcv-commons format: ordinals, strings, the working file)
from clause_lines import layout_rows, LAYOUTS  # noqa: E402

FA = os.path.join(ROOT, "download", "full-align")
HF = "https://huggingface.co/datasets/bcv-commons"
LAYER = "e/eng/eng_BSB+manual+bsb-tables"
UA = {"User-Agent": "bsb-add-books/1.0"}
TAU = 0.12          # least evidence for a word link
LINKED = 0.3        # the evidence of a saved link, when clause lines are derived from an .align
CONJ = ("and", "but", "for", "that", "when", "then", "because", "if", "so", "who", "which", "or")
NOTE = re.compile(r"\{[A-Z]:.*?\}", re.S)
MARK = re.compile(r"(?<![\w>.])v(\d+)(?=\s)")
OPENERS = "»„“‚‘›(>[\"'"


def get(url, path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        for attempt in range(4):  # Hugging Face drops a connection now and then
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                    data = r.read()
                break
            except OSError:
                if attempt == 3:
                    raise
        open(path + ".part", "wb").write(data)
        os.replace(path + ".part", path)
    return path


def tables(book):
    """{ref: {macula key: [BSB token positions]}} for one book, from the BSB Translation Tables layer."""
    idx = {k: json.load(open(get(f"{HF}/compact-alignments/resolve/main/_index/{book}_{k}.json",
                                 os.path.join(FA, "_index", f"{book}_{k}.json")), encoding="utf-8"))
           for k in ("lexemes", "keys", "fn_keys")}
    main = glob.glob(os.path.join(FA, f"{book}_*[!a].json"))
    main = [f for f in main if not f.endswith(".meta.json")]
    if not main:
        listing = json.load(urllib.request.urlopen(urllib.request.Request(
            f"https://huggingface.co/api/datasets/bcv-commons/full-alignments-manual/tree/main/{LAYER.replace('+', '%2B')}", headers=UA)))
        name = next(x["path"] for x in listing if os.path.basename(x["path"]).startswith(book + "_") and not x["path"].endswith(".meta.json"))
        for f in (name, name[:-5] + ".meta.json"):
            get(f"{HF}/full-alignments-manual/resolve/main/{f.replace('+', '%2B')}", os.path.join(FA, os.path.basename(f)))
        main = [os.path.join(FA, os.path.basename(name))]
    A = json.load(open(main[0], encoding="utf-8"))
    M = json.load(open(main[0][:-5] + ".meta.json", encoding="utf-8"))
    refs = list(idx["lexemes"].keys())
    out = {}

    def spans(s):
        for e in (s or "").split():
            o, _, sp = e.partition(":")
            if not sp or sp.startswith("@"):
                continue
            ids = []
            for part in sp.split(","):
                if "-" in part:
                    a, b = part.split("-")
                    ids += range(int(a), int(b) + 1)
                elif part.isdigit():
                    ids.append(int(part))
            yield int(o), ids
    for i, ref in enumerate(refs):
        d = out.setdefault(ref, {})
        for o, ids in spans(A[i] if i < len(A) else ""):
            for k in idx["keys"][ref][o].split("+"):
                d[k] = ids
        fn = (M.get("fn") or [])
        for o, ids in spans(fn[i] if i < len(fn) else ""):
            for k in idx["fn_keys"][ref][o].split("+"):
                d[k] = ids
    return out


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))


def sim(a, b):
    a, b = fold(a), fold(b)
    if len(a) < 3 or len(b) < 3:
        return 1.0 if a == b and a.isdigit() else 0.0
    r = difflib.SequenceMatcher(None, a, b).ratio()
    return r if r >= 0.78 else 0.0


def lexicon(path, key_cols):
    out = {}
    if os.path.exists(path):
        for l in open(path, encoding="utf-8").read().splitlines()[1:]:
            c = l.split("\t")
            k = tuple(c[i].lower() if i else c[i] for i in key_cols[0]) if False else None
            if key_cols == "eng":
                out[(c[0].lower(), c[1].lower())] = max(out.get((c[0].lower(), c[1].lower()), 0), float(c[3]))
            else:
                out[(c[0], c[3].lower())] = max(out.get((c[0], c[3].lower()), 0), float(c[5]))
    return out


def draft_verses(path):
    """(head lines, title line, [(verse, raw text, headings before)]) from a prose draft."""
    head, title, body = [], None, []
    for l in open(path, encoding="utf-8").read().splitlines():
        if l.startswith("!!<"):
            head.append(l)
        elif re.match(r"^===.*===\s*$", l) and title is None:
            title = l
        else:
            body.append(l)
    # a stream of text and headings
    stream, buf = [], []
    for l in body:
        if re.match(r"^==.*==\s*$", l):
            if buf:
                stream.append(("t", " ".join(buf)))
                buf = []
            stream.append(("h", l.strip()))
        elif l.strip():
            buf.append(l.strip())
        else:
            if buf:
                stream.append(("t", " ".join(buf)))
                buf = []
    if buf:
        stream.append(("t", " ".join(buf)))
    verses, pending = [], []
    for kind, t in stream:
        if kind == "h":
            pending.append(t)
            continue
        parts = MARK.split(t)
        if parts[0].strip() and verses:
            verses[-1][1] += " " + parts[0].strip()
        for i in range(1, len(parts) - 1, 2):
            verses.append([int(parts[i]), f"v{parts[i]} " + parts[i + 1].strip(), pending])
            pending = []
    return head, title, verses


def tokens_of(raw):
    """[(token, start, end)] of a verse's raw text: letter runs outside notes, the verse marker left out."""
    blank = list(raw)
    for m in NOTE.finditer(raw):
        for i in range(m.start(), m.end()):
            blank[i] = " "
    m = MARK.match(raw)
    if m:
        for i in range(m.start(), m.end()):
            blank[i] = " "
    s = "".join(blank)
    out, cur = [], None
    for i, ch in enumerate(s):
        if unicodedata.category(ch)[0] in ("L", "M"):
            if cur is None:
                cur = i
        elif cur is not None:
            out.append((s[cur:i], cur, i))
            cur = None
    if cur is not None:
        out.append((s[cur:], cur, len(s)))
    return out


def heb_cons(t):
    return re.sub(r"[^א-ת]", "", t)


def bhsa_segments(code, ch, verse, toks):
    """MACULA token key -> BHSA line index (within the verse), matched on the Hebrew consonants."""
    rows = [r for r in layout_rows(os.path.join(ROOT, LAYOUTS["bhsa"], f"{code}{ch:03d}.txt")) if r[0] == verse]
    bchars, bline = [], []
    for j, r in enumerate(rows):
        c = heb_cons(r[2])
        bchars += list(c)
        bline += [j] * len(c)
    mchars, mtok = [], []
    for t in toks:
        c = heb_cons(t["text"])
        mchars += list(c)
        mtok += [t["key"]] * len(c)
    sm = difflib.SequenceMatcher(None, mchars, bchars, autojunk=False)
    votes = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            votes.setdefault(mtok[blk.a + k], []).append(bline[blk.b + k])
    out, last = {}, 0
    for t in toks:
        v = votes.get(t["key"])
        last = max(set(v), key=v.count) if v else last
        out[t["key"]] = last
    return out, rows


def bcvq_segments(code, ch, verse):
    rows = json.load(open(os.path.join(ROOT, "orig", "heb-bcv-query-keys", f"{code}{ch:03d}.json"), encoding="utf-8"))
    segs = [r for r in rows if r["verse"] == verse]
    return {w: j for j, r in enumerate(segs) for w in r["words"]}, segs


def align_verse(D, H, bsb_tokens, links, lexE, lexH):
    """score[d][h] for draft tokens D and Hebrew tokens H; link d -> best h above TAU."""
    nd, nh = max(len(D), 1), max(len(H), 1)
    S = []
    for i, (w, _, _) in enumerate(D):
        lw = w.lower()
        row = []
        for j, h in enumerate(H):
            s = lexH.get((h["lexeme"], lw), 0.0)
            for b in links.get(h["key"], []):
                if b < len(bsb_tokens):
                    bw = bsb_tokens[b]
                    s = max(s, lexE.get((bw.lower(), lw), 0.0), 0.9 * sim(bw, w))
            pos = 1 - abs((i + 0.5) / nd - (j + 0.5) / nh)
            row.append(s * (0.55 + 0.45 * pos) + 0.04 * pos)
        S.append(row)
    link = []
    for i, row in enumerate(S):
        j = max(range(len(row)), key=row.__getitem__) if row else None
        link.append(j if j is not None and row[j] >= TAU else None)
    return S, link


def split_lines(D, raw, S, seg_of_h, nseg, cuts_after, conj):
    """Monotone labels: each draft token gets a line (0..nseg-1), non-decreasing; maximises the evidence per line
    plus cut bonuses (punctuation after the previous token, a conjunction starting the line)."""
    n = len(D)
    if n == 0:
        return []
    E = [[max([S[i][j] for j in range(len(S[i])) if seg_of_h[j] == s] or [0.0]) for s in range(nseg)] for i in range(n)]
    NEG = -1e9
    best = [[NEG] * nseg for _ in range(n)]
    back = [[0] * nseg for _ in range(n)]
    for s in range(nseg):
        best[0][s] = E[0][s] - 0.05 * s
    for i in range(1, n):
        cue = (0.7 if cuts_after[i - 1] else 0.0) + (0.35 if D[i][0].lower() in conj else 0.0)
        for s in range(nseg):
            stay = best[i - 1][s]
            move = max(((best[i - 1][t] + cue - 0.3 - 0.03 * (s - t - 1), t) for t in range(s)), default=(NEG, s))
            if stay >= move[0]:
                best[i][s], back[i][s] = stay + E[i][s], s
            else:
                best[i][s], back[i][s] = move[0] + E[i][s], move[1]
    s = max(range(nseg), key=lambda x: best[n - 1][x])
    lab = [0] * n
    for i in range(n - 1, -1, -1):
        lab[i] = s
        s = back[i][s]
    return lab


def lay_out_verse(code, ch, v, raw, headings, D, H, S, conj):
    """{layout: the verse's clause lines} from the evidence matrix S (draft tokens D x Hebrew tokens H)."""
    res = {}
    # cut cues: punctuation between token i and i+1
    cuts_after = [bool(re.search(r"[,.;:!?·)»«“”]", raw[D[i][2]:D[i + 1][1]])) for i in range(len(D) - 1)] + [True]
    for lay in LAYOUTS:
        if lay == "bhsa":
            seg_map, rows = bhsa_segments(code, ch, v, H)
            levels = [r[1] for r in rows]
        else:
            seg_map, rows = bcvq_segments(code, ch, v)
            lrows = [r for r in layout_rows(os.path.join(ROOT, LAYOUTS[lay], f"{code}{ch:03d}.txt")) if r[0] == v]
            levels = [r[1] for r in lrows]
        seg_of_h = [seg_map.get(h["key"], 0) for h in H]
        nseg = len(levels)
        lab = split_lines(D, raw, S, seg_of_h, nseg, cuts_after, conj) if D else []
        # the lines: raw text from the first token of each run (opening punctuation and the verse marker kept)
        starts = {}
        for i, s in enumerate(lab):
            starts.setdefault(s, i)
        out = [f"{h_}" for h_ in headings]
        used = sorted(starts)
        cut = {}
        for k, s in enumerate(used):
            if k == 0:
                cut[s] = 0
            else:
                p = D[starts[s]][1]
                q = p
                while q > 0 and not raw[q - 1].isspace():  # whole words only (het’s, Wo-n-er, »Gang)
                    q -= 1
                if q <= D[starts[used[k - 1]]][1]:  # the word began on the line above: cut after it instead
                    q = p
                    while q < len(raw) and not raw[q].isspace():
                        q += 1
                cut[s] = q
        ends = {s: (cut[used[k + 1]] if k + 1 < len(used) else len(raw)) for k, s in enumerate(used)}
        first_text = used[0] if used else None
        for s in range(nseg):
            if s in cut:
                out.append(f"//{levels[s] + 1} " + raw[cut[s]:ends[s]].strip())
            elif first_text is None or s < first_text:
                # nothing before the verse's first words: the marker line takes this place, the words follow later
                out.append(f"//{levels[s] + 1} =")
            else:
                out.append(f"//{levels[s] + 1} =")
        # a verse whose first line is a merge would lose its marker position: move the text up instead
        res[lay] = out
    return res


def clauses(pname, code, ch, linked=LINKED):
    """{layout: clause-line file lines} of a chapter, derived from its draft and its .align (what the website shows);
    None when the .align is missing or stale, or a layout file isn't here (setup.py --heb bhsa,bcv-query). Each
    saved link counts as evidence `linked` for its draft token; the cuts follow as in build()."""
    prose = os.path.join(ROOT, "export", pname, code, f"{code}{ch:03d}.txt")
    ap = prose[:-4] + ".align"
    if not os.path.exists(ap) or not all(os.path.exists(os.path.join(ROOT, LAYOUTS[l], f"{code}{ch:03d}.txt")) for l in LAYOUTS):
        return None
    head, title, verses = draft_verses(prose)
    h, rows = FULL.read_chapter(ap)
    if h != FULL.text_hash(ch, [(v, FULL.verse_text(raw)) for v, raw, _ in verses]):
        return None
    book = code.upper()
    P = LT.Project(pname)
    lexE = lexicon(os.path.join(P.learn, "lexicon_eng.tsv"), "eng")
    conj = {t for (e, t), sh in lexE.items() if e in CONJ and sh >= 0.08}
    sc = AL.scaffold(code, ch)["tokens"]
    keys = {k: FULL.index(book, k) for k in ("keys", "fn_keys")}
    files = {lay: head + ([title] if title else []) + ["", ""] for lay in LAYOUTS}
    for v, raw, headings in verses:
        H = sorted([t for t in sc if t["verse"] == v], key=lambda t: t["key"])
        col = {t["key"]: j for j, t in enumerate(H)}
        D = tokens_of(raw)
        S = [[0.0] * len(H) for _ in D]
        m, f, _ = rows.get(v, ("", "", "a"))
        ref = f"{book} {ch}:{v}"
        for kind, st in (("keys", m), ("fn_keys", f)):
            for o, ids in FULL.parse(st).items():
                for k in keys[kind][ref][o].split("+"):
                    if k in col:
                        for i in ids:
                            if i < len(D):
                                S[i][col[k]] = linked
        for lay, out in lay_out_verse(code, ch, v, raw, headings, D, H, S, conj).items():
            files[lay] += out
    return {lay: fix_leading_merges(files[lay]) for lay in LAYOUTS}


def build(pname, code, ch, out_dir=None):
    P = LT.Project(pname)
    book = code.upper()
    prose = os.path.join(ROOT, "export", pname, code, f"{code}{ch:03d}.txt")
    head, title, verses = draft_verses(prose)
    sc = AL.scaffold(code, ch)["tokens"]
    T = tables(book)
    lexE = lexicon(os.path.join(P.learn, "lexicon_eng.tsv"), "eng")
    lexH = lexicon(os.path.join(P.learn, "lexicon_hbo.tsv"), "hbo")
    conj = {t for (e, t), sh in lexE.items() if e in CONJ and sh >= 0.08}
    bsb_cache = {}
    align_rows, texts = [], []
    stats = {"tokens": 0, "linked": 0, "unplaced": 0}
    for v, raw, headings in verses:
        H = sorted([t for t in sc if t["verse"] == v], key=lambda t: t["key"])
        D = tokens_of(raw)
        c2, v2 = vrs.to_bsb(code, ch, v)
        af = os.path.join(ROOT, "reference", "BSB", f"{code}{c2:03d}.txt")
        if af not in bsb_cache:
            bsb_cache[af] = LT.verses_of(af)
        bsb_tokens = tokenize(bsb_cache[af].get((c2, v2), ""))
        S, link = align_verse(D, H, bsb_tokens, T.get(f"{book} {ch}:{v}", {}), lexE, lexH)
        stats["tokens"] += len(D)
        stats["linked"] += sum(1 for x in link if x is not None)
        # the .align row: content and function ordinals of the bcv-commons index -> draft token positions
        links = {}
        for i, j in enumerate(link):
            if j is not None:
                links.setdefault(H[j]["key"], []).append(i)
        m, f, miss = FULL.strings(links, FULL.ordinals(book, f"{book} {ch}:{v}"))
        stats["unplaced"] += len(miss)
        align_rows.append((v, m, f, "a"))
        texts.append((v, FULL.verse_text(raw)))
    d = out_dir
    paths = {}
    ap = os.path.join(d, f"{code}{ch:03d}.align") if d else os.path.join(ROOT, "export", pname, code, f"{code}{ch:03d}.align")
    os.makedirs(os.path.dirname(ap), exist_ok=True)
    FULL.write_chapter(ap, ch, align_rows, texts)
    paths["align"] = ap
    return paths, stats


def fix_leading_merges(lines):
    """A verse can't start with a merge line if its text comes later: the first text line's level stays, but the
    merge lines before it are fine for the format (the marker sits on the first text line). Only the chapter's very
    first clause line must hold text: if it is a merge, swap it with the first text line's text."""
    first = next((i for i, l in enumerate(lines) if l.startswith("//")), None)
    if first is not None and re.match(r"//\d+ =$", lines[first]):
        j = next((i for i in range(first, len(lines)) if lines[i].startswith("//") and not re.match(r"//\d+ =", lines[i])), None)
        if j is not None:
            lev_first = lines[first].split()[0]
            text = lines[j].split(" ", 1)[1]
            lines[first] = f"{lev_first} {text}"
            lines[j] = lines[j].split()[0] + " ="
    return lines


def labels_of(path, code, ch, layout):
    """Per verse: the line index (within the verse's layout lines) of each draft token, read from a clause file."""
    L = layout_rows(os.path.join(ROOT, LAYOUTS[layout], f"{code}{ch:03d}.txt"))
    seq = []
    for l in open(path, encoding="utf-8").read().splitlines():
        m = re.match(r"//(\d+) (.*)$", l)
        if m:
            seq.append(m[2].strip())
    out = {}
    for (v, _, _), text in zip(L, seq):
        k = len([x for x in out.get(v, {}).get("lines", [])])
        e = out.setdefault(v, {"lines": [], "lab": []})
        e["lines"].append(text)
        if not (text == "=" or text.startswith("= ")):
            n = len(tokens_of(text if MARK.match(text) else "x " + text)) - (0 if MARK.match(text) else 1)
            e["lab"] += [len(e["lines"]) - 1] * n
    return {v: e["lab"] for v, e in out.items()}


def compare(pname, code, ch, out_dir):
    """Agreement of the clause lines derived from the chapter's .align with an agent's clause-line files
    (export/<project>/_eval/local/clauses/<layout>/<code>/, local only)."""
    res = {}
    derived = clauses(pname, code, ch) or {}
    for lay in LAYOUTS:
        gold = os.path.join(ROOT, "export", pname, "_eval", "local", "clauses", lay, code, f"{code}{ch:03d}.txt")
        mine = os.path.join(out_dir, "clauses", lay, f"{code}{ch:03d}.txt")
        if lay in derived:
            os.makedirs(os.path.dirname(mine), exist_ok=True)
            open(mine, "w", encoding="utf-8").write("\n".join(derived[lay]) + "\n")
        if not os.path.exists(gold):
            continue
        G, M = labels_of(gold, code, ch, lay), labels_of(mine, code, ch, lay)
        tok = same = 0
        lines_same = lines = 0
        for v in G:
            g, m = G[v], M.get(v, [])
            for a, b in zip(g, m):
                tok += 1
                same += a == b
            # lines: the set of (line, first token) cuts
            gc = {(g[i], i) for i in range(len(g)) if i == 0 or g[i] != g[i - 1]}
            mc = {(m[i], i) for i in range(len(m)) if i == 0 or m[i] != m[i - 1]}
            lines += len(gc)
            lines_same += len(gc & mc)
        res[lay] = (same, tok, lines_same, lines)
    return res


def build_all(pname):
    from clause_lines import ot_chapters
    tok = linked = 0
    for code, ch in ot_chapters(pname):
        _, st = build(pname, code, ch)
        tok += st["tokens"]
        linked += st["linked"]
        print(f"{code}{ch:03d}: {100 * st['linked'] / max(st['tokens'], 1):.0f}% linked", flush=True)
    print(f"{pname}: {linked} of {tok} draft tokens linked ({100 * linked / max(tok, 1):.0f}%)")


def main():
    a = sys.argv[1:]
    if len(a) < 2 or (len(a) < 3 and a[1] != "--all"):
        raise SystemExit(__doc__)
    if a[1] == "--all":
        return build_all(a[0])
    pname, code, ch = a[0], a[1], int(a[2])
    out = os.path.join(ROOT, a[a.index("--out") + 1]) if "--out" in a else None
    paths, st = build(pname, code, ch, out)
    print(f"{pname} {code}{ch:03d}: {st['linked']} of {st['tokens']} draft tokens linked to a Hebrew token "
          f"({100 * st['linked'] / max(st['tokens'], 1):.0f}%)" + (f"; {st['unplaced']} Hebrew tokens not in the index" if st['unplaced'] else ""))
    for k, p in paths.items():
        print(f"  {k}: {os.path.relpath(p, ROOT)}")
    if "--compare" in a:
        out = out or os.path.join(ROOT, "scratch", "bridge", f"{code}{ch:03d}")
        for lay, (s, t, ls, l) in compare(pname, code, ch, out).items():
            print(f"  vs the agent's {lay} clause lines: tokens on the same line {s}/{t} ({100 * s / max(t, 1):.0f}%), "
                  f"lines starting at the same word {ls}/{l} ({100 * ls / max(l, 1):.0f}%)")


if __name__ == "__main__":
    main()
