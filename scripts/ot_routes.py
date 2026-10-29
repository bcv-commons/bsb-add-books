#!/usr/bin/env python3
"""The OT routes of the affix audit (scripts/morphs.py audit --route ...): the target words of the OT books the style
corpus has, linked to the Hebrew, with three independent readings of each Hebrew word (docs/language-store.md,
*The morph view*):

    hebrew   the Hebrew token's own features (orig/heb.sqlite, MACULA): person and number, negation from the clause,
             imperative / jussive / cohortative (mood=imperative; the two noted as modality), infinitive, participle, the
             object suffix of the clause, and the conjugation as a tense class (wayyiqtol, qatal: past; yiqtol, weqatal:
             non-past) -- a weak reading: Hebrew conjugations are aspect and discourse, not tense
    lxx      the Septuagint word MACULA gives for the token (its `greek` field), parsed: an identical NT form
             (orig/grc.sqlite, without accents) first, then an ending table (greek_parse)
    vamvas   the modern Greek word(s) of the Vamvas Bible (1850) aligned to the token by bcv-commons/full-alignments-llm,
             layer ell_GreVamvas+llm+jev-v4 (setup.py --only vamvas-align), on our import/CC0/ell/vamvas/ text once its
             fingerprint matches the layer file's; parsed by the same table plus the auxiliaries (θα / θέλω: future,
             να: subjunctive, ας: imperative, έχω: perfect)

The features use lang.greek_features' names, so one store entry's `greek` is tested on every route; route_want says
which claims a route can test (the Hebrew route has no subjunctive; the Greek routes no clause negation or object).

Target word -> Hebrew token: the project's OT links (_learn/links_hbo.tsv: target word and Hebrew lexeme per verse) where
the lexeme occurs once in the Hebrew verse (a verse where it repeats is skipped for that lexeme); token positions are used
instead if lang.sqlite has an `ot_links` table (book, ch, v, pos, key) beside nt_links.

    python3 scripts/ot_routes.py <project>          coverage per route and book; the Vamvas fingerprint check
"""
import collections, hashlib, json, os, re, sqlite3, sys, unicodedata

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
HEB = os.path.join(ROOT, "orig", "heb.sqlite")
GRC = os.path.join(ROOT, "orig", "grc.sqlite")
VAMVAS_LAYER = "ell_GreVamvas+llm+jev-v4"
VAMVAS_DIR = os.path.join(ROOT, "download", "full-alignments-llm", "e", "ell", VAMVAS_LAYER)
VAMVAS_TEXT = os.path.join(ROOT, "import", "CC0", "ell", "vamvas", "text")
FPS = os.path.join(VAMVAS_TEXT, "_fingerprints.json")
ROUTES = ("nt", "hebrew", "lxx", "vamvas")
NAMES = {"nt": "NT (Greek)", "hebrew": "OT Hebrew", "lxx": "OT LXX", "vamvas": "OT Vamvas"}

HEB_NEG = {"לֹא", "לָא", "אַל", "בַּל", "בְּלִי", "אַיִן", "בִּלְתִּי"}
TENSE_CLASS = {"aorist": "past", "imperfect": "past", "perfect": "past", "pluperfect": "past", "present": "nonpast",
               "future": "nonpast"}
HEB_CLASS = {"wayyiqtol": "past", "qatal": "past", "yiqtol": "nonpast", "weqatal": "nonpast"}
HEB_POS = {"verb": "verb", "noun": "noun", "adjective": "adj", "pronoun": "pron"}


# ---------- the Hebrew route ----------

def heb_book(book, con=None):
    """{(ch, v): [token rows]} of a Hebrew book (orig/heb.sqlite), in the Hebrew numbering"""
    con = con or sqlite3.connect(HEB)
    con.row_factory = sqlite3.Row
    out = collections.defaultdict(list)
    for r in con.execute("select * from tokens where book=? order by ch, v, word, n", (book.upper(),)):
        out[(r["ch"], r["v"])].append(r)
    return out


def heb_features(rows):
    """{key: {(feature, value)}} of a book's tokens (heb_book values): for verbs the design's mapping in the Greek names,
    plus tense_class (past / nonpast from the conjugation), conjugation and stem (for the re-label proposals)"""
    neg, obj = set(), {}
    for r in rows:
        if r["lemma"] in HEB_NEG and r["clause"]:
            neg.add(r["clause"])
        if r["role"] == "o" and r["pos"] in ("suffix", "pronoun") and r["person"] in ("first", "second", "third") \
                and r["clause"]:
            obj.setdefault(r["clause"], f"{'123'[['first', 'second', 'third'].index(r['person'])]}{(r['number'] or 's')[:1]}")
    out = {}
    for r in rows:
        fv = set()
        if r["pos"] == "verb":
            t = r["type"] or ""
            num = {"dual": "plural"}.get(r["number"], r["number"])
            mood = {"imperative": "imperative", "jussive": "imperative", "cohortative": "imperative",
                    "infinitive construct": "infinitive", "infinitive absolute": "infinitive",
                    "participle active": "participle", "participle passive": "participle"}.get(t)
            if t in ("jussive", "cohortative"):
                fv.add(("modality", t))
            if t in HEB_CLASS:
                fv.add(("tense_class", HEB_CLASS[t]))
                mood = "indicative"
            if mood:
                fv.add(("mood", mood))
            if t:
                fv.add(("conjugation", t))
            if r["stem"]:
                fv.add(("stem", r["stem"]))
            if num:
                fv.add(("number", num))
            if r["person"] in ("first", "second", "third") and num:
                fv |= {("person", r["person"]), ("person+number", f"{r['person'][:1]}{num[:1]}")}
                if mood == "imperative":
                    fv.add(("person+number+mood", f"{r['person'][:1]}{num[:1]}.imperative"))
            if r["clause"] in neg:
                fv.add(("negated", "yes"))
            if r["clause"] in obj:
                fv.add(("object", obj[r["clause"]]))
        out[r["key"]] = fv
    return out


# ---------- a Greek word parsed: identical NT forms first, then the ending table (LXX and Vamvas) ----------

def plain(w):
    """lower case, no accents or breathings, final sigma as σ, letters only"""
    s = "".join(c for c in unicodedata.normalize("NFD", (w or "").lower()) if not unicodedata.combining(c))
    return re.sub(r"[^α-ω]", "", s.replace("ς", "σ"))


_NT = None


def nt_forms(min_share=0.75):
    """{plain form: (tense, mood, person, number)} of the NT's verb forms (orig/grc.sqlite) where one parsing makes up
    min_share of the form's tokens"""
    global _NT
    if _NT is None:
        by = collections.defaultdict(collections.Counter)
        con = sqlite3.connect(GRC)
        for t, tense, mood, person, number in con.execute(
                "select text, tense, mood, person, number from tokens where class='verb'"):
            by[plain(t)][(tense, mood, person, number)] += 1
        _NT = {}
        for f, c in by.items():
            (p, n), = c.most_common(1)
            if f and n >= min_share * sum(c.values()):
                _NT[f] = p
    return _NT


P1, P2, P3 = "first", "second", "third"
S_, PL = "singular", "plural"
# (ending, tense, mood, person, number, needs: "aug" an augment, "noaug" none, None either), longest first within a group
ENDINGS = [
    # passive / middle futures and aorists
    ("θησονται", "future", "indicative", P3, PL, None), ("θησεται", "future", "indicative", P3, S_, None),
    ("θησομαι", "future", "indicative", P1, S_, None), ("θησεσθε", "future", "indicative", P2, PL, None),
    ("θησαν", "aorist", "indicative", P3, PL, None), ("θημεν", "aorist", "indicative", P1, PL, None),
    ("θητι", "aorist", "imperative", P2, S_, None), ("θητω", "aorist", "imperative", P3, S_, None),
    ("θητε", "aorist", "indicative", P2, PL, "aug"), ("θητε", "aorist", "subjunctive", P2, PL, "noaug"),
    ("θην", "aorist", "indicative", P1, S_, None), ("θησ", "aorist", "indicative", P2, S_, "aug"),
    ("θη", "aorist", "indicative", P3, S_, "aug"), ("θη", "aorist", "subjunctive", P3, S_, "noaug"),
    ("σαντο", "aorist", "indicative", P3, PL, None), ("σατο", "aorist", "indicative", P3, S_, None),
    ("σαμην", "aorist", "indicative", P1, S_, None), ("σασθαι", "aorist", "infinitive", None, None, None),
    # participles and infinitives
    ("μενοσ", "present", "participle", None, None, None), ("μενη", "present", "participle", None, None, None),
    ("μενον", "present", "participle", None, None, None), ("μενοι", "present", "participle", None, None, None),
    ("μενων", "present", "participle", None, None, None), ("ουσα", "present", "participle", None, None, None),
    ("οντεσ", "present", "participle", None, None, None), ("οντοσ", "present", "participle", None, None, None),
    ("σαντεσ", "aorist", "participle", None, None, None), ("σασα", "aorist", "participle", None, None, None),
    ("σθαι", "present", "infinitive", None, None, None), ("ναι", "aorist", "infinitive", None, None, None),
    ("σαι", "aorist", "infinitive", None, None, None), ("ειν", "present", "infinitive", None, None, None),
    # imperatives
    ("τωσαν", None, "imperative", P3, PL, None), ("σατω", "aorist", "imperative", P3, S_, None),
    ("ετω", "present", "imperative", P3, S_, None), ("ατω", "present", "imperative", P3, S_, None),
    ("σον", "aorist", "imperative", P2, S_, "noaug"),
    # middle / passive indicatives
    ("ονται", "present", "indicative", P3, PL, None), ("ουνται", "present", "indicative", P3, PL, None),
    ("ομεθα", "present", "indicative", P1, PL, "noaug"), ("ομαι", "present", "indicative", P1, S_, None),
    ("εται", "present", "indicative", P3, S_, None), ("ειται", "present", "indicative", P3, S_, None),
    ("αται", "present", "indicative", P3, S_, None), ("οντο", "imperfect", "indicative", P3, PL, None),
    ("ετο", "imperfect", "indicative", P3, S_, None), ("ειτο", "imperfect", "indicative", P3, S_, None),
    ("ομην", "imperfect", "indicative", P1, S_, None),
    # perfects
    ("κασιν", "perfect", "indicative", P3, PL, None), ("κασι", "perfect", "indicative", P3, PL, None),
    ("καμεν", "perfect", "indicative", P1, PL, "noaug"), ("κατε", "perfect", "indicative", P2, PL, "noaug"),
    # futures
    ("σουσιν", "future", "indicative", P3, PL, None), ("σουσι", "future", "indicative", P3, PL, None),
    ("σομεν", "future", "indicative", P1, PL, None), ("σετε", "future", "indicative", P2, PL, "noaug"),
    ("σεισ", "future", "indicative", P2, S_, None), ("σει", "future", "indicative", P3, S_, None),
    ("σω", "future", "indicative", P1, S_, None),
    # subjunctives
    ("σωσιν", "aorist", "subjunctive", P3, PL, None), ("σωσι", "aorist", "subjunctive", P3, PL, None),
    ("σωμεν", "aorist", "subjunctive", P1, PL, None), ("ωμεν", "present", "subjunctive", P1, PL, None),
    ("ητε", "present", "subjunctive", P2, PL, None),
    # aorists (sigmatic) and the past
    ("σαμεν", "aorist", "indicative", P1, PL, None), ("σατε", "aorist", "indicative", P2, PL, "aug"),
    ("σατε", "aorist", "imperative", P2, PL, "noaug"), ("σαν", "aorist", "indicative", P3, PL, None),
    ("σασ", "aorist", "indicative", P2, S_, "aug"), ("σασ", "aorist", "participle", None, None, "noaug"),
    ("σεν", "aorist", "indicative", P3, S_, None), ("σε", "aorist", "indicative", P3, S_, "aug"),
    ("σα", "aorist", "indicative", P1, S_, "aug"), ("οσαν", None, "indicative", P3, PL, None),
    ("κεν", None, "indicative", P3, S_, None), ("ον", None, "indicative", None, None, "aug"),
    ("εσ", None, "indicative", P2, S_, "aug"), ("εν", None, "indicative", P3, S_, "aug"),
    ("ε", None, "indicative", P3, S_, "aug"), ("αν", None, "indicative", P3, PL, "aug"),
    # presents
    ("ουσιν", "present", "indicative", P3, PL, None), ("ουσι", "present", "indicative", P3, PL, None),
    ("ουν", "present", "indicative", P3, PL, "noaug"), ("ωσιν", "present", "subjunctive", P3, PL, None),
    ("ομεν", "present", "indicative", P1, PL, "noaug"), ("ουμεν", "present", "indicative", P1, PL, None),
    ("ουμε", "present", "indicative", P1, PL, None), ("ειτε", "present", "indicative", P2, PL, None),
    ("ετε", "present", "indicative", P2, PL, "noaug"), ("εισ", "present", "indicative", P2, S_, None),
    ("ει", "present", "indicative", P3, S_, "noaug"), ("ω", "present", "indicative", P1, S_, "noaug"),
]
PREVERBS = ("απ", "αφ", "εξ", "εκ", "εισ", "κατ", "καθ", "μετ", "μεθ", "παρ", "περι", "προσ", "προ", "συν", "συ", "επ", "εφ",
            "υπ", "υφ", "αν", "δι", "εν", "εμ", "αντ", "ανθ")
IRREGULAR = {"ητο": ("imperfect", "indicative", P3, S_), "ητον": ("imperfect", "indicative", P3, S_),
             "ησαν": ("imperfect", "indicative", P3, PL), "ημην": ("imperfect", "indicative", P1, S_),
             "εισαι": ("present", "indicative", P2, S_), "ειναι": ("present", "indicative", P3, None),
             "ειμαι": ("present", "indicative", P1, S_), "εισθε": ("present", "indicative", P2, PL),
             "ειμεθα": ("present", "indicative", P1, PL), "ειπε": ("aorist", "indicative", P3, S_),
             "ειπεν": ("aorist", "indicative", P3, S_), "ειπον": ("aorist", "indicative", None, None),
             "λεγων": ("present", "participle", None, None), "λεγοντεσ": ("present", "participle", None, None)}


def augmented(w):
    if w[:1] in ("ε", "η") or w[:2] in ("ει", "ηυ"):
        return True
    for p in PREVERBS:
        if w.startswith(p) and len(w) > len(p) + 3 and w[len(p)] in ("ε", "η"):
            return True
    return False


def ending_parse(w):
    """(tense, mood, person, number) of a plain (accentless) Greek verb form by its ending, or None"""
    if w in IRREGULAR:
        return IRREGULAR[w]
    aug = augmented(w)
    for end, tense, mood, person, number, need in ENDINGS:
        if len(w) > len(end) + 1 and w.endswith(end) and (need is None or (need == "aug") == aug):
            if tense is None and mood == "indicative" and aug:
                tense = "past"                       # second aorist or imperfect: past, the tense not decided
            return (tense, mood, person, number)
    return None


THELO = {"θελω": (P1, S_), "θελεισ": (P2, S_), "θελει": (P3, S_), "θελομεν": (P1, PL), "θελουμεν": (P1, PL),
         "θελετε": (P2, PL), "θελουσι": (P3, PL), "θελουσιν": (P3, PL), "θελουν": (P3, PL)}
ECHO = {"εχω": ("perfect", P1, S_), "εχεισ": ("perfect", P2, S_), "εχει": ("perfect", P3, S_), "εχομεν": ("perfect", P1, PL),
        "εχετε": ("perfect", P2, PL), "εχουσι": ("perfect", P3, PL), "εχουν": ("perfect", P3, PL),
        "ειχον": ("pluperfect", None, None), "ειχε": ("pluperfect", P3, S_), "ειχεν": ("pluperfect", P3, S_),
        "ειχομεν": ("pluperfect", P1, PL), "ειχετε": ("pluperfect", P2, PL), "ειχαν": ("pluperfect", P3, PL)}


def greek_parse(words, modern=False):
    """(tense, mood, person, number, how) of the Greek word(s) rendering one Hebrew word, or None. how: 'nt-form' (an
    identical NT form), 'ending' (the table), 'aux' (modern: an auxiliary θα / θέλω, να, ας, έχω decided the tense or
    mood). The last word that parses is the verb (articles, particles and pronouns come before it)"""
    ws = [plain(w) for w in (words if isinstance(words, (list, tuple)) else [words])]
    ws = [w for w in ws if w]
    if not ws:
        return None
    nt = nt_forms()
    aux = None
    if modern:
        for w in ws:
            if w == "θα":
                aux = ("future", "indicative", None, None)
            elif w in THELO:
                aux = ("future", "indicative") + THELO[w]
            elif w in ("να", "ινα"):
                aux = (None, "subjunctive", None, None)
            elif w == "ασ":
                aux = (None, "imperative", None, None)
            elif w in ECHO:
                aux = (ECHO[w][0], "indicative", ECHO[w][1], ECHO[w][2])
    main, how = None, None
    for w in reversed(ws):
        if w in ("θα", "να", "ινα", "ασ", "μη", "μην", "δεν", "ου", "ουκ") or w in THELO or w in ECHO:
            continue
        if w in nt:
            main, how = nt[w], "nt-form"
            break
        p = ending_parse(w)
        if p:
            main, how = p, "ending"
            break
    if aux:
        t, m, pe, nu = aux
        if main:
            pe, nu = pe or main[2], nu or main[3]
            if t is None:                        # να / ας + verb: the verb's aspect (aorist or present stem)
                t = main[0] if main[0] in ("aorist", "present") else None
        return (t, m, pe, nu, "aux")
    return (*main, how) if main else None


def greek_feature_set(p):
    """{(feature, value)} of a greek_parse result, in lang.greek_features' names, plus tense_class and aspect"""
    if not p:
        return set()
    tense, mood, person, number = p[:4]
    out = set()
    if tense and tense != "past":
        out.add(("tense", tense))
    if tense:
        out.add(("tense_class", TENSE_CLASS.get(tense, "past" if tense == "past" else None)))
        out.add(("aspect", {"aorist": "perfective", "present": "imperfective", "imperfect": "imperfective",
                            "perfect": "perfect", "pluperfect": "perfect", "future": "future"}.get(tense, "past")))
    if mood:
        out.add(("mood", mood))
    if person:
        out.add(("person", person))
    if number:
        out.add(("number", number))
    if person and number:
        out.add(("person+number", f"{person[:1]}{number[:1]}"))
        if mood in ("subjunctive", "imperative", "optative"):
            out.add(("person+number+mood", f"{person[:1]}{number[:1]}.{mood}"))
    if tense and tense != "past" and mood:
        out.add(("tense+mood", f"{tense}.{mood}"))
    return {x for x in out if x[1]}


# ---------- the Vamvas route ----------

def vamvas_rows(code):
    """[(c, v, text)] of our Vamvas copy in the Hebrew numbering (as it is filed), or None"""
    f = os.path.join(VAMVAS_TEXT, f"{code.lower()}.txt")
    if not os.path.exists(f):
        return None
    out = []
    for l in open(f, encoding="utf-8"):
        cv, _, t = l.rstrip("\n").partition("\t")
        if ":" in cv:
            c, v = cv.split(":")
            out.append((int(c), int(v), t))
    return out


def english_rows(code, rows):
    """our Hebrew-numbered rows put back into the module's (KJV) numbering, as the layer was fingerprinted: a psalm
    title back into verse 1, merged Hebrew verses together under their English verse"""
    import vrs
    by = {}
    for c, v, t in rows:
        if not t:
            continue
        ec, ev = vrs.to_bsb(code.lower(), c, v)
        if ev == "title":
            ec, ev = c, 1
        k = (int(ec), int(ev))
        by[k] = (by.get(k, "") + " " + t).strip()
    return [(c, v, t) for (c, v), t in by.items()]


def vamvas_check():
    """{BOOK: (layer file or None, our fingerprint, layer fingerprint, match)} of the layer's OT books; our text is
    fingerprinted in the module's numbering (english_rows)"""
    import full_align as FA
    man = os.path.join(VAMVAS_DIR, "manifest.json")
    if not os.path.exists(man):
        return {}
    books = json.load(open(man, encoding="utf-8"))["languages"]["ell"]["layers"][VAMVAS_LAYER]["books"]
    out = {}
    for b, f in books.items():
        path = os.path.join(VAMVAS_DIR, f)
        if not os.path.exists(path):
            continue
        theirs = f[:-5].split("_", 1)[1][:8]
        rows = vamvas_rows(b)
        mine = FA.text_fingerprint(english_rows(b, rows))[0][:8] if rows else None
        if mine != theirs and os.path.exists(FPS):
            # a Hebrew verse that holds two English ones (ISA 63:19 + 64:1) can't be split back: the fetch recorded the
            # fingerprint of the module's own numbering, valid while our file is the one it wrote (its SHA-256)
            rec = json.load(open(FPS, encoding="utf-8")).get(b) or {}
            ours = os.path.join(VAMVAS_TEXT, f"{b.lower()}.txt")
            if rec.get("text_sha256") == hashlib.sha256(open(ours, "rb").read()).hexdigest():
                mine = rec["module"][:8]
        out[b] = (path, mine, theirs, mine == theirs)
    return out


def vamvas_words(book, check=None):
    """{Hebrew key: [Vamvas words]} of a book (the layer's main rows on our text, positions counted by compact-alignments'
    tokenizer in the Hebrew-numbered verse), or None when the book's fingerprint doesn't match ours"""
    import full_align as FA
    ck = (check if check is not None else vamvas_check()).get(book.upper())
    if not ck or not ck[3]:
        return None
    text = {(c, v): t for c, v, t in vamvas_rows(book)}
    keys = FA.index(book.upper(), "keys")
    out = collections.defaultdict(list)
    for ref, s in zip(FA.index(book.upper(), "lexemes"), json.load(open(ck[0], encoding="utf-8"))):
        c, v = (int(x) for x in ref.split(" ")[1].split(":"))
        toks = FA.tokenize(text.get((c, v), ""))
        ks = keys.get(ref, [])
        if not s or not toks:
            continue
        for o, ids in FA.parse(s.split("|")[0]).items():
            if o < len(ks) and ks[o]:
                ws = [toks[i] for i in sorted(ids) if i < len(toks)]
                for k in ks[o].split("+"):
                    out[k] += ws
    return out


# ---------- target word -> Hebrew token ----------

def ot_books(P):
    """the OT books (codes, lower case) of the project's corpus"""
    from books import BY_CODE
    return sorted({r[1] for r in P.corpus() if BY_CODE.get(r[1], (0, 0, ""))[2] == "ot"})


def whole_words(P, text, hyphen):
    """{plain token: [exact words]} of a verse: with hyphen parts a piece ("-ein", and the piece before it) maps to
    the whole hyphen word (tamu-ko)"""
    pl, ex = P.tok.tokens(text), P.tok.tokens(text, exact=True)
    if len(pl) != len(ex):
        ex = pl
    whole = list(ex)
    if hyphen:
        i = 0
        while i < len(ex):
            j = i + 1
            while j < len(ex) and pl[j].startswith("-"):
                j += 1
            if j > i + 1:
                w = ex[i] + "".join(ex[i + 1:j])
                for k in range(i, j):
                    whole[k] = w
            i = j
    out = collections.defaultdict(list)
    for p, w in zip(pl, whole):
        if w not in out[p]:
            out[p].append(w)
    return out


def ot_links(P, hyphen=False, books=None):
    """[(book, ch, v, exact target word, Hebrew key)] of the OT: by lang.sqlite's ot_links where it has one, else
    _learn/links_hbo.tsv with the lexeme unique in its Hebrew verse. -> (links, figures {book: (links, kept, skipped as
    repeated lexeme)})"""
    con = sqlite3.connect(HEB)
    books = books or ot_books(P)
    texts = {(r[1], r[2]): r[4] for r in P.corpus() if r[1] in books}
    db = os.path.join(P.learn, "lang.sqlite")
    out, fig = [], {}
    if os.path.exists(db):
        lc = sqlite3.connect(db)
        if lc.execute("select 1 from sqlite_master where name='ot_links'").fetchone():
            for b, c, v, pos, key in lc.execute("select book, ch, v, pos, key from ot_links"):
                if b.lower() in books:
                    toks = P.tok.tokens(texts.get((b.lower(), (c, v)), ""), exact=True)
                    if pos < len(toks):
                        out.append((b.upper(), c, v, toks[pos], key))
            return out, {b: (len(out), len(out), 0) for b in books}
    f = os.path.join(P.learn, "links_hbo.tsv")
    if not os.path.exists(f):
        return [], {}
    links = collections.defaultdict(list)
    for l in open(f, encoding="utf-8"):
        p = l.rstrip("\n").split("\t")
        if len(p) < 3 or not p[2].startswith("hbo:"):
            continue
        m = re.match(r"([1-3A-Z]{3}) (\d+):(\d+)$", p[0])
        if m and m[1].lower() in books:
            links[(m[1], int(m[2]), int(m[3]))].append((p[1], p[2][4:]))
    for b in books:
        heb = heb_book(b, con)
        n = kept = rep = 0
        for (B, c, v), ls in links.items():
            if B.lower() != b:
                continue
            toks = heb.get((c, v), [])
            by_lex = collections.defaultdict(list)
            for r in toks:
                by_lex[r["lexeme"]].append(r["key"])
            words = whole_words(P, texts.get((b, (c, v)), ""), hyphen)
            seen = set()
            for w, lex in ls:
                n += 1
                ks = by_lex.get(lex, [])
                if len(ks) != 1:
                    rep += len(ks) > 1
                    continue
                for ww in words.get(w, []):
                    if (ww, ks[0]) not in seen:
                        seen.add((ww, ks[0]))
                        out.append((B, c, v, ww, ks[0]))
                        kept += 1
        fig[b] = (n, kept, rep)
    return out, fig


# ---------- the rows the audit measures ----------

def route_tokens(pname, S, route, P=None, report=None):
    """morphs.affix_tokens' rows for an OT route: (class, {(affix, position)}, stem, features, even verse, ref, exact
    word, the reading's lemma or word). One row per target word form and Hebrew token linked to each other; the
    class is the Hebrew token's (verb, noun, ...). report: a dict filled with coverage figures"""
    import langtools as LT
    P = P or LT.Project(pname)
    links, fig = ot_links(P, getattr(S, "hyphen", False))
    con = sqlite3.connect(HEB)
    rows, books = [], sorted({l[0] for l in links})
    check = vamvas_check() if route == "vamvas" else {}
    cov = {}
    for b in books:
        heb = heb_book(b, con)
        tok = {r["key"]: r for rs in heb.values() for r in rs}
        hf = heb_features([r for rs in heb.values() for r in rs]) if route == "hebrew" else None
        vw = vamvas_words(b, check) if route == "vamvas" else None
        c = collections.Counter()
        for B, ch, v, w, key in (l for l in links if l[0] == b):
            r = tok.get(key)
            if r is None:
                continue
            cls = HEB_POS.get(r["pos"], r["pos"])
            verb = r["pos"] == "verb"
            c["links"] += 1
            c["verb links"] += verb
            if route == "hebrew":
                fv, lemma = hf.get(key, set()), r["lemma"]
            elif route == "lxx":
                g = r["greek"]
                p = greek_parse(g) if verb and g else None
                if verb:
                    c["with a word"] += bool(g)
                    c[f"parsed ({p[4]})" if p else "unparsed"] += bool(g)
                fv, lemma = greek_feature_set(p) if verb else set(), g or ""
            else:
                if vw is None:
                    continue
                ws = vw.get(key, [])
                p = greek_parse(ws, modern=True) if verb and ws else None
                if verb:
                    c["with a word"] += bool(ws)
                    c[f"parsed ({p[4]})" if p else "unparsed"] += bool(ws)
                fv, lemma = greek_feature_set(p) if verb else set(), " ".join(ws)
            ms = S.split(w)
            stem = next((m.form for m in ms if m.slot == "stem"), "")
            rows.append((cls, {(m.form, m.position) for m in ms if m.slot != "stem"}, stem, fv, v % 2 == 0,
                         f"{B} {ch}:{v}", w, lemma))
        if route == "vamvas" and vw is None:
            ck = check.get(b)
            c["skipped"] = 1
            c["why"] = ("no layer file" if not ck else f"fingerprint ours {ck[1]} / layer {ck[2]}")
        cov[b] = (fig.get(b.lower()), dict(c))
    if report is not None:
        report.update(cov)
    return rows


def route_want(route, want):
    """(the claim in the route's features, weak, why not) for a store entry's `greek` ({name: {values}}): None and the
    reason when the route can't test it"""
    if not want:
        return None, False, "no claim"
    if route == "nt":
        return want, False, None
    out, weak = {}, False
    for k, vs in want.items():
        if route == "hebrew":
            if k in ("person", "number", "person+number", "negated", "object"):
                out[k] = vs
            elif k == "mood":
                if not vs <= {"imperative", "infinitive", "participle", "indicative"}:
                    return None, False, "the Hebrew has no subjunctive or optative"
                out[k] = vs
            elif k == "person+number+mood":
                if not all(v.endswith(".imperative") for v in vs):
                    return None, False, "the Hebrew has no subjunctive or optative"
                out[k] = vs
            elif k in ("tense", "tense+mood"):
                cl = {TENSE_CLASS.get(v.split(".")[0]) for v in vs}
                if None in cl or len(cl) != 1:
                    return None, False, "the tenses span past and non-past"
                out["tense_class"], weak = cl, True
            else:
                return None, False, f"the Hebrew route has no {k}"
        else:
            if k in ("person", "number", "person+number", "tense", "mood", "tense+mood", "person+number+mood"):
                out[k] = vs
            else:
                return None, False, f"a {k} claim needs the clause (NT or Hebrew route)"
    return out, weak, None


ALT_KEYS = {"nt": ("tense", "mood", "person+number"), "hebrew": ("conjugation", "tense_class", "person+number", "stem"),
            "lxx": ("tense", "mood", "aspect", "person+number"), "vamvas": ("tense", "mood", "aspect", "person+number")}


def coverage(pname, routes=("hebrew", "lxx", "vamvas")):
    import langtools as LT
    import morphs
    P = LT.Project(pname)
    S = morphs.load(pname, P)
    out = {}
    for r in routes:
        rep = {}
        route_tokens(pname, S, r, P, rep)
        out[r] = rep
    return out


def ending_accuracy():
    """the ending table on the NT's own verb forms (types the NT lookup parses): {feature: (right, compared)} and the
    share of types it parses at all; a past of undecided tense counts right for an aorist or imperfect"""
    nt, out, parsed = nt_forms(), collections.defaultdict(lambda: [0, 0]), 0
    for f, p in nt.items():
        e = ending_parse(f)
        if not e:
            continue
        parsed += 1
        for i, k in enumerate(("tense", "mood", "person", "number")):
            if e[i] and p[i]:
                out[k][1] += 1
                out[k][0] += e[i] == p[i] or (k == "tense" and e[i] == "past" and p[i] in ("aorist", "imperfect"))
    return {k: tuple(v) for k, v in out.items()}, parsed / max(1, len(nt))


def main(a):
    if not a:
        raise SystemExit(__doc__)
    ck = vamvas_check()
    print("Vamvas layer (fingerprint of our text in the module's numbering / the layer file's):")
    bad = [b for b, x in sorted(ck.items()) if not x[3]]
    print(f"  {len(ck) - len(bad)} of {len(ck)} OT books match" + (f"; not: {', '.join(bad)}" if bad else ""))
    acc, cov = ending_accuracy()
    print(f"Ending table on the NT's verb form types: parses {cov:.0%}; right: "
          + ", ".join(f"{k} {r / n:.0%} of {n}" for k, (r, n) in acc.items()))
    for route, rep in coverage(a[0]).items():
        print(f"\n{NAMES[route]}:")
        for b, (fig, c) in sorted(rep.items()):
            print(f"  {b}: links {fig[0] if fig else '-'}, kept {fig[1] if fig else '-'} (lexeme repeated in the verse: "
                  f"{fig[2] if fig else '-'}); " + ", ".join(f"{k} {v}" for k, v in c.items()))


if __name__ == "__main__":
    main(sys.argv[1:])
