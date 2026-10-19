#!/usr/bin/env python3
"""Publish the website (docs/website.md). Two ways, both after the same checks and build:

    python3 scripts/deploy_site.py             check, build, stage on the `site` branch (in the worktree .site/); the
                                               maintainer commits and pushes it, and Netlify (linked to the GitHub repo,
                                               branch `site`, no build command) publishes it as it is
    python3 scripts/deploy_site.py --netlify   check, build and upload build/site/ with the Netlify CLI (`netlify`
                                               installed; NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID in the environment or
                                               .env): no `site` branch, no GitHub link; --draft gives a preview address
                                               instead of the live site
    --no-check                                 skip check_project.py (not for a real deploy)

Steps:
  1. refuse if the files the site shows have uncommitted changes (export/, scripts/), so the site equals a commit;
  2. scripts/check_project.py passes for every project, in full: the edition texts are on this machine; the clause
     layouts (orig/heb-bhsa, orig/heb-bcv-query: read for the clause views, never published) are used where they are
     here, and a missing one only leaves its view out (a commercial site has no BHSA view: setup.py --heb bcv-query);
  3. scripts/build_site.py into build/site/;
  4. either the worktree .site/ on branch `site` (created the first time: an orphan branch with no history shared with
     main, or the existing local or remote `site`), its files replaced by the new build and staged; it stops there and
     prints the commit and push commands, which are the maintainer's: nothing is pushed;
     or (--netlify) `netlify deploy --dir build/site --prod`, the upload the maintainer asked for by the option.
"""
import os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import localenv  # noqa: E402

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
            print(f"note: {lay} is not here, so the site has no clause view on it (python3 scripts/setup.py --heb bhsa,bcv-query)")
    netlify, token, site = "--netlify" in a, "", ""
    if netlify:
        token, site = localenv.key("NETLIFY_AUTH_TOKEN") or "", localenv.key("NETLIFY_SITE_ID") or ""
        if not shutil.which("netlify"):
            raise SystemExit("the Netlify CLI is not installed: npm install -g netlify-cli (docs/website.md)")
        if not token or not site:
            raise SystemExit("set NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID in the environment or in .env (docs/website.md)")
    if "--no-check" not in a and projects():
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "check_project.py"), *projects()], cwd=ROOT)
        if r.returncode:
            raise SystemExit("check_project.py failed: no deploy")
    out = os.path.join(ROOT, "build", "site")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_site.py"), "--out", os.path.relpath(out, ROOT)], cwd=ROOT)
    if r.returncode:
        raise SystemExit("build_site.py failed")
    built = open(os.path.join(out, "BUILT_FROM")).read().strip()
    if netlify:
        cmd = ["netlify", "deploy", "--dir", out, "--site", site, "--message", f"built from {built}"]
        if "--draft" not in a:
            cmd.append("--prod")
        r = subprocess.run(cmd, cwd=ROOT, env={**os.environ, "NETLIFY_AUTH_TOKEN": token})
        raise SystemExit(r.returncode and "netlify deploy failed")
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
