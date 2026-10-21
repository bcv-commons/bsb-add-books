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
  ===title=== lines aside);
- spelling (projects with `spell_check: true`, or `--spell`): every word form the style corpus writes
  only with other marks ("spelling: zøveqase -> zøveqasé"), and every form it doesn't have at all
  ("not in the corpus"), reported as information: a new name or word may be right, a mark seldom is.
  With morph entries in the store (scripts/morphs.py), a form the corpus lacks but whose parts it has (the store's
  affixes on the stem of a corpus word) is listed apart, "built from parts: tukamubona = tu-ka-mu-bon-a", with a
  note where the stem has other marks than the corpus gives it.
  Matching elsewhere ignores the project's `ignore_marks`; this check keeps every mark.

OT chapters whose verses fall in other BSB chapters (orig/vrs, see vrs.py) are
reported as information, not as problems: the draft keeps the Hebrew numbering.

Usage: python3 scripts/check_draft.py <project> [code ...] [--spell] [--chapter N]   (default: all books)
"""
import os, re, sys
from project import project, sources, ROOT, project_dir
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
    a = sys.argv[1:]
    spell = "--spell" in a
    only = int(a[a.index("--chapter") + 1]) if "--chapter" in a else None
    a = [x for i, x in enumerate(a) if x != "--spell" and x != "--chapter" and not (i and a[i - 1] == "--chapter")]
    pname = a[0]
    p = project(pname)
    base = project_dir(pname)
    codes = a[1:] or sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))
                             and re.fullmatch(r"[0-9a-z]{3}", d))
    LP = None
    import modes
    if spell or modes.mode(p)["spell_check"]:
        import langtools as LT
        LP = LT.Project(pname)
    n_bad = n = 0
    for code in codes:
        d = os.path.join(base, code)
        for f in sorted(os.listdir(d)):
            if re.fullmatch(r"[0-9a-z]{3}\d{3}\.txt", f):
                if only is not None and int(f[3:6]) != only:
                    continue
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
                if LP:
                    import langtools as LT
                    text = " ".join(LT.verses_of(os.path.join(d, f)).values())
                    marks, unknown = LP.spell_check(text)
                    parts, unknown = LP.built(unknown)
                    if marks:
                        print(f"{f}: spelling: " + "; ".join(
                            f"{w}{f' ×{k}' if k > 1 else ''} -> {', '.join(c)}" for w, k, c in marks))
                    if parts:
                        print(f"{f}: built from parts: " + "; ".join(
                            f"{w}{f' ×{k}' if k > 1 else ''} = {p}" + (f" ({nt})" if nt else "") for w, k, p, nt in parts))
                    if unknown:
                        print(f"{f}: not in the corpus: " + ", ".join(f"{w}{f' ×{k}' if k > 1 else ''}" for w, k in unknown))
    print(f"{n} chapters checked, {n_bad} with problems")


if __name__ == "__main__":
    main()
