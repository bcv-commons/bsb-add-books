#!/usr/bin/env python3
"""Sync this edition's two OSIS files with Den Frie Bibel's repository, github.com/EzerIT/DFB.

    python3 import/CC0/dan/dan-1871-1907/sync_from_upstream.py            # the pinned commit (README.md)
    python3 import/CC0/dan/dan-1871-1907/sync_from_upstream.py --latest   # update to the latest commit
    python3 import/CC0/dan/dan-1871-1907/sync_from_upstream.py --check    # only report what would change
    python3 import/CC0/dan/dan-1871-1907/sync_from_upstream.py --commit <sha>

It copies tekst/DA_OT1871.OSIS.xml and tekst/DA_NT1907.OSIS.xml from the commit into osis/
(git-ignored), and writes the commit and the files' SHA-256 into README.md. Nothing is committed.

Needs git. The sparse, shallow clone of tekst/ in download/editions/EzerIT-DFB/ is shared with
../den-frie-bibel/sync_from_upstream.py.
"""
import datetime, hashlib, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
REPO = "https://github.com/EzerIT/DFB.git"
SPARSE = ["/tekst/", "/sfm/", "/oversigt.inc.php"]
CACHE = os.path.join(ROOT, "download", "editions", "EzerIT-DFB")
OSIS = os.path.join(HERE, "osis")
FILES = ["DA_OT1871.OSIS.xml", "DA_NT1907.OSIS.xml"]


def git(*args, capture=False):
    r = subprocess.run(["git", *args], cwd=CACHE, check=True, text=True,
                       stdout=subprocess.PIPE if capture else subprocess.DEVNULL, stderr=subprocess.PIPE)
    return r.stdout.strip() if capture else None


def checkout(commit):
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


def describe(path):
    data = open(path, "rb").read()
    text = data.decode("utf-8")
    books = len(re.findall(r'<div osisID="[^"]+" type="book"', text))
    verses = len(re.findall(r"<verse osisID=", text))
    return hashlib.sha256(data).hexdigest(), f"({len(data):,} bytes; {books} books, {verses:,} verses)"


def main():
    argv = sys.argv[1:]
    check = "--check" in argv
    m = re.search(r"- Commit: `([0-9a-f]{40})`", open(os.path.join(HERE, "README.md"), encoding="utf-8").read())
    pin = m[1] if m else None
    commit = argv[argv.index("--commit") + 1] if "--commit" in argv else None if "--latest" in argv else pin
    sha, date, subject = checkout(commit)
    print(f"EzerIT/DFB {sha[:10]} ({date}, {subject})")
    lines = []
    for name in FILES:
        src, dst = os.path.join(CACHE, "tekst", name), os.path.join(OSIS, name)
        digest, info = describe(src)
        old = describe(dst)[0] if os.path.exists(dst) else None
        state = "new" if old is None else "unchanged" if old == digest else "changed"
        print(f"  {name}: {state} {info}")
        lines.append(f"{digest}  {name}  {info}")
        if not check and state != "unchanged":
            os.makedirs(OSIS, exist_ok=True)
            shutil.copyfile(src, dst)
    if check:
        return
    if sha == pin:
        return print("  osis/ at the pinned commit; README.md unchanged.")
    readme = os.path.join(HERE, "README.md")
    s = open(readme, encoding="utf-8").read()
    s = re.sub(r"- Commit: .*", f'- Commit: `{sha}` ({date}, "{subject}")', s)
    s = re.sub(r"- Synced: .*", f"- Synced: {datetime.date.today().isoformat()}", s)
    s = re.sub(r"(Expected SHA-256:\n\n```\n).*?(\n```)", lambda m: m.group(1) + "\n".join(lines) + m.group(2), s, flags=re.S)
    open(readme, "w", encoding="utf-8").write(s)
    print("  osis/ and README.md updated (osis/ is git-ignored; review README.md with git diff).")


if __name__ == "__main__":
    main()
