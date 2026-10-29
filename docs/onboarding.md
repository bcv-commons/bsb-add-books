# Onboarding a new language project

How a new language comes into this repository, from the first conversation with a team to published chapters.
Two facts decide how the tools work: **how well the model knows the language**, and **how free the existing
translations are**.

| | Danish (`dan_BSB`) | Jamaican (`jam_BSB`) | a language the model doesn't know |
|---|---|---|---|
| Existing translation | Den Frie Bibel (CC0) | Di Jamiekan Nyuu Testiment (non-free) | the team's translation, often NT only |
| Familiarity | `known` | `partial` (`close_to: English`) | `unknown` |
| Agents | draft from their own Danish; the memory keeps decisions consistent | write Jamaican, not English: forms checked against the corpus | learn the language from the corpus while drafting; invent nothing |

For the third case two sample editions come without a project: the Bodo Parja NT (CC BY, Odia script) and the
Zinza NT (CC BY-SA) (`import/README.md`, *Sample editions*).

## 0. The wizard

`python3 scripts/onboard.py` walks a team through the set-up. In Claude Code, "set up a new language" runs it
through the `new-project` skill. The steps:

1. **The language:** its ISO 639-3 code, or its name to look the code up; a dialect id where a variety has no code;
   the team's school language.
2. **The editions** in the bcv-commons/bibles catalogue and its sources (helloAO, openbible, eBible, the Digital
   Bible Platform), with licence and coverage. You pick the style corpus. Your own USFM or SFM files (e.g. from
   Paratext) work too (`m`): the wizard says where to copy them and converts them. From SFM files it also reads the
   team's conventions (Unicode form, line endings, versification, headings, the divine name, the `\id` line and file
   names; `scripts/sfm_profile.py`) and asks you to confirm them: the drafts sent back as SFM follow them.
3. **Import and fetch** into the right licence folder. Texts stay out of git. The NT basis, the quote marks and the
   script (ISO 15924, `script:` in edition.yaml) are read from the text: the script from the bcv-commons/bibles
   catalogue (`edition-struct.json`, detected there from the text) when it lists the edition, else by
   `scripts/script_code.py` (a team's own files). `fetch_edition.py --find` shows it per edition. The script is named
   in the probes, picks a donor's `nllb_init` in the same script, and sets the reading direction of the target text
   in the site and the wiki view (right to left for Arabic, Hebrew, Syriac, Thaana, N'Ko, Adlam). The USFM export
   needs nothing for it: Paratext takes the direction from the project's language settings.
4. **The project** `export/<language>/<language>_BSB/`, its book order and the first chapter to draft. The book order
   is the Hebrew Bible's (`tanakh`) unless the team's Bible follows another: `protestant` (Genesis … Malachi) or
   `septuagint` (Orthodox); it orders the lists, the site and book ranges, never the file names (`book_order`,
   `docs/configuration.md`). A book that a non-free edition has is quarantined now, before the probes.
5. **AI work:** the probes run through the API when `ANTHROPIC_API_KEY` is set (billed per token), else through
   Claude Code (`claude -p`, no tools). Drafting always runs in Claude Code.
6. **The probes** (about a minute): the scores, the model's slips, and a suggested familiarity. A speaker accepts or
   overrides it; for `partial` the wizard asks `close_to`. For `unknown`, **the donor** (`scripts/donor.py`, about 15k
   tokens): the language's relatives by descent from Glottolog (`structure`: whole levels of the tree until five), and
   the nearest relative the model writes, measured by a write probe on up to three candidates (a Bible to probe
   against, and an NLLB code or a Wikipedia of 1,000+ articles; the largest of each level, nearest first). The
   nearest one written well (58 by verse) wins over a better-scoring one further away, which the seed prompt names
   as a cross-check; `known: none` where the model writes none of them. The `donor:` block sets the seeds' source
   (`scripts/seeds.py prompt`), the second-draft model's start (`nllb_init`) and `close_to`.
7. **The tools** the familiarity switches on, with the tokens per chapter logged so far in that mode
   (`scripts/usage.py`). For an `unknown` language it also offers the second-draft model (below).
8. **Set-up:** sources and the Hebrew layout, alignment lexicons, a matching alignment layer
   (`scripts/lang.py layers <project> --write`), the empty store and wiki with the probe's slips as first entries,
   `CREDITS.md`, `STATUS.md`. A language written without spaces between words (Thai, Lao, Khmer, Myanmar, Tibetan,
   Chinese, Japanese: `script_code.NO_SPACES`) gets its words as tokenizer v2 cuts them (compact-alignments' tokenizer,
   also bibles' `tools/verse-text`; our copy is `scripts/full_align.py`): Han per character, Myanmar per syllable,
   Thai/Khmer/Lao at the zero-width space. The lexicons, concordance and packs then count these units as words.
9. **What comes next**, asked for in Claude Code: the memory, the style guide, a reference chapter, then the
   chapters. At the end the wizard opens the website's local preview (`docs/website.md`).

Options: `--answers FILE.yaml` (answers from a file), `--yes` (no questions), `--dry-run` (changes nothing). The
answers are saved as `_onboard_answers.yaml`; a stopped onboarding continues. Other editions come in with the
`import-edition` skill first.

### Keys

Keys go in the git-ignored `.env` in the working copy, or in the environment (the environment wins):

- `DBT_API_KEY=…` for the Digital Bible Platform (free at https://4.dbt.io). Without it the wizard waits for one
  when a language is only there. DBT texts are filed as non-free: the text stays local and any book it has is
  drafted in quarantine.
- `ANTHROPIC_API_KEY=…` for the probes and priors through the API.
- `NETLIFY_AUTH_TOKEN=…` and `NETLIFY_SITE_ID=…` to publish the website from your machine (`docs/website.md`).

## 1. What we ask a team

- **The target language** (ISO 639-3, or a dialect id), the language the team reads, and the books they want first.
- **Existing translations** in or close to the language: where from, under what licence, which books. Each becomes
  an *edition* in `import/`.
- **Who reviews** the drafts, and who may publish them.

Nothing else is needed: the existing translations are a style corpus, not a source.

## 2. The two settings

**Licence class** of each edition, from its folder in `import/` (`import/README.md`):

| Class | Folders | What follows |
|---|---|---|
| public domain | `CC0/` | nothing required; credited as a courtesy (`CREDITS.md`) |
| attributable | `CC-BY/`, `CC-BY-SA/` | its credit line; quarantine only with `quarantine_attributable: true` |
| non-free | `non-free/`, `CC-ND/`, `CC-NC/` | the text stays local; a book it has is drafted in quarantine; quotations short and credited (`docs/licensing.md`) |

**School language** (`school_language`): the team's working language. The wiki, the store's notes and the translator
notes (unless `notes_language` says otherwise) are written in it.

**Familiarity** (`familiarity` in `project.yaml`) comes from three short probes, each run by a fresh model with no
tools (`python3 scripts/probe_language.py <project> run`, or `write`, `read`, `tell` one by one with `--score`):

- **write:** 16 BSB verses into the language, chrF against the edition;
- **read:** 16 corpus verses into English, chrF against the BSB (verses with names left out);
- **tell apart:** 24 pairs of a corpus verse and a copy with one change; which is the published one?

Each score is shown beside its floor (unrelated verses scored against each other). The suggestion:

- read less than 15 above its floor: `unknown` (the model doesn't understand it);
- write, by verse, less than 10 above its floor: `unknown` (it reads the language, likely through a related one, but
  can't write it; the wizard asks for that language as `close_to`);
- write, by verse, 58 or more: `known`;
- otherwise `partial`: understood, written with slips.

The thresholds are provisional; read the answers too. `python3 scripts/modes.py <project>` prints the mode.

## 3. What the mode switches on

| | known | partial | unknown |
|---|---|---|---|
| Language memory (store `profile/` + `wiki/`) | the project's decisions: terms, names, style | + the variety's grammar and forms | + a term base and the gaps |
| Verse pack (`verse_pack.py`) | `memory`: decisions touching each verse | `dialect`: + lexicon renderings, corpus phrases | `full`: + similar verses, open searches |
| Rule bundle in the prompt (`docs/prompts/modes.md`) | use and extend the memory | + the variety, not the standard language | + no knowledge assumed; names by the letter rules |
| Verb marking (`pack_grammar`) | off | off | `binding` once the store has cells the human OT clearly marks: the chapter's verbs of those cells listed in the prompt, checked in the loop |
| Style check (`style.py`) | off | on | on |
| Spell check against the corpus (`spell_check`) | off | on | on |
| Held-out test book (`learn-language` skill) | no | optional | yes, if the corpus has an OT book |
| Second-draft model (`second_draft`) | no | off (still being tested) | offered |

In every mode the team's input page (`wiki/team-input.md`, `scripts/team_input.py`) turns their decisions into
binding store entries. The licence class adds, independently: quarantine, the quotation rule in every prompt,
`CREDITS.md`, and which generated files stay local.

**The second-draft model** is a fine-tuned NLLB trained on the corpus (`scripts/nllb/`). Its source is the Vamvas Bible
in modern Greek by default (`import/CC0/ell/vamvas/`, public domain; its wording is closer to the original's), or the
BSB in English (`nllb_source: bsb`); the wizard asks, and fetches the Vamvas text (`pip install pysword==0.2.8`). It drafts each chapter a second time; `scripts/triage.py` lists the verses where it and the agent
disagree, for review first. It is never a draft. Training needs an NVIDIA GPU with 8 GB or more (about 5–7 hours),
an Apple GPU with about 32 GB, or a rented GPU.

## 4. Steps

1. **Import the editions** (`import-edition` skill): the licence folder, `credit`, and `get_text` (how a clone gets
   the text). `python3 scripts/fetch_edition.py --find <iso>` lists what can be fetched.
2. **Probe the familiarity** (`probe_language.py`): set `familiarity`, and `close_to` for a variety; for an unknown
   language the donor (`python3 scripts/donor.py run <project> --write`) and, where it knows one, the seeds
   (`python3 scripts/seeds.py prompt <project>` for a fresh agent). Then the **family brief**: a research agent
   (effort high) with `python3 scripts/seeds.py brief <project>` writes what the language and its relatives mark, from
   their grammars, with a status and sources per point, and turns the points into seeds (`docs/language-store.md`,
   *The brief*; local in `_eval/local/` when a source is NC/ND). Know what you are looking for, know where to look;
   the corpus decides.
3. **Create the project** (`new-project` skill): `project.yaml` from `export/_template/`, the style guide, the
   divine names.
4. **Build the memory:**
   - `python3 scripts/align.py <project>`: the lexicons. The English and Greek sides take seconds. The Hebrew side
     first fetches each OT chapter of the corpus from the scaffold API (cached in `download/scaffold/`): a whole OT
     takes 15–20 minutes the first time.
   - `python3 scripts/memory_prompt.py <project> --init`: creates the empty store and wiki and prints the prompt for
     an agent that builds them from the corpus.
   - For a `known` or `partial` language, `python3 scripts/priors.py write <project>` records what the model believes
     about the grammar; `priors.py check` tests each item against the corpus and shows where the standard language
     leaks in.
   - For `unknown`, follow the `learn-language` skill (a test chapter, a held-out book, curation).
   - `python3 scripts/wiki.py view <project>` gives the team one page to read; they correct it in the wiki.
5. **Draft:** a reference chapter first, reviewed with the team. Then one book agent per book drafts the chapters
   one after another (`draft-chapter` skill, `make_prompt.py <project> <code> --book`, `chapter_check.py` in its
   loop). For the OT, `package.py` builds the clause packages; the agent writes the draft tagged (`word^n`) and
   `full_align.py split` makes the draft and its word alignment.
6. **Check** after each run: `python3 scripts/check_project.py <project>`. The agents keep to the rules as they
   write; this is the double check.
7. **Review and publish:** the team reads the drafts and the wiki; `scripts/status.py` marks chapters `in-review`
   and `published`. Drafts may be online from the start, marked as drafts (`docs/workflow.md`, *Draft status*).

## 5. What is published

Everything we make is CC0 (CC BY-SA where it builds on share-alike data), for every licence class: drafts, notes,
the store, the wiki's prose, lexicons, statistics. Quotations from non-free editions stay short and credited. Their
texts and the generated files that print them (verse packs, alignment links, style reports) stay local. Where an
edition already has a book we draft, `docs/workflow.md` (*When an edition already has the book*) gives the cases.

## External tools

- **eflomal** (GPL-3.0, Östling & Tiedemann) gives better alignment lexicons. It is run as a separate program, not
  bundled. Without it `scripts/align.py` uses a built-in IBM Model 2.
- **eflomal on macOS:** Apple clang has no OpenMP. Run `brew install libomp`, then build eflomal's `src/` with
  `-Xpreprocessor -fopenmp -I$(brew --prefix libomp)/include` and link with `-lomp`.
- **Alignment layers:** `python3 scripts/lang.py layers <project> --write` finds a bcv-commons alignment layer
  built on exactly the edition's text (matched by text fingerprint) and sets it as `lexeme_aligner` in
  `project.yaml`. The wizard runs it.
