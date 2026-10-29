# Configuration

Two YAML files. Commented templates: `import/_template/edition.yaml`, `export/_template/project.yaml`.

## The data root

The scripts read and write their data (`orig/`, `reference/`, `download/`, `import/`, `export/`, `build/`,
`local_output/`) under the **data root**: the environment variable `MAKE_TANAKH_ROOT` if it is set, else the folder
the toolkit is in, as in a work copy. The toolkit itself (`scripts/`, `docs/`, `.claude/`, `.githooks/`, `books.tsv`)
is always read from where the scripts are. So a repo that holds make-tanakh as a submodule runs it on a work copy's
data with `MAKE_TANAKH_ROOT=<work copy> python3 <submodule>/scripts/...` (`docs/related-repos.md`). The data root is a
git repo with the template's `.gitignore`, like a work copy: the checks and the site read its tracked files.

## edition.yaml

In `import/<licence>/<language>/<edition>/`; the text is in `text/`. The licence folders are described in
`import/README.md`. Projects name an edition by its id, unique across the folders.

| Field | Meaning |
|---|---|
| `name`, `language` | readable name; language code |
| `role` | `style` (corpus only), `continue` (drafts continue it), `revise`, `source` (a source for the second-draft model, not a corpus) |
| `nllb_code` | a source edition's NLLB language code (`ell_Grek`) |
| `script` | optional: the text's writing system as an ISO 15924 code (`Latn`, `Orya`, `Arab`); without it, `scripts/script_code.py` takes the script of most of the corpus's letters. `scripts/onboard.py` writes it when it imports an edition: from the bcv-commons/bibles catalogue (`edition-struct.json`) when it lists the edition, else from that detection. It sets the NLLB code, the script the probes name, the donor's `nllb_init` (a relative in the same script first) and, for a right-to-left script (Arab, Hebr, Syrc, Thaa, Nkoo, Adlm), `dir="rtl"` and `lang` on the target text in the site and the wiki view |
| `text_dir` | folder with the imported files (default `text`) |
| `nt_basis` | Greek text of the edition's NT: `critical`, `majority` or `tr` |
| `books` | BSB codes of the books present (optional) |
| `quarantine` | books agents must never see |
| `quote_hint` | sentence added to the prompt on how the edition marks quotes |
| `source`, `licence`, `attribution` | provenance; the licence must match the folder; `attribution` for CC BY and CC BY-SA |
| `credit` | the line shown with quotations from the edition (any licence) |
| `licence_source` | `fetched`: `fetch_edition.py` writes `licence` and `credit` from the source's copyright line |
| `published_text` | the published form (USFM zip or folder) quotations must match, when `text/` is a newer working copy |
| `published_also` | further USFM files or folders of the published text (books published elsewhere) |
| `fetch` | recipe for `scripts/fetch_edition.py`: `source` (`helloao`, `openbible`, `ebible`, `dbt`, `local`), `id` |
| `get_text` | how a clone gets the text (a command, or why it isn't available); printed when the text is missing; with `fetch` the default is `fetch_edition.py <edition>` |
| `sfm` | the team's SFM conventions, written by `scripts/sfm_profile.py --write` from their files in `source/`: `normalization` (NFC, NFD), `line_endings` (crlf, lf), `versification` (english, hebrew; `evidence.versification`), `id_line` (`{BOOK}` for the code), `ide`, `file_pattern` (`{nn}{BOOK}`), `heading` (s, s1), `paragraphs`, `divine_name` (the words marked `\nd`), `footnotes` (their parts: `fr fk ft`), `also` (markup recorded, not produced), `newest` (the book followed where they differ), `differs_in_older_books`; `scripts/export_usfm.py` follows it |
| `derived_work` | approval of derived work: `{approved_by, date, form, for, returned_to}`; needed before a `local_output/` project builds on a non-free or CC-ND edition (`docs/licensing.md`, *Three output paths*) |

## project.yaml

In `export/<lang>/<id>/` (or `export/CC-NC/…`, `local_output/…`: the folder decides the output path,
`docs/licensing.md`, *Three output paths*). Drafts go to `<project>/<code>/`. In `export/`, a `based_on` edition
with `role: revise` must be CC0; `scripts/project.py` refuses any other.

| Field | Meaning |
|---|---|
| `language`, `language_name` | target language (default: the `based_on` edition's); its name in prompts |
| `based_on` | edition the project continues; supplies `nt_basis` and the style corpus |
| `style_from` | editions used as style corpus (default `[based_on]`) |
| `derived_from` | editions the work derives from (only under `export/CC-NC/` or `local_output/`); reused there without quarantine or quotation limits; a `based_on` edition with `role: revise` is always included |
| `nt_basis` | overrides the inherited basis |
| `quarantine`, `do_not_open` | books and paths kept from the agents (`scripts/quarantine.py` maintains `quarantine`) |
| `quarantine_attributable` | `true`: also quarantine books a CC BY / BY-SA style edition has |
| `lexeme_aligner` | id of a bcv-commons alignment layer for the style edition (below) |
| `familiarity` | `known` (default) \| `partial` \| `unknown`: picks the rule bundle (`docs/prompts/modes.md`), the verse-pack level and the check defaults (`scripts/modes.py`) |
| `close_to` | for `partial`: the standard language agents must not fall back on (`English` for Jamaican) |
| `corpus_name` | how prompts name the style corpus (`the Jamaican NT`); default: the editions' names |
| `school_language` | the team's working language for the wiki, the store's notes and analysis (default `English`) |
| `notes_language` | language of the translator notes (default: `school_language`) |
| `style_check` | run `scripts/style.py` on each chapter and work through its flags (default: on for `partial` and `unknown`) |
| `spell_check` | `check_draft.py --spell`: word forms the corpus writes only with other marks, and forms it lacks (default: on for `partial` and `unknown`) |
| `script` | optional: the target's writing system (ISO 15924), over its style editions' `script`; it makes the second-draft model's target code (`<iso>_<script>`) and keeps its init in the same script (`scripts/script_code.py`) |
| `tokenise` | target tokenising (`scripts/langtools.py`): `split_hyphens`, `word_chars` (`U+A789` or literal), `ignore_marks` (default: the store's `orthography.ignore_marks`) |
| `second_draft` | `nllb` or `none`, set by the wizard: whether the project plans a fine-tuned NLLB as a second opinion for review triage (`scripts/triage.py`, from `_eval/local/second/nllb/`); never a draft |
| `nllb_source` | the second-draft model's source: a source edition (default `vamvas`, modern Greek) or `bsb` (the assisting translation, English); `scripts/nllb/source.py` |
| `donor` | the relatives of a language the model doesn't know, written by `scripts/donor.py run <project> --write`: `known` (ISO 639-3 of the nearest relative the model writes, by a write probe, or `none`; the seeds' source, `scripts/seeds.py`), `name`, `known_score` (its write probe, chrF by verse), `candidates` ({iso: score} of the probed ones), `structure` (the closest relatives by Glottolog, whatever the model knows), `structure_level`, `nllb_init` (the NLLB language the second-draft model starts from: `nllb/data.py --init-lang`'s default; for a target not in Latin script a relative written in the target's script first, else `script_code.init_for_script`'s choice, the reason added to `why`), `why` |
| `pack_grammar` | the verb-marking block of the pack (pack v4, needs the store's verb cells). Unset: `binding` for familiarity `unknown` once the store has cells the human OT clearly marks, else off (`modes.py <project>` shows which); `false` turns it off, `true` gives the block alone. `binding` also lists the chapter's verbs of clearly marked cells in the prompt, and `chapter_check.py` reports one lacking the pattern unless the notes have `unmarked <ch>:<v> <cell>: <reason>` (`cell_check.py <project> unmarked \| try …` turns those into store entries); `verse_pack.py --grammar` for one pack |
| `rules` | project rules added to every prompt |
| `book_rules` | lines added to the book agent's prompt only (`make_prompt.py --book`) |
| `style_notes` | free text for the prompt's style section |
| `style_guides` | style guides (relative to the project) read for every book besides `<code>/<code>_style_guide.md`; `{code}`, `{nnn}` are filled in |
| `default_style_guide` | style guide read while the book has none |
| `style_model` | files read as the style model while the project has no finished chapters |
| `quotes`, `chapter_word`, `book_titles` | presentation in the chapter files |
| `book_title_rule` | sentence added when the book has no title (none in `book_titles` or a style edition's `===Title, …===` line) |
| `header` | header lines of a chapter file, `{file}` and `{date}` filled in; a list or `{ot: [...], nt: [...]}` |
| `footnotes` | `false`: no footnotes (default `true`) |
| `footnotes_header` | header lines of a footnote file |
| `notes_structure` | structure of the notes file, replacing the prompt's default |
| `inline_notes` | allow inline notes: one entry per kind (`T`, `E`, `H`, `N`: when to use it), optional `glossary` and `placement`; checked by `check_draft.py` |
| `report_items` | what the agent's final report names besides the verse check (default: footnotes created) |
| `draft_statement` | statement shown with every draft (`STATUS.md`, site) |
| `team_name` | the team the site's status strip names, without "the" ("Jamaican Bible review team"): "not yet checked or approved by the Jamaican Bible review team"; default "<language> language team" |
| `publish_statement` | statement recorded on publishing, with `{by}` and `{date}` (`scripts/status.py publish`) |
| `site` | `false`: the project is left off the website |
| `sfm` | fields of the style edition's `sfm:` block (above) to set otherwise for this project's SFM export (`heading: s`, `versification: hebrew`) |

## Textual basis

```
nt_basis   NT original              NT assisting translation
critical   orig/grc   (BGB)         reference/BSB
majority   orig/grc-rp (RP 2018)    reference/MSB
tr         orig/grc-rp (RP 2018)    reference/MSB
```

The OT always uses `orig/heb` + `reference/BSB`. The project's `nt_basis` wins, else the `based_on` edition's, else
`critical`. `tr` maps to RP, the closest text in the repo (`docs/sources.md`). `python3 scripts/project.py <project>`
shows the resolved setup.

## lexeme_aligner

A bcv-commons alignment layer for the style edition's language, decoded by `scripts/lang.py build` onto the project's
NT tokens as a second alignment beside eflomal's (CC0 positions):

- compact-alignments: `<iso>_<edition>` (statistical);
- full-alignments-llm: `<edition>+llm+<name>` (checked by a language model);
- full-alignments-manual: an id with `+manual+`.

A book is used where the layer was built on exactly our text (the file name's text fingerprint), or, for a compact
layer from helloAO, on helloAO's text matched to ours word by word. `python3 scripts/lang.py layers <project>
[--write]` lists the layers built on our text and sets the best one; `onboard.py` runs it.
