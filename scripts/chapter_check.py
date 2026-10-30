"""The checks of one chapter inside the drafting loop (docs/workflow.md, the book agent): one command, one list.
The drafting agent runs it after each chapter and fixes what it finds before the next one.

To fix (the command fails while any is left):
  - format and verses: scripts/check_draft.py (--spell where the project's mode sets the spell check)
  - alignment (a .align beside the draft, OT and NT): scripts/full_align.py check
  - quotations in the chapter's notes and footnotes: scripts/quotes.py
  - verb marking, in a binding project (`pack_grammar`, scripts/modes.py: by default for an unknown language with
    clearly marked cells): a verb of a cell the human OT clearly marks whose tagged words lack the pattern, unless the
    notes say why (`unmarked <ch>:<v> ...`), scripts/cell_check.py (binding_fix)
To review (reported, not failed; each kept one explained in the chapter's notes):
  - lost or added negations: scripts/rough_check.py (its markers are learned from the corpus; with a .align beside the
    draft, a negation the alignment links to a draft word counts too, so a negation word that is also a common other
    word, Hebrew אל "do not" / "to", is no false flag)
  - verb marking (a store with observed verb cells and an OT in the style corpus): a cell the book's drafts mark
    clearly less often than the human OT does, scripts/cell_check.py (book_review)
  - word parts (a store with affix chains that mark Greek features, and the NT aligned to the Greek): a Hebrew verb whose
    draft word lacks the affix for its subject, object, negation or mood, where the human NT carries it on most verbs
    with that feature, scripts/morphs.py (chain_review; `morphs.py <project> rates` shows which are checked)
  - a Hebrew target (language he): the copy check, scripts/heb_copy.py
  - alternations (store entries with an `alternation` block): a draft word written with marks whose cues in the NT
    (the word before or after, the Greek lemma; in the OT the LXX word of the Hebrew it renders) point only to another
    form, scripts/alternations.py (review)
  - names against the book so far (from the .align files, OT and NT): a name of the original rendered in this chapter
    otherwise than in the earlier chapters of the book (their most frequent rendering, seen at least twice)

Usage: python3 scripts/chapter_check.py <project> <code> <chapter>
"""
import collections, difflib, os, re, sqlite3, subprocess, sys

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
from books import BY_CODE, tools  # noqa: E402
from project import project, project_dir  # noqa: E402
import modes  # noqa: E402


def run(*args):
    r = subprocess.run([sys.executable, *tools(args)], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def names(pname, code, upto):
    """{lexeme: {chapter: Counter(rendering)}} of the original's proper names, from the .align files of chapters <= upto"""
    import full_align as FA
    if BY_CODE[code][2] == "nt":
        con = sqlite3.connect(os.path.join(ROOT, "orig", "grc.sqlite"))
        proper = {k: lx for k, lx in con.execute("select key, lemma from tokens where book = ? and type = 'proper'",
                                                 (code.upper(),))}
    else:
        con = sqlite3.connect(os.path.join(ROOT, "orig", "heb.sqlite"))
        proper = {k: lx for k, lx in con.execute("select key, lexeme from tokens where book = ? and type = 'proper'",
                                                 (code.upper(),))}
    out = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for c, ch, txt, al in FA.chapters(pname, code):
        if ch > upto or not os.path.exists(al):
            continue
        _, rows = FA.read_chapter(al)
        verses = dict(FA.draft_texts(txt))
        for v, (main, _, _) in rows.items():
            words = FA.tokenize(verses.get(v, ""))
            keys = FA.index(code.upper(), "keys").get(f"{code.upper()} {ch}:{v}", [])
            for o, pos in FA.parse(main).items():
                for k in (keys[o].split("+") if o < len(keys) and keys[o] else []):
                    if proper.get(k) and pos:
                        out[proper[k]][ch][" ".join(words[i] for i in pos if i < len(words))] += 1
    return out


def same_name(a, b):
    """the same name with other prefixes or suffixes of the language (בבית לחם / מבית לחם, ליהודה / שביהודה)"""
    m = difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b)).size
    short = min(len(a), len(b))
    if short < 3:                       # a two-letter name (נח, שם): the whole of it, with at most two letters added
        return m == short and abs(len(a) - len(b)) <= 2
    return m >= 3 and m >= short - 3


def name_flags(pname, code, ch):
    flags = []
    for lx, by_ch in names(pname, code, ch).items():
        if ch not in by_ch:
            continue
        before = collections.Counter()
        for c, n in by_ch.items():
            if c < ch:
                before.update(n)
        if not before:
            continue
        top, k = before.most_common(1)[0]
        if k < 2:
            continue
        for form in by_ch[ch]:
            if not same_name(form, top):
                flags.append(f"name {lx}: “{form}” here, “{top}” in the earlier chapters ({k}x)")
    return flags


def main(a):
    if len(a) != 3:
        print(__doc__); sys.exit(2)
    pname, code, ch = a[0], a[1], int(a[2])
    p, m = project(pname), modes.mode(project(a[0]))
    d = os.path.join(project_dir(pname), code)
    nnn = f"{ch:03d}"
    txt = os.path.join(d, f"{code}{nnn}.txt")
    if not os.path.exists(txt):
        sys.exit(f"no {os.path.relpath(txt, ROOT)}")
    fix, review = [], []
    rc, out = run("scripts/check_draft.py", pname, code, "--chapter", str(ch), *(["--spell"] if m["spell_check"] else []))
    if rc or not re.search(r"\b0 with problems", out):
        fix += [f"check_draft: {l}" for l in out.splitlines() if l.strip() and "chapters checked" not in l]
    if os.path.exists(os.path.join(d, f"{code}{nnn}.align")):
        rc, out = run("scripts/full_align.py", "check", pname, code, str(ch))
        if rc or not out.rstrip().endswith("ok"):
            fix += [f"alignment: {l}" for l in out.splitlines() if l.strip()]
    side = [os.path.join(d, f"{code}{nnn}{s}") for s in ("_notes.md", "_footnotes.txt")]
    side = [f for f in side if os.path.exists(f)]
    if side:
        rc, out = run("scripts/quotes.py", pname, *side)
        if rc or not re.search(r"\b0 problems", out):
            fix += [f"quotations: {l}" for l in out.splitlines() if l.strip() and "CREDITS.md" not in l]
    rc, out = run("scripts/rough_check.py", pname, txt, "--no-added")
    review += [f"negation {l}" for l in out.splitlines() if re.match(r"\d+:\d+\s", l)]
    if (p.get("language") or "").split("-")[0] in ("he", "heb") and BY_CODE[code][2] == "ot":
        rc, out = run("scripts/heb_copy.py", pname, code, str(ch))
        review += [f"copy: {l}" for l in out.splitlines() if l.startswith(f"{code}{nnn}") and " 0 verses" not in l]
    review += name_flags(pname, code, ch)
    if BY_CODE[code][2] == "ot":
        import cell_check
        fix += cell_check.binding_fix(pname, code, ch)
        review += cell_check.book_review(pname, code, ch)
        import morphs                             # affix chains: the parts the Hebrew verb calls for (morphs.py review)
        if os.path.exists(os.path.join(d, f"{code}{nnn}.align")) or os.path.exists(os.path.join(d, f"{code}{nnn}.tagged")):
            review += morphs.chain_review(pname, code, ch)
    import alternations                           # forms told apart by their marks (tone): the store's cues
    review += alternations.review(pname, code, ch)
    print(f"{pname} {code} {ch}: {len(fix)} to fix, {len(review)} to review")
    for l in fix:
        print(f"  FIX     {l}")
    for l in review:
        print(f"  REVIEW  {l}")
    sys.exit(1 if fix else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
