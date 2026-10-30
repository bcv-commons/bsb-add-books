# make-tanakh

Draft new Bible translations chapter by chapter, **directly from the Hebrew and Greek**. The **BSB** (or the
**MSB** for a majority-text NT) is the only assisting translation. Existing translations in the target language
serve as **style** models. `docs/workflow.md` describes the way of working.

## Why "Tanakh"

**Tanakh** (תנ״ך) is the Jewish name for the Hebrew Bible. The word is an acronym of its three sections: **T**orah,
**N**evi'im and **K**etuvim.

- **Torah** ("instruction", "teaching") is the five books of Moses: Genesis, Exodus, Leviticus, Numbers and
  Deuteronomy.
- **Nevi'im** ("Prophets") has two parts. The *Former Prophets* tell Israel's history in the land: Joshua, Judges,
  Samuel and Kings. The *Latter Prophets* are Isaiah, Jeremiah, Ezekiel and the Twelve, the shorter prophets from
  Hosea to Malachi.
- **Ketuvim** ("Writings") holds the rest: Psalms, Proverbs and Job; the five scrolls (Song of Songs, Ruth,
  Lamentations, Ecclesiastes, Esther), read at the festivals; then Daniel, Ezra–Nehemiah and Chronicles.

Counted the Jewish way, these are 24 books. Christian Bibles count the same text as 39 books, because they split
Samuel, Kings, Chronicles, Ezra–Nehemiah and the Twelve. This repository follows the Tanakh's order by default,
from Genesis to Chronicles (a project can choose another order: `book_order`, `docs/configuration.md`).

**A text kept with great care.** For more than two thousand years, Jewish scribes copied these books by hand under
strict rules. A Torah scroll was written letter by letter from a correct copy, and a scroll with errors was not
used. From about the 7th to the 10th century, the **Masoretes** of Tiberias went further. They added vowel points
and accents to fix how each word is read, and they wrote the *Masorah* in the margins: notes that count words and
letters and mark unusual forms, so that later copyists could check their work. The Masoretes also marked the end of
each verse, and our verse numbers still follow their divisions. Their work survives in codices such as the **Aleppo
Codex** (about 930) and the **Leningrad Codex** (1008), the oldest complete Hebrew Bible. The Dead Sea Scrolls,
copied a thousand years earlier, show how faithfully the text was handed down through exile, dispersion and
persecution.

This repository drafts from that text. The Hebrew it works with is the Leningrad Codex, in the Westminster
Leningrad Codex (WLC) and the ETCBC's BHSA, and our drafts of the Tanakh keep the Hebrew verse numbering (`docs/sources.md`).

**The foundation of the whole Bible.** The Tanakh is also the foundation of the other books of the Christian
Bible. The Gospels and the Apostolic Writings quote it throughout and build on it. Yeshua himself speaks of "the
Law of Moses, the Prophets and the Psalms" (Luke 24:44), the Tanakh's three sections. The toolkit drafts these
writings as well, from the Greek.

## Start here: a new language

```
git clone https://github.com/bcv-commons/make-tanakh.git my-work && cd my-work
git remote rename origin template          # the template stays a remote: merge its updates later
pip install pyyaml usfmtc
python3 scripts/onboard.py
```

The clone is your **work copy**: your projects go there, and it takes the template's updates by merging
(`docs/workflow.md`, *Your work copy*). The wizard sets up a language project step by step, from the language and its existing translations to the
tools that fit it. The full guide: [`docs/onboarding.md`](docs/onboarding.md).

**What you need:** Python 3, and [Claude Code](https://claude.com/claude-code) or an Anthropic API key. Keys go in
the git-ignored `.env` in the repository folder (or the environment):

- `ANTHROPIC_API_KEY=…` to run the probes through the API;
- `DBT_API_KEY=…` for languages only on the Digital Bible Platform (free at https://4.dbt.io).

**Your work as a website:** `python3 scripts/build_site.py --preview`, then open `build/site/index.html`. To put it
online: [`docs/website.md`](docs/website.md).

**Two small demo projects** show a project after some work, each with its store, wiki and alignments:

- `export/dan/dan_BSB/`: Danish, a language the model knows well, continuing Den Frie Bibel (CC0); one chapter each
  of Genesis (33), Joshua (16) and Daniel (12), with their style guides and review overviews;
- `export/jam/jam_BSB/`: Jamaican Creole, partly known; its style edition is non-free; Genesis 1.

Their editions' texts are not in git. Get them with `python3 import/CC0/dan/den-frie-bibel/sync_from_upstream.py`
(Danish) and `python3 scripts/fetch_edition.py jambswn-et` (Jamaican; needs `DBT_API_KEY`). Delete the project
folders and their editions when you no longer want them. Two more sample editions, NTs without a project, stand for
a language the model doesn't know: Bodo Parja (CC BY, Odia script) and Zinza (CC BY-SA). See
[`import/README.md`](import/README.md), *Sample editions*.

## Related repos

This repo is the template: tools, formats, docs and skills, plus the two demos. Projects live in a **work copy**, a
copy of the template that merges its updates and keeps only data (`docs/workflow.md`, *Your work copy*), so the
template stays free of project data. New tools start in bcv-commons/make-tanakh-grammar and come here when they are
measured. How the three relate, what each gives the others and how versions are pinned:
[`docs/related-repos.md`](docs/related-repos.md); the versions: [`CHANGELOG.md`](CHANGELOG.md).

## Layout

```
reference/      the assisting translations                                             *
  BSB/          Berean Standard Bible, whole Bible           gen001.txt … rev022.txt
  MSB/          Majority Standard Bible, NT only             mat001.txt … rev022.txt
orig/                                                                                  *
  heb/          Hebrew/Aramaic Tanakh (Hebrew verse numbers) gen001.txt …
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
docs/           onboarding, workflow, configuration, sources, licensing, formats, related repos, prompt templates
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
if installed, for better alignment lexicons (`scripts/align.py`; see `docs/onboarding.md`, *External tools*); pysword
for the second-draft model's Greek source (`import/CC0/ell/vamvas/`).

In [Claude Code](https://claude.com/claude-code), `CLAUDE.md` gives the rules and four skills guide the main tasks:
`import-edition`, `new-project`, `learn-language` (a language the model doesn't know) and `draft-chapter`.

1. **Sources** (about a minute): `python3 scripts/setup.py`. For the Tanakh add the Hebrew clause layouts:
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
