#!/usr/bin/env python3
"""Score a language store (profile/*.json) against a checklist of topics: how much of a reference store a test run
found. Each topic has one or more regular expressions; it counts as found when one matches the text of a live entry
(id, value, note, forms) of the store, both with accents and tone marks folded away. Used to compare study agents (internal-docs plan, Part B phase 5).

Checklist (JSON): {"topics": {"<topic>": ["<regex>", ...], ...}}

    python3 scripts/score_store.py <store dir> <checklist.json> [--missing]
"""
import json, os, re, sys, unicodedata


def fold(s):
    """Accents and tone marks off, so that a store writing the folded form (-eav) matches the checklist's -eáv."""
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def store_text(d):
    out = []
    for f in ("observations.json", "decisions.json"):
        p = os.path.join(d, f)
        if os.path.exists(p):
            for e in json.load(open(p, encoding="utf-8")).get("entries", []):
                if e.get("status") in ("superseded", "rejected"):
                    continue
                out.append(" ".join(str(e.get(k, "")) for k in ("id", "value", "note"))
                           + " " + " ".join(str(x.get("form", "")) for x in e.get("evidence", []) if isinstance(x, dict)))
    return "\n".join(out)


def score(d, checklist):
    text = fold(store_text(d))
    topics = json.load(open(checklist, encoding="utf-8"))["topics"]
    found = {t: any(re.search(fold(rx), text, re.I) for rx in rxs) for t, rxs in topics.items()}
    return found


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    found = score(a[0], a[1])
    n = sum(found.values())
    print(f"{a[0]}: {n} of {len(found)} topics ({100 * n / len(found):.0f}%)")
    if "--missing" in a:
        print("  missing: " + ", ".join(t for t, ok in found.items() if not ok))


if __name__ == "__main__":
    main()
