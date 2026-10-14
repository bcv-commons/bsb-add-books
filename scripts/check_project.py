#!/usr/bin/env python3
"""The final check of a project before its files are committed or published: every check in one run.

  - drafts: verse and format checks (check_draft.py);
  - the language store, with the quotation rules (language_profile.py check --project), if the project has one;
  - the wiki: links, generated blocks, quotations (wiki.py lint), if the project has one;
  - quotations in every publishable file, and CREDITS.md (quotes.py);
  - draft status: no published chapter changed since it was published (status.py check).

The agents are expected to comply as they write (the chapter prompt carries the rules, and they run the store
validator, the wiki lint and quotes.py on their own files); this is the double check afterwards.

Usage: python3 scripts/check_project.py <project> [<project> ...]     exit 1 if any check fails
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(label, cmd):
    r = subprocess.run([sys.executable] + cmd, cwd=ROOT, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    summary = next((l for l in out if "problem" in l and not l.lstrip().startswith(("note", "problem"))), out[-1] if out else "")
    print(f"{'ok  ' if r.returncode == 0 else 'FAIL'} {label}: {summary.strip()}")
    if r.returncode:
        for l in out[:-1][:20]:
            print(f"       {l}")
    return r.returncode == 0


def main():
    projects = sys.argv[1:]
    if not projects:
        raise SystemExit(__doc__)
    ok = True
    for p in projects:
        d = os.path.join(ROOT, "export", p)
        print(f"== {p}")
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import project as P
        for e, how in P.missing_texts(P.project(p)):
            print(f"warn text: edition {e} is not here, so quotations and store evidence from it are not checked; get it: {how}")
        ok &= run("drafts", ["scripts/check_draft.py", p])
        if os.path.isdir(os.path.join(d, "profile")):
            ok &= run("store", ["scripts/language_profile.py", "check", os.path.join(d, "profile"), "--project", p])
        if os.path.isdir(os.path.join(d, "wiki")):
            ok &= run("wiki", ["scripts/wiki.py", "lint", p])
        ok &= run("quotations", ["scripts/quotes.py", p])
        ok &= run("status", ["scripts/status.py", p, "check"])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
