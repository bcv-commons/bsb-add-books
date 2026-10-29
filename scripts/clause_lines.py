#!/usr/bin/env python3
"""Clause-line versions of a project's prose drafts: the same text, laid out one line per Hebrew clause line, for the
website's clause views (docs/clause-sidecar.md, authoring format).

They are never stored: scripts/build_site.py derives them at build time from each draft and its word alignment (OT: the Hebrew layouts; NT: the Greek one)
(<code>NNN.align, scripts/full_align.py) with scripts/bridge_align.py's clauses(), on the layouts:
    bhsa        orig/heb-bhsa (ETCBC BHSA 2021): the view is CC BY-NC 4.0; the layout files stay local, never published
    bcv-query   orig/heb-bcv-query (MACULA Hebrew + UHB, hebrew-clause-layout v0.37): the view is CC BY-SA 4.0
    gntl        orig/grc-gntl (MACULA Greek, greek-nt-clause-layout v0.5; scripts/build_grc_gntl.py): NT, the view is CC BY 4.0
The text must stay the prose draft's, word for word: the clause view is a display of the draft, not another
translation; this script checks that.

    python3 scripts/clause_lines.py check <project> [<code> <ch>]   derive and check (all OT chapters by default)
    python3 scripts/clause_lines.py show <project> <code> <ch> [--layout bhsa|bcv-query]   print the derived lines

Format (one line per line of the layout file, in order):
    //N vK text       the first line of verse K; N = the Hebrew line's level + 1
    //N text          a further line
    //N =             this Hebrew line is rendered inside the line above (no words of its own on a line)
    //N = words       the same, naming the words of the line above that render it
Headings (==…==), the title (===…===) and header lines (!!<…>!!) are copied from the draft as they are.
"""
import os, re, sys

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
from books import BY_CODE  # noqa: E402
from project import project_dir  # noqa: E402

LAYOUTS = {"bhsa": "orig/heb-bhsa", "bcv-query": "orig/heb-bcv-query", "gntl": "orig/grc-gntl"}   # gntl: the NT's (build_grc_gntl.py)
KEYS = {"bcv-query": "orig/heb-bcv-query-keys", "gntl": "orig/grc-gntl-keys"}   # each line's word keys
LICENCE = {"bhsa": "CC BY-NC 4.0 (the clause layout is ETCBC's BHSA 2021: non-commercial use, attribution)",
           "bcv-query": "CC BY-SA 4.0 (the clause layout is bcv-commons/hebrew-clause-layout v0.37, from MACULA Hebrew and UHB)",
           "gntl": "CC BY 4.0 (the clause layout is bcv-commons/greek-nt-clause-layout v0.5, from MACULA Greek, Nestle 1904)"}


def paths(pname, code, ch, layout="bhsa"):
    nnn = f"{int(ch):03d}"
    prose = os.path.join(project_dir(pname), code, f"{code}{nnn}.txt")
    src = os.path.join(ROOT, LAYOUTS[layout], f"{code}{nnn}.txt")
    return prose, None, src


def layout_rows(path):
    rows = []
    for l in open(path, encoding="utf-8").read().splitlines()[1:]:
        m = re.match(r"(\d+):(\d+) (.*)$", l)
        if m:
            rows.append((int(m[1]), int(m[2]), m[3].strip()))
    return rows


def norm(t):
    return re.sub(r"\s+", " ", t).strip()


def prose_text(path):
    lines = [l for l in open(path, encoding="utf-8").read().splitlines() if not l.startswith(("!!<", "=="))]
    return norm(" ".join(lines))


def clause_rows(lines):
    """[(line no, level, verse or None, text, merged)] and problems, from a clause-line file's lines."""
    rows, problems = [], []
    for n, l in enumerate(lines, 1):
        if not l.strip() or l.startswith(("!!<", "==")):
            continue
        m = re.match(r"//(\d+) (.*)$", l)
        if not m:
            problems.append(f"line {n}: not a clause line: {l[:70]}")
            continue
        text = m[2].strip()
        merged = text == "=" or text.startswith("= ")
        v = re.match(r"v(\d+)(?=\s)", text)
        rows.append((n, int(m[1]) - 1, int(v[1]) if v else None, text, merged))
    return rows, problems


def check(pname, code, ch, layout, lines, quiet=False):
    """Problems (empty list when the clause lines are right): one line per layout line, levels and verse starts as
    the layout has them, merges only below a line with text, named words found in the line above, and the text
    equal to the prose draft's."""
    prose, _, src = paths(pname, code, ch, layout)
    import bridge_align as BA
    have = {v for v, _, _ in BA.draft_verses(prose)[2]}
    L = [r for r in layout_rows(src) if r[0] in have]   # a layout verse the draft's text lacks (JHN 5:4: Nestle 1904 has it, the BGB not)
    rows, problems = clause_rows(lines)
    if len(rows) != len(L):
        problems.append(f"{len(rows)} clause lines, the layout has {len(L)}")
    first = {}
    for i, (v, lev, _) in enumerate(L):
        first.setdefault(v, i)
    for i, (r, l) in enumerate(zip(rows, L)):
        n, lev, v, text, merged = r
        if lev != l[1]:
            problems.append(f"line {n}: level {lev + 1}, the layout has {l[1] + 1} (verse {l[0]}: {l[2][:30]})")
        if first.get(l[0]) == i and not merged and v != l[0]:
            problems.append(f"line {n}: verse {l[0]} starts here (expected 'v{l[0]}' at the start)")
        if v is not None and v != l[0] and not (i and first.get(v) is not None and first[v] == i):
            problems.append(f"line {n}: v{v} on a line of verse {l[0]}")
        if merged:
            if i == 0:
                problems.append(f"line {n}: a merge on the first line")
            else:
                above = next((x[3] for x in reversed(rows[:i]) if not x[4]), "")
                for w in text[1:].split():
                    if w not in above:
                        problems.append(f"line {n}: named word {w!r} is not in the line above")
    got = norm(" ".join(r[3] for r in rows if not r[4]))
    want = prose_text(prose)
    if got != want:
        a, b = got.split(), want.split()
        i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
        problems.append(f"the text differs from the prose draft at word {i + 1}: clause file '{' '.join(a[max(0, i - 3):i + 4])}' "
                        f"vs draft '{' '.join(b[max(0, i - 3):i + 4])}'")
    if not quiet:
        print(f"{code}{int(ch):03d} {layout}: {len(rows)} lines, " + (f"{len(problems)} problems" if problems else "ok"))
        for p in problems[:30]:
            print("  " + p)
    return problems


def ot_chapters(pname):
    d = project_dir(pname)
    out = []
    for code in BY_CODE:
        if BY_CODE[code][2] != "ot" or not os.path.isdir(os.path.join(d, code)):
            continue
        for f in sorted(os.listdir(os.path.join(d, code))):
            m = re.fullmatch(rf"{code}(\d{{3}})\.txt", f)
            if m:
                out.append((code, int(m[1])))
    return out


def derived(pname, code, ch):
    import bridge_align as BA
    return BA.clauses(pname, code, ch)


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("check", "show"):
        raise SystemExit(__doc__)
    cmd, pname = a[0], a[1]
    if cmd == "show":
        lay = a[a.index("--layout") + 1] if "--layout" in a else "bhsa"
        d = derived(pname, a[2], int(a[3]))
        if not d:
            raise SystemExit("no clause lines: the .align is missing or stale, or a layout isn't here (setup.py --heb bhsa,bcv-query)")
        print("\n".join(d[lay]))
        return
    chs = [(a[2], int(a[3]))] if len(a) > 3 else ot_chapters(pname)
    bad = none = 0
    for code, ch in chs:
        d = derived(pname, code, ch)
        if not d:
            none += 1
            print(f"{code}{ch:03d}: no clause lines (.align missing or stale, or no layout)")
            continue
        bad += any([check(pname, code, ch, lay, d[lay], quiet=len(chs) > 1 and True) for lay in d])
    print(f"{pname}: {len(chs)} chapters, {len(chs) - none - bad} ok, {bad} with problems, {none} without clause lines")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
