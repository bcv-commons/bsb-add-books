#!/usr/bin/env python3
"""Move a clause-line draft from one Hebrew clause layout to another (BHSA <-> bcv-query <-> MACULA).

A clause-line draft has one target line per line of its layout (orig/heb-<layout>/<code>NNN.txt):
'//N text', '//N =' for a merged line (scripts/clause_sidecar.py). The layouts segment the same Hebrew
words differently, so the draft's lines are re-assigned by the words: each source line goes to the
target segment that holds its first Hebrew word (words matched per verse on their consonants).
- a target segment that gets one or more source lines takes their text, joined;
- a target segment that gets none (the target layout split a source line) becomes '//N =', merged into
  the line above;
- N is the target layout's level + 1.
Headings and blank lines travel with the line they precede. Check the result with
scripts/check_clauses-style tools or clause_sidecar.py against the target layout; read the joined and
merged lines, which may want a reorder.

Usage: python3 scripts/relayout.py <draft> --from <layout dir or file> --to <layout dir or file> [--out FILE]
       e.g. --from orig/heb-bhsa --to orig/heb-bcv-query (the chapter file is found by the draft's name)
"""
import difflib, os, re, sys


def layout(path):
    rows = []
    for l in open(path, encoding="utf-8").read().splitlines()[1:]:
        m = re.match(r"(\d+):(\d+) (.*)$", l)
        if m:
            rows.append((int(m[1]), int(m[2]), m[3].strip()))
    return rows


def words(t):
    return [c for c in (re.sub(r"[^א-ת]", "", w) for w in t.replace("־", " ").replace("׀", " ").split()) if c]


def draft_lines(path):
    head, lines, pending = [], [], []
    for l in open(path, encoding="utf-8").read().splitlines():
        m = re.match(r"//(\d+) (.*)$", l)
        if m:
            lines.append((pending, m[2])); pending = []
        elif not lines:
            head.append(l)
        else:
            pending.append(l)
    return head, lines, pending


def relayout(draft, src, dst):
    """(new text, stats). src and dst are layout chapter files."""
    A, B = layout(src), layout(dst)
    head, lines, tail = draft_lines(draft)
    if len(lines) != len(A):
        raise SystemExit(f"{draft}: {len(lines)} clause lines, but {src} has {len(A)}: is the draft on that layout?")
    seg_of = []
    for v in sorted({a[0] for a in A}):
        ai = [i for i, a in enumerate(A) if a[0] == v]
        bi = [j for j, b in enumerate(B) if b[0] == v]
        if not bi:
            raise SystemExit(f"verse {v} is missing in {dst}")
        aw = [(i, w) for i in ai for w in words(A[i][2])]
        bw = [(j, w) for j in bi for w in words(B[j][2])]
        sm = difflib.SequenceMatcher(None, [w for _, w in aw], [w for _, w in bw], autojunk=False)
        pos = {blk.a + k: blk.b + k for blk in sm.get_matching_blocks() for k in range(blk.size)}
        for i in ai:
            first = next((x for x, (ii, _) in enumerate(aw) if ii == i), None)
            near = [pos[x] for x in range(first, -1, -1) if x in pos] if first is not None else []
            seg_of.append(bw[near[0]][0] if near else bi[0])
    groups = {j: [] for j in range(len(B))}
    for i, j in enumerate(seg_of):
        groups[j].append(i)
    body, stats = [], {"one": 0, "joined": 0, "merged": 0}
    for j, b in enumerate(B):
        for i in groups[j]:
            body += lines[i][0]
        texts = [lines[i][1] for i in groups[j] if not lines[i][1].startswith("=")]
        if not texts:
            stats["merged"] += 1
            body.append(f"//{b[1] + 1} =")
        else:
            stats["one" if len(groups[j]) == 1 else "joined"] += 1
            body.append(f"//{b[1] + 1} " + " ".join(texts))
    return "\n".join(head + body + tail) + "\n", stats, len(A), len(B)


def main():
    a = sys.argv[1:]
    if len(a) < 5 or "--from" not in a or "--to" not in a:
        raise SystemExit(__doc__)
    draft = a[0]
    m = re.search(r"[0-9a-z]{3}\d{3}", os.path.basename(draft))
    def pick(p):
        if not os.path.isdir(p):
            return p
        if not m:
            raise SystemExit(f"{draft}: no <code>NNN in the file name; pass the layout files themselves")
        return os.path.join(p, m[0] + ".txt")
    src, dst = pick(a[a.index("--from") + 1]), pick(a[a.index("--to") + 1])
    text, stats, na, nb = relayout(draft, src, dst)
    out = a[a.index("--out") + 1] if "--out" in a else None
    if out:
        open(out, "w", encoding="utf-8").write(text)
    else:
        sys.stdout.write(text)
    print(f"{draft}: {na} lines on {src} -> {nb} on {dst}: {stats['one']} one to one, {stats['joined']} joined, "
          f"{stats['merged']} merged", file=sys.stderr)


if __name__ == "__main__":
    main()
