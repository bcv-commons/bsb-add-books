"""Shared pieces of the language toolkit (docs/proposals/language-toolkit/): a project's style corpus
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
from project import project, sources, edition  # noqa: E402
import vrs  # noqa: E402


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
        cls = re.escape(self.extra)
        self.rx = re.compile(rf"[\w{cls}]+(?:-[\w{cls}]+)*" if self.split else rf"[\w{cls}]+")

    def plain(self, s):
        """Lower case, the ignored marks removed (NFC)."""
        s = unicodedata.normalize("NFD", s.lower())
        return unicodedata.normalize("NFC", "".join(c for c in s if c not in self.marks))

    def tokens(self, s):
        out = []
        for w in self.rx.findall(self.plain(s)):
            if self.split and "-" in w:
                first, *rest = w.split("-")
                out += ([first] if first else []) + ["-" + r for r in rest if r]
            else:
                out.append(w)
        return [t for t in out if not t.isdigit()]


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
    Kuni Genesis). {"BOOK c:v": text}; None if a published text named isn't there."""
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
        self.dir = os.path.join(ROOT, "export", name)
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
