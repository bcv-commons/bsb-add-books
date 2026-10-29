---
name: import-edition
description: Import an existing Bible translation into import/<licence>/<language>/<edition>/ as style corpus or as an edition to continue or revise, with its textual basis, licence and quarantine. Use when the user provides an existing translation or asks to add one.
---

# Import an existing edition

Folders and rules: `import/README.md`; fields: `docs/configuration.md` and the template's comments. For a new
language, `python3 scripts/onboard.py` imports and fetches the editions it finds (and creates the project).

1. **Ask first:**
   - name, language code, and its `role`: `style` (corpus only), `continue` (new drafts continue it) or `revise`;
   - source and licence, which pick the folder: `CC0/` (public domain, CC0), `CC-BY/`, `CC-BY-SA/` (with
     `attribution`), `CC-ND/` (any CC licence with ND), `CC-NC/` (NC without ND), else `non-free/` (also when unclear,
     with `licence: private use only`). Only `edition.yaml` of the last three is in git: keep it free of private
     details. Check the licence statement before using an open folder; every quoted edition gets a `credit` line;
   - which Greek text its NT follows (`nt_basis`: `critical`, `majority`, `tr`); if unsure, look at test verses
     (Mt 17:21, Acts 8:37, 1 Jn 5:7) and propose a value;
   - whether any of its books are to be translated independently (quarantine);
   - a language but no file: `python3 scripts/fetch_edition.py --find <iso>` lists the editions of
     bcv-commons/bibles (helloAO, openbible; DBT with the user's `DBT_API_KEY`) and eBible, with licences. Propose
     one; CrossWire and single GitHub sources are checked by hand.
2. **Create it:** copy `import/_template/` to `import/<licence>/<language>/<edition>/` (`<language>`: the ISO 639-3
   code, `dan`, or for a dialect an interim id agreed with the user; the edition id must be unique across the
   folders), put the files in `text/` (or `text_dir`) with BSB book codes as names where possible (`books.tsv`), and
   fill in `edition.yaml`.
   - **Fetched:** a `fetch:` block (see the template), then `python3 scripts/fetch_edition.py <edition>`. It checks
     the licence against the folder and writes `text/` (git-ignored) and `fetch.lock.json` (in git). If the licence
     can't be read from the source, check it yourself and pass `--licence-checked`; if a later fetch reports a
     changed source, show the user before passing `--update`.
   - **Synced from its own source** (e.g. a GitHub repository): a `sync_from_upstream.py` in the edition folder,
     modelled on `import/CC0/dan/den-frie-bibel/` (pinned commit, files git-ignored); set `get_text` to the command.
   - A text that can be fetched or synced is never in git; only one copied in by hand is (open folders only).
3. **Quarantine:** a book that a non-free edition (also `CC-ND/`, `CC-NC/`) has is drafted only in quarantine
   (`python3 scripts/quarantine.py <project> <code>`; `make_prompt.py` enforces it). Keep reports that quote the
   edition out of the agents' reach (`do_not_open:` in the project).
4. **The team's SFM conventions** (an edition with their Paratext files in `source/`): `python3 scripts/sfm_profile.py
   <edition>` prints what their books show (Unicode form, line endings, versification with its evidence, headings,
   paragraph markers, the divine name, `\id` line, file names) and what is uncertain (which book is the newest);
   show it to the user, then `--write` puts it into `edition.yaml` (`sfm:`). On a later delivery it reports the
   changes before anything is overwritten.
5. **Check:** `python3 scripts/project.py <project>` for a project that uses it shows the edition in `style_from`
   and the inherited `nt_basis` and quarantine.

Ask the user before adding an edition that isn't public domain to git. Don't commit; the user commits.
