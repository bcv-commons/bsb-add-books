# bsb-add-books: notes for Claude

Draft Bible translations chapter by chapter, directly from the Hebrew and Greek, with the
BSB (or the MSB for a majority-text NT) as the only assisting translation and existing
translations as style models. `README.md` gives the layout, `docs/workflow.md` the way of
working; this file adds the rules that hold for any task here.

## Start here

1. **Sources first.** `reference/BSB/`, `reference/MSB/`, `orig/` and `download/` are not in git. If they are
   missing, run `python3 scripts/setup.py` (about a minute). For the OT add the Hebrew clause
   layouts, built side by side in `orig/heb-<layout>/`: `--heb bhsa,bcv-query`. `bhsa` (ETCBC
   BHSA 2021, needs `text-fabric`) is the drafting layout, copied to `orig/heb/`; `bcv-query`
   (CC BY-SA 4.0) is for published clause structure; `macula` is an open, slow alternative. The clause packages need
   the prepared structures `orig/heb.sqlite` and `orig/grc.sqlite`: `setup.py` fetches them (`--only src`, bcv-query's
   published cache v1, pinned SHA-256; seconds) and adds the local layers (BHSA layout rows, our BGB/RP mapping).
   `python3 scripts/src.py build` builds them from MACULA instead (about 50 minutes; with the UBS columns).
2. **Requirements:** Python 3 with PyYAML (`pip install pyyaml`) for the project scripts, and
   `usfmtc` (`pip install usfmtc`) for USFM sources (`scripts/usfm_usj.py`).
   `scripts/macula_to_tf.py` also needs `text-fabric`.
   The language toolkit's aligner (`scripts/align.py`) uses eflomal if installed (else a built-in model).
3. **New language?** `docs/onboarding.md`: the mode (familiarity × licence) decides how the tools work;
   `scripts/onboard.py` is the step-by-step setup (editions from the bcv-commons/bibles catalogue, project, memory).
4. **Skills** for the main tasks (in `.claude/skills/`):
   - `new-project`: set up `export/<project>/` and its style guide;
   - `import-edition`: add an existing translation to `import/`;
   - `draft-chapter`: draft chapters, one fresh agent per chapter, and check them.
   - `learn-language`: prepare a language the model doesn't know (aligner, concordance, store, wiki, packs, tests).

## Decisions (binding)

- **File names:** BSB book codes everywhere (`gen001.txt`, `jhn003.txt`); `books.tsv` lists
  them. OT files and drafts keep the **Hebrew verse numbering**; `orig/vrs/` maps it to the
  BSB's.
- **Greek NT:** `orig/grc` is the Berean Greek Bible (the BSB's Greek), `orig/grc-rp` is
  Robinson-Pierpont 2018 (the MSB's). An edition sets `nt_basis` (`critical | majority |
  tr`) in `edition.yaml`; a project inherits it through `based_on`.
- **Clause lines are guidance, not a law:** a draft may keep a natural word order and render
  two Hebrew clauses in one line. Merging lines is a display choice; the data only records
  which words render which Hebrew clause (`docs/proposals/clause-overlay/`).
- **No source texts in git.** Sources come from `scripts/setup.py` at pinned versions.
- **Imported editions are filed by licence:** `import/CC0/`, `import/CC-BY/`, `import/CC-BY-SA/` (in git) and
  `import/non-free/` (texts git-ignored, only `edition.yaml` and README in git; the default when the licence is unclear), then by language:
  the ISO 639-3 code (`import/CC0/dan/`), or for a dialect an interim id (`ch-de-be`; the
  scheme is still open). Edition ids are unique across the folders. Details: `import/README.md`.
- **`export/` is public domain (CC0),** like the BSB/MSB: only our own work goes there. A
  project can revise only a CC0 edition; derived data with another licence (BHSA- or
  MACULA-based clause sidecars) doesn't go into `export/` (`export/README.md`).
- **What we derive is free, what we quote is credited** (`docs/licensing.md`): drafts, notes, wiki
  prose, the language store and statistics learned from any edition, non-free ones included, are
  CC0 (CC BY-SA only where built on share-alike data). Quotes from an edition are short (a phrase, at
  most a verse per point; at most 10% of a book's verses per file, 2% of the edition in all),
  unchanged, from its published text, with the reference and the edition's `credit` line; they are
  not under our CC0. Bulk text stays local: the editions' texts, verse packs, alignment links, style
  reports, `_eval/local/`. The limits apply to non-free editions; public-domain and CC BY / BY-SA ones
  are credited (`CREDITS.md`). **Agents comply as they write:** chapter prompts carry the rule
  (`quotes.py --rule` for other agents), the store validator and `wiki.py lint` enforce it, and
  `scripts/check_project.py` is the double check, not the place where text is fixed afterwards
  (`.githooks/pre-commit` runs it; `git config core.hooksPath .githooks` once per clone).
- **Draft status:** every chapter is a `draft` until a team publishes it (`scripts/status.py`);
  drafts may be online, always marked as drafts (`docs/workflow.md`, *Draft status*).
- **Licences:** code MIT (`LICENSE`), docs and templates CC0 (`LICENSE-docs`), drafts CC0;
  each source text and imported edition keeps its own (`docs/sources.md`, `import/README.md`).
- **Commits:** the user commits. Don't commit unless asked.
- **Roles across bcv-commons:** bcv-query derives the Hebrew clause structure from MACULA;
  lexeme-aligner derives clause sidecars for editions from its alignments; this repo drafts
  along the clause lines and exports exact sidecars.

## Pitfalls

- **Two clause layouts, two jobs.** `orig/heb/` (the drafting layout, a copy of `orig/heb-bhsa/`)
  is BHSA data (ETCBC), CC BY-NC 4.0: its lines are BHSA clause atoms, the number after the colon
  BHSA's `tab`. Agents consult it as a reference work, as a translator would; the drafts are our
  own text and stay free (CC0). Never publish the BHSA files themselves, not in git, not on the site branch. Our
  drafts laid out on the BHSA layout may be shown, as **CC BY-NC 4.0** with the ETCBC credited and the licence
  shown prominently (the website's BHSA view; decided by the user, 2026-10-14): BY-NC allows adaptations,
  non-commercially. Those clause lines are never stored: `scripts/build_site.py` derives them at build time from
  each draft and its `.align` on the local layout files (`scripts/clause_lines.py`), so nothing laid out on BHSA is
  in git. Everything else built on BHSA (sidecars, indexes, the levels as data) stays unpublished. Clause
  structure for open reuse is built on the bcv-query layout (`orig/heb-bcv-query/`, CC BY-SA 4.0; the site's
  MACULA/UHB view); `scripts/relayout.py` moves a clause-line draft between layouts. The BHSA copy itself may be used only non-commercially: a commercial user of
  this repo drafts on `bcv-query` (`--drafting bcv-query`) or asks the ETCBC.
  **Its text is never copied either:** the Hebrew quoted in notes, store and wiki is the WLC (MACULA Hebrew in
  `orig/heb.sqlite`, the clause packages; public domain); `scripts/notes_hebrew.py` fills the notes' verses from it and adds
  the credit line, and `quotes.py` reports accented Hebrew that isn't the WLC word for word (2026-10-16).
- **Don't use BSB text files from other converters:** older ones dropped verse markers and
  footnotes inside `\wj` (words of Jesus). Use the files `setup.py` builds.
- **Quarantine is required for non-free text.** A book that a non-free style edition has
  (`import/non-free/`) is drafted only in quarantine: `python3 scripts/quarantine.py <project> <code>`
  moves its files out of the edition's `text/` and lists the book; `make_prompt.py` refuses otherwise.
  A chapter the edition doesn't have needs none (Kuni Genesis 31–50 beside the edition's 1–30; `--chapter N`
  checks it); without the edition's text here, the whole-book rule holds.
  A public-domain edition never needs it; an attributable one (CC BY, CC BY-SA) only with
  `quarantine_attributable: true`. Draft with fresh agents, not forks (`docs/workflow.md`).
- **The shoresh API** (`https://shoresh.qombi.com`) rejects Python's default User-Agent (403);
  the first call per chapter can take over a minute.
- **Hebrew chapter counts** differ from the BSB's in Joel (4 / 3) and Malachi (3 / 4); use
  `books.heb_chapters()` for `orig/heb`.

## Commands

```
python3 scripts/setup.py [--heb bhsa,bcv-query,macula] [--drafting LAYOUT] [--only bsb,msb,bgb,rp,vrs,src,editions] [--force]
python3 scripts/onboard.py [--answers F] [--yes] [--dry-run] # wizard for a new language: editions, project, memory
python3 scripts/fetch_edition.py --find <iso>       # editions of a language (bcv-commons/bibles, eBible)
python3 scripts/fetch_edition.py <edition> | --all  # fetch an edition by its recipe into import/
python3 scripts/project.py <project> [code]          # resolved sources for a project
python3 scripts/modes.py <project>                   # the project's mode (familiarity x licence) and what it switches on
python3 scripts/probe_language.py <project> run | write|read|tell [--score F] # how well the model knows the language (sets familiarity)
python3 scripts/priors.py write|check <project>     # what the model believes about the language (profile/priors.yaml), tested against the corpus
python3 scripts/usage.py <project> add <code><nnn> --tokens N | summary # tokens per chapter, by familiarity
python3 scripts/memory_prompt.py <project>           # prompt for an agent that builds the store and wiki, by mode
python3 scripts/make_prompt.py <project> <code> <ch> [--end-align] # chapter prompt for a fresh agent (OT: tagged drafting)
python3 scripts/package.py <project> <code> <ch>   # clause packages for an OT chapter (orig/heb.sqlite, the project's .align, store, NT bridge)
python3 scripts/check_draft.py <project> [code]      # verse/format checks of drafts
python3 scripts/notes_hebrew.py <project> <code> <ch> | --all | show <code> <ch>:<v> # the notes' Hebrew/Greek from the WLC/BGB, with the credit line
python3 scripts/quarantine.py <project> <code> [--release] # quarantine a book (required for non-free editions)
python3 scripts/status.py <project> [set|publish|check] # draft status per chapter; writes STATUS.md
python3 scripts/quotes.py <project> [--credits|--rule] # quotations within docs/licensing.md; CREDITS.md; the agents' rule
python3 scripts/check_project.py <project>           # the final double check: drafts, store, wiki, quotations, status
python3 scripts/align.py <project> [--sides eng,hbo,grc] # lexicons of the style corpus (eflomal or IBM2)
python3 scripts/concord.py <project> <cmd> <arg>     # agents' search tool: eng, tgt, like, lex, hlex, forms, gloss, store
python3 scripts/verse_pack.py <project> <code> <ch>  # precompiled per-verse pack (store hits, lexicon, similar verses)
python3 scripts/score.py <project> <draft>           # chrF against a held-out human translation, with floors
python3 scripts/style.py <project> <draft> [--brief]  # style against the human translations: flags, watch items, models
python3 scripts/language_profile.py check <dir>      # validate a language profile (docs/proposals/language-profile/)
python3 scripts/wiki.py sync|lint <project>          # a project's language wiki: pages + generated store blocks
python3 scripts/wiki.py view <project>               # one offline HTML file to read the wiki and search the store
python3 scripts/build_site.py                        # the website from tracked files (build/site/)
python3 scripts/deploy_site.py                       # check, build, stage it on the `site` branch (.site/); the user commits and pushes
python3 scripts/wrap_draft.py <file>                 # wrap a draft at ~100 chars
python3 scripts/vrs.py <code> <ch>                   # Hebrew -> BSB verse mapping of a chapter
python3 scripts/clause_sidecar.py <draft> <orig/heb file> <BOOK> --out DIR --index-dir DIR
python3 scripts/fetch_heb_macula.py <code>[:ch[-ch]] # MACULA clause layout for one book or chapters
python3 scripts/build_heb_bcvquery.py <release> [--law] [--out DIR] # bcv-query clause layout
python3 scripts/build_heb_bhsa.py [--tf DIR] [--out DIR] [code ...] # BHSA 2021 clause layout (needs text-fabric)
python3 scripts/relayout.py <draft> --from <layout> --to <layout> # move a clause-line draft between layouts
python3 scripts/clause_lines.py check <project> [<code> <ch>] | show <project> <code> <ch> # the site's clause lines, derived from .align
python3 scripts/bridge_align.py <project> <code> <ch> | --all # word alignment (.align) by script, no model
python3 scripts/full_align.py listing|prompt <project> <code> <ch> | check <project> [<code> [<ch>]] | export <project> # .align (bcv-commons format): the agent's sheet and prompt, checks, the HF layer
python3 scripts/full_align.py tag|split <project> <code> <ch> # the tagged interim format (word^n) <-> prose + .align
python3 scripts/src.py build [code ...] | layouts [--layout L] | map | speakers | show <code> <c>:<v> | bridge <lexeme> | export-open DIR # orig/heb.sqlite, orig/grc.sqlite (MACULA + numbering + BSB tables; local)
python3 scripts/lang.py build|derive|report <project> | hbo <project> <lexeme> | grc <project> <strong> # the project's language DB: NT occurrences of any Hebrew word via the LXX; derived grammar statistics
python3 scripts/macula_to_tf.py <delivery dir>       # draft Text-Fabric dataset (needs text-fabric)
```

Sources, versions and licences: `docs/sources.md`. Config fields: `docs/configuration.md`.
Proposals for bcv-commons: `docs/proposals/`.
