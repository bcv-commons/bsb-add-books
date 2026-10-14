#!/usr/bin/env python3
"""What a chapter costs: tokens, tool calls and minutes per drafting agent, logged per project, summarised by
familiarity across all projects (the wizard's estimates come from here; docs/onboarding.md).

    python3 scripts/usage.py <project> add <code><nnn> --tokens N [--calls N] [--minutes M] [--note TEXT]
    python3 scripts/usage.py summary            # per familiarity: chapters logged, median tokens per chapter

The log is export/<project>/_learn/usage.tsv (figures only, in git): date, chapter, familiarity, tokens, calls,
minutes, note. The draft-chapter skill adds a line after every chapter from the agent's usage report.
"""
import datetime, glob, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from project import project  # noqa: E402

COLS = ["date", "chapter", "familiarity", "tokens", "calls", "minutes", "note"]


def log_path(pname):
    return os.path.join(ROOT, "export", pname, "_learn", "usage.tsv")


def rows(path):
    if not os.path.exists(path):
        return []
    lines = open(path, encoding="utf-8").read().splitlines()
    return [dict(zip(COLS, l.split("\t"))) for l in lines[1:] if l.strip()]


def add(pname, chapter, tokens, calls="", minutes="", note=""):
    path = log_path(pname)
    fam = project(pname).get("familiarity") or "unset"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write("\t".join(COLS) + "\n")
        f.write("\t".join(str(x) for x in (datetime.date.today().isoformat(), chapter, fam, tokens, calls, minutes,
                                           note.replace("\t", " "))) + "\n")


def by_familiarity():
    """{familiarity: [tokens per chapter, ...]} over every project's log."""
    out = {}
    for f in glob.glob(os.path.join(ROOT, "export", "*", "*", "_learn", "usage.tsv")):
        for r in rows(f):
            if r.get("tokens", "").isdigit():
                out.setdefault(r["familiarity"], []).append(int(r["tokens"]))
    return out


def estimate(familiarity):
    """(median tokens per chapter, chapters logged) for a familiarity, or None if nothing is logged yet."""
    xs = by_familiarity().get(familiarity)
    return (int(statistics.median(xs)), len(xs)) if xs else None


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    if a[0] == "summary":
        for fam, xs in sorted(by_familiarity().items()):
            print(f"{fam:8} {len(xs):3} chapters  median {int(statistics.median(xs)):>8} tokens  (min {min(xs)}, max {max(xs)})")
        return
    if len(a) < 3 or a[1] != "add" or "--tokens" not in a:
        raise SystemExit(__doc__)
    opt = lambda k: a[a.index(k) + 1] if k in a else ""
    add(a[0], a[2], int(opt("--tokens")), opt("--calls"), opt("--minutes"), opt("--note"))
    print(f"logged {a[2]} in {os.path.relpath(log_path(a[0]), ROOT)}")


if __name__ == "__main__":
    main()
