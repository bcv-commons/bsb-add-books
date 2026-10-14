"""USFM -> USJ, the way bcv-commons/bibles does it: parse with usfmtc (pip install usfmtc), with
that repo's two fixes for usfmtc bugs (both CC0, from github.com/bcv-commons/bibles):

- protect()/restore() (pipeline/core/usfm_pipes.py): a `|` used as text, not as the start of a
  marker's attributes, survives parsing (usfmtc drops everything after it);
- fix_adjacent_w_spacing() (pipeline/core/usfm_to_verses.py): the space between two adjacent
  \\w … \\w* words, which usfmtc's outUsj() drops, is put back. Here it is widened to any two
  adjacent character markers: usfmtc drops that space between other markers too (eng-asv
  Gen 1:16 "\\add he made\\add* \\w the\\w*" came out "he madethe").
Line breaks inside a paragraph's text become spaces.

    from usfm_usj import usfm_to_usj
    usj = usfm_to_usj(usfm_text)      # USJ 3.0 dict; its "content" works with convert_usj.py

Used by fetch_edition.py (eBible) and by sync scripts in import/ (Den Frie Bibel's sfm/).
"""
import os, re, tempfile

PLACEHOLDER = "\ue000"  # private use: never in a source text
_NESTED = r"(?:[^\\]|\\\+[a-z]+\d*\*?)"  # text, or a nested \+tag / \+tag* inside the span
_KEEP = re.compile(
    r"\\(\+?)([a-z]+\d*)\s" + _NESTED + r"*?\|[^\\]*?\\\1\2\*"   # \tag ... | ... \tag*
    r"|\\[a-z]+\d*-[se]\s*\|[^\\]*?\\\*"                          # \tag-s |...\*
    r"|\\(f|fe|x)\s.*?\\\3\*"                                     # notes
    r"|\\rem\b[^\n]*",                                              # remarks
    re.S)


def protect(usfm):
    """Swap each `|` that is text for a placeholder (attribute spans, notes and \\rem keep theirs)."""
    if PLACEHOLDER in usfm:
        raise ValueError("source text contains the pipe placeholder U+E000")
    out, pos = [], 0
    for m in _KEEP.finditer(usfm):
        out.append(usfm[pos:m.start()].replace("|", PLACEHOLDER))
        out.append(m.group(0))
        pos = m.end()
    out.append(usfm[pos:].replace("|", PLACEHOLDER))
    return "".join(out)


def restore(node):
    """Put `|` back in every string of a parsed USJ tree (in place); returns the tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str):
                node[k] = v.replace(PLACEHOLDER, "|")
            else:
                restore(v)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, str):
                node[i] = v.replace(PLACEHOLDER, "|")
            else:
                restore(v)
    return node


def fix_adjacent_w_spacing(node):
    """Insert the space usfmtc drops between two adjacent character-marker nodes (in place), and turn
    line breaks inside text into spaces."""
    if isinstance(node, dict):
        content = node.get("content")
        if isinstance(content, list):
            fixed, prev_was_char = [], False
            for child in content:
                is_char = isinstance(child, dict) and child.get("type") == "char"
                if is_char and prev_was_char:
                    fixed.append(" ")
                fixed.append(child.replace("\n", " ") if isinstance(child, str) else child)
                prev_was_char = is_char
            node["content"] = fixed
        for value in node.values():
            if isinstance(value, (dict, list)):
                fix_adjacent_w_spacing(value)
    elif isinstance(node, list):
        for item in node:
            fix_adjacent_w_spacing(item)
    return node


def usfm_to_usj(usfm):
    try:
        import usfmtc
    except ImportError:
        raise SystemExit("USFM sources need usfmtc: pip install usfmtc")
    with tempfile.NamedTemporaryFile("w", suffix=".usfm", delete=False, encoding="utf-8") as f:
        f.write(protect(usfm))
        path = f.name
    try:
        usj = restore(usfmtc.readFile(path).outUsj())
    finally:
        os.remove(path)
    return fix_adjacent_w_spacing(usj)
