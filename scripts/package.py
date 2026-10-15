#!/usr/bin/env python3
"""Clause packages for a drafting agent (internal-docs plan, sections 5 and 16): one block per Hebrew clause line of
the drafting layout, built from orig/heb.sqlite (scripts/src.py), the project's earlier word alignments (.align),
its store, and, for a language learnt from its NT, the occurrence index (scripts/lang.py). The numbers are the
tagged format's verse-local token numbers (scripts/full_align.py): the agent writes them after its words.

Per clause line:
    §<verse>.<line> L<level> <MACULA clause rule>
     <n> <Hebrew> <gloss> [<morphology for verbs; the referent for pronouns and suffixes>] · ...
     BSB: the BSB words that render these tokens, each with its token numbers (word^n), gaps as …
     had: what this project already wrote for these lexemes (earlier chapters' .align), the store's decisions,
          and for an NT-only language how the NT renders them (Hebrew -> LXX Greek -> the NT's words)
Writes export/<project>/_learn/packs/<code>NNN.pkg.md (git-ignored, like the verse packs).

Levels by the project's mode (scripts/modes.py): known -> tokens, BSB, the project's renderings and decisions;
partial -> the same; unknown -> also the NT renderings through the LXX bridge.

    python3 scripts/package.py <project> <code> <ch> [--level known|partial|unknown] [--out FILE]
"""
import collections, os, re, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import full_align as FULL  # noqa: E402
import langtools as LT  # noqa: E402
import vrs  # noqa: E402
from project import project  # noqa: E402

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
    """{lexeme: Counter(draft word)} from the project's .align files (all OT chapters but `skip`)."""
    out = collections.defaultdict(collections.Counter)
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
                lex = con.execute("select lexeme from tokens where key=?", (keys[o].split("+")[0],)).fetchone()
                if lex and lex[0]:
                    out[lex[0]][" ".join(words[v][i] for i in ids if i < len(words[v]))] += 1
    return out


def store_terms(pname):
    """{lexeme: value} of the store's live term decisions keyed by a Hebrew Strong's number (term:H3068)."""
    import json
    out = {}
    f = os.path.join(ROOT, "export", pname, "profile", "decisions.json")
    if os.path.exists(f):
        for e in json.load(open(f, encoding="utf-8")).get("entries", []):
            m = re.fullmatch(r"H0*(\d+[a-z]?)", str(e.get("source", "")))
            if e.get("kind") == "term" and m and e.get("status") not in ("superseded", "rejected"):
                out[m[1].zfill(4)] = e.get("value")
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
    return out


def morph(t):
    cls, stem, typ, per, gen, num = t["class"], t["stem"], t["type"], t["person"], t["gender"], t["number"]
    if cls == "verb":
        pgn = "".join(PGN.get(x, "") for x in (per, gen, num) if x)
        return f"{STEM.get(stem, stem or '')}.{TYPE.get(typ, typ or '')}{('.' + pgn) if pgn else ''}"
    return ""


def build(pname, code, ch, level=None):
    p = project(pname)
    level = level or p.get("familiarity") or "known"
    if not os.path.exists(HEB):
        raise SystemExit("no orig/heb.sqlite: python3 scripts/src.py build (the prepared Hebrew structure; once)")
    con = sqlite3.connect(HEB)
    con.row_factory = sqlite3.Row
    book = code.upper()
    lay = drafting_layout(code, ch)
    toks = con.execute("select * from tokens where book=? and ch=? order by key", (book, ch)).fetchall()
    line_of = {r["key"]: (r["line"], r["level"]) for r in con.execute(
        "select l.key, l.line, l.level from layout l join tokens t on t.key=l.key where t.book=? and t.ch=? and l.layout=?",
        (book, ch, lay))}
    by_key = {t["key"]: t for t in toks}
    mem = memory(pname, con, (code, ch))
    terms = store_terms(pname)
    lexemes = sorted({t["lexeme"] for t in toks if t["kind"] == "c" and t["lexeme"]})
    bridge = nt_bridge(pname, lexemes) if level == "unknown" else {}
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
           "# Per line: §verse.line L(level) rule / tokens: n Hebrew gloss [morph; ref=referent] / BSB words^n /"
           " had: this project's renderings (count), store decisions, the NT's words (unknown languages)", ""]
    lines = collections.OrderedDict()
    for t in toks:
        if t["n"] is None:
            continue
        ln = line_of.get(t["key"], (None, None))
        lines.setdefault((t["v"], ln[0]), []).append(t)
    seen_v, k = None, 0
    for (v, line), group in lines.items():
        cur_v = v
        if v != seen_v:
            out.append(f"v{v}")
            seen_v, k = v, 0
        k += 1
        lev = line_of.get(group[0]["key"], (None, None))[1]
        cl = con.execute("select rule from nodes where id=?", (group[0]["clause"] or group[-1]["clause"],)).fetchone()
        out.append(f"§{v}.{k} L{'' if lev is None else lev} {cl['rule'] if cl and cl['rule'] else ''}".rstrip())
        cells, seen_n = [], set()
        for t in group:
            if t["n"] in seen_n:  # a fused token: one number
                continue
            seen_n.add(t["n"])
            heb = POINTS.sub("", "".join(x["text"] for x in group if x["n"] == t["n"]))
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
        if pos:
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
            if mem.get(lex):
                tot = sum(mem[lex].values())
                bits += [f"{w}×{c}" for w, c in mem[lex].most_common(2) if c >= 2 and c / tot >= 0.2]
            if bridge.get(lex):
                bits.append("NT:" + "/".join(f"{w}×{c}" for w, c in bridge[lex]))
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
