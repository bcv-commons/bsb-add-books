"""Shared pieces of the language toolkit (docs/onboarding.md): a project's style corpus
paired with the assisting translation, the target-language tokeniser, chrF.

Nothing here knows a language. The tokeniser is configured in project.yaml:

    tokenise:
      split_hyphens: true        # 'Yesu-qa' -> 'yesu' '-qa' (suffixes written with a hyphen)
      word_chars: [U+A789, U+0304]   # characters that belong to words besides letters (U+ or literal)
      ignore_marks: [U+0300]     # marks removed for matching; default: the store's orthography.ignore_marks

and the corpus is the project's style_from editions (their text/ folders), paired verse by verse with the
assisting translation (BSB, or MSB for a majority-text NT). OT editions keep the Hebrew verse numbering;
they are paired with the BSB through orig/vrs.
"""
import collections, glob, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from books import BY_CODE  # noqa: E402
from project import project, sources, edition, project_dir  # noqa: E402
import vrs  # noqa: E402


def _word_marks():
    """A regex class body: every combining mark (Unicode categories Mn, Mc, Me) and the zero-width (non-)joiner. In
    many scripts they sit inside words (Indic vowel signs and virama, Hebrew points, Arabic vowels, Thai vowels, tone
    marks), and \\w doesn't match them: without them a word in Odia or Devanagari falls apart into its letters."""
    rs, start = [], None
    for c in [*range(0x20000), *range(0xE0100, 0xE01F0)] + [None]:
        m = c is not None and unicodedata.category(chr(c))[0] == "M"
        if m and start is None:
            start = c
        elif not m and start is not None:
            rs.append((start, prev))
            start = None
        prev = c
    return "".join(re.escape(chr(a)) + ("-" + re.escape(chr(b)) if b > a else "") for a, b in rs) + "\u200c\u200d"


WORD_MARKS = _word_marks()

_INHERENT = None


def romanise(s):
    """A rough Latin reading of a word in another script, from the Unicode character names, with for each Latin letter
    the index of the character it comes from: (latin, owners). Latin letters stay as they are. In the scripts with an
    inherent vowel (those that have a virama: Devanagari, Bengali, Odia, Tamil, ...) a consonant reads with 'a'
    ('ORIYA LETTER KA' -> ka), a vowel sign replaces it, the virama removes it; anusvara and candrabindu read n, visarga
    h. Elsewhere a letter reads as its name's last word (CYRILLIC SMALL LETTER EF -> ef): only good enough to line names
    up, as scripts/lang.py's name letters do."""
    global _INHERENT
    if _INHERENT is None:
        _INHERENT = {unicodedata.name(chr(c)).split(" SIGN ")[0] for c in range(0x900, 0x2000)
                     if unicodedata.name(chr(c), "").endswith("SIGN VIRAMA")}
    out, own = [], []
    for i, c in enumerate(s):
        n = unicodedata.name(c, "")
        if not n or "LATIN" in n or not c.isalpha() and unicodedata.category(c)[0] != "M":
            if c.isalpha():
                out.append(c.lower()); own.append(i)
            continue
        script = re.split(r" (?:CAPITAL |SMALL )?(?:LETTER|VOWEL SIGN|SIGN) ", n)[0]
        word = n.split()[-1].lower()
        if script in _INHERENT:
            if " VOWEL SIGN " in n:
                if out and out[-1] == "a":
                    out.pop(); own.pop()
                word = n.split(" VOWEL SIGN ")[-1].split()[0].lower()
            elif n.endswith("SIGN VIRAMA"):
                if out and out[-1] == "a":
                    out.pop(); own.pop()
                continue
            elif n.endswith(("SIGN ANUSVARA", "SIGN CANDRABINDU")):
                word = "n"
            elif n.endswith("SIGN VISARGA"):
                word = "h"
            elif " SIGN " in n and " LETTER " not in n:
                continue                                  # nukta, avagraha and other signs: no sound of their own
        elif " LETTER " not in n:
            continue
        elif len(word) > 1:                               # an alphabet's letter name: its consonant (ef, be, ghe, beh)
            word = (word[1:] if word[0] == "e" else word[:-2] if word.endswith("eh") else
                    word[:-1] if word[-1] in "ae" and word[0] not in "aeiou" else word)
        out += list(word); own += [i] * len(word)
    return "".join(out), own


def verses_of(path):
    """{(chapter, verse): text} of a repo chapter file (<code>NNN.txt: vN markers; notes, headings and poetry
    marks removed; a bridge 'v21-22' is keyed by its first verse), or of a book file (<code>.txt: lines
    'chapter:verse<TAB>text', headings '== … ==' and 'Chapter N' lines skipped)."""
    if re.fullmatch(r"[0-9a-z]{3}\.txt", os.path.basename(path)):
        out = {}
        for l in open(path, encoding="utf-8").read().splitlines():
            m = re.match(r"(\d+):(\d+)\t(.*)$", l)
            if m:
                out[(int(m[1]), int(m[2]))] = re.sub(r"\s+", " ", re.sub(r"\{[A-Z]:[^{}]*\}", " ", m[3])).strip()
        return out
    ch = int(os.path.basename(path)[3:6])
    body = [re.sub(r"^//\d+ ", "", l) for l in open(path, encoding="utf-8").read().splitlines()
            if not l.startswith(("!!", "===")) and not re.fullmatch(r"==.*==", l)]
    text = re.sub(r"\{[A-Z]:[^{}]*\}", " ", " ".join(body))
    parts = re.split(r"(?<![\w>.])v(\d+)(?:-\d+)?(?=\s)", text)
    return {(ch, int(parts[i])): re.sub(r"\s+", " ", parts[i + 1]).strip() for i in range(1, len(parts) - 1, 2)}


class Tokeniser:
    def __init__(self, cfg=None, marks=()):
        cfg = cfg or {}
        self.split = bool(cfg.get("split_hyphens", False))
        ch = lambda m: chr(int(m[2:], 16)) if m.upper().startswith("U+") else m
        wc = cfg.get("word_chars") or []
        self.extra = "".join(ch(c) for c in (wc if isinstance(wc, list) else list(wc)))
        self.marks = {ch(m) for m in (cfg.get("ignore_marks") or marks)}
        # combining marks belong to the word (\w doesn't match them): the plain forms keep those not ignored, the exact
        # forms every one
        cm = re.escape(self.extra) + WORD_MARKS
        self.rx = re.compile(rf"[\w{cm}]+(?:-[\w{cm}]+)*" if self.split else rf"[\w{cm}]+")
        self.rx_exact = self.rx

    def plain(self, s):
        """Lower case, the ignored marks removed (NFC)."""
        s = unicodedata.normalize("NFD", s.lower())
        return unicodedata.normalize("NFC", "".join(c for c in s if c not in self.marks))

    def exact(self, s):
        """Lower case, every mark kept (NFC): the form as the edition writes it."""
        return unicodedata.normalize("NFC", s.lower())

    def tokens(self, s, exact=False):
        """Word tokens (suffixes after a hyphen as '-x' tokens when split_hyphens). Matching uses the plain tokens (the
        ignored marks removed: an agent's search finds every spelling); exact=True keeps the marks, for spelling."""
        out = []
        for w in (self.rx_exact.findall(self.exact(s)) if exact else self.rx.findall(self.plain(s))):
            w = w.strip("\u200c\u200d")                    # a joiner at the word's edge is display (after a final virama)
            if self.split and "-" in w:
                first, *rest = w.split("-")
                out += ([first] if first else []) + ["-" + r for r in rest if r]
            else:
                out.append(w)
        return [t for t in out if not self.plain(t).isdigit()]   # a number with a stray mark too: exact and plain align


def usfm_verses(text):
    """{(BOOK, chapter, verse): text} of a USFM file (notes, cross references and markers removed)."""
    m = re.search(r"\\id (\w+)", text)
    code = m[1].upper() if m else "?"
    text = re.sub(r"\\f .*?\\f\*|\\x .*?\\x\*", " ", text, flags=re.S)
    out = {}
    for part in re.split(r"\\c (?=\d)", text)[1:]:
        ch = int(re.match(r"\d+", part)[0])
        for v in re.finditer(r"\\v (\d+)\S*\s+(.*?)(?=\\v \d|\Z)", part, re.S):
            t = re.sub(r"\\\+?[a-z0-9]+\*?|\|[^\\\s]*", " ", v[2])
            out[(code, ch, int(v[1]))] = re.sub(r"\s+", " ", t).strip()
    return out


def published_verses(ed):
    """The published text of an edition, for checking quotations: its `published_text` (a USFM zip or folder)
    or else its text/ folder, plus `published_also` (further USFM files or folders: books published elsewhere, such as
    an OT book published apart from the NT). {"BOOK c:v": text}; None if a published text named isn't there."""
    import zipfile
    src = ed.get("published_text")
    out = {}
    if not src:
        d = os.path.join(ROOT, ed["dir"], ed.get("text_dir", "text"))
        for f in sorted(glob.glob(os.path.join(d, "*.txt"))):
            b = os.path.basename(f)
            if re.fullmatch(r"[0-9a-z]{3}(\d{3})?\.txt", b):
                out.update({f"{b[:3].upper()} {c}:{v}": t for (c, v), t in verses_of(f).items()})
        return out
    path = os.path.join(ROOT, src)
    if not os.path.exists(path):
        return None
    if path.endswith(".zip"):
        z = zipfile.ZipFile(path)
        files = [(n, z.read(n).decode("utf-8", "replace")) for n in z.namelist() if n.lower().endswith((".usfm", ".sfm"))]
    else:
        files = [(f, open(f, encoding="utf-8").read()) for f in glob.glob(os.path.join(path, "*.*sfm"))]
    for extra in ed.get("published_also") or []:
        xp = os.path.join(ROOT, extra)
        if not os.path.exists(xp):
            return None
        files += [(f, open(f, encoding="utf-8-sig").read()) for f in ([xp] if os.path.isfile(xp) else
                                                                     glob.glob(os.path.join(xp, "*.*sfm")))]
    for _, t in files:
        out.update({f"{b} {c}:{v}": x for (b, c, v), x in usfm_verses(t).items()})
    return out


def eng_tokens(s):
    return re.findall(r"[a-z]+(?:'[a-z]+)?", s.lower().replace("’", "'"))


class Project:
    """A project's corpus, tokeniser and folders."""

    def __init__(self, name):
        self.name = name
        self.p = project(name)
        self.dir = project_dir(name)
        self.learn = os.path.join(self.dir, "_learn")
        self.profile = os.path.join(self.dir, "profile")
        marks = []
        for fn in ("observations.json", "decisions.json"):
            f = os.path.join(self.profile, fn)
            if os.path.exists(f):
                marks += (json.load(open(f, encoding="utf-8")).get("orthography") or {}).get("ignore_marks", [])
        self.tok = Tokeniser(self.p.get("tokenise"), marks)
        self.editions = [edition(e) for e in self.p["style_from"]]
        self._rows = None
        self._spell = None
        self._seg = None

    def spellings(self):
        """{plain token: Counter(exact token)}: how the corpus writes each form that matching sees without the ignored
        marks (a tone or accent mark the tokenizer is told to ignore). The tools match on plain forms but must show and check these."""
        if self._spell is None:
            sp = collections.defaultdict(collections.Counter)
            for r in self.corpus():
                for w in self.tok.tokens(r[4], exact=True):
                    sp[self.tok.plain(w)][w] += 1
            self._spell = sp
        return self._spell

    def english_words(self, text):
        """the words of a store value that are English, not the target language: words of the assisting translation
        that the corpus never writes (a gloss or an explanation left in a value)"""
        if getattr(self, "_eng", None) is None:
            self._eng = {w.lower() for r in self.corpus() for w in re.findall(r"[A-Za-z]+", r[3])}
        sp = self.spellings()
        return [w for w in re.findall(r"[A-Za-z]+", re.sub(r"<[^<>]*>", " ", text or ""))
                if len(w) > 1 and w.lower() in self._eng and self.tok.plain(w) not in sp]

    def store_forms(self):
        """Exact tokens of the live term, formula and name entries' values and alternatives (they count as attested): the
        target language only, so English in brackets (a gloss left in a value) and <slot> placeholders are left out, and
        glosses (Greek, Hebrew) never count."""
        out = set()
        for fn in ("observations.json", "decisions.json"):
            f = os.path.join(self.profile, fn)
            if os.path.exists(f):
                for e in json.load(open(f, encoding="utf-8")).get("entries", []):
                    if e.get("status") in ("superseded", "rejected") or e.get("kind") not in ("term", "formula", "name"):
                        continue
                    for v in [e.get("value")] + [a.get("value") for a in e.get("alternatives") or [] if isinstance(a, dict)]:
                        if isinstance(v, str):
                            v = re.sub(r"<[^<>]*>|\([^()]*\)", " ", v)
                            eng = {w.lower() for w in self.english_words(v)} if e.get("kind") != "name" else set()
                            out.update(t for t in self.tok.tokens(v, exact=True) if t.lower() not in eng)
        return out

    def spell_check(self, text):
        """Spelling of a draft against the corpus, as the edition writes it (every mark kept).
        Returns (marks, unknown): marks = [(form, n, corpus spellings)] for forms the corpus has only with other marks
        (zøveqase -> zøveqasé), unknown = [(form, n)] for forms it doesn't have at all (new names, new words, typos).
        The store's decided forms count as attested."""
        sp, store = self.spellings(), self.store_forms()
        seen = collections.Counter(self.tok.tokens(text, exact=True))
        marks, unknown = [], []
        for w, n in seen.most_common():
            if w in store:
                continue
            c = sp.get(self.tok.plain(w))
            if not c:
                unknown.append((w, n))
            elif w not in c:
                marks.append((w, n, [x for x, _ in c.most_common(3)]))
        return marks, unknown

    def segmenter(self):
        """the store's morph view (scripts/morphs.py), or None without morph entries"""
        if self._seg is None:
            import morphs
            self._seg = morphs.load(self.name, self) or False
        return self._seg or None

    def parts(self, form, confirmed=False):
        """an exact form as its parts (ba-ka-gaamb-a), or None (one part, or no morph view; confirmed: also where an
        affix is not confirmed)"""
        S = self.segmenter()
        if not S:
            return None
        import morphs
        if confirmed and getattr(self, "_aff", None) is None:
            import grammar
            self._aff = morphs.affix_entries(grammar.load(self.name))
        return morphs.parts(S, form, self._aff if confirmed else None)

    def built(self, unknown):
        """Of spell_check's unknown forms, those the store's morph view builds from known parts (the store's affixes
        and the stem of a corpus word): [(form, n, parts, note)], note naming a stem written with other marks than the
        corpus writes it. The rest stay unknown: (built, still unknown)."""
        S = self.segmenter()
        if not S:
            return [], unknown
        import morphs
        out, rest = [], []
        for w, n in unknown:
            b = morphs.built(S, w)
            if b:
                out.append((w, n, *b))
            else:
                rest.append((w, n))
        return out, rest

    def spelled(self, form):
        """A plain form as the corpus writes it: the most frequent spelling, and any other one used at least a fifth as
        often ('bègó (also begó)'). Forms the corpus lacks are returned as they are."""
        c = self.spellings().get(self.tok.plain(form))
        if not c:
            return form
        (best, n), *rest = c.most_common()
        alts = [w for w, k in rest if k * 5 >= n]
        return best + (f" (also {', '.join(alts)})" if alts else "")

    def text_dirs(self):
        return [os.path.join(ROOT, e["dir"], e.get("text_dir", "text")) for e in self.editions]

    def glossary(self):
        rows = []
        for e in self.editions:
            g = os.path.join(ROOT, e["dir"], "glossary.tsv")
            if os.path.exists(g):
                rows += [l.split("\t") for l in open(g, encoding="utf-8").read().splitlines()[1:]]
        return rows

    def assist_dir(self, code):
        return sources(self.p, code)[2]

    def corpus(self, exclude=()):
        """[(ref, code, (ch, v), assisting text, target text)] for every verse of the style corpus."""
        if self._rows is None:
            rows, cache = [], {}
            for d in self.text_dirs():
                for f in sorted(glob.glob(os.path.join(d, "*.txt"))):
                    b = os.path.basename(f)
                    if not re.fullmatch(r"[0-9a-z]{3}(\d{3})?\.txt", b) or b[:3] not in BY_CODE:
                        continue
                    code, ot = b[:3], BY_CODE[b[:3]][2] != "nt"
                    for key, t in verses_of(f).items():
                        c, v = vrs.to_bsb(code, *key) if ot else key
                        af = os.path.join(ROOT, self.assist_dir(code), f"{code}{c:03d}.txt")
                        if af not in cache:
                            cache[af] = verses_of(af) if os.path.exists(af) else {}
                        rows.append((f"{code.upper()} {key[0]}:{key[1]}", code, key, cache[af].get((c, v), ""), t))
            self._rows = rows
        return [r for r in self._rows if r[1] not in exclude]


def ngrams(s, n):
    s = re.sub(r"\s+", " ", s).strip()
    return collections.Counter(s[i:i + n] for i in range(len(s) - n + 1))


def chrf(hyp, ref, beta=2.0, N=6):
    """chrF (character n-grams 1..N, Popović 2015)."""
    ps, rs = [], []
    for n in range(1, N + 1):
        h, r = ngrams(hyp, n), ngrams(ref, n)
        m = sum((h & r).values())
        if sum(h.values()) and sum(r.values()):
            ps.append(m / sum(h.values())); rs.append(m / sum(r.values()))
    if not ps:
        return 0.0
    p, r = sum(ps) / len(ps), sum(rs) / len(rs)
    return 0.0 if p + r == 0 else 100 * (1 + beta ** 2) * p * r / (beta ** 2 * p + r)


def chrf3(hyps, refs, beta=3.0, N=6):
    """chrF3 as sacrebleu's corpus_chrf computes it (char_order 6, word_order 0, beta 3, whitespace removed, case kept),
    the figure SIL reports: n-gram counts summed over the segments (verses), an F-score per order, averaged over the
    orders both sides have. Takes the texts as written (unicode NFC); checked against sacrebleu 2.x."""
    tot = [[0, 0, 0] for _ in range(N)]                     # matches, hypothesis n-grams, reference n-grams
    for h, r in zip(hyps, refs):
        h = re.sub(r"\s+", "", unicodedata.normalize("NFC", h)); r = re.sub(r"\s+", "", unicodedata.normalize("NFC", r))
        for n in range(1, N + 1):
            hc = collections.Counter(h[i:i + n] for i in range(len(h) - n + 1))
            rc = collections.Counter(r[i:i + n] for i in range(len(r) - n + 1))
            t = tot[n - 1]; t[0] += sum((hc & rc).values()); t[1] += sum(hc.values()); t[2] += sum(rc.values())
    score, eff, f2 = 0.0, 0, beta ** 2
    for m, nh, nr in tot:
        if nh > 0 and nr > 0:
            eff += 1
        p = m / nh if nh else 0.0; rr = m / nr if nr else 0.0
        d = f2 * p + rr
        score += (1 + f2) * p * rr / d if d > 0 else 0.0
    return 100 * score / eff if eff else 0.0
