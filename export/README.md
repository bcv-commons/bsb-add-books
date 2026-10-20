# export/: our drafts, public domain

Everything we write here (the drafts, their notes and footnotes, style guides and
review overviews) is dedicated to the public domain under CC0 1.0 Universal, like the
BSB and MSB it builds on: https://creativecommons.org/publicdomain/zero/1.0/

The one exception is `export/CC-NC/`: work derived from non-commercial editions, under their licence
(`export/CC-NC/README.md`). Work derived from other non-free editions never comes here: it goes to `local_output/`
(not in git), returned to the rights holder (`docs/licensing.md`, *Three output paths*).

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
  a clause layout carry that layout's licence and don't go here. The drafts laid out on a layout (the website's
  clause views: BHSA CC BY-NC 4.0, ETCBC credited; MACULA/UHB CC BY-SA 4.0) are not stored either:
  `scripts/build_site.py` derives them at build time from the drafts and their `.align` files. Other data built on
  BHSA (sidecars, indexes) never goes here or anywhere public. Drafts made on the BHSA layout are our own text and go
  here as prose.
- **Word alignments** (`<code>/<code>NNN.align`, next to each OT draft): which draft words render which Hebrew word,
  in the bcv-commons compact-alignments format (numbers only, no text; CC0; `scripts/full_align.py`). Made by script
  (`scripts/bridge_align.py`, profile `a`) or by the drafting agent (profile `b`); `full_align.py export` builds the
  Hugging Face layer `<edition>+draft+bsb-add-books` from them.

One folder per project, by language: `export/<language>/<langID>_BSB/` (ISO 639-3 code, or an
interim dialect id), with `project.yaml` (start from `_template/`) and the
chapters in `<code>/` under it, BSB book codes (`export/dan/dan_BSB/gen/gen020.txt`). The scripts
take the project id `dan/dan_BSB`. Drafts of chapters that a published translation already
covers go to `quarantine/<code>/` there, which is not in git.
