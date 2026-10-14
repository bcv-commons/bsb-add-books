# export/: our drafts, public domain

Everything we write here (the drafts, their notes and footnotes, style guides and
review overviews) is dedicated to the public domain under CC0 1.0 Universal, like the
BSB and MSB it builds on: https://creativecommons.org/publicdomain/zero/1.0/

To keep that possible:

- **Only our own work goes here.** No text copied from an edition in `import/`. A
  project may continue an edition with new books, and use editions as a style corpus,
  but it can revise only a CC0 edition (`scripts/project.py` checks this). What we learn
  from an edition (the wiki, the language store, lexicons, statistics) is ours and CC0, for
  non-free editions too; short quotations in it are credited and stay their owner's
  (`docs/licensing.md`). Generated files that print corpus verses (verse packs, alignment
  links, style reports, `_eval/local/`) are git-ignored.
- **Drafts are marked as drafts.** `status.yaml` in a project records each chapter's status
  (`draft` until published, with the date and statement); `STATUS.md` shows it
  (`scripts/status.py`, `docs/workflow.md`).
- **No derived data with another licence.** Clause sidecars and other data built from
  a clause layout carry that layout's licence: from BHSA (`orig/heb-bhsa/`, the drafting
  layout, CC BY-NC) they never go here or anywhere public; from bcv-query (CC BY-SA 4.0) or MACULA
  (CC BY 4.0) they keep that licence and its attribution, so they belong elsewhere or are labelled
  as such. Drafts made on the BHSA layout are our own text and go here as prose.

One folder per project, by language: `export/<language>/<langID>_BSB/` (ISO 639-3 code, or an
interim dialect id such as `ch-de-be`), with `project.yaml` (start from `_template/`) and the
chapters in `<code>/` under it, BSB book codes (`export/dan/dan_BSB/gen/gen020.txt`). The scripts
take the project id `dan/dan_BSB`. Drafts of chapters that a published translation already
covers go to `quarantine/<code>/` there, which is not in git.
