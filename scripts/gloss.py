#!/usr/bin/env python3
"""Glosses in the language store: the Greek or Hebrew word a term, formula or name renders, as it stands in a source
verse, with its lemma and the reference (docs/language-store.md, *Glosses*). English is never stored: it is generated
for people from the gloss, through the BSB alignment (the bsb tables of orig/grc.sqlite and orig/heb.sqlite).

  check <project>                every gloss in the store against the source texts (as language_profile.py check does)
  propose <project> [--write]    a gloss for each live term, formula and name without one, from the project's alignment
                                 (the Greek and Hebrew lexicons in _learn/, the entry's Hebrew source); English in brackets
                                 in a value moves to the note. --write marks the entry superseded and appends a copy with
                                 the gloss (id + '.gloss'), its glosses marked proposed, for an agent to confirm
  show <project> <id> ...        an entry's glosses, with the generated English line
  words <project> "<BOOK C:V>"   a verse's words with their lemmas and English (generated), to write a gloss from: the
                                 NT in the project's Greek text (BGB or RP), the OT in the WLC

A gloss: {"lang": "grc" | "hbo" | "arc", "form": the word or phrase as the verse writes it, "lemma": as orig/grc.sqlite
or orig/heb.sqlite writes it (for Hebrew the consonants are enough), "ref": "MRK 1:38"}; "proposed": true until an agent
or the team confirms it. Greek is checked against the MACULA Greek tokens (orig/grc.sqlite) and the BGB and RP verse
text (orig/grc, orig/grc-rp); Hebrew and Aramaic against MACULA Hebrew, the WLC (orig/heb.sqlite), never BHSA: a form
with accents is the WLC word as written, one without accents may leave them out, one without vowels may leave them out.
"""
import collections, glob, json, os, re, sqlite3, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from books import BY_CODE  # noqa: E402

LANGS = {"grc": "grc", "hbo": "heb", "arc": "heb"}
REF = re.compile(r"^([1-3A-Z][A-Z0-9]{2}) (\d{1,3}):(\d{1,3})$")
SCRIPT = {"grc": re.compile(r"^[Ͱ-Ͽἀ-῿̀-ͯ’' ,.;·]+$"),
          "heb": re.compile(r"^[֐-׿יִ-ﭏ ]+$")}
ACCENTS = re.compile(r"[֑-ֽ֯]")          # cantillation and meteg
POINTS = re.compile(r"[֑-ׇ]")                 # every mark: accents, vowels, dagesh, shin dots
KINDS = ("term", "formula", "name")
_con, _lemmas = {}, {}


def db(side):
    if side not in _con:
        f = os.path.join(ROOT, "orig", f"{side}.sqlite")
        if not os.path.exists(f):
            raise FileNotFoundError(f"orig/{side}.sqlite (python3 scripts/setup.py --only src)")
        _con[side] = sqlite3.connect(f)
    return _con[side]


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def bare(s):
    """Greek without accents, breathings and case; Hebrew consonants only"""
    s = POINTS.sub("", nfc(s))
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)).casefold().replace("ς", "σ")


def tokens(side, ref):
    """[(key, text, after, lemma, lexeme or strong, kind c|f)] of a verse (Hebrew numbering in the OT)"""
    m = REF.match(ref or "")
    if not m:
        return []
    cols = "key, text, '' , lemma, strong, kind" if side == "grc" else "key, text, after, lemma, lexeme, kind"
    return db(side).execute(f"select {cols} from tokens where book=? and ch=? and v=? order by key",
                            (m[1], int(m[2]), int(m[3]))).fetchall()


def surface(side, rows):
    if side == "grc":
        return " ".join(nfc(r[1]) for r in rows if r[1])
    return "".join(nfc(r[1] or "") + (r[2] or "") for r in rows)


def lemma_known(side, lemma):
    if side not in _lemmas:
        cols = ("lemma",) if side == "grc" else ("lemma", "stronglemma")
        s = set()
        for c in cols:
            s |= {nfc(x) for (x,) in db(side).execute(f"select distinct {c} from tokens") if x}
        _lemmas[side] = (s, {bare(x) for x in s})
    exact, plain = _lemmas[side]
    return nfc(lemma) in exact or bare(lemma) in plain


def verse_text(code, ref, side):
    """the verse in orig/grc (BGB) and orig/grc-rp (RP), for a Greek form the MACULA tokens spell otherwise"""
    m = REF.match(ref)
    return [nfc(greek_verses(os.path.join(ROOT, "orig", d, f"{code}{int(m[2]):03d}.txt")).get((int(m[2]), int(m[3])), ""))
            for d in ("grc", "grc-rp")]


def check(g):
    """the problems of one gloss ([] = fine)"""
    out = []
    lang = g.get("lang")
    if lang not in LANGS:
        return [f"gloss lang {lang!r} (grc, hbo or arc)"]
    side = LANGS[lang]
    for k in ("form", "lemma", "ref"):
        if not g.get(k):
            out.append(f"gloss without {k}")
    if out:
        return out
    m = REF.match(g["ref"])
    if not m or m[1].lower() not in BY_CODE:
        return [f"gloss ref {g['ref']!r}"]
    if (BY_CODE[m[1].lower()][2] == "nt") != (side == "grc"):
        return [f"gloss {lang} from {g['ref']}: Greek glosses come from the NT, Hebrew and Aramaic from the OT"]
    form, lemma = nfc(g["form"]).strip(), nfc(g["lemma"]).strip()
    for k, v in (("form", form), ("lemma", re.sub(r" \([IV]+\)$", "", lemma))):   # MACULA's homonym number: δοῦλος (II)
        if not SCRIPT[side].match(v):
            out.append(f"gloss {k} {v!r} is not {'Greek' if side == 'grc' else 'Hebrew'} script")
    if out:
        return out
    try:
        rows = tokens(side, g["ref"])
        if not lemma_known(side, lemma):
            out.append(f"gloss lemma {lemma!r} is not a lemma of orig/{side}.sqlite")
    except FileNotFoundError as e:
        return [f"not checked: {e} is missing"]
    if not rows:
        return out + [f"gloss ref {g['ref']} is not in orig/{side}.sqlite"]
    if side == "grc":
        texts = [surface(side, rows)] + verse_text(m[1].lower(), g["ref"], side)
        if not any(form.casefold() in t.casefold() for t in texts):
            out.append(f"gloss form {form!r} is not in {g['ref']}" + (" (as written: accents, breathing)" if any(
                bare(form) in bare(t) for t in texts) else ""))
        if lemma not in {nfc(r[3]) for r in rows} and bare(lemma) not in {bare(r[3]) for r in rows}:
            out.append(f"gloss lemma {lemma!r} is not the lemma of a word in {g['ref']}")
    else:
        wlc = surface(side, rows)
        if ACCENTS.search(form):
            ok = form in wlc
        elif POINTS.search(form):
            ok = form in ACCENTS.sub("", wlc)
        else:
            ok = form in POINTS.sub("", wlc)
        if not ok:
            out.append(f"gloss form {form!r} is not the WLC text of {g['ref']}" + (
                " (the consonants match: the vowels or accents differ from the WLC's)" if bare(form) in bare(wlc) else ""))
        if bare(lemma) not in {bare(r[3]) for r in rows} | {bare(x) for (x,) in db(side).execute(
                "select stronglemma from tokens where book=? and ch=? and v=?", (m[1], int(m[2]), int(m[3])))}:
            out.append(f"gloss lemma {lemma!r} is not the lemma of a word in {g['ref']}")
    return out


_bsb = {}


def english(g, keys=None):
    """the BSB words aligned to the gloss's form in its verse (generated, for people), or ''; keys: these tokens"""
    import full_align as FA
    import langtools as LT
    import vrs
    side = LANGS.get(g.get("lang"))
    m = REF.match(g.get("ref") or "")
    if not side or not m:
        return ""
    try:
        rows = tokens(side, g["ref"])
    except FileNotFoundError:
        return ""
    want = set(re.split(r"[\s\u05be]+", bare(g.get("form", ""))))
    seen, hit = set(), [r for r in rows if r[0] in keys] if keys else []
    if keys:
        want = set()
    for r in rows:                        # the first occurrence of each word of the form
        if r[1] and bare(r[1]) in want and bare(r[1]) not in seen:
            seen.add(bare(r[1])); hit.append(r)
    if side == "heb" and not hit:        # a word written with its prefixes: the content token inside it
        hit = [r for r in rows if r[1] and r[5] == "c" and any(bare(r[1]) in w for w in want)]
    if side == "grc" and not hit:        # spelled as the BGB or RP writes it, not as MACULA's Nestle text
        for ed in (("bgb", "grc"), ("rp", "grc-rp")):
            keys = {k for w, k in greek_words(None, g["ref"], ed) if k and bare(w) in want}
            hit = [r for r in rows if r[0] in keys]
            if hit:
                break
    code, c, v = m[1].lower(), int(m[2]), int(m[3])
    if side == "heb":
        c, v = vrs.to_bsb(code, c, v)
        if v == "title":
            return ""
    f = os.path.join(ROOT, "reference", "BSB", f"{code}{c:03d}.txt")
    if f not in _bsb:
        _bsb[f] = LT.verses_of(f) if os.path.exists(f) else {}
    toks = FA.tokenize(_bsb[f].get((c, v), ""))
    pos = set()
    for r in hit:
        p = db(side).execute("select positions from bsb where key=?", (r[0],)).fetchone()
        pos |= {int(x) for x in (p[0].split() if p else []) if int(x) < len(toks)}
    return " ".join(toks[i] for i in sorted(pos))


def line(g):
    """'ἄγω: Ἄγωμεν (MRK 1:38) — English (generated): let us go'"""
    en = english(g)
    return (f"{g.get('lemma')}: {g.get('form')} ({g.get('ref')})" + (" [proposed]" if g.get("proposed") else "")
            + (f" — English (generated): {en}" if en else ""))


def glosses(e):
    return [g for g in (e.get("gloss") or []) if isinstance(g, dict)]


# ---------- matching: a verse's source words against the store's glosses ----------

_strong = {}


def greek_strongs(lemma):
    """the Strong's numbers of a Greek lemma (orig/grc.sqlite)"""
    if lemma not in _strong:
        _strong[lemma] = {str(s) for (s,) in db("grc").execute("select distinct strong from tokens where lemma=?", (nfc(lemma),)) if s}
    return _strong[lemma]


def verse_keys(code, ch, v, lxx_share=0.2):
    """what a verse of the original offers to match glosses: {('heb', bare lemma)}, {('lxx', Greek Strong's)} the LXX
    usually renders its words with (orig/heb.sqlite lxx: at least lxx_share of a word's renderings), or for an NT verse
    {('grc', Greek Strong's)}; content words only"""
    nt = BY_CODE[code][2] == "nt"
    try:
        if nt:
            return {("grc", str(s)) for (s,) in db("grc").execute(
                "select strong from tokens where book=? and ch=? and v=? and kind='c'", (code.upper(), ch, v)) if s}
        out = set()
        for lemma, sl, lex in db("heb").execute("select lemma, stronglemma, lexeme from tokens where book=? and ch=? and v=? "
                                                "and kind='c'", (code.upper(), ch, v)):
            out |= {("heb", bare(x)) for x in (lemma, sl) if x} | {("hebp", nfc(x)) for x in (lemma, sl) if x}
            eq = db("heb").execute("select greekstrong, n from lxx where lexeme=?", (lex,)).fetchall()
            tot = sum(n for _, n in eq) or 1
            out |= {("lxx", str(g)) for g, n in eq if n >= 3 and n / tot >= lxx_share}
        return out
    except FileNotFoundError:
        return set()


def matches(e, keys):
    """why an entry's glosses match a verse ('lemma' for a Hebrew or Greek gloss of a word in it, 'lxx' for a Greek
    gloss the LXX uses for one of its Hebrew words), or None"""
    heb = [g for g in glosses(e) if g.get("lang") in ("hbo", "arc")]
    def hit(lemma):                       # a pointed lemma matches as pointed (עֶבֶד the noun is not עָבַד the verb)
        return ("hebp", nfc(lemma)) in keys if POINTS.search(lemma) else ("heb", bare(lemma)) in keys
    if any(hit(g.get("lemma", "")) for g in heb):
        return "lemma"
    if heb and any(k[0] == "heb" for k in keys):   # a Hebrew gloss decides for an OT verse: no detour through the Greek
        return None
    for g in glosses(e):
        if g.get("lang") == "grc":
            st = greek_strongs(g.get("lemma", ""))
            if any(("grc", s) in keys for s in st):
                return "lemma"
            if not g.get("proposed") and any(("lxx", s) in keys for s in st):   # the detour only for a confirmed gloss
                return "lxx"
    return None


def short(e):
    """the glosses' lemmas, for a pack line: 'אֱלֹהִים / θεός'"""
    return " / ".join(dict.fromkeys(nfc(g.get("lemma", "")) for g in glosses(e) if g.get("lemma")))


# ---------- proposals ----------

BRACKETS = re.compile(r"\s*\(([^()]*)\)")


def split_value(v, english=None):
    """(value without bracketed text, [bracketed texts]): during the transition, brackets in a value hold English.
    With english (a function: the English words of a text, langtools.Project.english_words), only brackets with an
    English word in them: one in the language itself stays in the value (a name's meaning told in the language)"""
    if not isinstance(v, str):
        return v, []
    keep = lambda x: english is not None and not english(x)
    out = BRACKETS.sub(lambda m: m.group(0) if keep(m.group(1)) else "", v).strip()
    return out, [x.strip() for x in BRACKETS.findall(v) if not keep(x)]


def lexicon(P, side, min_share=0.1):
    """{target word (plain): Counter(source key: count)}, the alignments that carry at least min_share of the source
    word's links (noise left out): grc keys are letters-only Greek words of the project's Greek text, hbo keys lexemes"""
    f = os.path.join(P.learn, f"lexicon_{side}.tsv")
    out = collections.defaultdict(collections.Counter)
    if not os.path.exists(f):
        return out
    for r in (l.split("\t") for l in open(f, encoding="utf-8").read().splitlines()[1:]):
        if side == "hbo" and len(r) >= 6 and float(r[5]) >= min_share:
            out[P.tok.plain(r[3])][r[0].split(":", 1)[-1]] += int(r[4])
        elif side == "grc" and len(r) >= 4 and float(r[3]) >= min_share:
            out[P.tok.plain(r[1])][r[0]] += int(r[2])
    return out


def greek_edition(P):
    """the project's Greek text (align.py's grc side): (map edition, orig folder)"""
    return ("bgb", "grc") if P.p.get("nt_basis", "critical") == "critical" else ("rp", "grc-rp")


_gw = {}


def greek_key(w):
    """align.py's Greek source word: no accents, cut to 6 letters"""
    return bare(w)[:6]


def greek_verses(path):
    """{(c, v): text} of an orig/grc or orig/grc-rp chapter file ('c:v text' lines)"""
    out = {}
    for l in open(path, encoding="utf-8").read().splitlines() if os.path.exists(path) else []:
        m = re.match(r"(\d+):(\d+)\s+(.*)$", l)
        if m:
            out[(int(m[1]), int(m[2]))] = m[3]
    return out


def greek_words(P, ref, edition=None):
    """[(word as the project's Greek text writes it, MACULA key)] of an NT verse (orig/grc.sqlite map)"""
    m = REF.match(ref)
    ed, d = edition or greek_edition(P)
    code, c, v = m[1].lower(), int(m[2]), int(m[3])
    f = os.path.join(ROOT, "orig", d, f"{code}{c:03d}.txt")
    if f not in _gw:
        _gw[f] = greek_verses(f)
    words = re.findall(r"[^\W\d_]+", nfc(_gw[f].get((c, v), "")))
    keys = dict(db("grc").execute("select pos, key from map where edition=? and book=? and ch=? and v=?", (ed, m[1], c, v)))
    return [(w, keys.get(i)) for i, w in enumerate(words)]


def token(side, key):
    return db(side).execute("select key, text, '', lemma, '', kind from tokens where key=?", (key,)).fetchone() if key else None


def from_evidence(P, e, lex_g, lex_h):
    """glosses from the entry's evidence verses: the source word its target form is aligned to (one per language)"""
    out = []
    for r in e.get("evidence", []):
        m = REF.match(r.get("ref", ""))
        if not m or m[1].lower() not in BY_CODE:
            continue
        nt = BY_CODE[m[1].lower()][2] == "nt"
        lang = "grc" if nt else "heb"
        if any((g["lang"] == "grc") == nt for g in out):
            continue
        form = r.get("form") or split_value(e.get("value"))[0]
        words = [P.tok.plain(w) for w in P.tok.tokens(re.sub(r"<[^>]*>", " ", str(form)))]
        lex = lex_g if nt else lex_h
        try:
            cands = ([(w, token("grc", k)) for w, k in greek_words(P, r["ref"])] if nt
                     else [(t[1], t) for t in tokens("heb", r["ref"])])
        except FileNotFoundError:
            return out
        best = None
        for w in words:
            for src, n in lex.get(w, {}).items():
                for written, t in cands:
                    if not t or not written or t[5] != "c":
                        continue
                    if (greek_key(written) == src if nt else str(t[4]) == src) and (best is None or n > best[0]):
                        best = (n, written, t)
        if best:
            _, written, t = best
            out.append({"lang": "grc" if nt else ("arc" if is_aramaic(t[0]) else "hbo"), "form": nfc(written),
                        "lemma": nfc(t[3]), "ref": r["ref"], "proposed": True})
    return out


def is_aramaic(key):
    r = db("heb").execute("select lang from tokens where key=?", (key,)).fetchone()
    return bool(r and r[0] == "A")


def from_source(e, greek=()):
    """a Hebrew gloss from the entry's source (a Strong's number H430, or Hebrew words): an occurrence the LXX renders
    with the entry's Greek gloss, else the first"""
    src = str(e.get("source") or "")
    m = re.match(r"^H(\d+)([a-z]?)$", src.strip())
    try:
        if m:
            lex = f"{int(m[1]):04d}{m[2]}"
            rows = db("heb").execute("select key, book, ch, v, text, lemma, lang, greek from tokens where lexeme=? and kind='c' "
                                     "order by key", (lex,)).fetchall() or db("heb").execute(
                "select key, book, ch, v, text, lemma, lang, greek from tokens where lexeme like ? and kind='c' order by key",
                (lex + "%",)).fetchall()
            want = {bare(g["lemma"]) for g in greek} | {bare(g["form"]) for g in greek}
            fits = lambda r: plausible(e, {"lang": "arc" if r[6] == "A" else "hbo", "form": r[4], "ref": f"{r[1]} {r[2]}:{r[3]}"})
            row = (next((r for r in rows[:300] if r[7] and bare(r[7]) in want and fits(r)), None)
                   or next((r for r in rows[:300] if fits(r)), None) or (rows[0] if rows else None))
        elif e.get("kind") == "name" and re.fullmatch(r"[A-Z][a-z]+(?: [A-Z][a-z]+)?", src.strip()):
            row = db("heb").execute("select key, book, ch, v, text, lemma, lang from tokens where kind='c' and (english=? or "
                                    "gloss=?) order by key limit 1", (src.strip(), src.strip())).fetchone()
        else:
            heb = re.findall(r"[א-ת][֑-ׇא-ת]*", src)
            if not heb:
                return None
            row = db("heb").execute("select key, book, ch, v, text, lemma, lang from tokens where lemma=? or stronglemma=? "
                                    "order by key limit 1", (nfc(heb[0]), nfc(heb[0]))).fetchone()
    except FileNotFoundError:
        return None
    if not row:
        return None
    return {"lang": "arc" if row[6] == "A" else "hbo", "form": nfc(row[4]), "lemma": nfc(row[5]),
            "ref": f"{row[1]} {row[2]}:{row[3]}", "proposed": True, "sure": True}


STOP_EN = {"the", "a", "an", "of", "to", "and", "in", "on", "for", "his", "her", "my", "your", "their", "our", "is", "be",
           "was", "were", "by", "with", "at", "from", "that", "this", "it", "he", "she", "they", "you", "we", "i", "x", "n"}


def hints(e):
    """English the entry gives for what it means: its words, its id, the English of its source"""
    text = " ".join(list(e.get("words") or []) + [e["id"].split(":", 1)[-1].split(".")[0].replace("_", " "),
                                                    re.sub(r"[HG]\d+[a-z]?|<[^>]*>|[\u0590-\u05ff]+", " ", str(e.get("source") or ""))])
    return {w.lower()[:4] for w in re.findall(r"[A-Za-z]+", text) if w.lower() not in STOP_EN and len(w) > 2}


def plausible(e, g):
    """a proposed gloss whose generated English shares a word (4 letters) with the entry's hints; no hints: plausible"""
    h = hints(e)
    en = {w.lower()[:4] for w in re.findall(r"[A-Za-z]+", english(g)) if w.lower() not in STOP_EN}
    return not h or bool(h & en)


def propose(pname, write=False):
    import langtools as LT
    P = LT.Project(pname)
    lex_g, lex_h = lexicon(P, "grc"), lexicon(P, "hbo")
    report = collections.Counter()
    left = []
    for fn in ("decisions.json", "observations.json"):
        path = os.path.join(P.profile, fn)
        if not os.path.exists(path):
            continue
        d = json.load(open(path, encoding="utf-8"))
        add = []
        for e in d.get("entries", []):
            if e.get("kind") not in KINDS or e.get("status") == "superseded":
                continue
            value, english = split_value(e.get("value"), P.english_words)
            if glosses(e) and not english:
                report["glossed already"] += 1
                continue
            if e.get("method") == "team-decision":
                report["team decisions (the team adds the gloss)"] += 1
                left.append((e["id"], "a team decision: only the team changes it"))
                continue
            gs = glosses(e) or from_evidence(P, e, lex_g, lex_h)
            h = from_source(e, [g for g in gs if g["lang"] == "grc"]) if not any(g["lang"] != "grc" for g in gs) else None
            if h:
                gs = gs + [h]
            dropped = [g for g in gs if g.get("proposed") and not g.get("sure") and not plausible(e, g)]
            gs = [{k: v for k, v in g.items() if k != "sure"} for g in gs if g not in dropped]
            if dropped:
                report["proposals dropped (English unlike the entry's)"] += len(dropped)
            heb_first = bool(re.match(r"^H\d", str(e.get("source") or "")) or re.search(r"[א-ת]", str(e.get("source") or "")))
            gs.sort(key=lambda g: (g["lang"] == "grc") if heb_first else (g["lang"] != "grc"))
            if english:
                report["English moved from value to note"] += 1
            if not gs:
                report["no gloss found"] += 1
                left.append((e["id"], "built form or no aligned word: the agent glosses it"
                             + (" (interlinear for a form built by rule)" if e.get("attested") == "by-rule" else "")))
                if not english:
                    continue
            else:
                report["proposed"] += 1
            new = dict(e, id=e["id"] if e["id"].endswith(".gloss") else e["id"] + ".gloss", supersedes=e["id"], value=value,
                       by="script:gloss.py", gloss=gs)
            for a in new.get("alternatives") or []:
                if isinstance(a, dict) and isinstance(a.get("value"), str):
                    a["value"], extra = split_value(a["value"], P.english_words)
                    if extra:
                        a["note"] = "; ".join([a.get("note", "")] * bool(a.get("note")) + [f"English: {x}" for x in extra])
            if english:
                new["note"] = "; ".join([e["note"]] * bool(e.get("note")) + [f"English: {x}" for x in english])
            if not gs:
                new.pop("gloss")
            if write:
                e["status"] = "superseded"
                add.append(new)
            else:
                print(f"{e['id']}: {value!r}" + "".join(f"\n    {line(g)}" for g in gs))
        if write and add:
            d["entries"] += add
            json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"{os.path.relpath(path, ROOT)}: {len(add)} entries with glosses appended (their old entries superseded)")
    print(f"{pname}: " + ", ".join(f"{k} {n}" for k, n in report.most_common()))
    if left:
        print(f"{len(left)} for the agent pass:")
        for i, why in left[:40]:
            print(f"  {i}: {why}")
        if len(left) > 40:
            print(f"  ... and {len(left) - 40} more")


def store_entries(pname):
    import langtools as LT
    P = LT.Project(pname)
    for fn in ("observations.json", "decisions.json", "external.json"):
        f = os.path.join(P.profile, fn)
        if os.path.exists(f):
            yield from json.load(open(f, encoding="utf-8")).get("entries", [])


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("check", "propose", "show", "words"):
        raise SystemExit(__doc__)
    if a[0] == "propose":
        return propose(a[1], "--write" in a)
    if a[0] == "words":
        import langtools as LT
        P, ref = LT.Project(a[1]), a[2].upper()
        m = REF.match(ref)
        if not m or m[1].lower() not in BY_CODE:
            raise SystemExit(f"{a[2]!r}: give a reference like \"MRK 1:38\"")
        nt = BY_CODE[m[1].lower()][2] == "nt"
        rows = ([(w, token("grc", k)) for w, k in greek_words(P, ref)] if nt else
                [(t[1], t) for t in tokens("heb", ref) if t[1]])
        lang = "grc" if nt else "hbo"
        for w, t in rows:
            if t:
                print(f"{w}\t{t[3]}\t{'content' if t[5] == 'c' else 'function'}\t"
                      f"{english({'lang': lang, 'form': t[1], 'ref': ref}, {t[0]})}")
        return
    if a[0] == "show":
        for e in store_entries(a[1]):
            if e.get("id") in a[2:]:
                print(f"{e['id']} ({e.get('status')}): {e.get('value')!r}")
                for g in glosses(e):
                    print("   ", line(g), *(f"\n    problem: {p}" for p in check(g)))
        return
    n, bad = collections.Counter(), 0
    for e in store_entries(a[1]):
        if e.get("status") == "superseded":
            continue
        for g in glosses(e):
            n["proposed" if g.get("proposed") else "confirmed"] += 1
            for p in check(g):
                bad += 1
                print(f"{e.get('id')}: {p}")
    print(f"{a[1]}: glosses {dict(n)}, {bad} problems")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
