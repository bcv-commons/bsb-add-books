#!/usr/bin/env python3
"""Prepare a new version of the website on the `site` branch; the maintainer commits and pushes it, and Netlify
(linked to GitHub, production branch `site`, no build command) publishes it as it is.

    python3 scripts/deploy_site.py            check, build, stage on `site` (in the worktree .site/)
    python3 scripts/deploy_site.py --no-check  skip check_project.py (not for a real deploy)

Steps:
  1. refuse if the files the site shows have uncommitted changes (export/, scripts/), so the site equals a commit;
  2. the clause layouts are here (orig/heb-bhsa, orig/heb-bcv-query: read for the clause views, never published), and
     scripts/check_project.py passes for every project, in full: the edition texts are on this machine;
  3. scripts/build_site.py into build/site/;
  4. the worktree .site/ on branch `site` (created the first time: an orphan branch with no history shared with
     main, or the existing local or remote `site`); its files are replaced by the new build and staged.
It stops there and prints the commit and push commands: commits and pushes are the maintainer's. Nothing is pushed.
"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WT = os.path.join(ROOT, ".site")
BRANCH = "site"


def git(*a, cwd=ROOT, check=True):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout.strip()


def projects():
    out = git("ls-files", "export")
    return sorted({os.path.dirname(f)[len("export/"):] for f in out.splitlines()
                   if f.endswith("/project.yaml") and not f.startswith("export/_")})


def worktree():
    if os.path.exists(os.path.join(WT, ".git")):
        return
    if git("branch", "--list", BRANCH):
        git("worktree", "add", WT, BRANCH)
    elif git("ls-remote", "--heads", "origin", BRANCH, check=False):
        git("fetch", "origin", BRANCH)
        git("worktree", "add", "-b", BRANCH, WT, f"origin/{BRANCH}")
    else:
        git("worktree", "add", "--orphan", "-b", BRANCH, WT)
    print(f"worktree .site/ on branch {BRANCH}")


def main():
    a = sys.argv[1:]
    dirty = git("status", "--porcelain", "--", "export", "scripts")
    if dirty:
        raise SystemExit("uncommitted changes in what the site shows; commit them first, so the site equals a commit:\n" + dirty)
    for lay in ("orig/heb-bhsa", "orig/heb-bcv-query"):
        if not os.path.isdir(os.path.join(ROOT, lay)):
            raise SystemExit(f"{lay} is missing: the clause views are built from it (python3 scripts/setup.py --heb bhsa,bcv-query)")
    if "--no-check" not in a:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "check_project.py"), *projects()], cwd=ROOT)
        if r.returncode:
            raise SystemExit("check_project.py failed: no deploy")
    out = os.path.join(ROOT, "build", "site")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_site.py"), "--out", os.path.relpath(out, ROOT)], cwd=ROOT)
    if r.returncode:
        raise SystemExit("build_site.py failed")
    worktree()
    for f in os.listdir(WT):
        if f == ".git":
            continue
        p = os.path.join(WT, f)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    for f in os.listdir(out):
        s, d = os.path.join(out, f), os.path.join(WT, f)
        shutil.copytree(s, d) if os.path.isdir(s) else shutil.copy2(s, d)
    git("add", "-A", cwd=WT)
    built = open(os.path.join(out, "BUILT_FROM")).read().strip()
    changes = git("status", "--short", cwd=WT).splitlines()
    print(f"\n.site/ (branch {BRANCH}): {len(changes)} files changed, built from {built}")
    if not changes:
        print("nothing changed since the last version on the branch")
        return
    print(f"Staged; to publish (Netlify deploys the push):\n"
          f"  git -C .site commit -m \"Site built from main {built}\"\n"
          f"  git -C .site push -u origin {BRANCH}")


if __name__ == "__main__":
    main()
