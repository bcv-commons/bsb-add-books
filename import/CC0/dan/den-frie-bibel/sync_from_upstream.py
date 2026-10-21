#!/usr/bin/env python3
"""Sync this edition with Den Frie Bibel's own repository, github.com/EzerIT/DFB.

    python3 import/CC0/dan/den-frie-bibel/sync_from_upstream.py            # the pinned commit (edition.yaml)
    python3 import/CC0/dan/den-frie-bibel/sync_from_upstream.py --latest   # update to the latest commit
    python3 import/CC0/dan/den-frie-bibel/sync_from_upstream.py --check    # only report what would change
    python3 import/CC0/dan/den-frie-bibel/sync_from_upstream.py --commit <sha>

Without options it fetches the commit pinned in edition.yaml, so a fresh clone gets the same corpus
the project was built with, and leaves edition.yaml and README.md as they are. --latest (or --commit)
moves the pin.

It copies, from the commit:
- tekst/*.txt into text/, renaming Den Frie Bibel's Danish book stems to the BSB codes
  (1mos001.txt -> gen001.txt, matt001.txt -> mat001.txt, sl001.txt -> psa001.txt …);
- sfm/ (the books Den Frie Bibel writes directly in USFM: one .SFM per book, with every chapter,
  and a .cre credits file per finished chapter) into sfm/, under the upstream names;
- the chapters of sfm/ that Den Frie Bibel publishes, converted into text/ (gen001.txt …): parsed
  with usfmtc as bcv-commons/bibles does (scripts/usfm_usj.py; pip install usfmtc), rendered like
  the BSB files (scripts/convert_usj.py), with the .cre credits as header lines.
Content is unchanged; files no longer upstream are removed. It then writes the commit, the book
coverage and, for sfm/, which chapters have text and which Den Frie Bibel publishes (its
oversigt.inc.php) into edition.yaml and README.md, and prints what was added, changed and
removed. Nothing is committed; review the change with git diff.

Not copied: the 1871/1907 OSIS files, tekst/orig/
(the Hebrew/Aramaic text, not public domain) and translators.txt (e-mail addresses).

Needs git (a sparse, shallow clone of tekst/ is kept in download/editions/EzerIT-DFB/).
"""
import datetime, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from books import BOOKS, heb_chapters  # noqa: E402
from convert_usj import bracket_to_next, chapter_text, split_chapters  # noqa: E402
from usfm_usj import usfm_to_usj  # noqa: E402

REPO = "https://github.com/EzerIT/DFB.git"
SPARSE = ["/tekst/", "/sfm/", "/oversigt.inc.php"]
CACHE = os.path.join(ROOT, "download", "editions", "EzerIT-DFB")
TEXT = os.path.join(HERE, "text")
QUAR = os.path.join(HERE, "quarantine")      # quarantined books (scripts/quarantine.py), git-ignored
SFM = os.path.join(HERE, "sfm")
OT = {"gen": "1mos", "exo": "2mos", "lev": "3mos", "num": "4mos", "deu": "5mos", "jos": "jos", "jdg": "dom", "rut": "ruth",
      "1sa": "1sam", "2sa": "2sam", "1ki": "1kong", "2ki": "2kong", "1ch": "1krøn", "2ch": "2krøn", "ezr": "ezra", "neh": "neh",
      "est": "est", "job": "job", "psa": "sl", "pro": "ordsp", "ecc": "præd", "sng": "højs", "isa": "es", "jer": "jer",
      "lam": "klages", "ezk": "ez", "dan": "dan", "hos": "hos", "jol": "joel", "amo": "am", "oba": "obad", "jon": "jon",
      "mic": "mika", "nam": "nah", "hab": "hab", "zep": "sef", "hag": "hagg", "zec": "zak", "mal": "mal"}
NT = dict(zip("mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev".split(),
              "matt mark luk joh apg rom 1kor 2kor gal ef fil kol 1thess 2thess 1tim 2tim tit filem hebr jak 1pet 2pet 1joh "
              "2joh 3joh jud åb".split()))
STEM_TO_CODE = {v: k for k, v in {**OT, **NT}.items()}
NAMES = {"gen": "Gen", "jos": "Josh", "1sa": "1 Sam", "1ki": "1 Kgs", "1ch": "1 Chr", "2ch": "2 Chr", "ezr": "Ezra", "neh": "Neh",
         "est": "Esth", "sng": "Song", "dan": "Dan", "hos": "Hos", "mal": "Mal", "lev": "Lev", "deu": "Deut", "2sa": "2 Sam",
         "2ki": "2 Kgs", "pro": "Prov", "ecc": "Eccl", "ezk": "Ezek", "jol": "Joel", "amo": "Amos", "mic": "Mic", "luk": "Luke",
         "act": "Acts", "num": "Num", "jdg": "Judg", "rut": "Ruth", "job": "Job", "psa": "Ps", "isa": "Isa", "jer": "Jer",
         "lam": "Lam", "oba": "Obad", "jon": "Jonah", "nam": "Nah", "hab": "Hab", "zep": "Zeph", "hag": "Hag", "zec": "Zech",
         "exo": "Exod"}


def git(*args, cwd=CACHE, capture=False):
    r = subprocess.run(["git", *args], cwd=cwd, check=True, text=True,
                       stdout=subprocess.PIPE if capture else subprocess.DEVNULL, stderr=subprocess.PIPE)
    return r.stdout.strip() if capture else None


def checkout(commit):
    """A sparse, shallow clone of tekst/ at the commit (default: upstream HEAD); returns (sha, date, subject)."""
    if not os.path.isdir(os.path.join(CACHE, ".git")):
        os.makedirs(CACHE, exist_ok=True)
        git("init", "-q")
        git("remote", "add", "origin", REPO)
        git("config", "core.sparseCheckout", "true")
    if not commit:
        commit = git("ls-remote", REPO, "HEAD", capture=True).split()[0]
    git("sparse-checkout", "set", "--no-cone", *SPARSE)     # the same set in both sync scripts (shared clone)
    git("fetch", "-q", "--depth", "1", "origin", commit)
    git("checkout", "-q", "--force", "FETCH_HEAD")
    sha = git("rev-parse", "HEAD", capture=True)
    date, subject = git("log", "-1", "--format=%cs%x09%s", capture=True).split("\t", 1)
    return sha, date, subject


def upstream_files():
    """text/ file name -> content (bytes): tekst/ files as they are (an opening [ before a verse number moved into
    that verse, convert_usj.bracket_to_next), plus the published sfm/ chapters converted."""
    src = os.path.join(CACHE, "tekst")
    out, unknown = {}, []
    for f in sorted(os.listdir(src)):
        m = re.fullmatch(r"(.+?)(\d{3})\.txt", f)
        if m and m[1] in STEM_TO_CODE:
            raw = open(os.path.join(src, f), "rb").read()
            out[f"{STEM_TO_CODE[m[1]]}{m[2]}.txt"] = bracket_to_next(raw.decode("utf-8")).encode("utf-8")
        elif f.endswith(".txt") and f != "translators.txt":
            unknown.append(f)
    for name, data in sfm_chapters().items():
        if name in out:
            print(f"  WARNING: {name} is in both tekst/ and sfm/; kept the tekst/ file")
        else:
            out[name] = data
    return out, unknown


def oversigt():
    return open(os.path.join(CACHE, "oversigt.inc.php"), encoding="utf-8").read()


def published(stem, over):
    """The chapters Den Frie Bibel publishes for a book ($chap in oversigt.inc.php)."""
    m = re.search(r"\$chap\['" + re.escape(stem) + r"'\]\s*=\s*(\[[^\]]*\]|range\((\d+),\s*(\d+)\))", over)
    if not m:
        return []
    return list(range(int(m[2]), int(m[3]) + 1)) if m[2] else [int(x) for x in re.findall(r"\d+", m[1])]


def sfm_chapters():
    """The published chapters of each sfm/ book as text/ files: usfmtc via usfm_usj.py (as bcv-commons/bibles),
    rendered by convert_usj.py, with the chapter's .cre credits as header lines and Den Frie Bibel's book title.
    Its own \\zei markers are left out."""
    over, out = oversigt(), {}
    for f in sorted(os.listdir(os.path.join(CACHE, "sfm"))):
        if not f.upper().endswith(".SFM"):
            continue
        usfm = open(os.path.join(CACHE, "sfm", f), encoding="utf-8").read()
        book = re.search(r"\\id\s+(\S+)", usfm).group(1)
        code = book.lower()
        stem = {**OT, **NT}.get(code)
        if not stem:
            print(f"  WARNING: sfm/{f}: unknown book {book}, not converted")
            continue
        m = re.search(r"\$title\['" + re.escape(stem) + r"'\]\s*=\s*'([^']+)'", over)
        title = m[1] if m else book
        pub = set(published(stem, over))
        content = usfm_to_usj(re.sub(r"\\zei \d+\\zei\*\s?", "", usfm))["content"]
        for number, items in split_chapters(content):
            if number not in pub:
                continue
            cre = os.path.join(CACHE, "sfm", f"{f[:-4]}{number:03d}.cre")
            head = [l.strip() for l in open(cre, encoding="utf-8")] if os.path.exists(cre) else []
            text = chapter_text("", "", book, title, number, items).split("\n")
            text = [l for l in head if l] + text[2:]      # the .cre lines replace convert_usj's two header lines
            text = "\n".join(text).replace(f"==={title}, chapter {number}===", f"==={title}, kapitel {number}===")
            out[f"{code}{number:03d}.txt"] = text.encode("utf-8")
    return out


def sfm_report():
    """Per .SFM book: the chapters with text, and the chapters Den Frie Bibel publishes (oversigt.inc.php)."""
    over, out = oversigt(), []
    for f in sorted(os.listdir(os.path.join(CACHE, "sfm"))):
        if not f.upper().endswith(".SFM"):
            continue
        t = open(os.path.join(CACHE, "sfm", f), encoding="utf-8").read()
        book = re.search(r"\\id\s+(\S+)", t).group(1)
        parts = re.split(r"\\c (\d+)", t)
        text = [int(parts[i]) for i in range(1, len(parts), 2)
                if len(re.findall(r"[A-Za-zÆØÅæøå]{3,}", re.sub(r"\\\S+", " ", parts[i + 1]))) > 20]
        code = book.lower()
        out.append((f, NAMES.get(code, book), len(parts) // 2, text, published({**OT, **NT}.get(code, ""), over)))
    return out


def spans(nums):
    out, start = [], None
    for i, n in enumerate(nums):
        if start is None:
            start = n
        if i + 1 == len(nums) or nums[i + 1] != n + 1:
            out.append(f"{start}" if start == n else f"{start}–{n}")
            start = None
    return ", ".join(out) or "none"


def coverage(names):
    counts = {}
    for n in names:
        counts[n[:3]] = counts.get(n[:3], 0) + 1
    order = [b[0] for b in BOOKS]
    present = [c for c in order if c in counts]
    missing = [NAMES.get(c, c) for c in order if c not in counts]
    partial = [f"{NAMES.get(c, c)} {counts[c]}/{heb_chapters(c)}" for c in present if counts[c] < heb_chapters(c)]
    return len(names), present, missing, partial


def wrap(prefix, items, sep, width=100, indent="# "):
    lines, line = [], prefix
    for i, item in enumerate(items):
        piece = item + (sep if i < len(items) - 1 else ".")
        if len(line) + len(piece) + 1 > width:
            lines.append(line.rstrip())
            line = indent + piece
        else:
            line += ("" if line.endswith(("[", " ")) else " ") + piece
    lines.append(line.rstrip())
    return lines


def update_yaml(sha, date, names):
    path = os.path.join(HERE, "edition.yaml")
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"[0-9a-f]{40}( \(\d{4}-\d{2}-\d{2}\))?", f"{sha} ({date})", s)
    n, present, missing, partial = coverage(names)
    block = [f"# Present in part: {n} chapters of {len(present)} books (at the commit above)."]
    block += wrap("# Missing books:", missing, ",")
    block += wrap("# Partial:", partial, ",")
    block += ["# From sfm/ (USFM, converted into text/; only the chapters Den Frie Bibel publishes, see README.md):"]
    block += wrap("#", [f"{name} {spans(pub)} (text in {spans(text)})" for _, name, _, text, pub in sfm_report()], ";")
    block += wrap("books: [", present, ",", indent="        ")
    block[-1] = block[-1].rstrip(".") + "]"
    s = re.sub(r"# Present in part:.*?\nbooks: \[[^\]]*\]", "\n".join(block), s, flags=re.S)
    open(path, "w", encoding="utf-8").write(s)


def update_readme(sha, date, subject, n, sfm):
    path = os.path.join(HERE, "README.md")
    s = open(path, encoding="utf-8").read()
    rows = ["| file | book | chapters | with text | published by Den Frie Bibel |", "|---|---|---|---|---|"]
    rows += [f"| `{f}` | {name} | {nch} | {spans(text)} | {spans(pub)} |" for f, name, nch, text, pub in sfm]
    s = re.sub(r"(<!-- sfm -->\n)(?:.*?\n)?(<!-- /sfm -->)", lambda m: m.group(1) + "\n".join(rows) + "\n" + m.group(2), s, flags=re.S)
    s = re.sub(r"- Commit: .*", f'- Commit: `{sha}` ({date}, "{subject}")', s)
    s = re.sub(r"- Synced: .*", f"- Synced: {date_today()}, {n} chapter files", s)
    open(path, "w", encoding="utf-8").write(s)


def pinned():
    m = re.search(r"\b([0-9a-f]{40})\b", open(os.path.join(HERE, "edition.yaml"), encoding="utf-8").read())
    return m[1] if m else None


def date_today():
    return datetime.date.today().isoformat()


def main():
    argv = sys.argv[1:]
    check = "--check" in argv
    commit = argv[argv.index("--commit") + 1] if "--commit" in argv else None if "--latest" in argv else pinned()
    sha, date, subject = checkout(commit)
    keep_pin = sha == pinned()
    print(f"EzerIT/DFB {sha[:10]} ({date}, {subject})")
    up, unknown = upstream_files()
    # quarantined books: listed in edition.yaml, or already in quarantine/; their files stay out of text/
    yml = open(os.path.join(HERE, "edition.yaml"), encoding="utf-8").read()
    m = re.search(r"^quarantine:\s*\[([^\]]*)\]", yml, re.M)
    qbooks = {c.strip() for c in (m[1].split(",") if m else []) if c.strip()}
    qbooks |= {f[:3] for f in os.listdir(QUAR)} if os.path.isdir(QUAR) else set()
    home = lambda f: QUAR if f[:3] in qbooks else TEXT
    have = {f for d in (TEXT, QUAR) if os.path.isdir(d) for f in os.listdir(d) if f.endswith(".txt")}
    read = lambda p: open(p, "rb").read()
    where = lambda f: os.path.join(QUAR if os.path.exists(os.path.join(QUAR, f)) else TEXT, f)
    added = sorted(set(up) - have)
    removed = sorted(have - set(up))
    changed = sorted(f for f in set(up) & have if up[f] != read(where(f)))
    if qbooks:
        print(f"  quarantined (kept in quarantine/, not text/): {' '.join(sorted(qbooks))}")
    print(f"  {len(up)} chapter files upstream: {len(added)} new, {len(changed)} changed, {len(removed)} no longer upstream")
    for label, names in (("new", added), ("changed", changed), ("removed", removed)):
        if names:
            print(f"  {label}: " + " ".join(n[:-4] for n in names))
    if unknown:
        print("  WARNING: upstream files with an unknown book stem, not copied: " + " ".join(unknown))
    up_sfm = {f: os.path.join(CACHE, "sfm", f) for f in os.listdir(os.path.join(CACHE, "sfm"))}
    have_sfm = set(os.listdir(SFM)) if os.path.isdir(SFM) else set()
    s_added, s_removed = sorted(set(up_sfm) - have_sfm), sorted(have_sfm - set(up_sfm))
    s_changed = sorted(f for f in set(up_sfm) & have_sfm if read(up_sfm[f]) != read(os.path.join(SFM, f)))
    print(f"  {len(up_sfm)} sfm/ files upstream: {len(s_added)} new, {len(s_changed)} changed, {len(s_removed)} no longer upstream")
    sfm = sfm_report()
    for f, name, nch, text, pub in sfm:
        print(f"    {f}: {name}, {nch} chapters, text in {spans(text)}, published {spans(pub)}")
    if check:
        return
    os.makedirs(SFM, exist_ok=True)
    for f in s_added + s_changed:
        shutil.copyfile(up_sfm[f], os.path.join(SFM, f))
    for f in s_removed:
        os.remove(os.path.join(SFM, f))
    os.makedirs(TEXT, exist_ok=True)
    for f in added + changed:
        os.makedirs(home(f), exist_ok=True)
        if os.path.exists(where(f)) and os.path.dirname(where(f)) != home(f):
            os.remove(where(f))
        open(os.path.join(home(f), f), "wb").write(up[f])
    for f in removed:
        os.remove(where(f))
    if keep_pin:
        return print("  text/ and sfm/ at the pinned commit; edition.yaml and README.md unchanged.")
    update_yaml(sha, date, list(up))
    update_readme(sha, date, subject, len(up), sfm)
    print("  text/, sfm/, edition.yaml and README.md updated to the new commit; review with git diff, then commit.")


if __name__ == "__main__":
    main()
