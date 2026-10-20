#!/usr/bin/env python3
"""Clause packages for a drafting agent: one block per Hebrew clause line of
the drafting layout, built from orig/heb.sqlite (scripts/src.py), the project's earlier word alignments (.align),
its store, and, for a language learnt from its NT, the occurrence index (scripts/lang.py). The numbers are the
tagged format's verse-local token numbers (scripts/full_align.py): the agent writes them after its words.

Per clause line:
    §<verse>.<line> L<level> <MACULA clause rule>  [speech: <speaker>]   the line is (in) a quotation by that speaker;
                                                    [speech 2: <speaker>, inside <outer speaker>'s] a quotation inside one
                                                    (bcv-commons/hebrew-speaker-layer, CC BY 4.0, on the Hebrew; without
                                                    it Clear's MACULA Quotation and Speaker Data, one level, CC BY 4.0)
     <n> <Hebrew> <gloss> [<morphology for verbs; the referent for pronouns and suffixes>] · ...
     BSB: the BSB words that render these tokens, each with its token numbers (word^n), gaps as …
     had: what this project already wrote for these lexemes (earlier chapters' .align), the store's decisions,
          and for an NT-only language how the NT renders them (Hebrew -> LXX Greek -> the NT's words)
Writes export/<project>/_learn/packs/<code>NNN.pkg.md (git-ignored, like the verse packs).

Levels by the project's mode (scripts/modes.py):
  known    lean: the line header, each token's number and Hebrew word (a function word with its gloss), and `had:`
           (the project's renderings and the store's decisions), and the speech marks (who speaks, quotations inside
           quotations: punctuation the model can't see in the Hebrew); no content-word glosses, morphology, referents or
           BSB words. Measured on Danish Gen 28:
           the fuller packages changed neither chrF nor the alignment against the lean need (the numbers, for tagging)
  partial  the full package: glosses, verb forms, referents, BSB words, speech, `had:`
  unknown  the full package, and the NT's words through the LXX bridge

    python3 scripts/package.py <project> <code> <ch> [--level known|partial|unknown] [--out FILE]
"""
import collections, os, re, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import full_align as FULL  # noqa: E402
import langtools as LT  # noqa: E402
import vrs  # noqa: E402
from project import project, project_dir  # noqa: E402
from books import BY_CODE  # noqa: E402

HEB = os.path.join(ROOT, "orig", "heb.sqlite")
POINTS = re.compile(r"[֑-ֽ֯׀׃-׆]")
SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
PGN = {"first": "1", "second": "2", "third": "3", "masculine": "m", "feminine": "f", "common": "c", "both": "c",
       "singular": "s", "plural": "p", "dual": "d"}
STEM = {"qal": "q", "niphal": "N", "piel": "D", "pual": "Dp", "hiphil": "H", "hophal": "Hp", "hithpael": "tD"}
TYPE = {"wayyiqtol": "wyq", "qatal": "qtl", "yiqtol": "yqt", "weqatal": "wqt", "imperative": "impv",
        "jussive": "juss", "cohortative": "coh", "participle active": "ptc", "participle passive": "ptcp",
        "infinitive construct": "inf", "infinitive absolute": "infabs"}


def drafting_layout(code, ch):
    """'bhsa' or 'bcv-query': the layout orig/heb is a copy of (the agent's clause lines)."""
    mine = open(os.path.join(ROOT, "orig", "heb", f"{code}{ch:03d}.txt"), encoding="utf-8").read()
    for lay, d in (("bhsa", "heb-bhsa"), ("bcv-query", "heb-bcv-query")):
        f = os.path.join(ROOT, "orig", d, f"{code}{ch:03d}.txt")
        if os.path.exists(f) and open(f, encoding="utf-8").read() == mine:
            return lay
    return "bhsa"


def memory(pname, con, skip):
    """{lexeme: Counter(draft word)} and {(lexeme, sense): Counter} from the project's .align files (all OT chapters
    but `skip`); the sense is MACULA's sensenumber (measured: in about half of the lexemes with several senses the
    project's top rendering differs by sense, e.g. אִשָּׁה wife / women, ראה see / appear)."""
    out = collections.defaultdict(collections.Counter)
    by_sense = collections.defaultdict(collections.Counter)
    for code, ch, draft, ap in FULL.chapters(pname):
        if (code, ch) == skip or not os.path.exists(ap):
            continue
        h, rows = FULL.read_chapter(ap)
        if h != FULL.text_hash(ch, FULL.draft_texts(draft)):
            continue
        text = open(draft, encoding="utf-8").read()
        words = collections.defaultdict(list)
        for v, a, b in FULL.file_tokens(text):
            words[v].append(text[a:b])
        book = code.upper()
        for v, (m, f, _) in rows.items():
            ref = f"{book} {ch}:{v}"
            keys = FULL.index(book, "keys").get(ref, [])
            for o, ids in FULL.parse(m).items():
                if o >= len(keys) or not keys[o]:
                    continue
                lex = con.execute("select lexeme, sensenumber from tokens where key=?", (keys[o].split("+")[0],)).fetchone()
                if lex and lex[0]:
                    w = " ".join(words[v][i] for i in ids if i < len(words[v]))
                    out[lex[0]][w] += 1
                    if lex[1]:
                        by_sense[(lex[0], lex[1])][w] += 1
    return out, by_sense


def store_terms(pname):
    """{lexeme: value} of the store's live term decisions keyed by a Hebrew Strong's number (term:H3068)."""
    import json
    out = {}
    f = os.path.join(project_dir(pname), "profile", "decisions.json")
    if os.path.exists(f):
        for e in json.load(open(f, encoding="utf-8")).get("entries", []):
            m = re.fullmatch(r"H0*(\d+[a-z]?)", str(e.get("source", "")))
            if e.get("kind") == "term" and m and e.get("status") not in ("superseded", "rejected"):
                out[m[1].zfill(4)] = e.get("value")
    return out


def team_ot(pname):
    """{lexeme: [(word, count)]}: how the style edition's own OT renders each Hebrew lexeme (the human text of the
    OT books the edition has), from the aligner's links (_learn/lexicon_hbo.tsv, scripts/align.py --sides hbo). Where the
    edition has OT books, this is a better guide to the team's words than the NT bridge, and the two together better
    than either."""
    import csv
    f = os.path.join(project_dir(pname), "_learn", "lexicon_hbo.tsv")
    out = collections.defaultdict(list)
    if os.path.exists(f):
        for r in csv.DictReader(open(f, encoding="utf-8"), delimiter="\t"):
            lex, n = r["lexeme"].replace("hbo:", ""), int(r["count"])
            if n >= 2 and len(out[lex]) < 3:
                out[lex].append((r["target"], n))
    return out


def nt_bridge(pname, lexemes):
    """{lexeme: [(form, count)]}: how the project's NT renders each lexeme's LXX equivalents (scripts/lang.py)."""
    import lang as L
    P = LT.Project(pname)
    if not os.path.exists(L.db_path(P)):
        return {}
    _, con = L.connect(pname)
    # rank by association (Dice), so that function words and affixes linked to almost every Greek word drop out
    form_links = collections.Counter(dict(con.execute(
        "select t.form, count(*) from nt_links l join nt_tokens t on t.book=l.book and t.ch=l.ch and t.v=l.v and t.pos=l.pos "
        "group by t.form").fetchall()))
    out = {}
    for lex in lexemes:
        bridge = con.execute("select greekstrong, sum(n) from h.lxx where lexeme=? group by greekstrong order by 2 desc",
                             (lex,)).fetchall()
        c = {}
        for g, n in bridge[:2]:
            r, _ = L.renderings(con, [g.lstrip("0")])
            tot = sum(r[g.lstrip("0")].values())
            for form, k in r[g.lstrip("0")].items():
                dice = 2 * k / (form_links[form] + tot)
                if k >= 2 and dice >= 0.05 and not form.startswith("-"):
                    c[form] = max(c.get(form, (0, 0)), (dice, k))
        if c:
            out[lex] = [(f, k) for f, (d, k) in sorted(c.items(), key=lambda x: -x[1][0])[:3]]
    widen(con, lexemes, out)
    return out


def widen(con, lexemes, out, sparse=5):
    """Where the LXX route gives fewer than `sparse` NT renderings (the LXX word is rare or absent in the NT: goat עֵז ->
    αἴξ, while the NT has ἔριφος), the NT Greek words with the Hebrew word's English gloss, kept to one Louw-Nida sense
    (the largest group), and their renderings. Louw-Nida is UBS material inside MACULA Greek: used here locally (packages are git-ignored)."""
    import lang as L
    heb = sqlite3.connect(HEB)
    gloss = {}
    for lex, g, n in heb.execute("select lexeme, coalesce(english, gloss), count(*) from tokens where kind='c' and lexeme in (%s) "
                                 "group by lexeme, coalesce(english, gloss)" % ",".join("?" * len(lexemes)), list(lexemes)):
        if g and n > gloss.get(lex, ("", 0))[1]:
            gloss[lex] = (g.lower().strip("[]. ").split(" ")[-1], n)
    need = {lex: gloss[lex][0] for lex in lexemes if lex in gloss and sum(k for _, k in out.get(lex, [])) < sparse}
    if not need:
        return
    by_gloss, ln_of = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    for strong, g, ln in con.execute("select strong, gloss, ln from g.tokens where kind is null or kind <> 'f'"):
        if strong and g:
            w = g.lower().strip("[]. ").split(" ")[-1]
            if w in need.values():
                by_gloss[w][strong.lstrip("0")] += 1
                if ln:
                    ln_of[strong.lstrip("0")][ln.split()[0]] += 1
    for lex, w in need.items():
        groups = collections.Counter()
        for s, n in by_gloss.get(w, {}).items():
            if ln_of[s]:
                groups[ln_of[s].most_common(1)[0][0]] += n
        if not groups:
            continue
        best = groups.most_common(1)[0][0]
        strongs = [s for s in by_gloss[w] if ln_of[s] and ln_of[s].most_common(1)[0][0] == best]
        r, _ = L.renderings(con, strongs)
        c = collections.Counter()
        for s in strongs:
            c.update(r.get(s, {}))
        extra = [(f, k) for f, k in c.most_common(6) if k >= 2 and not f.startswith("-")]
        if extra:
            out[lex] = list(dict.fromkeys(out.get(lex, []) + extra))[:3]


def morph(t):
    cls, stem, typ, per, gen, num = t["class"], t["stem"], t["type"], t["person"], t["gender"], t["number"]
    if cls == "verb":
        pgn = "".join(PGN.get(x, "") for x in (per, gen, num) if x)
        return f"{STEM.get(stem, stem or '')}.{TYPE.get(typ, typ or '')}{('.' + pgn) if pgn else ''}"
    return ""


def build(pname, code, ch, level=None):
    p = project(pname)
    level = level or p.get("familiarity") or "known"
    lean = level == "known"
    if not os.path.exists(HEB):
        raise SystemExit("no orig/heb.sqlite: python3 scripts/setup.py --only src (the prepared structures; seconds)")
    con = sqlite3.connect(HEB)
    con.row_factory = sqlite3.Row
    book = code.upper()
    lay = drafting_layout(code, ch)
    toks = con.execute("select * from tokens where book=? and ch=? order by key", (book, ch)).fetchall()
    line_of = {r["key"]: (r["line"], r["level"]) for r in con.execute(
        "select l.key, l.line, l.level from layout l join tokens t on t.key=l.key where t.book=? and t.ch=? and l.layout=?",
        (book, ch, lay))}
    by_key = {t["key"]: t for t in toks}
    mem, mem_sense = memory(pname, con, (code, ch))
    terms = store_terms(pname)
    lexemes = sorted({t["lexeme"] for t in toks if t["kind"] == "c" and t["lexeme"]})
    bridge = nt_bridge(pname, lexemes) if level == "unknown" else {}
    ot = team_ot(pname) if level in ("unknown", "partial") else {}   # the edition's own OT, when it has one
    # lexicon forms are plain (the ignored marks removed for matching); show them as the corpus spells them
    SP = LT.Project(pname).spelled if (bridge or ot) else (lambda w: w)
    # the BSB verses (tables positions are in the BSB verse's compact tokens)
    bsb_cache = {}

    def bsb_tokens(v):
        c2, v2 = vrs.to_bsb(code, ch, v)
        f = os.path.join(ROOT, "reference", "BSB", f"{code}{c2:03d}.txt")
        if f not in bsb_cache:
            bsb_cache[f] = LT.verses_of(f)
        return FULL.tokenize(bsb_cache[f].get((c2, v2), ""))

    def who(key):
        t = by_key.get(key) or con.execute("select * from tokens where key=?", (key,)).fetchone()
        if not t:
            return None
        here = t["ch"] == ch and t["n"] is not None
        return f"{(t['english'] or t['gloss'] or '').replace(' ', '_')}{('(' + str(t['n']) + ('' if t['v'] == cur_v else ' v' + str(t['v'])) + ')') if here else ''}"

    out = [f"# {book} {ch}: clause packages ({lay} layout, level {level}). Write your words with these numbers: word^n.",
           ("# Per line: §verse.line L(level) rule [speech] / tokens: n Hebrew (function words with a gloss) / had: this "
            "project's renderings (count) and the store's decisions" if lean else
            "# Per line: §verse.line L(level) rule / tokens: n Hebrew gloss [morph; ref=referent] / BSB words^n /"
            " had: this project's renderings (count), store decisions, OT: the edition's own OT (the human text; its"
            " words for this Hebrew word), NT: the NT's words through the LXX (unknown languages)"), ""]
    lines = collections.OrderedDict()
    for t in toks:
        if t["n"] is None:
            continue
        ln = line_of.get(t["key"], (None, None))
        lines.setdefault((t["v"], ln[0]), []).append(t)
    # the speaker layer: each token's segment (its bcv-query layout line) -> the quotation it stands in, with its level
    seg_of, frame = {}, None
    if con.execute("select count(*) from sqlite_master where name='speaker_segments'").fetchone()[0]:
        segs = {r["line"]: r for r in con.execute("select * from speaker_segments where book=? and ch=?", (book, ch))}
        quot = {}
        for r in con.execute("select l.key, l.line from layout l join tokens t on t.key=l.key where t.book=? and t.ch=? "
                             "and l.layout='bcv-query'", (book, ch)):
            if r["line"] in segs:
                seg_of[r["key"]] = segs[r["line"]]
        frames = collections.Counter(r["frame"] for r in segs.values())
        if segs and frames.most_common(1)[0][0]:
            frame = frames.most_common(1)[0][0]

        def chain(qid):
            """The speakers from this quotation outward: [inner, outer, ...]."""
            names = []
            while qid:
                if qid not in quot:
                    quot[qid] = con.execute("select speaker, parent from speaker_quotations where id=?", (qid,)).fetchone()
                q = quot[qid]
                if not q:
                    break
                names.append(q["speaker"] or "?")
                qid = q["parent"]
            return names
    if seg_of:
        out[2:2] = ["# Speech: [speech: X] a quotation by X; [speech 2: Y, inside X's] Y quoted inside X's speech (inner"
                    " quotation marks). From the Hebrew Bible Speaker Layer (bcv-commons, CC BY 4.0; with Clear Bible's MACULA"
                    " Quotation and Speaker Data, CC BY 4.0, and SIL Glyssen, MIT)."] + (
            [f"# Frame: the chapter as a whole is spoken by {frame} (a psalm, a first-person account): that is not a"
             " quotation, so no quotation marks for it; a [speech] inside it is one."] if frame else [])
    has_sp = con.execute("select count(*) from sqlite_master where name='speakers'").fetchone()[0]
    booknum = list(BY_CODE).index(code) + 1
    spans = []
    if has_sp and not seg_of:  # Clear's spans, when the speaker layer isn't here  # the quotations touching this chapter (verses in English numbering, words as MACULA keys)
        lo, hi = booknum * 1000000 + max(ch - 1, 0) * 1000, booknum * 1000000 + (ch + 2) * 1000
        spans = con.execute("select speaker, word_start, word_end from speakers where stop >= ? and start <= ?", (lo, hi)).fetchall()

    def speaking(group):
        """Who speaks in this clause line: the speaker layer's segment that has most of its tokens (the line is the
        drafting layout's, the segments bcv-query's), else the Clear quotations whose word span covers one of its tokens."""
        if seg_of:
            c = collections.Counter(seg_of[t["key"]]["line"] for t in group if t["key"] in seg_of)
            if not c:
                return ""
            r = next(seg_of[t["key"]] for t in group if t["key"] in seg_of and seg_of[t["key"]]["line"] == c.most_common(1)[0][0])
            if not r["level"]:
                return ""
            names = chain(r["quotation"])
            part = " (part of the line)" if r["share"] < 0.5 else ""
            if r["level"] == 1 or len(names) < 2:
                return f"  [speech: {names[0] if names else r['speaker']}]{part}"
            return f"  [speech {r['level']}: {names[0]}, inside " + ", inside ".join(f"{n}'s" for n in names[1:]) + f"]{part}"
        who_ = [sp for sp, a, b in spans if a and b and any(a <= t["key"] <= b for t in group)]
        return f"  [speech: {', '.join(dict.fromkeys(who_))}]" if who_ else ""
    seen_v, k = None, 0
    for (v, line), group in lines.items():
        cur_v = v
        if v != seen_v:
            out.append(f"v{v}")
            seen_v, k = v, 0
        k += 1
        lev = line_of.get(group[0]["key"], (None, None))[1]
        cl = con.execute("select rule from nodes where id=?", (group[0]["clause"] or group[-1]["clause"],)).fetchone()
        out.append((f"§{v}.{k} L{'' if lev is None else lev} {cl['rule'] if cl and cl['rule'] else ''}".rstrip())
                   + speaking(group))
        cells, seen_n = [], set()
        for t in group:
            if t["n"] in seen_n:  # a fused token: one number
                continue
            seen_n.add(t["n"])
            heb = POINTS.sub("", "".join(x["text"] for x in group if x["n"] == t["n"]))
            if lean:  # known language: the number and the word are what tagging needs; a function word also its
                # gloss, which helps to place it (B4: function words 88% linked without, 95-99% with full glosses)
                gl = (t["english"] or t["gloss"] or "").replace(" ", "_") if t["kind"] == "f" else ""
                cells.append(f"{t['n']} {heb}" + (f" {gl}" if gl else ""))
                continue
            gl = (t["english"] or t["gloss"] or "").replace(" ", "_")
            extra = [m] if (m := morph(t)) else []
            refs = [r[0] for r in con.execute("select target from refs where key=? and kind in ('participantref','subjref')", (t["key"],))]
            names = [w for w in (who(r) for r in refs[:2]) if w]
            if names and (t["class"] in ("pron", "verb")):
                extra.append("ref=" + "+".join(names))
            cells.append(f"{t['n']} {heb} {gl}" + (f" [{'; '.join(extra)}]" if extra else ""))
        out.append("  " + " · ".join(cells))
        # BSB: the words linked to this line's tokens, in BSB order, with the token numbers
        pos = collections.defaultdict(set)
        for t in group:
            b = con.execute("select positions from bsb where key=?", (t["key"],)).fetchone()
            for x in (b[0].split() if b else []):
                pos[int(x)].add(t["n"])
        if pos and not lean:
            bt = bsb_tokens(v)
            words, last = [], None
            for i in sorted(pos):
                if i >= len(bt):
                    continue
                if last is not None and i > last + 1:
                    words.append("…")
                words.append(bt[i] + "^" + ",".join(map(str, sorted(pos[i]))))
                last = i
            out.append("  BSB: " + " ".join(words))
        had = []
        for t in group:
            if t["kind"] != "c" or not t["lexeme"]:
                continue
            lex = t["lexeme"]
            bits = []
            if lex in terms:
                bits.append(f"store={terms[lex]}")
            ms = mem_sense.get((lex, t["sensenumber"])) if t["sensenumber"] else None
            if ms and sum(ms.values()) >= 2:  # this sense's renderings first; the lexeme's top one if it differs
                tot = sum(ms.values())
                here = [(w, c) for w, c in ms.most_common(2) if c >= 2 and c / tot >= 0.2]
                bits += [f"{w}×{c}" for w, c in here]
                top = mem[lex].most_common(1)[0] if mem.get(lex) else None
                if top and here and top[0] != here[0][0]:
                    bits.append(f"(other senses: {top[0]}×{top[1]})")
            elif mem.get(lex):
                tot = sum(mem[lex].values())
                bits += [f"{w}×{c}" for w, c in mem[lex].most_common(2) if c >= 2 and c / tot >= 0.2]
            if ot.get(lex):
                bits.append("OT:" + "/".join(f"{SP(w)}×{c}" for w, c in ot[lex]))
            if bridge.get(lex):
                bits.append("NT:" + "/".join(f"{SP(w)}×{c}" for w, c in bridge[lex]))
            if bits:
                had.append(f"{t['n']}:" + " ".join(bits))
        if had:
            out.append("  had: " + " · ".join(had))
    return "\n".join(out) + "\n"


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        raise SystemExit(__doc__)
    pname, code, ch = a[0], a[1], int(a[2])
    level = a[a.index("--level") + 1] if "--level" in a else None
    text = build(pname, code, ch, level)
    out = a[a.index("--out") + 1] if "--out" in a else os.path.join(LT.Project(pname).learn, "packs", f"{code}{ch:03d}.pkg.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(text)
    print(f"{os.path.relpath(out, ROOT)}: {text.count(chr(10) + '§')} clause lines, {len(text)} chars")


if __name__ == "__main__":
    main()
