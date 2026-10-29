"""Wrap prose paragraphs of a tekst-style draft file at ~100 chars, in place.
Lines starting with '!!', '===', '==' or '//' (poetry lines) and blank lines are left untouched.
Usage: python3 scripts/wrap_draft.py <file> [...]"""
import re, sys, textwrap

for path in sys.argv[1:]:
    out, para = [], []
    def flush():
        if para:
            # glue each verse marker to the following word so a line never ends in "vN"
            text = re.sub(r"\b(v\d+) ", "\\1\x00", " ".join(para))
            out.extend(l.replace("\x00", " ") for l in textwrap.wrap(text, 100, break_on_hyphens=False))
            para.clear()
    for line in open(path, encoding="utf-8").read().split("\n"):
        if not line.strip() or line.startswith(("!!", "==", "//")):
            flush(); out.append(line)
        else:
            para.append(line.strip())
    flush()
    open(path, "w", encoding="utf-8").write("\n".join(out).rstrip() + "\n")
