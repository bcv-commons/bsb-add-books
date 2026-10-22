#!/usr/bin/env python3
"""Side effects of a drafting option: the arms of an A/B (projects drafting the same chapters, one option apart),
measured by script on what a change of the prompt or the pack can cost elsewhere in a verse. For any language: no
human translation needed (a chapter the style corpus has can be scored with score.py besides).

Per arm, pooled over its chapters (OT drafts with their .align, scripts/full_align.py):
  no word    the source's content tokens marked as having no target word (!, u, e in the .align): a dropped clause or
             a meaning left out shows here first
  added      draft words added for no source token (+ in the .align)
  length     draft tokens per source content token
  neg -      verses whose original negates more often than the draft (scripts/rough_check.py: negation markers
             learned from the corpus, or a negation the .align links to a word)
  neg +      verses with a negation marker the original lacks
  English?   draft words not in the corpus or the store but in the English
  review     REVIEW lines of scripts/chapter_check.py (names, copies, negations)
  cells      the word-level cell check (scripts/cell_check.py): verbs of the marked cells that carry the pattern
Markers and cells are measured against one project's store (--ref, default the first arm), so that what the arms'
agents added to their own stores doesn't move the yardstick.
Groups pool arms of one kind (rounds of the same option): name=project,project,...

Usage: python3 scripts/compare_arms.py <code> <chapters, e.g. 46-47> <arm> ... [--ref PROJECT]
       an arm: a project (dan/x) or a group (binding=dan/x_r1,dan/x_r2)
"""
import collections, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import langtools as LT  # noqa: E402
import full_align as FA  # noqa: E402
import rough_check as RC  # noqa: E402

KEYS = ("content", "none", "added", "draft", "neg-", "neg+", "eng", "review", "cells", "cells_n", "verses")


def run(*args):
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout + r.stderr


def measure(pname, code, chs, R, markers):
    """the counts of one arm over its chapters"""
    P = LT.Project(pname)
    t = collections.Counter()
    (eng, names), store, sp = RC.english_forms(R), P.store_forms(), P.spellings()
    book = code.upper()
    files = []
    for ch in chs:
        f = os.path.join(P.dir, code, f"{code}{ch:03d}.txt")
        ap = f[:-4] + ".align"
        if not os.path.exists(f):
            raise SystemExit(f"{pname}: {os.path.relpath(f, ROOT)} is missing")
        files.append(f)
        verses = dict(FA.draft_texts(f))
        _, rows = FA.read_chapter(ap) if os.path.exists(ap) else (None, {})
        src, linked = RC.source_negations(code, ch), RC.aligned_negations(f) if os.path.exists(ap) else {}
        for v, text in verses.items():
            t["verses"] += 1
            nc = len(FA.index(book, "keys").get(f"{book} {ch}:{v}", []))
            m, fn, _ = rows.get(v, ("", "", ""))
            dm, df = FA.decisions(m), FA.decisions(fn)
            t["content"] += nc
            t["none"] += len(set(dm["none"]) | set(dm["u"]) | set(dm["e"]))
            t["added"] += len({p for p, _ in dm["plus"] + df["plus"]})
            t["draft"] += len(FA.tokenize(text))
            n_src, n_tgt = src.get(v, 0), max(RC.marker_count(R, text, markers), linked.get(v, 0))
            t["neg-"] += n_src > n_tgt
            t["neg+"] += bool(n_tgt and not n_src)
            t["eng"] += any(w not in store and not sp.get(P.tok.plain(w)) and w.lower() in eng
                            and w.lower() not in names for w in P.tok.tokens(text, exact=True))
        t["review"] += len(re.findall(r"^\s+REVIEW", run("scripts/chapter_check.py", pname, code, str(ch)), re.M))
    out = run("scripts/cell_check.py", R.name, *files)
    m = re.search(r"judged cells: draft (\d+)/(\d+)", out)
    if m:
        t["cells"], t["cells_n"] = int(m[1]), int(m[2])
    return t


def main():
    a = sys.argv[1:]
    if len(a) < 3 or a[0] in ("-h", "--help"):
        raise SystemExit(__doc__)
    ref = a[a.index("--ref") + 1] if "--ref" in a else None
    a = [x for i, x in enumerate(a) if x != "--ref" and (i == 0 or a[i - 1] != "--ref")]
    code, rng, arms = a[0], a[1], a[2:]
    lo, _, hi = rng.partition("-")
    chs = list(range(int(lo), int(hi or lo) + 1))
    groups = []
    for x in arms:
        name, _, ps = x.rpartition("=")
        groups.append((name or ps, ps.split(",")))
    R = LT.Project(ref or groups[0][1][0])
    R.name = ref or groups[0][1][0]
    markers = set(RC.learn_markers(R)[0])
    pct = lambda x, n: f"{x}/{n} ({100 * x / max(n, 1):.0f}%)"
    print(f"{code} {rng}: {len(groups)} arm(s); markers and cells against {R.name}\n")
    print(f"{'arm':28} {'no word':>15} {'added':>7} {'length':>6} {'neg -':>5} {'neg +':>5} {'Engl?':>5} "
          f"{'review':>6} {'cells':>15}")
    for name, ps in groups:
        tot = collections.Counter()
        for p in ps:
            tot.update(measure(p, code, chs, R, markers))
        print(f"{name:28} {pct(tot['none'], tot['content']):>15} {tot['added']:>7} "
              f"{tot['draft'] / max(tot['content'], 1):>6.2f} {tot['neg-']:>5} {tot['neg+']:>5} {tot['eng']:>5} "
              f"{tot['review']:>6} {pct(tot['cells'], tot['cells_n']):>15}")
    print(f"\n({sum(len(ps) for _, ps in groups)} projects, chapters {rng}; counts pooled within an arm: neg -, neg +, "
          "English? and review are verses or lines)")


if __name__ == "__main__":
    main()
