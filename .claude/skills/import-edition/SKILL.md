---
name: import-edition
description: Import an existing Bible translation into import/<licence>/<language>/<edition>/ as style corpus or as an edition to continue or revise, with its textual basis, licence and quarantine. Use when the user provides an existing translation or asks to add one.
---

# Import an existing edition

Fields are explained in `docs/configuration.md`; the template has comments.

1. **Ask first:**
   - name, language code, and its role: `style` (corpus only), `continue` (new drafts continue
     it) or `revise`;
   - where it comes from and under what licence. This picks the folder (`import/README.md`):
     `CC0/` (public domain or CC0), `CC-BY/` (CC BY), `CC-BY-SA/` (CC BY-SA), both with their
     `attribution`, or `non-free/` (any other licence, open or not, for now; its texts git-ignored, `edition.yaml` in git, so keep it free of private details). If
     unclear, use `non-free/` and write `private use only`. Don't put an edition in an open
     folder without checking its licence statement, and
     ask the user before adding one that isn't public domain to git;
   - which Greek text its NT follows (`nt_basis`: `critical`, `majority`, `tr`). If unsure,
     look at a few test verses (e.g. Mt 17:21, Acts 8:37, 1 Jn 5:7) and propose a value;
   - whether any of its books are to be translated independently (quarantine).
   - if the user names a language but no file: `python3 scripts/fetch_edition.py --find <iso>`
     lists the editions of bcv-commons/bibles (helloAO, openbible; DBT and PKF are listed but
     need a key or a decoder) and eBible, with their licences. Propose one; CrossWire and
     single GitHub sources are checked by hand.
2. **Create it:** copy `import/_template/` to `import/<licence>/<language>/<edition>/`, where
   `<language>` is the ISO 639-3 code (`dan`), or for a dialect an interim id agreed with the
   user (`ch-de-be`), (the edition id
   must not exist in another licence folder), put the files in `text/`
   (or the folder named in `text_dir`), and fill in `edition.yaml`. Name the files with the
   BSB book codes where possible (`books.tsv`), so prompts can point to the right book.
   - **To fetch it** instead of copying files: add a `fetch:` block (see the template) and run
     `python3 scripts/fetch_edition.py <edition>`. It checks the source's licence against the
     folder, writes `text/` (git-ignored) and `fetch.lock.json` (in git). If the licence can't be
     read from the source, check it yourself and pass `--licence-checked`. If a later fetch
     reports that the source changed, show the user before passing `--update`.
   - **A text with one source of its own** (e.g. a GitHub repository): write a
     `sync_from_upstream.py` in the edition folder, on the model of
     `import/CC0/dan/den-frie-bibel/` or `import/CC0/dan/dan-1871-1907/`: the files git-ignored, copied
     from the commit pinned in the edition (`--latest` or `--commit` moves the pin), `--check` to only
     report, and the commit and coverage or checksums recorded in the edition's `README.md`; set
     `get_text` to the command.
   - **A text that can be fetched from a URL is never in git**, also in `CC0/` and `CC-BY/`: the edition's
     `.gitignore` keeps `text/` out. Only a text copied in by hand, with no source to fetch it from, is
     kept in git (open folders only).
   - For a new language, `python3 scripts/onboard.py` does the fetching (and creates the project).
3. **Quarantine:** a non-free edition's books can be drafted only in quarantine
   (`python3 scripts/quarantine.py <project> <code>`, which moves the files and lists the book;
   `make_prompt.py` enforces it). Keep comparison reports that quote it out of the agents' reach
   (`do_not_open:` in the project).
4. **Check:** `python3 scripts/project.py <project>` for a project that uses it shows the
   edition in `style_from` and the inherited `nt_basis` and quarantine.

Editions in `import/CC0/`, `import/CC-BY/` and `import/CC-BY-SA/` are published with the repository, so their
licence must allow it; `import/non-free/` stays local. Don't commit; the user commits.
