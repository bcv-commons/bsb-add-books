#!/usr/bin/env python3
"""Where a reviewer looks first: the verses where the project's draft and an independent second draft disagree most.
The signal is chrF between the two drafts' verses (plain tokens, marks ignored): low = disagree. Tested against a held-out
human text, the lowest quarter by this signal finds the agent's weaker verses better than chance (AUC about 0.65-0.7),
with an NLLB second draft as well as an in-context one.

Second drafts are read from <project>/_eval/local/second/<name>/<code>NNN.txt (`icl` from scripts/icl_draft.py; any
other name for a second draft from another system, e.g. `nllb` from a fine-tuned NLLB model). Without --second, a chapter
uses `nllb` where the project has an NLLB draft of it, else `icl`; with --second, the named drafts are averaged. The
output names verses and figures only, no text, so it may
go into a review overview (--overview: a section between triage markers in <code>/<code>_review_overview.md, or the
project's review_overview.md, replaced on a rerun).

Usage: python3 scripts/triage.py <project> <code> <ch>[-<ch>|,<ch>..] [--second nllb,icl] [--share 0.25] [--overview]
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import langtools as LT  # noqa: E402
from project import project_dir  # noqa: E402

BEGIN, END = "<!-- triage:begin -->", "<!-- triage:end -->"


def chapters(spec):
    out = []
    for part in spec.split(","):
        lo, _, hi = part.partition("-")
        out += list(range(int(lo), int(hi or lo) + 1))
    return out


def rows(pname, code, chs, names):
    P = LT.Project(pname)
    pd = project_dir(pname)
    pl = P.tok.plain
    out, used = [], set()
    for ch in chs:
        f = os.path.join(pd, code, f"{code}{ch:03d}.txt")
        if not os.path.exists(f):
            print(f"# no draft {os.path.relpath(f, ROOT)}", file=sys.stderr)
            continue
        draft = {k: t for k, t in LT.verses_of(f).items() if k[0] == ch}
        sec = {}
        for n in (names or ("nllb", "icl")):
            sf = os.path.join(pd, "_eval", "local", "second", n, f"{code}{ch:03d}.txt")
            if os.path.exists(sf):
                sec[n] = {(ch, v): t for (c, v), t in LT.verses_of(sf).items()}
                if not names:            # the default: the first that exists
                    break
        if not sec:
            print(f"# {code} {ch}: no second draft ({', '.join(names or ('nllb', 'icl'))})", file=sys.stderr)
            continue
        used |= set(sec)
        for k in sorted(draft):
            s = {n: LT.chrf(pl(draft[k]), pl(d[k])) for n, d in sec.items() if d.get(k)}
            if s:
                out.append((k, sum(s.values()) / len(s), s))
    return out, sorted(used)


def table(code, rs, used, share):
    rs = sorted(rs, key=lambda r: r[1])
    n = max(1, round(len(rs) * share))
    first = {r[0] for r in rs[:n]}
    lines = [f"Verses where the draft and the second draft{'s' if len(used) > 1 else ''} ({', '.join(used)}) agree least: "
             f"a reviewer looks at these first ({n} of {len(rs)}, the lowest {share:.0%}). Agreement is chrF between the "
             f"drafts (0-100); it says where they differ, not which is right (`scripts/triage.py`).", "",
             "| Verse | Agreement | " + " | ".join(used) + " |", "|---|---|" + "---|" * len(used)]
    for k, m, s in rs[:n]:
        lines.append(f"| {k[0]}:{k[1]} | **{m:.0f}** | " + " | ".join(f"{s[u]:.0f}" if u in s else "" for u in used) + " |")
    by_ch = {}
    for k, m, _ in rs:
        by_ch.setdefault(k[0], []).append(m)
    lines += ["", "Per chapter: " + "; ".join(f"{code} {c}: mean {sum(v) / len(v):.0f}, look first "
                                               f"{sum(1 for f in first if f[0] == c)}" for c, v in sorted(by_ch.items()))]
    return lines


def write_overview(pname, code, chs, lines):
    pd = project_dir(pname)
    f = next((x for x in (os.path.join(pd, code, f"{code}_review_overview.md"), os.path.join(pd, "review_overview.md"))
              if os.path.exists(x)), os.path.join(pd, code, f"{code}_review_overview.md"))
    s = open(f, encoding="utf-8").read() if os.path.exists(f) else f"# Review overview: {code}\n"
    span = f"{chs[0]}" if len(chs) == 1 else f"{chs[0]}–{chs[-1]}"
    block = "\n".join([BEGIN, f"## Look first: {code} {span}", ""] + lines + [END])
    s = (re.sub(re.escape(BEGIN) + ".*?" + re.escape(END), lambda m: block, s, flags=re.S) if BEGIN in s
         else s.rstrip("\n") + "\n\n" + block + "\n")
    open(f, "w", encoding="utf-8").write(s)
    print(f"# written to {os.path.relpath(f, ROOT)}", file=sys.stderr)


def main():
    a = sys.argv[1:]
    if len(a) < 3 or a[0] in ("-h", "--help"):
        raise SystemExit(__doc__)
    pname, code, chs = a[0], a[1], chapters(a[2])
    names = a[a.index("--second") + 1].split(",") if "--second" in a else None
    share = float(a[a.index("--share") + 1]) if "--share" in a else 0.25
    rs, used = rows(pname, code, chs, names)
    if not rs:
        raise SystemExit("nothing to compare")
    lines = table(code, rs, used, share)
    print("\n".join(lines))
    if "--overview" in a:
        write_overview(pname, code, chs, lines)


if __name__ == "__main__":
    main()
