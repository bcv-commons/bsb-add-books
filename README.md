# bsb-add-books

Draft new Bible translations chapter by chapter, **directly from the Hebrew and Greek**. The **BSB** (or the
**MSB** for a majority-text NT) is the only assisting translation. Existing translations in the target language
serve as **style** models. `docs/workflow.md` describes the way of working.

## Start here: a new language

```
git clone https://github.com/bcv-commons/bsb-add-books.git && cd bsb-add-books
pip install pyyaml usfmtc
python3 scripts/onboard.py
```

The wizard sets up a language project step by step, from the language and its existing translations to the
tools that fit it. The full guide: [`docs/onboarding.md`](docs/onboarding.md).

**What you need:** Python 3, and [Claude Code](https://claude.com/claude-code) or an Anthropic API key. Keys go in
the git-ignored `.env` in the repository folder (or the environment):

- `ANTHROPIC_API_KEY=…` to run the probes through the API;
- `DBT_API_KEY=…` for languages only on the Digital Bible Platform (free at https://4.dbt.io).

**Your work as a website:** `python3 scripts/build_site.py --preview`, then open `build/site/index.html`. To put it
online: [`docs/website.md`](docs/website.md).

**Two demo projects** show a project after some work:

- `export/dan/dan_BSB/`: Danish, a language the model knows well, continuing Den Frie Bibel (CC0);
- `export/jam/jam_BSB/`: Jamaican Creole, partly known; its style edition is non-free.

Their editions' texts are not in git. Get them with `python3 import/CC0/dan/den-frie-bibel/sync_from_upstream.py`
(Danish) and `python3 scripts/fetch_edition.py jambswn-et` (Jamaican; needs `DBT_API_KEY`). Delete the project
folders and their editions when you no longer want them. Two more sample editions, NTs without a project, stand for
a language the model doesn't know: Bodo Parja (CC BY, Odia script) and Zinza (CC BY-SA). See
[`import/README.md`](import/README.md), *Sample editions*.

## Layout

```
reference/      the assisting translations                                             *
  BSB/          Berean Standard Bible, whole Bible           gen001.txt … rev022.txt
  MSB/          Majority Standard Bible, NT only             mat001.txt … rev022.txt
orig/                                                                                  *
  heb/          Hebrew/Aramaic OT (Hebrew verse numbering)   gen001.txt …
  grc/          Berean Greek Bible (BGB), the BSB's Greek    mat001.txt … (+ _notes.txt)
  grc-rp/       Robinson-Pierpont 2018, the MSB's Greek      mat001.txt … (+ _notes.txt)
  vrs/          Hebrew -> BSB verse numbering maps
import/         existing translations, by licence (CC0/, CC-BY/, CC-BY-SA/, non-free/, ...)
  <language>/<edition>/   edition.yaml + text/ (the text is fetched, not kept in git)
export/         our drafts, public domain (CC0)
  <language>/<lang>_BSB/  one project: project.yaml, status.yaml + STATUS.md, CREDITS.md
    <code>/     <code>NNN.txt, <code>NNN_notes.md, <code>NNN_footnotes.txt, style guide
    _eval/      test drafts and reports; _eval/local/ is not in git
books.tsv       book codes, names, chapter counts
docs/           onboarding, workflow, configuration, sources, licensing, formats, prompt templates
scripts/        conversion, prompts, checks
.claude/skills/ Claude Code skills
download/       raw source files                                                       *
```

`*` Not in git: `scripts/setup.py` downloads the sources at pinned versions and builds these folders. The
`_notes.txt` files hold each Greek text's own notes (the BGB's footnotes; Robinson-Pierpont's differences from
Nestle-Aland). All files use the **BSB book codes** (`gen`, `1ki`, `jhn`, …) plus a three-digit chapter number.

Formats: the language store in [`docs/language-store.md`](docs/language-store.md), clause sidecars in
[`docs/clause-sidecar.md`](docs/clause-sidecar.md), configuration fields in
[`docs/configuration.md`](docs/configuration.md).

## Working on a project

Requirements: Python 3 with PyYAML and `usfmtc`; numpy and scipy for the style check (`scripts/style.py`); eflomal,
if installed, for better alignment lexicons (`scripts/align.py`; see `docs/onboarding.md`, *External tools*).

In [Claude Code](https://claude.com/claude-code), `CLAUDE.md` gives the rules and four skills guide the main tasks:
`import-edition`, `new-project`, `learn-language` (a language the model doesn't know) and `draft-chapter`.

1. **Sources** (about a minute): `python3 scripts/setup.py`. For the OT add the Hebrew clause layouts:
   `--heb bhsa,bcv-query`. BHSA (the default drafting layout) needs `text-fabric` and is for non-commercial use only.
   For an open setup use `--heb bcv-query --drafting bcv-query`.
2. **Editions:** `python3 scripts/setup.py --only editions` fetches every edition with a `fetch:` recipe;
   `python3 scripts/fetch_edition.py <edition>` fetches one. `edition.yaml` says where any other text comes from.
3. **Check a project:** `python3 scripts/modes.py <project>` (its mode) and `python3 scripts/check_project.py
   <project>` (drafts, store, wiki, quotations, status).
4. **Draft a book:** `python3 scripts/make_prompt.py <project> <code> --book` prints the prompt for one book agent.
   It drafts the chapters one after another and checks each with `scripts/chapter_check.py`. The `draft-chapter`
   skill runs this.

Once per clone, before your first commit: `git config core.hooksPath .githooks` (runs the double check).

## Licence

- **Code** (`scripts/`): MIT, see `LICENSE`.
- **Documentation and templates:** CC0, see `LICENSE-docs`.
- **Our drafts** (`export/`): public domain under CC0, like the BSB and MSB.
- **Imported editions** (`import/`): their own licences, by folder (`import/README.md`).
- **Source texts:** their own licences, below.

What we learn from an edition (wiki, store, lexicons, statistics) is ours, CC0, for every edition. Quotations from
it are short and credited, and its text stays local (`docs/licensing.md`). Every chapter is a draft until a team
publishes it (`scripts/status.py`).

## Sources

| Folder | Text | Licence |
|---|---|---|
| `reference/BSB/` | Berean Standard Bible (bsb2usfm v5.16) | public domain (CC0) |
| `reference/MSB/` | Majority Standard Bible, NT (bsb2usfm v5.16) | public domain (CC0) |
| `orig/grc/` | Berean Greek Bible | public domain (CC0) |
| `orig/grc-rp/` | Robinson-Pierpont Byzantine Textform 2018 | public domain |
| `orig/vrs/` | Hebrew → English verse map (bcv-commons/bibles, from STEPBible TVTMS) | CC BY 4.0 |
| `orig/heb-bhsa/` | ETCBC BHSA 2021 clause atoms | **CC BY-NC 4.0** |
| `orig/heb-bcv-query/` | bcv-query Hebrew clause layout v0.37 (MACULA Hebrew + UHB) | CC BY-SA 4.0 |
| `orig/heb/` | the drafting layout: a copy of one of the two (BHSA by default) | as its source |

BHSA is the drafting layout, consulted like a reference work; its files are never published. bcv-query is for
every published clause structure, and the drafting layout for commercial users. `--drafting LAYOUT` picks the copy
in `orig/heb/`; `scripts/relayout.py` moves a draft between layouts. Versions and rebuilding: `docs/sources.md`.
