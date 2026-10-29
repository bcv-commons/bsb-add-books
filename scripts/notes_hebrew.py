#!/usr/bin/env python3
"""The original text in a chapter's notes: from the open text, never from orig/heb/.

orig/heb/ is our BHSA copy (the BHS text, CC BY-NC): agents consult its clause layout but never copy its text. The
original that the notes quote comes from the open texts: the Westminster Leningrad Codex (public domain) via MACULA
Hebrew in orig/heb.sqlite, and for the NT the Berean Greek Bible (orig/grc/, CC0).

- A notes table with a row per verse (Verse · Hebrew · <language> · BSB · Comment) gets the whole verse in its original
  column, written here from the WLC / BGB (the agent leaves it empty, or anything it wrote is replaced).
- A table with a row per choice (Danish, Jamaican: the Hebrew phrase · the rendering · …) keeps the agent's phrase;
  quotes.py checks that a long one is the WLC word for word.
- The file ends with a credit line for the original text (replaced, not repeated, on a second run).

    python3 scripts/notes_hebrew.py <project> <code> <ch>      fill one chapter's notes
    python3 scripts/notes_hebrew.py <project> --all            every chapter's notes in the project (and its test drafts)
    python3 scripts/notes_hebrew.py show <code> <ch>:<v>       print one verse of the open original (for an agent)
"""
import glob, os, re, sqlite3, sys

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
from books import BY_CODE  # noqa: E402
from project import project_dir  # noqa: E402

CREDIT_MARK = "Original text in these notes:"
CREDIT = {"ot": f"*{CREDIT_MARK} Hebrew from the Westminster Leningrad Codex (public domain), via MACULA Hebrew "
                f"(CC BY 4.0, Clear Bible), filled in by scripts/notes_hebrew.py.*",
          "nt": f"*{CREDIT_MARK} Greek from the Berean Greek Bible (public domain, CC0), filled in by "
                f"scripts/notes_hebrew.py.*"}
VERSE_HEAD = re.compile(r"^(verse|vers|v\.?|vers\.?)$", re.I)
SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def original_verses(code, ch):
    """{verse: text} of the open original: WLC (MACULA Hebrew, orig/heb.sqlite) or BGB (orig/grc)."""
    if BY_CODE[code][2] == "nt":
        import langtools as LT
        f = os.path.join(ROOT, "orig", "grc", f"{code}{ch:03d}.txt")
        return {v: t for (c, v), t in LT.verses_of(f).items()} if os.path.exists(f) else {}
    db = os.path.join(ROOT, "orig", "heb.sqlite")
    if not os.path.exists(db):
        raise SystemExit("orig/heb.sqlite is missing: python3 scripts/setup.py --only src")
    out = {}
    for v, t, a in sqlite3.connect(db).execute("select v, text, after from tokens where book=? and ch=? order by key",
                                              (code.upper(), ch)):
        out[v] = out.get(v, "") + (t or "") + (a or "")
    return {v: re.sub(r"\s+", " ", t).strip() for v, t in out.items()}


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def notes_table(md):
    """The notes' verse table (the first Markdown table whose first column is Verse/Vers):
    -> (rows, header cells, the notes without it, (first line, last line) of the table or None)."""
    lines, rows, head, out, i, span = md.splitlines(), [], None, [], 0, None
    while i < len(lines):
        l = lines[i]
        if head is None and l.lstrip().startswith("|") and VERSE_HEAD.match(split_row(l)[0]) and i + 1 < len(lines) \
                and SEP.match(lines[i + 1]):
            head, start, i = split_row(l), i, i + 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            span = (start, i)
            k = len(out) - 1                       # the table's own heading, when nothing else is under it
            while k >= 0 and not out[k].strip():
                k -= 1
            nxt = next((x for x in lines[i:] if x.strip()), "")
            if k >= 0 and re.match(r"^#{1,6} ", out[k]) and (not nxt or re.match(r"^#{1,6} ", nxt)):
                del out[k:]
            continue
        out.append(l)
        i += 1
    return rows, head, "\n".join(l for l in out if CREDIT_MARK not in l), span


def verse_numbers(cell):
    """'1' '1.2.6.22' '1–3' '3,5' '16a' 'v3' -> [1, 2, …]"""
    out = []
    for part in re.split(r"[.,;/ ]+", re.sub(r"^v", "", cell.strip(), flags=re.I)):
        m = re.match(r"^(\d+)[a-z]?(?:\s*[-–]\s*(\d+))?", part)
        if m:
            a, b = int(m[1]), int(m[2] or m[1])
            out += list(range(a, min(b, a + 200) + 1))
    return out


def per_verse(rows, orig):
    """A row per verse whose original column is the verse (whole, left empty, or cut to a few words with …), not a
    row per choice (Danish, Jamaican), even where a chapter has one choice per verse (a list of names)."""
    vs = [verse_numbers(r[0]) for r in rows]
    if not (rows and orig and len(rows) >= 0.8 * len(orig) and all(len(v) == 1 for v in vs)
            and len({v[0] for v in vs}) == len(vs)):
        return False

    def whole(r, v):
        cell = r[1].strip() if len(r) > 1 else ""
        n, full = len(cell.split()), len((orig.get(v) or "").split())
        return not cell or cell.endswith("…") or (full and n >= 0.6 * full)
    return sum(whole(r, v[0]) for r, v in zip(rows, vs)) >= 0.8 * len(rows)


def fill(path, code, ch):
    """Fill one notes file: the whole verse in a per-verse table's original column, and the credit line. -> (cells, changed)"""
    md = open(path, encoding="utf-8").read()
    rows, head, _, span = notes_table(md)
    orig = original_verses(code, ch)
    lines, cells = md.splitlines(), 0
    if span and head and len(head) >= 3 and per_verse(rows, orig):
        for i in range(span[0] + 2, span[1]):
            c = split_row(lines[i])
            vs = verse_numbers(c[0])
            if len(c) >= 3 and vs and orig.get(vs[0]) and c[1] != orig[vs[0]]:
                c[1] = orig[vs[0]].replace("|", "/")
                lines[i] = "| " + " | ".join(c) + " |"
                cells += 1
    body = "\n".join(l for l in lines if CREDIT_MARK not in l).rstrip()
    new = body + "\n\n" + CREDIT["nt" if BY_CODE[code][2] == "nt" else "ot"] + "\n"
    if new != md:
        open(path, "w", encoding="utf-8").write(new)
    return cells, new != md


def project_notes(pname):
    pdir = project_dir(pname)
    out = []
    for f in sorted(glob.glob(os.path.join(pdir, "**", "*_notes.md"), recursive=True)):
        if "/_eval/local/" in f.replace(os.sep, "/"):
            continue
        m = re.fullmatch(r"([0-9a-z]{3})(\d{3})_notes\.md", os.path.basename(f))
        if m and m[1] in BY_CODE:
            out.append((f, m[1], int(m[2])))
    return out


def main():
    a = sys.argv[1:]
    if a[:1] == ["show"] and len(a) == 3:
        ch, v = map(int, a[2].split(":"))
        print(original_verses(a[1], ch).get(v, ""))
        return
    if len(a) == 2 and a[1] == "--all":
        todo = project_notes(a[0])
    elif len(a) == 3:
        f = os.path.join(project_dir(a[0]), a[1], f"{a[1]}{int(a[2]):03d}_notes.md")
        if not os.path.exists(f):
            raise SystemExit(f"no notes {os.path.relpath(f, ROOT)}")
        todo = [(f, a[1], int(a[2]))]
    else:
        raise SystemExit(__doc__)
    cells = changed = 0
    for f, code, ch in todo:
        c, ch_ = fill(f, code, ch)
        cells += c
        changed += ch_
    print(f"{a[0]}: {len(todo)} notes files, {changed} changed, {cells} verses filled from the open original")


if __name__ == "__main__":
    main()
