# The website

`scripts/build_site.py` builds a static site from your projects: per language a home page with every chapter's
status, a reader (prose, verse by verse with notes, the clause views of chapters with a word alignment), the language memory and the
credits. It needs no server and fetches nothing, so it opens from disk or any static host.

## Look at your work

```
python3 scripts/build_site.py --preview
```

Open `build/site/index.html` in a browser. `--preview` includes files not yet committed; `build/` is git-ignored.
The onboarding wizard runs this at its end.

## What the site shows

- Only what git tracks in `export/<lang>/<id>/`: drafts, notes, footnotes, `STATUS.md`, the wiki, `CREDITS.md`. Every
  page carries the draft statement (`draft_statement`) and a status strip at the top that stays in view: an
  unreviewed draft (amber), in review, or published by the team (green, with the date), naming the team
  (`team_name`, else "the <language> language team"). A page that isn't published says Draft in its tab title and asks
  search engines not to index it. The language memory opens every page and the store with a notice that it is the
  agents' working analysis, not checked by the team, and tags each entry "team" or "not reviewed". `site: false` in `project.yaml` leaves a project out.
- Never the editions' texts, verse packs, alignment links, style reports, `_eval/local/`, `local_output/` or
  `export/CC-NC/` (`docs/licensing.md`). A leak test stops the build if a page holds a local path or private address.
- **Clause views** are derived at build time from each draft's `.align` and the local clause layouts, which are never
  published. The BHSA view (`orig/heb-bhsa/`) is CC BY-NC 4.0, ETCBC credited, licence on the page: **non-commercial
  only**. A commercial site leaves it out (`python3 scripts/setup.py --heb bcv-query`, no `bhsa`) and keeps the
  bcv-query view (CC BY-SA 4.0). NT chapters have one clause view, the Greek NT clause layout (`orig/grc-gntl/`, CC BY
  4.0, bcv-commons/greek-nt-clause-layout from MACULA Greek; `setup.py --only gntl`, which runs
  `scripts/build_grc_gntl.py` and needs pyarrow), on the same button as the bcv-query view. Without a layout there are
  no clause views.

## Publish

`python3 scripts/deploy_site.py` refuses uncommitted changes in `export/` and `scripts/` (the site equals a commit),
runs `scripts/check_project.py` for every project (the edition texts must be on this machine), then builds. Two ways
to publish on Netlify (a free personal account is enough):

**A. Linked to GitHub (updates by `git push`).**

1. `python3 scripts/deploy_site.py` stages the site on the branch `site` (worktree `.site/`, no history shared with
   `main`) and prints the commit and push commands:
   ```
   git -C .site commit -m "Site built from main <commit>"
   git -C .site push -u origin site
   ```
2. Once, on https://app.netlify.com: **Add new site → Import an existing project → GitHub**, pick the repository,
   **Branch to deploy: `site`**, **Build command:** empty, **Publish directory: `.`**.

Netlify publishes every push to `site`.

**B. Upload from your machine (no branch, no GitHub link).** Once: install the Netlify CLI (`npm install -g
netlify-cli`), create a token (**User settings → Applications → Personal access tokens**) and a site (`netlify
sites:create --name <name>`), and put both in `.env` (git-ignored) or the environment:

```
NETLIFY_AUTH_TOKEN=...
NETLIFY_SITE_ID=...
```

Then each time:

```
python3 scripts/deploy_site.py --netlify           # the live site
python3 scripts/deploy_site.py --netlify --draft   # a preview address, live site unchanged
```

A keeps every version in git and suits several maintainers; B suits one. Any other static host works too: publish
the `site` branch or `build/site/`.
