# The website: look at your work, and publish it if you want

The repository builds a static website from your projects: for each language a home page with the status of every
chapter, a reader (prose, verse by verse with notes, and the clause views of OT chapters), the language memory and
the credits. It needs no server and fetches nothing when it is read, so it can be opened from the disk or put on any
static host.

## 1. Look at your work (nothing is published)

```
python3 scripts/build_site.py --preview
```

Then open `build/site/index.html` in a browser (on a Mac `open build/site/index.html`, on Linux `xdg-open …`). The
onboarding wizard does this at its end and opens your first chapter. `--preview` also shows files you have not
committed yet; run it again after each chapter. `build/` is git-ignored.

## 2. What the site shows, and what it never shows

- Only what git tracks in `export/`: drafts, notes, footnotes, `STATUS.md`, the wiki, `CREDITS.md`. Every page carries
  the project's draft statement (`draft_statement` in `project.yaml`): the chapters are drafts until a team publishes
  them (`scripts/status.py`).
- Never the editions' texts, verse packs, alignment links, style reports, `_eval/local/` or `local_output/`
  (`docs/licensing.md`). The build reads only tracked files, and a leak test stops it if a page holds a local path or
  a private address.
- **The clause views** are derived at build time from each draft's `.align` and the clause layouts on your machine,
  which are never published themselves. The view on the BHSA layout (`orig/heb-bhsa/`) is CC BY-NC 4.0, with the ETCBC
  credited and the licence shown on the page: **non-commercial only**. A commercial site builds without it
  (`python3 scripts/setup.py --heb bcv-query`, no `bhsa`): the open view on the bcv-query layout (CC BY-SA 4.0) stays.
  Without any layout the site simply has no clause views.
- A project under `local_output/` (work returned to a rights holder) is never on the site.

## 3. Publish it on Netlify (optional)

Netlify hosts a static site for free (a personal account is enough). `scripts/deploy_site.py` runs the checks
(`scripts/check_project.py` for every project, the edition texts must be on this machine), builds the site from the
committed state and publishes it in one of two ways. Commit your work first: the script refuses uncommitted changes
in `export/` and `scripts/`, so the site always equals a commit.

### Way A: linked to your GitHub repository (updates by `git push`)

Once:

1. `python3 scripts/deploy_site.py`: it builds the site and stages it on a branch `site` (in the folder `.site/`, a
   git worktree; `site` shares no history with `main`). Commit and push it with the two commands it prints:
   ```
   git -C .site commit -m "Site built from main <commit>"
   git -C .site push -u origin site
   ```
2. On https://app.netlify.com: **Add new site → Import an existing project → GitHub**, allow Netlify to read the
   repository (a private one works too), pick it, and set **Branch to deploy: `site`**, **Build command: empty**,
   **Publish directory: `.`** (the branch's `netlify.toml` says the same). Deploy.
3. Optional: **Site configuration → Change site name** for a nicer address (`<name>.netlify.app`), or a domain of your
   own under **Domain management**.

Each update: commit your work, `python3 scripts/deploy_site.py`, then the commit and push it prints. Netlify publishes
every push to `site`.

### Way B: upload from your machine (no `site` branch, no GitHub link)

Once:

1. Install the Netlify CLI (needs Node.js): `npm install -g netlify-cli`.
2. A token: on Netlify, **User settings → Applications → Personal access tokens → New access token**.
3. A site: `netlify sites:create --name <name>` (or **Add new site → Deploy manually** in the web interface); note its
   **Site ID** (in the command's output, or **Site configuration → Site details**).
4. Put both in `.env` in the repository folder (git-ignored), or in the environment:
   ```
   NETLIFY_AUTH_TOKEN=...
   NETLIFY_SITE_ID=...
   ```

Each update: commit your work, then

```
python3 scripts/deploy_site.py --netlify           # the live site
python3 scripts/deploy_site.py --netlify --draft   # a preview address first, the live site unchanged
```

### Which one

Way A keeps every published version in git and lets anyone with push rights update the site; Way B needs no branch
and no link between Netlify and GitHub, and suits one maintainer. Both publish the same files. Other static hosts
(GitHub Pages, Cloudflare Pages, any web server) work as well: publish the `site` branch, or the folder `build/site/`.
