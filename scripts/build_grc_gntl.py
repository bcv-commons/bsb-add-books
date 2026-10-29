#!/usr/bin/env python3
"""Build orig/grc-gntl/<code>NNN.txt from the Greek NT clause layout (bcv-commons/greek-nt-clause-layout, CC BY 4.0;
MACULA Greek, Nestle 1904), for the website's Greek clause view of NT drafts (scripts/clause_lines.py).

Input: download/greek-nt-clause-layout/<tag>/clauses.parquet (`setup.py --only gntl`, pinned). Needs pyarrow.

Output, one file per chapter, in the format of the Hebrew layouts:

    <code> <chapter>
    <verse>:<level> <text>          one line per clause segment; level = text_depth

- orig/grc-gntl-keys/<code>NNN.json, parallel to the lines: each segment's verse, first word key, clause key and words
  (MACULA Greek ids, the keys of the compact-alignments index), as orig/heb-bcv-query-keys/ for the Hebrew.
- orig/grc-gntl/_source.json: the input and its tag.

Usage: python3 scripts/build_grc_gntl.py [code ...]
"""
import collections, json, os, sys
from books import BY_CODE, CODE, ROOT

sys.path.insert(0, os.path.join(CODE, "scripts"))
from setup import GNTL_TAG  # noqa: E402

SRC = os.path.join(ROOT, "download", "greek-nt-clause-layout", GNTL_TAG, "clauses.parquet")
OUT = os.path.join(ROOT, "orig", "grc-gntl")
KEYS = os.path.join(ROOT, "orig", "grc-gntl-keys")


def main():
    import pyarrow.parquet as pq
    only = {c.lower() for c in sys.argv[1:]}
    if not os.path.exists(SRC):
        raise SystemExit(f"{os.path.relpath(SRC, ROOT)} missing: python3 scripts/setup.py --only gntl")
    code_of = {c.upper(): c for c in BY_CODE if BY_CODE[c][2] == "nt"}
    rows = pq.read_table(SRC, columns=["book", "chapter", "verse", "seg", "text", "text_depth", "clause", "first",
                                       "words"]).to_pylist()
    by = collections.defaultdict(list)
    for r in rows:
        code = code_of.get(r["book"])
        if code and (not only or code in only):
            by[(code, r["chapter"])].append(r)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(KEYS, exist_ok=True)
    for (code, ch), rs in sorted(by.items()):
        rs.sort(key=lambda r: r["seg"])
        lines = [f"{code} {ch}"] + [f"{r['verse']}:{r['text_depth']} {r['text']}" for r in rs]
        open(os.path.join(OUT, f"{code}{ch:03d}.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
        keys = [{"verse": r["verse"], "first": r["first"], "clause_key": r["clause"] or r["first"], "words": r["words"]}
                for r in rs]
        json.dump(keys, open(os.path.join(KEYS, f"{code}{ch:03d}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"input": os.path.relpath(SRC, ROOT), "dataset": "bcv-commons/greek-nt-clause-layout", "tag": GNTL_TAG,
               "licence": "CC BY 4.0", "depth": "text_depth"}, open(os.path.join(OUT, "_source.json"), "w"), indent=1)
    print(f"orig/grc-gntl/: {len(by)} chapters from greek-nt-clause-layout {GNTL_TAG}")


if __name__ == "__main__":
    main()
