#!/usr/bin/env python3
"""Draft status of a project's chapters: every chapter is a draft until a team publishes it.

export/<project>/status.yaml records the chapters that are not plain drafts:

  chapters:
    rut001: {status: in-review, by: the team, date: 2026-11-02, note: first reading done}
    rut002: {status: published, by: the team, date: 2026-12-01, statement: "...", sha256: "..."}

  - draft       (default, not listed) written with AI agents from the Hebrew/Greek; not reviewed;
  - in-review   a team is working on it;
  - published   the team has approved it: the date, who, the publishing statement and the file's SHA-256
                at that moment are recorded; a later change to the file shows as "changed since published".

The statements come from project.yaml (`draft_statement`, `publish_statement`, with {by} and {date}),
else the defaults below. `STATUS.md` in the project is rewritten on every change: it is what a reader of the
repository sees, and what a site shows next to the text.

Usage: python3 scripts/status.py <project>                          summary; rewrites STATUS.md
       python3 scripts/status.py <project> set <code>[:ch[-ch]] draft|in-review [--by NAME] [--note TEXT]
       python3 scripts/status.py <project> publish <code>[:ch[-ch]] --by NAME [--statement TEXT] [--date YYYY-MM-DD]
       python3 scripts/status.py <project> check                    exit 1 if a published chapter changed
"""
import datetime, glob, hashlib, os, re, sys
import yaml

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
from project import project, edition, editions_with_book, book_files, missing_text, project_dir  # noqa: E402
from books import BY_CODE, order  # noqa: E402

DRAFT_STATEMENT = ("Draft. Translated with AI agents directly from the Hebrew and Greek, with the BSB as the only "
                   "assisting translation; not yet reviewed or approved by a language team. Not for use as "
                   "published Scripture. Public domain (CC0).")
PUBLISH_STATEMENT = ("Published on {date} by {by}, after review by the language team. Drafted with AI agents directly "
                     "from the Hebrew and Greek and revised by the team. Public domain (CC0).")
STATUSES = ("draft", "in-review", "published")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def chapter_files(pdir, book_order=None):
    """{'gen001': path} of the project's drafted chapters (quarantine/ and _eval/ not included), in the project's
    reading order (books.ORDERS)."""
    out = {}
    for f in glob.glob(os.path.join(pdir, "*", "*.txt")):
        b = os.path.basename(f)
        if re.fullmatch(r"[0-9a-z]{3}\d{3}\.txt", b) and os.path.basename(os.path.dirname(f)) == b[:3]:
            out[b[:6]] = f
    rank = {c: i for i, c in enumerate(order(book_order))}
    return dict(sorted(out.items(), key=lambda kv: (rank[kv[0][:3]], kv[0])))


def load(pdir):
    f = os.path.join(pdir, "status.yaml")
    d = yaml.safe_load(open(f, encoding="utf-8")) if os.path.exists(f) else None
    return (d or {}).get("chapters") or {}


def save(pdir, chapters):
    f = os.path.join(pdir, "status.yaml")
    head = ("# Draft status per chapter (scripts/status.py; docs/workflow.md, Draft status).\n"
            "# A chapter not listed here is a draft. Change it with scripts/status.py, not by hand.\n")
    body = yaml.safe_dump({"chapters": dict(sorted(chapters.items()))}, allow_unicode=True, sort_keys=False, width=110)
    open(f, "w", encoding="utf-8").write(head + body)


def statements(p):
    return p.get("draft_statement") or DRAFT_STATEMENT, p.get("publish_statement") or PUBLISH_STATEMENT


def state(pdir, p):
    """[(chapter, path, record)] for every drafted chapter; record has status and, if published, 'changed'."""
    chapters = load(pdir)
    out = []
    for ch, f in chapter_files(pdir, p.get("book_order")).items():
        r = dict(chapters.get(ch) or {"status": "draft"})
        if r["status"] == "published":
            r["changed"] = r.get("sha256") != sha(f)
        out.append((ch, f, r))
    return out


def ranges(nums):
    out, start, prev = [], None, None
    for n in nums + [None]:
        if start is None:
            start = prev = n
        elif n is not None and n == prev + 1:
            prev = n
        else:
            out.append(f"{start}" if start == prev else f"{start}–{prev}")
            start = prev = n
    return ", ".join(out)


def write_status_md(pname, pdir, p):
    draft_st, _ = statements(p)
    rows = state(pdir, p)
    by_book = {}
    for ch, f, r in rows:
        by_book.setdefault(ch[:3], []).append((ch, r))
    n = {s: sum(1 for _, _, r in rows if r["status"] == s) for s in STATUSES}
    L = [f"# Status: {p.get('language_name') or pname}", "",
         f"{len(rows)} chapters: **{n['draft']} draft**, {n['in-review']} in review, {n['published']} published.", "",
         "> " + re.sub(r"^([^\s.]+\.)", r"**\1**", draft_st), "",
         "| Book | Chapters | Status | Existing edition |", "|---|---|---|---|"]
    files = chapter_files(pdir, p.get("book_order"))
    Q = None
    # the figures measured where the edition's text was present: kept when it is not here (a fresh clone has no
    # non-free texts), so that STATUS.md doesn't change with the machine it is written on
    prev = {}
    sf = os.path.join(pdir, "STATUS.md")
    if os.path.exists(sf):
        for l in open(sf, encoding="utf-8").read().splitlines():
            m = re.match(r"\| .*\(`(\w{3})`\) \| .* \| (.*) \|$", l)
            if m:
                prev[m[1]] = m[2]
    for code, chs in by_book.items():
        ex = []
        ours = {int(c[3:]) for c, _ in chs}
        for e, cls in editions_with_book(p, code):
            ed = edition(e)
            fs = book_files(ed, code)
            theirs = {int(os.path.basename(f)[3:6]) for f in fs if re.fullmatch(r"[0-9a-z]{3}\d{3}\.txt", os.path.basename(f))}
            whole = not fs or any(re.fullmatch(r"[0-9a-z]{3}\.txt", os.path.basename(f)) for f in fs)
            both = ours if whole else ours & theirs
            if missing_text(e):           # any licence: a fresh clone has no fetched or synced texts
                m = re.search(rf"{re.escape(e)} \(.*?(?=; [\w.-]+ \((?:non-free|public-domain|attributable|share-alike)\)|$)",
                              prev.get(code, ""))  # this edition's whole entry (it contains '; ' itself)
                old = m[0] if m else None
                ex.append(old or (f"{e} ({cls}): not shown; ours drafted independently (its text is not on this machine, "
                                  "so the overlap is not measured here)" if cls == "non-free" else
                                  f"{e} ({cls}): its text is not on this machine"))
            elif not both:
                ex.append(f"{e} ({cls}) has chapters {ranges(sorted(theirs))}: ours continue it")
            elif cls == "non-free":
                if Q is None:
                    import quotes
                    Q = quotes.Quotes(pname)
                o = quotes.overlap(Q, [files[c] for c, _ in chs if int(c[3:]) in both], code)
                ex.append(f"{e} ({cls}): not shown; ours drafted independently, {o['share']:.0%} shared "
                          f"(independent ≈ 20%)" + ("" if o["independent"] else " **check: more than independent drafts share**"))
            else:
                ex.append(f"{e} ({cls}): shown alongside" + ("" if both == ours else f" (chapters {ranges(sorted(both))})"))
        name = BY_CODE[code][1] if len(BY_CODE[code]) > 1 else code
        parts = []
        for st in STATUSES:
            cs = [c for c, r in chs if r["status"] == st]
            if cs:
                parts.append(f"{st}: {ranges([int(c[3:]) for c in cs])}")
        L.append(f"| {name} (`{code}`) | {len(chs)} | {'; '.join(parts)} | {'; '.join(ex) or '—'} |")
    tests = {}
    for f in glob.glob(os.path.join(pdir, "_eval", "**", "*.txt"), recursive=True):
        b = os.path.basename(f)
        if re.fullmatch(r"[0-9a-z]{3}\d{3}\.txt", b) and "/local/" not in f:
            tests.setdefault(os.path.relpath(os.path.dirname(f), pdir), []).append(b[:6])
    if tests:
        L += ["", "## Test drafts (not part of the drafts)", "",
              "Written to test the method on books a language team has translated; the team's translation stands.", ""]
        L += [f"- `{d}/`: {', '.join(sorted(cs))}" for d, cs in sorted(tests.items())]
    pub = [(ch, r) for ch, _, r in rows if r["status"] == "published"]
    if pub:
        L += ["", "## Published", ""]
        for ch, r in pub:
            L.append(f"- **{ch}** ({r.get('date')}, {r.get('by')}): {r.get('statement')}"
                     + (" **Changed since published.**" if r.get("changed") else ""))
    rev = [(ch, r) for ch, _, r in rows if r["status"] == "in-review"]
    if rev:
        L += ["", "## In review", ""] + [f"- **{ch}**: {r.get('by', '')}, since {r.get('date', '')}"
                                         + (f". {r['note']}" if r.get("note") else "") for ch, r in rev]
    open(os.path.join(pdir, "STATUS.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    return n


def select(pdir, spec):
    m = re.fullmatch(r"([0-9a-z]{3})(?::(\d+)(?:-(\d+))?)?", spec)
    if not m:
        raise SystemExit(f"not a book or chapter range: {spec} (e.g. rut, rut:2, rut:1-4)")
    code, a, b = m[1], m[2], m[3]
    chs = [c for c in chapter_files(pdir) if c[:3] == code]
    if a:
        lo, hi = int(a), int(b or a)
        chs = [c for c in chs if lo <= int(c[3:]) <= hi]
    if not chs:
        raise SystemExit(f"no drafted chapters for {spec} in {os.path.relpath(pdir, ROOT)}")
    return chs


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    pname = a[0]
    p = project(pname)
    pdir = project_dir(pname)
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    today = datetime.date.today().isoformat()
    cmd = a[1] if len(a) > 1 else "show"
    chapters = load(pdir)
    files = chapter_files(pdir, p.get("book_order"))
    if cmd == "set":
        st = a[3]
        if st not in ("draft", "in-review"):
            raise SystemExit("set takes draft or in-review; use publish to publish")
        for ch in select(pdir, a[2]):
            if st == "draft":
                chapters.pop(ch, None)
            else:
                chapters[ch] = {"status": st, "by": opt("--by", ""), "date": opt("--date", today)} | (
                    {"note": opt("--note")} if opt("--note") else {})
        save(pdir, chapters)
    elif cmd == "publish":
        by = opt("--by")
        if not by:
            raise SystemExit("publish needs --by NAME (the team or person who approved it)")
        date = opt("--date", today)
        _, pub_st = statements(p)
        statement = opt("--statement") or pub_st.format(by=by, date=date)
        for ch in select(pdir, a[2]):
            chapters[ch] = {"status": "published", "by": by, "date": date, "statement": statement, "sha256": sha(files[ch])}
        save(pdir, chapters)
    elif cmd == "check":
        bad = [ch for ch, _, r in state(pdir, p) if r.get("changed")]
        print("\n".join(f"{ch}: changed since it was published; publish again or set it back to in-review" for ch in bad)
              or f"{pname}: no published chapter changed")
        write_status_md(pname, pdir, p)
        sys.exit(1 if bad else 0)
    elif cmd != "show":
        raise SystemExit(__doc__)
    n = write_status_md(pname, pdir, p)
    print(f"{pname}: {n['draft']} draft, {n['in-review']} in review, {n['published']} published "
          f"({os.path.relpath(os.path.join(pdir, 'STATUS.md'), ROOT)})")


if __name__ == "__main__":
    main()
