"""Mechanical checks for drafted chapters in export/<project>/<code>/<code>NNN.txt.

For each chapter:
- the 'vN' markers match the verses of the original text exactly (order, no gaps,
  no duplicates; Hebrew numbering in the OT, the project's Greek text in the NT);
- inline notes ({T:} {E:} {H:} {N:}): none, unless the project sets inline_notes; then only its
  kinds, balanced braces, no space before a note, {N:} only with a glossary key, and verse references
  inside a note written "v. 12", never "v12" (reserved for verse markers);
- opening and closing quotes are balanced (quote pair from project.yaml);
- no prose line longer than 105 characters (run wrap_draft.py);
- the _notes.md and _footnotes.txt files exist, and every footnote verse exists (header and
  ===title=== lines aside).

OT chapters whose verses fall in other BSB chapters (orig/vrs, see vrs.py) are
reported as information, not as problems: the draft keeps the Hebrew numbering.

Usage: python3 scripts/check_draft.py <project> [code ...]     (default: all books)
"""
import os, re, sys
from project import project, sources, ROOT
import vrs


def orig_file_verses(path, nt):
    # NT: 'chapter:verse text'; OT (heb): 'verse:indent text'
    vs = []
    for line in open(path, encoding="utf-8").read().splitlines()[1:]:
        m = re.match(r"(\d+):(\d+)", line)
        if not m:
            continue
        v = int(m.group(2) if nt else m.group(1))
        if not vs or vs[-1] != v:
            vs.append(v)
    return vs


def check(pname, p, code, path):
    problems = []
    ch = int(os.path.basename(path)[3:6])
    orig_dir, _, _ = sources(p, code)
    src = os.path.join(ROOT, orig_dir, f"{code}{ch:03d}.txt")
    text = open(path, encoding="utf-8").read()
    body = "\n".join(l for l in text.splitlines() if not l.startswith("!!"))
    inl = p.get("inline_notes")
    notes = list(re.finditer(r"\{([A-Z]):([^{}]*)\}", body))
    plain = re.sub(r"\{[A-Z]:[^{}]*\}", "", body)          # the text without its inline notes
    marks = [int(x) for x in re.findall(r"(?<![\w>.])v(\d+)(?=\s)", plain)]
    want = orig_file_verses(src, orig_dir != "orig/heb") if os.path.exists(src) else None
    if want is None:
        problems.append(f"no original text {src}")
    elif marks != want:
        missing = sorted(set(want) - set(marks))
        extra = sorted(set(marks) - set(want))
        dup = sorted({v for v in marks if marks.count(v) > 1})
        problems.append(f"verses differ from {orig_dir}: missing {missing} extra {extra} duplicate {dup}")
    if not inl:
        if re.search(r"\{[TEHN]:", body):
            problems.append("inline notes in text")
    else:
        kinds = {k for k in inl if len(k) == 1}
        if plain.count("{") or plain.count("}"):
            problems.append("unbalanced or nested braces in inline notes")
        bad = sorted({m[1] for m in notes} - kinds)
        if bad:
            problems.append(f"inline note kinds not in project.yaml: {bad}")
        if [m for m in notes if m.start() and body[m.start() - 1] in " \n"]:
            problems.append("space before an inline note")
        if inl.get("glossary"):
            keys = sorted({m[2].strip() for m in notes if m[1] == "N"} - set(inl["glossary"]))
            if keys:
                problems.append(f"{{N:}} keys not in the glossary: {keys}")
        vn = [m[2] for m in notes if re.search(r"(?<![\w>.])v\d+", m[2])]
        if vn:
            problems.append(f"'vN' inside {len(vn)} inline note(s): write 'v. N'")
    quotes = p.get("quotes") or "„“"           # a pair: „“, or a pair of two-character marks, >><<
    q_open, q_close = quotes[:len(quotes) // 2], quotes[len(quotes) // 2:]
    if body.count(q_open) != body.count(q_close):
        problems.append(f"quotes unbalanced {q_open}{body.count(q_open)} / {q_close}{body.count(q_close)}")
    long = [l for l in body.splitlines() if len(l) > 105 and not l.startswith("//")]
    if long:
        problems.append(f"{len(long)} long lines (run wrap_draft.py)")
    stem = path[:-4]
    if not os.path.exists(stem + "_notes.md"):
        problems.append("no _notes.md")
    fn = stem + "_footnotes.txt"
    if os.path.exists(fn) and want:
        bad = [l for l in open(fn, encoding="utf-8").read().splitlines()
               if l.strip() and not l.startswith(("!!", "===")) and (not re.match(r"v(\d+)", l) or int(re.match(r"v(\d+)", l).group(1)) not in want)]
        if bad:
            problems.append(f"footnotes with unknown verse: {bad[:3]}")
    return problems


def main():
    pname = sys.argv[1]
    p = project(pname)
    base = os.path.join(ROOT, "export", pname)
    codes = sys.argv[2:] or sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
    n_bad = n = 0
    for code in codes:
        d = os.path.join(base, code)
        for f in sorted(os.listdir(d)):
            if re.fullmatch(r"[0-9a-z]{3}\d{3}\.txt", f):
                n += 1
                probs = check(pname, p, code, os.path.join(d, f))
                if probs:
                    n_bad += 1
                    print(f"{f}: " + "; ".join(probs))
                ch = int(f[3:6])
                if sources(p, code)[0] == "orig/heb" and os.path.exists(os.path.join(ROOT, "orig", "heb", f)):
                    bsb, shifts = vrs.chapter(code, ch)
                    if bsb != [ch]:
                        print(f"{f}: info: BSB numbering differs: " + "; ".join(shifts))
    print(f"{n} chapters checked, {n_bad} with problems")


if __name__ == "__main__":
    main()
