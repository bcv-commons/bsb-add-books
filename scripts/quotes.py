#!/usr/bin/env python3
"""Check a project's publishable files against the quotation rules of docs/licensing.md.

A quotation is a run of 5 or more written words (a hyphenated suffix is part of its word) that stands in one verse of a style edition (or in at most 3:
longer common formulas are not quotations of a verse). Drafts (<code>NNN.txt) are not checked: they are our
own text, and a phrase they share with the edition is the language's, not a quotation. For each file:
  - per book of the edition, at most 10% of its words quoted;
  - every quotation is in the edition's published text (`published_text`, else its text/): a quotation of
    a newer working copy that differs from the published text is a problem;
  - quotations keep the edition's marks (tone, accents) as written: a warning when only the plain form matches;
and for the files together, at most 2% of the edition's words quoted. The project's CREDITS.md (written by
`--credits`) must carry each quoted edition's `credit` line and say that quotations are not under CC0.

Usage: python3 scripts/quotes.py <project> [FILE ...] [--credits | --rule]
       --credits: write export/<project>/CREDITS.md from the editions' credit lines
       --rule:    print the quotation rule for an agent's prompt (in every chapter prompt already)
       Without files: every file in export/<project>/ that git does not ignore (the files that get published).
"""
import collections, glob, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import langtools as LT  # noqa: E402

N = 5
BOOK_SHARE, TOTAL_SHARE = 0.10, 0.02
MAX_QUOTE = 15                 # words in one quotation (a store note, a notes line): a phrase or a short verse
# The original in our files is quoted from the open texts (the WLC via MACULA Hebrew, orig/heb.sqlite; the BGB,
# orig/grc), never copied from orig/heb/ (our BHSA copy, the BHS text, CC BY-NC): scripts/notes_hebrew.py fills the
# notes' verses. A run of more Hebrew or Greek words than this must be the open text word for word.
CHECK_ORIGINAL = 6
ORIGINAL_RUN = re.compile(r"(?:[\u0590-\u05FF\uFB1D-\uFB4F]+[\s\u05BE\u05C0\u05C3.,;:()…·-]*)+|"
                          r"(?:[\u0370-\u03FF\u1F00-\u1FFF]+[\s.,;:·’'()…-]*)+")
ORIGINAL_WORD = re.compile(r"[\u05D0-\u05EA][\u0591-\u05C7\u05D0-\u05EA]*|[\u0370-\u03FF\u1F00-\u1FFF]+")
_OPEN = {}


def open_text(script):
    """The open original as one string of words: 'heb' the WLC (orig/heb.sqlite, verse by verse, prefixes joined to their
    words as printed), 'grc' the BGB (orig/grc). NFC. '' if absent."""
    import unicodedata
    if script not in _OPEN:
        words = []
        if script == "heb":
            db = os.path.join(ROOT, "orig", "heb.sqlite")
            if os.path.exists(db):
                import sqlite3
                verse, last = [], None
                for b_, c, v, t, a in sqlite3.connect(db).execute("select book, ch, v, text, after from tokens order by key"):
                    if (b_, c, v) != last and verse:
                        words += ORIGINAL_WORD.findall("".join(verse))
                        verse = []
                    last = (b_, c, v)
                    verse.append((t or "") + (a or ""))
                words += ORIGINAL_WORD.findall("".join(verse))
        else:
            import langtools as LT
            for f in sorted(glob.glob(os.path.join(ROOT, "orig", "grc", "*.txt"))):
                if re.fullmatch(r"[0-9a-z]{3}\d{3}\.txt", os.path.basename(f)):
                    for t in LT.verses_of(f).values():
                        words += ORIGINAL_WORD.findall(t)
        _OPEN[script] = unicodedata.normalize("NFC", " " + " ".join(words) + " ") if words else ""
    return _OPEN[script]


ACCENT = re.compile(r"[\u0591-\u05AF]")   # Hebrew cantillation: only copied text carries it


def original_runs(text, limit=CHECK_ORIGINAL):
    """Runs of more than `limit` Hebrew or Greek words copied from a text (Hebrew: with accents) that are not the open text
    word for word, i.e. not the WLC / BGB: [(words, first words)]."""
    out = []
    for m in ORIGINAL_RUN.finditer(text):
        words = ORIGINAL_WORD.findall(m[0])
        if len(words) <= limit:
            continue
        heb = "\u05D0" <= words[0][0] <= "\u05EA"
        if heb and not ACCENT.search(m[0]):
            continue                      # written by hand (no accents): the agent's own phrase or a list, not a copy
        import unicodedata
        ref = open_text("heb" if heb else "grc")
        if ref and unicodedata.normalize("NFC", " " + " ".join(words) + " ") not in ref:
            out.append((len(words), " ".join(words[:4])))
    return out


def merged(ts):
    """Written words: suffixes the tokeniser splits off ('-pakha', '-ge') go back onto their word."""
    out = []
    for t in ts:
        if t.startswith("-") and out:
            out[-1] += t
        else:
            out.append(t)
    return out


class Quotes:
    def __init__(self, pname):
        self.P = P = LT.Project(pname)
        self.w = lambda tok, t: merged(tok.tokens(t))
        self.written_tok = LT.Tokeniser(P.p.get("tokenise"), ())       # lower case only: marks kept
        from project import LICENCE_CLASS
        from books import BY_CODE
        # every verse of the style editions; only non-free editions are limited (public domain and CC BY / BY-SA
        # editions are credited, and their licences allow more than we quote)
        self.rows, self.limited_eds = [], []
        for eid, ed in zip(P.p["style_from"], P.editions):
            limited = LICENCE_CLASS.get(ed["licence_folder"], "non-free") == "non-free"
            if limited:
                self.limited_eds.append(eid)
            for d in [os.path.join(ROOT, ed["dir"], ed.get("text_dir", "text"))]:
                for f in sorted(glob.glob(os.path.join(d, "*.txt"))):
                    b = os.path.basename(f)
                    if re.fullmatch(r"[0-9a-z]{3}(\d{3})?\.txt", b) and b[:3] in BY_CODE:
                        for (c, v), t in LT.verses_of(f).items():
                            if t:
                                self.rows.append((f"{b[:3].upper()} {c}:{v}", b[:3], (c, v), "", t, eid, limited))
        self.words = sum(len(self.w(P.tok, r[4])) for r in self.rows if r[6]) or 1
        self.book_words = collections.Counter()
        for r in self.rows:
            if r[6]:
                self.book_words[r[1]] += len(self.w(P.tok, r[4]))
        self.grams = collections.defaultdict(set)
        for i, r in enumerate(self.rows):
            ts = self.w(P.tok, r[4])
            for j in range(len(ts) - N + 1):
                g = self.grams[tuple(ts[j:j + N])]
                if len(g) < 8:
                    g.add(i)
        self.published, self.credits = set(), []
        self.pub_missing = []
        for eid, ed in zip(P.p["style_from"], P.editions):
            if ed.get("credit") or ed.get("attribution"):
                self.credits.append(ed.get("credit") or ed.get("attribution"))
            if eid not in self.limited_eds:
                continue
            pv = LT.published_verses(ed)
            if pv is None:
                self.pub_missing.append(ed["id"] if "id" in ed else ed["dir"])
                continue
            for t in pv.values():
                ts = self.w(P.tok, t)
                self.published |= {tuple(ts[j:j + N]) for j in range(len(ts) - N + 1)}
        self.has_published = bool(self.published)

    def runs(self, text):
        """[(start, end, verse indices)] of the quotations in a text (plain tokens)."""
        ts = self.w(self.P.tok, text)
        out, j = [], 0
        while j <= len(ts) - N:
            g = self.grams.get(tuple(ts[j:j + N]))
            if not g:
                j += 1
                continue
            vs, k = set(g), j + 1
            while k <= len(ts) - N:
                nxt = vs & self.grams.get(tuple(ts[k:k + N]), set())
                if not nxt:
                    break
                vs, k = nxt, k + 1
            if len(vs) <= 3:
                out.append((j, k + N - 1, vs))
            j = k + N - 1
        return ts, out

    def check_text(self, text, own_book=None):
        """own_book: the book of a test draft (export/<project>/_eval/<name>-test/<code>NNN*): its text and notes were
        written before the agent could see the edition's book, so a match with that book is our own wording that
        coincides with the human one, not a quotation."""
        ts, runs = self.runs(text)
        wt = self.w(self.written_tok, text)
        same = len(wt) == len(ts)
        verses, quoted, unpublished, marks = collections.Counter(), 0, [], []
        for a, b, vs in runs:
            vs = {v for v in vs if self.rows[v][6] and self.rows[v][1] != own_book}  # limited (non-free) editions only
            if not vs:
                continue
            quoted += b - a
            verses[self.rows[min(vs)][1]] += b - a
            run = ts[a:b]
            if self.has_published and any(tuple(run[i:i + N]) not in self.published for i in range(len(run) - N + 1)):
                unpublished.append((self.rows[min(vs)][0], " ".join(run)[:80]))
            if same:
                w = wt[a:b]
                if not any(" ".join(w) in " ".join(self.w(self.written_tok, self.rows[v][4])) for v in vs):
                    marks.append((self.rows[min(vs)][0], " ".join(w)[:80]))
        return quoted, verses, unpublished, marks

    def check_snippet(self, text, max_words=MAX_QUOTE):
        """Problems of one short text an agent wrote (a store entry's note, a form, a notes line): a quotation of a
        non-free edition longer than max_words, not from the published text, or without its marks."""
        ts, runs = self.runs(text)
        out = []
        for a, b, vs in runs:
            vs = {v for v in vs if self.rows[v][6]}
            if vs and b - a > max_words:
                out.append(f"quotes {b - a} words of {self.rows[min(vs)][0]} (at most {max_words}: a phrase, not the verse)")
        _, _, unpub, marks = self.check_text(text)
        out += [f"{ref} quoted from the working copy, not the published text" for ref, _ in unpub]
        out += [f"{ref} quoted without the edition's marks: “{s_}”" for ref, s_ in marks]
        return out

    def check_files(self, files, credit_file=None):
        problems, warnings, total, per_file = [], [], 0, []
        files = [f for f in files if not re.fullmatch(r"[0-9a-z]{3}\d{3}\.txt", os.path.basename(f))]
        for f in files:
            text = open(f, encoding="utf-8", errors="replace").read()
            m = re.fullmatch(r"([0-9a-z]{3})\d{3}\D.*", os.path.basename(f))
            test = m and re.search(r"/_eval/[^/]+-test/", f.replace(os.sep, "/"))
            quoted, verses, unpub, marks = self.check_text(text, m[1] if test else None)
            for n, start in original_runs(text):
                problems.append(f"{os.path.relpath(f, ROOT)}: {n} Hebrew/Greek words (“{start} …”) that are not the open text "
                                f"word for word: quote the WLC or the BGB (scripts/notes_hebrew.py), never orig/heb/")
            total += quoted
            rel = os.path.relpath(f, ROOT)
            if not quoted:
                continue
            for book, n in verses.items():
                if n > BOOK_SHARE * self.book_words[book]:
                    problems.append(f"{rel}: quotes {n} of the {self.book_words[book]} words of {book.upper()} "
                                    f"({n / self.book_words[book]:.0%}, over {BOOK_SHARE:.0%}); shorten, or keep the file local")
            for ref, s in unpub:
                problems.append(f"{rel}: {ref} quoted from the working copy, not the published text: “{s}”")
            for ref, s in marks[:5]:
                warnings.append(f"{rel}: {ref} quoted without the edition's marks: “{s}”")
            if len(marks) > 5:
                warnings.append(f"{rel}: {len(marks) - 5} more quotations without the edition's marks")
            per_file.append((rel, quoted, verses))
        cf = credit_file or os.path.join(self.P.dir, "CREDITS.md")
        ctext = open(cf, encoding="utf-8").read() if os.path.exists(cf) else ""
        if total:
            for c in self.credits:
                if c not in ctext:
                    problems.append(f"{os.path.relpath(cf, ROOT)} lacks the credit line “{c}” (run with --credits)")
        if total > TOTAL_SHARE * self.words:
            problems.append(f"together the files quote {total} words, {100 * total / self.words:.1f}% of the edition "
                            f"(over {TOTAL_SHARE:.0%})")
        if self.pub_missing:
            warnings.append(f"published text not found for {', '.join(self.pub_missing)} (published_text in edition.yaml); "
                            "quotations not checked against it")
        self.per_file = per_file
        return problems, warnings, total


INDEPENDENT_SHARE, LONG_RUNS = 0.40, 3.0


def overlap(Q, files, code):
    """How much of our drafts of a book stands word for word in an edition's text of the same book: the share of
    words in shared runs of 5+ words, runs of 15+ words per 1000 words, the longest run. Independent literal
    translations of the same source share about 20% and one 15-word run per 1000 words (Danish Genesis drafted in
    quarantine against Den Frie Bibel); over 40% or 3 per 1000 suggests copying."""
    words = shared = long_ = longest = 0
    for f in files:
        ts, runs = Q.runs(open(f, encoding="utf-8").read())
        words += len(ts)
        for a, b, vs in runs:
            if Q.rows[min(vs)][1] == code:
                shared += b - a
                long_ += b - a >= 15
                longest = max(longest, b - a)
    share, per1000 = shared / max(words, 1), 1000 * long_ / max(words, 1)
    return {"share": share, "long_per_1000": per1000, "longest": longest,
            "independent": share <= INDEPENDENT_SHARE and per1000 <= LONG_RUNS}


def publishable(pname):
    d = os.path.join(ROOT, "export", pname)
    files = [os.path.join(dp, f) for dp, _, fs in os.walk(d) for f in fs
             if f.endswith((".md", ".txt", ".json", ".tsv", ".yaml", ".html"))]
    ignored = set(subprocess.run(["git", "check-ignore", "--no-index", "--stdin"], input="\n".join(files), capture_output=True,
                                 text=True, cwd=ROOT).stdout.split("\n"))
    return [f for f in files if f not in ignored]


def rule_text(pname):
    """The quotation rule for an agent's prompt (make_prompt.py puts it in every chapter prompt; print it with
    --rule for other agents, e.g. a curation agent). Empty when no style edition is non-free."""
    from project import project, edition, LICENCE_CLASS
    p = project(pname)
    eds = [edition(e) for e in p["style_from"]]
    names = [ed.get("name") or e for e, ed in zip(p["style_from"], eds)
             if LICENCE_CLASS.get(ed["licence_folder"], "non-free") == "non-free"]
    if not names:
        return ""
    return ("**Quoting " + " and ".join(names) + "** (not free; `docs/licensing.md`). Learn from it freely; quote it only "
            "in short pieces, in notes, store entries and the wiki alike: a word or a phrase, at most " + str(MAX_QUOTE) +
            " words in one place, and an evidence `form` of at most 4 words (the attested word or phrase, not the "
            "verse). Copy a quotation exactly as written (tone marks, accents, punctuation; `…` for a left-out part) "
            "and give its reference. Never paste a verse, a verse pack's lines or search output into a file. Your "
            f"draft is your own translation: never take a verse into it whole. At the end run `python3 scripts/quotes.py "
            f"{pname} <the notes and wiki files you wrote>` and fix every problem.")


def write_credits(Q):
    from project import LICENCE_CLASS
    f = os.path.join(Q.P.dir, "CREDITS.md")
    lines = ["# Credits", "",
             "Our work in this folder (drafts, notes, the wiki's prose, the language store, statistics) is dedicated to "
             "the public domain (CC0 1.0). We learned from and quote the editions below (docs/licensing.md).", ""]
    groups = {"non-free": [], "attributable": [], "public-domain": []}
    for eid, ed in zip(Q.P.p["style_from"], Q.P.editions):
        c = ed.get("credit") or ed.get("attribution")
        if c:
            groups[LICENCE_CLASS.get(ed["licence_folder"], "non-free")].append(c)
    heads = {"non-free": "Quoted in short passages, with references, under the quotation right and the edition's own terms; "
                         "**these quotations are not covered by CC0** and stay with their owners:",
             "attributable": "Quoted under the edition's licence, which asks for this credit:",
             "public-domain": "Public domain; credited with thanks:"}
    for k, cs in groups.items():
        if cs:
            lines += [heads[k], ""] + [f"- {c}" for c in cs] + [""]
    if os.path.exists(os.path.join(Q.P.learn, "lexicon_hbo.tsv")):
        lines += ["Data:", "",
                  "- `_learn/lexicon_hbo.tsv`: Hebrew lexeme ids, lemmas and glosses from MACULA Hebrew (Clear Bible, "
                  "https://github.com/Clear-Bible/macula-hebrew), CC BY 4.0, via the bcv-commons scaffold API; "
                  "the Kuni renderings and counts are ours (CC0)."]
    open(f, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{os.path.relpath(f, ROOT)} written")


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    if "--rule" in a:
        print(rule_text(a[0]) or "(no non-free style edition: no quotation limits; credit the editions)")
        return
    Q = Quotes(a[0])
    if "--credits" in a:
        write_credits(Q)
        a.remove("--credits")
    files = a[1:] or publishable(a[0])
    problems, warnings, total = Q.check_files(files)
    print("\n".join(problems + [f"warning: {w}" for w in warnings]))
    for rel, q, by in sorted(Q.per_file, key=lambda x: -x[1])[:8]:
        print(f"  {q:5} quoted words  {rel}  (" + ", ".join(f"{b.upper()} {n}" for b, n in by.most_common(4)) + ")")
    print(f"{len(files)} files, {total} quoted words ({100 * total / max(Q.words, 1):.2f}% of the edition), "
          f"{len(problems)} problems, {len(warnings)} warnings")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
