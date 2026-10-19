# Configuration

Two kinds of config files, both YAML. Templates with comments:
`import/_template/edition.yaml` and `export/_template/project.yaml`.

## import/<licence>/<language>/<edition>/edition.yaml

Describes an existing translation that was imported into `import/<licence>/<language>/<edition>/text/`.
The licence folder (`CC0`, `CC-BY`, `CC-BY-SA`, `non-free`) is described in `import/README.md`; projects
name the edition by its id alone, which must be unique across the folders.

| Field | Meaning |
|---|---|
| `name`, `language` | human-readable name; language code |
| `role` | `style` (corpus only), `continue` (new drafts continue it), `revise` |
| `text_dir` | folder with the imported files (default `text`) |
| `nt_basis` | Greek text the edition's NT follows: `critical`, `majority` or `tr` |
| `books` | BSB codes of the books present (optional) |
| `quarantine` | books agents must never see |
| `quote_hint` | sentence added to the prompt about how the edition marks quotes |
| `source`, `licence`, `attribution` | provenance; the licence must match the folder; `attribution` for CC BY and CC BY-SA |
| `fetch` | optional recipe for `scripts/fetch_edition.py`: `source` (`helloao`, `openbible`, `ebible`), `id`, `books` (optional subset) |
| `get_text` | how a clone gets the text, which is not in git: a command, or why it isn't available. `modes.py`, `check_project.py` and `make_prompt.py` print it when the text is missing (with a `fetch` recipe it defaults to `fetch_edition.py`) |

## export/<project>/project.yaml

Describes a drafting project. Drafts go to `export/<project>/<code>/`. Everything in
`export/` is public domain (CC0, `export/README.md`), so `based_on` an edition with
`role: revise` must be a CC0 edition there; `scripts/project.py` refuses any other. A revision of another edition is
a project on a derived path (`export/CC-NC/`, `local_output/`; `docs/licensing.md`, *Three output paths*).

`derived_work` (optional): the approval of derived work by the rights holder or the translation team, `{approved_by,
date, form, for, returned_to}`; a project under `local_output/` that builds on a non-free or CC-ND edition needs it.

| Field | Meaning |
|---|---|
| `language`, `language_name`, `notes_language` | target language, its name in prompts, language of the notes |
| `based_on` | edition this project continues; it supplies `nt_basis` and the style corpus |
| `style_from` | editions used as style corpus (default `[based_on]`) |
| `derived_from` | editions the project's work is derived from; only for a project under `export/CC-NC/` or `local_output/` (where the project folder is decides its output). Their text may be reused there without quarantine or quotation limits; a `based_on` edition with `role: revise` is always included |
| `nt_basis` | overrides the inherited basis |
| `quarantine`, `do_not_open` | books and paths kept from the agents (`scripts/quarantine.py` maintains `quarantine`) |
| `quarantine_attributable` | `true`: also quarantine books that an attributable (CC BY, CC BY-SA) style edition has; non-free editions always need it, public-domain ones never |
| `familiarity` | `known` \| `partial` \| `unknown`: how well the model knows the language (`scripts/probe_language.py`); picks the rule bundle (`docs/prompts/modes.md`), the verse-pack level and the style-check default (`scripts/modes.py`, `docs/onboarding.md`) |
| `close_to` | for `partial`: the standard language agents must not fall back on (`Standard German`) |
| `corpus_name` | how the prompts name the style corpus (`the Kuni NT, Ruth and Jonah`); default: the editions' names |
| `school_language` | the team's working language: the wiki, the store's notes and all analysis are written in it (only quotations in the target language); default for `notes_language` |
| `style_check` | `true` / `false` (default by familiarity: on for partial and unknown): the chapter prompt has the agent run `scripts/style.py` on its chapter and work through the flags (compares with the human translations in the corpus; for a language the model doesn't know) |
| `draft_statement` | the statement shown with every draft (`STATUS.md`, sites); default: drafted with AI agents from the Hebrew and Greek, not yet reviewed, not for use as published Scripture, CC0 |
| `publish_statement` | the statement recorded when a chapter is published, with `{by}` and `{date}` (`scripts/status.py publish`) |
| `quotes`, `chapter_word`, `book_titles` | presentation in the chapter files |
| `style_guides` | style guides (relative to the project folder) read for every book, besides the book's own `<code>/<code>_style_guide.md`; `{code}` and `{nnn}` stand for the chapter's book code and number (e.g. a verse pack `_learn/packs/{code}{nnn}.md`) |
| `default_style_guide` | style guide read when the book has none of its own yet |
| `inline_notes` | allow inline notes in the text: one entry per kind (`T`, `E`, `H`, `N`: when to use it), optional `glossary` (the keys `{N:}` may take) and `placement`; without it the text has none. `check_draft.py` checks kinds, keys, placement and `v. 12` in notes |
| `spell_check` | default by mode (on for `partial` and `unknown`); `true`: `check_draft.py` lists every word form the style corpus writes only with other marks, and every form it lacks (information); the chapter prompt tells the agent to take the corpus spelling. Matching elsewhere ignores `ignore_marks`; this keeps every mark |
| `second_draft` | `nllb` or `none` (the wizard asks in the `unknown` mode): whether the project plans a fine-tuned NLLB as the second draft for review triage (`scripts/triage.py` reads it from `_eval/local/second/nllb/`); a second opinion, never a draft |
| `pack_budget` | characters (on trial, not set by any project): a `full` verse pack shows, per verse, as many corpus verses as fit in this many characters of target text, chosen by silnlp's greedy coverage on the English words and word pairs (pack v3), instead of the 2 most similar verses (pack v2). `verse_pack.py --budget` sets it for one pack. The A/B against v2 at 2k and 6k decides the default |
| `tokenise` | target-language tokenising for the toolkit (`scripts/langtools.py`): `split_hyphens` (suffixes after a hyphen are tokens), `word_chars` (characters that belong to words besides letters, `U+A789` or literal), `ignore_marks` (default: the store's `orthography.ignore_marks`) |
| `footnotes` | `false`: the drafts have no footnotes (default `true`) |
| `header` | the header lines of a chapter file, `{file}` and `{date}` filled in; a list, or `{ot: [...], nt: [...]}` (default: as in the earlier chapters) |
| `footnotes_header` | the header lines of a footnote file, `{file}` and `{date}` filled in |
| `notes_structure` | the structure of the notes file, replacing the default list in the prompt |
| `style_model` | files read as the style model while the project has no finished chapters (e.g. chapters of the style edition) |
| `report_items` | what the agent's final report names besides the verse check (default: footnotes created) |
| `book_title_rule` | sentence added to the prompt when the book has no title: none in `book_titles` and none in a style edition's own chapter files (their `===Title, …===` line is used) |
| `rules` | project rules added to every prompt |
| `style_notes` | free text added to the style section of the prompt |

## How the textual basis is resolved

```
nt_basis   NT original              NT assisting translation
critical   orig/grc   (BGB)         reference/BSB
majority   orig/grc-rp (RP 2018)    reference/MSB
tr         orig/grc-rp (RP 2018)    reference/MSB
```

The OT always uses `orig/heb` + `reference/BSB`. The project's own `nt_basis` wins; otherwise
it is taken from `based_on`, otherwise `critical`.

`tr` maps to RP because no Textus Receptus text is in the repo. RP and the TR
differ in about 1,800 places, mostly small, and the MSB footnotes many of them.
If an edition follows the TR closely, consider adding a TR text as
`orig/grc-tr` and a third basis.

`python3 scripts/project.py <project>` shows the resolved setup.

- **`lexeme_aligner`** (project, optional): the id of lexeme-aligner's compact-alignments layer for the style
  edition's language (Kuni: `kvg_wbt`). `scripts/lang.py build` decodes it onto the project's NT tokens as a second
  alignment beside eflomal's (CC0 positions; the layer's source text is fetched from its provider, so far helloAO).

