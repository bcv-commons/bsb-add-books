# Related repos

make-tanakh is one of three repos. Each describes the family from its own side, with the same outline; this is
make-tanakh's copy. The others: `RELATIONS.md` in the work copy and in make-tanakh-grammar.

## 1. The three repos

| Repo | Role | History | Visibility |
|---|---|---|---|
| **bcv-commons/make-tanakh** (this repo) | the stable toolkit and template: scripts, formats, docs, skills | its own | public |
| **make-tanakh-work** (today larsgson/bsb-add-books-work, to be renamed) | data only: projects, drafts, language stores, alignments, the website; a classical template copy | shared with make-tanakh | public |
| **bcv-commons/make-tanakh-grammar** | the rules-engine lab (how source grammar is rendered in a target language, measured component by component), the language analysis published as bcv-commons/language-analysis, and the place where new tools start | its own | public, screened (no protected texts) |

Any team can make its own work copy the same way (`docs/workflow.md`, *Your work copy*).

## 2. This repo's role

**Belongs here:** the tools (`scripts/`), the formats and their docs (`docs/`), the prompt templates
(`docs/prompts/`), the skills (`.claude/skills/`), the project and edition templates (`export/_template/`,
`import/_template/`), the edition recipes of the sample editions, and two small demo projects (`export/dan/dan_BSB/`
with one chapter each of Genesis, Joshua and Daniel, `export/jam/jam_BSB/` with Genesis 1).

**Doesn't belong here:** project data beyond the demos (drafts, stores, wikis, alignments of real projects), the
website's content, experiments and tools still being measured. Those live in a work copy or in make-tanakh-grammar.

## 3. What it takes from the others, and how that is pinned

- **From make-tanakh-grammar: promoted tools.** A tool that is measured and general comes as one delivery
  (patches and VERIFY files). It is implemented here in this repo's way, not merged; the grammar repo then drops its
  copy and logs the move in its `PROMOTIONS.md`. make-tanakh never imports the grammar repo's code. If a tool here
  ever reads grammar's results, it reads them as a published dataset at a pinned version, like the sources below.
- **From a work copy: fixes and demos.** A fix found while drafting comes as a patch (`git diff template/main --
  <path>`), is applied here and goes back to the work copy with its next merge. The demo projects are copied from a
  work copy's published state, by file.
- **From the rest of bcv-commons and the sources:** bcv-query's clause layouts and prepared source structures,
  compact-alignments' index, the speaker layer, the bibles catalogue, the BSB/MSB and the Greek texts, Grambank,
  Glottolog, STEPBible. Each is pinned by tag, commit or SHA-256 in `scripts/setup.py` (and the edition recipes'
  `fetch.lock.json`), and listed with its version and licence in `docs/sources.md`.

## 4. What it gives the others, and in what form

- **Tags** (`vMAJOR.MINOR.PATCH`): a work copy merges a tag, and the grammar repo pins one as a submodule. What
  changed between tags is in `CHANGELOG.md`.
- **Stable formats.** These are kept, or changed only with a version note in `CHANGELOG.md` (what changed, and how
  existing files move over):

  | Format | Defined in | Version marker |
  |---|---|---|
  | the language store (`profile/*.json`) | `docs/language-store.md`, `docs/language-store/schema/language_profile.schema.json` | the tag |
  | clause sidecars | `docs/clause-sidecar.md` | the tag |
  | the `.align` working format | `scripts/full_align.py` (docstring) | follows compact-alignments' `tokenizer_version` 2 and `text_fp_version` 1 |
  | the compact-alignments layer (`full_align.py export`) | `scripts/full_align.py` | `_layer.json` `version` 3, `tokenizer_version`, `text_fp_version` |
  | `orig/heb.sqlite`, `orig/grc.sqlite` | `scripts/src.py` (docstring and `SCHEMA`), `docs/sources.md` | the source structure `v1` (`SRC_V` in `setup.py`) |

  Adding an optional field or a table is not a breaking change; renaming, removing or changing the meaning of one
  is, and gets a new minor version before 1.0, a new major version after.
- **The template itself:** a work copy merges `template/main` (or a tag) and so gets the scripts, docs, skills and
  demos.
- **A data root apart from the code:** with `MAKE_TANAKH_ROOT` set, the scripts work on that folder's data and read
  only their own code from make-tanakh (`docs/configuration.md`, *The data root*). make-tanakh-grammar pins
  make-tanakh as a submodule at a tag and runs it on a work copy this way.

## 5. How a change travels

1. A new tool starts in make-tanakh-grammar and is measured there.
2. When it is ready, it comes to make-tanakh as one delivery; it is implemented here, checked, and committed.
3. A release is tagged here.
4. Each work copy merges `template/main` or the tag; its `scripts/`, `docs/` and `.claude/` stay identical to the
   template's.
5. The grammar repo moves its pin to the new tag and drops its copy of the tool.

A fix found in a work copy takes the short way: a patch to make-tanakh, then back with the next merge. The user
commits in every repo; agents don't.

## 6. Licences and what never moves

- Code MIT, docs and templates CC0, drafts CC0; each source text and edition keeps its own licence
  (`docs/licensing.md`, `docs/sources.md`, `import/README.md`).
- No source texts in git, in any of the three repos: `scripts/setup.py` fetches them at pinned versions.
- Non-free edition texts, quarantined books and `local_output/` stay on the machine that has them.
- BHSA data (`orig/heb-bhsa/`, the drafting copy in `orig/heb/`, and everything built on it: sidecars, indexes,
  layout rows) stays local, in every repo. Only the drafts themselves, our own text, move.
- The grammar repo publishes nothing that contains a protected text.

## 7. Version records

- **This repo:** its tags, `CHANGELOG.md` (format changes in their own section), and the source pins in
  `scripts/setup.py` and `docs/sources.md`.
- **A work copy:** the tag or commit it merged (`git describe template/main`), in its merge commits.
- **make-tanakh-grammar:** the submodule commit, and in each published result the toolkit version it ran on.
- **Contract test,** run in a work copy after each merge, and here before a tag:

  ```
  git diff template/main -- scripts docs .claude      # empty in a work copy: no tools of its own
  python3 scripts/check_project.py <project>          # every project: drafts, store, wiki, alignments, quotations, status
  python3 scripts/full_align.py check <project>       # the .align files against the drafts
  python3 scripts/src.py stats                        # orig/heb.sqlite and orig/grc.sqlite open with the expected tables
  ```

  Here, `<project>` is each demo project (`dan/dan_BSB`, `jam/jam_BSB`).
