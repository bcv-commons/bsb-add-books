#!/usr/bin/env python3
"""Build orig/heb/<code>NNN.txt from bcv-query's Hebrew clause layout (MACULA Hebrew + UHB; no NC data).

Input: a bcv-query release, or a delivery folder: any folder holding <BOOK>_<CCC>.jsonl files, one
row per clause segment (docs/proposals/hebrew-clause-layout/schema/clause_segment.schema.json),
anywhere below it. A build.json next to them gives the segmentation version.

Output, one file per chapter, in the same format as the BHSA and MACULA routes:

    <code> <chapter>
    <verse>:<level> <text>          one line per clause segment, Hebrew verse numbering

- level: text_depth (the text-level hierarchy), or text_depth_law with --law.
- text: the segment's text as bcv-query gives it (the qere where ketiv and qere differ; the ketiv
  is in the row's ketiv_qere).
- orig/heb-keys/<code>NNN.json, parallel to the lines: each segment's verse, first word key,
  clause_key and words, for the clause sidecars (word keys stay valid as long as the segmentation
  version does).
- orig/heb/_source.json: where the files come from (input, segmentation version, depth field).

Usage: python3 scripts/build_heb_bcvquery.py <release or delivery dir> [--law] [--out DIR] [code ...]
"""
import glob, json, os, re, sys
from books import BY_CODE, ROOT


def main():
    argv = sys.argv[1:]
    law = "--law" in argv
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(ROOT, "orig", "heb")
    args = [a for a in argv if not a.startswith("--") and a != out]
    if not args:
        raise SystemExit(__doc__)
    src, codes = args[0], set(args[1:])
    field = "text_depth_law" if law else "text_depth"
    keys_dir = os.path.join(os.path.dirname(out.rstrip("/")), os.path.basename(out.rstrip("/")) + "-keys")
    files = {}
    for path in glob.glob(os.path.join(src, "**", "*.jsonl"), recursive=True):
        m = re.fullmatch(r"([1-3A-Z]{3})_(\d{3})\.jsonl", os.path.basename(path))
        if m and m[1].lower() in BY_CODE and (not codes or m[1].lower() in codes):
            files.setdefault((m[1].lower(), int(m[2])), path)      # a chapter in several sets: the first one
    if not files:
        raise SystemExit(f"no <BOOK>_<CCC>.jsonl files under {src}")
    os.makedirs(out, exist_ok=True)
    os.makedirs(keys_dir, exist_ok=True)
    seg_version = None
    for b in glob.glob(os.path.join(src, "**", "build.json"), recursive=True):
        seg_version = (json.load(open(b, encoding="utf-8")).get("segmentation") or {}).get("version")
        break
    for (code, ch), path in sorted(files.items()):
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        rows.sort(key=lambda r: (r["verse"], r.get("seg", 0)))
        lines = [f"{code} {ch}"] + [f"{r['verse']}:{r[field]} {r['text']}" for r in rows]
        open(os.path.join(out, f"{code}{ch:03d}.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
        keys = [{"verse": r["verse"], "first": r["first"], "clause_key": r["clause_key"], "words": r["words"]} for r in rows]
        json.dump(keys, open(os.path.join(keys_dir, f"{code}{ch:03d}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"source": "bcv-query", "input": os.path.abspath(src), "segmentation": seg_version, "levels": field,
               "chapters": len(files)}, open(os.path.join(out, "_source.json"), "w", encoding="utf-8"), indent=1)
    print(f"orig/heb: {len(files)} chapters from {src} ({field}; segmentation {seg_version}) -> {out}")


if __name__ == "__main__":
    main()
