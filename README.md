# bsb-add-books

Draft new Bible translations chapter by chapter, **directly from the Hebrew and
Greek**, with the **BSB** (or, for majority-text projects, the **MSB**) as the
only assisting translation, and with existing translations in the target
language as **style** models.

`docs/workflow.md` describes the way of working, which comes from earlier drafting
projects (Bern German and Danish) done in the same way.

## Layout

```
reference/      the assisting translations
  BSB/          Berean Standard Bible, whole Bible           gen001.txt … rev022.txt   *
  MSB/          Majority Standard Bible, NT only             mat001.txt … rev022.txt   *
orig/                                                                                  *
  heb/          Hebrew/Aramaic OT (Hebrew verse numbering)   gen001.txt …
  grc/          Berean Greek Bible (BGB), the BSB's Greek    mat001.txt … (+ _notes.txt)
  grc-rp/       Robinson-Pierpont 2018, the MSB's Greek      mat001.txt … (+ _notes.txt)
  vrs/          Hebrew -> BSB verse numbering maps           org-to-eng(.multiverse).json
import/         existing translations, filed by licence (import/README.md)
  CC0/          public domain and CC0 editions
  CC-BY/        CC BY editions
  CC-BY-SA/     CC BY-SA editions
  non-free/     all other editions: only edition.yaml in git, texts kept local      *
    <language>/ ISO 639-3 code (dan), or an interim dialect id (ch-de-be)
      <edition>/ edition.yaml + text/
export/         our drafts, public domain (CC0, export/README.md)
  <language>/   ISO 639-3 code (dan), or an interim dialect id (ch-de-be)
    <lang>_BSB/ one project (project id e.g. dan/dan_BSB): project.yaml,
                status.yaml + STATUS.md (draft status), CREDITS.md (quoted editions)
      <code>/   <code>NNN.txt, <code>NNN_notes.md, <code>NNN_footnotes.txt,
                <code>_style_guide.md, <code>_review_overview.md
      quarantine/  drafts of chapters a published translation covers           *
books.tsv       book codes, names, chapter counts
docs/           onboarding, workflow, configuration, sources, licensing, prompt templates
scripts/        conversion, prompt generation, checks
.claude/skills/ Claude Code skills: import-edition, new-project, learn-language, draft-chapter
CLAUDE.md       rules for Claude Code (the private CLAUDE.local.md is not in git)
download/       raw source files                                                       *
```

`*` Not in git. The source texts aren't kept in the repository: `scripts/setup.py`
downloads them (pinned versions) into `download/` and builds these folders. Imported
editions are kept when their licence allows it (`import/CC0/`, `import/CC-BY/`,
`import/CC-BY-SA/`).

The `_notes.txt` files hold each Greek text's own notes: the BGB's footnotes
(variants, OT quotations), and Robinson-Pierpont's differences from Nestle-Aland.
The chapter prompt points the drafting agent to them.

All files use the **BSB book codes** (`gen`, `1ki`, `jhn`, …) plus a three-digit
chapter number.

## Quick start

Requirements: Python 3 and PyYAML (`pip install pyyaml`); for USFM sources (eBible editions,
Den Frie Bibel's `sfm/`) also `usfmtc` (`pip install usfmtc`); numpy and scipy for the style check
(`scripts/style.py`); eflomal, if installed, gives better alignment lexicons (`scripts/align.py`).

**A new language project starts with [`docs/onboarding.md`](docs/onboarding.md):** what we ask a team,
the two settings that decide how the tools work (how well the model knows the language, how free the
existing translations are), and the steps from the first edition to published chapters.

With [Claude Code](https://claude.com/claude-code), `CLAUDE.md` gives the rules and four skills in
`.claude/skills/` guide the main tasks: `import-edition`, `new-project`, `learn-language` (a language
the model doesn't know) and `draft-chapter` (also callable as `/draft-chapter` etc.).

**A new language:** `python3 scripts/onboard.py`, a step-by-step setup: it finds the language's editions in
the bcv-commons/bibles catalogue, fetches them into `import/`, creates the project and its memory, and says
what comes next.

After cloning:

1. **Sources** (about 70 MB, about a minute): `python3 scripts/setup.py`. For the OT add the Hebrew
   clause layouts: `--heb bhsa,bcv-query` (BHSA 2021, the drafting layout, needs `text-fabric` and is
   for non-commercial use; bcv-query, CC BY-SA 4.0, for published structure), or only
   `--heb bcv-query --drafting bcv-query` for an open setup.
2. **Editions.** Their texts aren't in git. Those with a `fetch:` recipe come with
   `python3 scripts/setup.py --only editions`; Den Frie Bibel with
   `python3 import/CC0/dan/den-frie-bibel/sync_from_upstream.py` (its pinned commit). A non-free
   edition's text has to be obtained from its owner; `edition.yaml` says where from (the Kuni edition
   builds from eBible: `python3 import/non-free/kvg/KVG-KuNT/build_text.py`).
3. **Check a project:** `python3 scripts/modes.py <project>` (its mode and what it switches on) and
   `python3 scripts/check_project.py <project>` (drafts, store, wiki, quotations, status).
4. **Draft a chapter:** `python3 scripts/make_prompt.py <project> <code> <chapter>` prints the prompt for a
   fresh agent; `docs/workflow.md` gives the way of working.

Before your first commit, once per clone: `git config core.hooksPath .githooks` (runs the double check).

## Licence

- **Code** (`scripts/`): MIT, see `LICENSE`.
- **Documentation and templates:** CC0, see `LICENSE-docs` (with its exceptions).
- **Our drafts** (`export/`): public domain under CC0, like the BSB and MSB.
- **Imported editions** (`import/`): their own licences, by folder (`import/README.md`).
- **Source texts:** their own licences, below.

## Sources and licences

| Folder | Text | Licence |
|---|---|---|
| `reference/BSB/` | Berean Standard Bible (bsb2usfm v5.16, 2026-09-29) | public domain (CC0, since 2023-04-30) |
| `reference/MSB/` | Majority Standard Bible, NT (bsb2usfm v5.16) | public domain (CC0) |
| `orig/grc/` | Berean Greek Bible (greekbible.org/bgb.docx) | public domain (CC0) |
| `orig/grc-rp/` | Robinson-Pierpont Byzantine Textform 2018 | public domain |
| `orig/vrs/` | Hebrew → English verse map (bcv-commons/bibles, from STEPBible TVTMS) | CC BY 4.0 |
| `orig/heb-bhsa/`, `orig/heb-bcv-query/` | Hebrew/Aramaic OT clause layouts: ETCBC BHSA 2021 clause atoms; the bcv-query layout (MACULA Hebrew + UHB) | BHSA **CC BY-NC 4.0** (attribution, non-commercial); bcv-query release CC BY-SA 4.0 |
| `orig/heb/` | the drafting layout: a copy of one of them (BHSA by default) | as its source |

The Hebrew clause layout is built three ways, side by side (see `docs/sources.md`):
- the ETCBC BHSA 2021 (`setup.py --heb bhsa`): the deepest hierarchy, and the drafting layout.
  Agents consult it like a reference work; the drafts are our own text and stay free. The BHSA
  files, their levels and anything laid out on them are never published;
- the bcv-query Hebrew clause layout release v0.22 (`setup.py --heb bcv-query`), with the
  text-level hierarchy, pinned by tag and SHA-256: for every published clause structure
  (sidecars, clause-line editions), and the drafting layout for commercial users;
- MACULA Hebrew via the shoresh API (`setup.py --heb macula`, or
  `python3 scripts/fetch_heb_macula.py <code>` for one book, `rut:1` for one chapter).

`--drafting LAYOUT` picks the copy in `orig/heb/`; `scripts/relayout.py` moves a clause-line
draft from one layout to another.

Details, versions and how to rebuild every folder: `docs/sources.md`.

**Licences, in short** (`docs/licensing.md`): what we make is CC0, CC BY-SA only where it builds on
share-alike data. What we learn from an edition (wiki, language store, lexicons, statistics) is ours
for every edition, non-free ones included; quotations from it are short and credited, and its text stays
local. Every chapter is a draft until a team publishes it (`scripts/status.py`, `STATUS.md`).
