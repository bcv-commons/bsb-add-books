# Onboarding a new language project

How a new language comes into this repository, from the first conversation with a team to published
chapters. Two facts about the situation decide how the tools work: **how well the model knows the
language**, and **how free the existing translations are**. The three pilots cover the main cases.

| | Danish | Bern German | Kuni |
|---|---|---|---|
| Existing translation | Den Frie Bibel (public domain) | Bietenhard's NT (all rights reserved) | Kuni NT, Ruth, Jonah (CC BY-NC-ND) |
| Licence class | public domain | non-free | non-free |
| The model knows the language | well (`known`) | the standard language better than the dialect (`partial`) | not at all (`unknown`) |
| Agents | draft from their own Danish; the memory keeps decisions consistent | write Bernese, not Standard German: check forms against the corpus | learn Kuni from the corpus while drafting; invent nothing |

## 0. The wizard

`python3 scripts/onboard.py` (or, in Claude Code, "set up a new language": the `new-project` skill asks the same
questions and runs it) walks a new team through the steps below:

1. **AI work:** how the probes run. Through the API when `ANTHROPIC_API_KEY` is set (billed per token; the key is
   read from the environment or from the git-ignored `.env`, and never stored by the scripts), else through Claude Code (`claude -p` with no tools: the
   subscription's usage). Drafting itself always runs in Claude Code, on a subscription or with a key behind it.
2. **The language:** code, dialect id, name (from the catalogue), school language.
3. **The editions** the bcv-commons/bibles catalogue and its sources (helloAO, openbible, eBible) have, with
   licence class and coverage; the user picks.
4. **Import and fetch** into the right licence folder, texts git-ignored; NT basis and quote marks read from the text.
5. **The project:** id and books to draft; a book a non-free edition has is quarantined now, before the probes.
6. **The probes** (write, read, tell apart; about a minute, ~15k tokens): the scores beside their floors, the
   model's slips, one verse beside the edition, and a suggested familiarity with the reason. The user (best: a
   speaker) accepts or overrides it; for `partial` the wizard asks `close_to`.
7. **The tools** the familiarity switches on, with the tokens per chapter logged so far in that mode
   (`scripts/usage.py`); the user confirms.
8. **Set-up:** sources and the Hebrew layout, lexicons, the empty store and wiki, the probe's slips as the first
   store entries (to be checked), `CREDITS.md`, `STATUS.md`.
9. **What comes next:** the memory, the style guide, a reference chapter, then waves, each asked for in Claude Code
   in plain words.

`--answers FILE.yaml` takes the answers from a file (`--yes`: no questions), `--dry-run` shows what it would do;
the answers used are saved as `_onboard_answers.yaml`. An edition that isn't in these sources is brought in with
the `import-edition` skill first, and named to the wizard by its id.

### Editions on the Digital Bible Platform (DBT)

Some languages are only on DBT (the source behind Bible.is), which needs a personal API key (free to register at
https://4.dbt.io). Put it where the scripts find it and git never sees it: a line `DBT_API_KEY=...` in the file `.env`
in the working copy (git-ignored), or the environment variable `DBT_API_KEY`.

The same file can hold `ANTHROPIC_API_KEY=...` for the model through the API (the probes, the priors); the
environment wins when both are set. Other secrets (`NETLIFY_AUTH_TOKEN`) come from the environment only.

`fetch_edition.py --find <iso>` and the wizard then list the language's DBT texts, and fetch them like the other
sources. DBT's texts are licensed for display in apps, so they are filed as non-free: the text stays local, quoted only
within the limits, and any book it has is drafted in quarantine.

## 1. What we ask a team

- **The target language** (ISO 639-3, or a dialect id), the language the team reads (the notes and the wiki
  are written in it), the books they want first.
- **Existing translations** in the language or close to it: where from, under what licence, which books.
  Each one becomes an *edition* in `import/` (the `import-edition` skill).
- **Who reviews** the drafts, and who may publish them.

Nothing else is needed: the drafts are made from the Hebrew and Greek with the BSB, the tools are in the
repository, and the existing translations are a style corpus, not a source.

## 2. The two settings

**Licence class** of each edition, from its folder in `import/` (`import/README.md`):

| Class | Folders | What follows |
|---|---|---|
| public domain | `CC0/` | nothing required; credited as a courtesy (`CREDITS.md`) |
| attributable | `CC-BY/`, `CC-BY-SA/` | its credit line; quarantine only with `quarantine_attributable: true` |
| non-free | `non-free/` (all rights reserved, NC, ND, private use, unclear) | the text stays local; a book it has is drafted in quarantine; quotations short and credited (`docs/licensing.md`) |

**School language** (`school_language`): the team's working language. The wiki, the store's notes and all
analysis are written in it, and the translator notes too unless `notes_language` says otherwise; only
quotations and examples are in the target language. Danish: Danish; Bern German: Standard German; Kuni:
English.

**Familiarity** (`familiarity` in `project.yaml`), measured with three short probes, each a fresh agent with
no tools (`python3 scripts/probe_language.py <project> write|read|tell`, then `--score` its answer): **write**
translates 16 verses into the language, **read** 16 corpus verses into English, **tell apart** picks the
published verse from 24 pairs with one changed word. See *Calibration* below.

| Familiarity | Write probe chrF (read: see Calibration) | Example | The agents |
|---|---|---|---|
| `known` | 65 and up | Danish | draft from their own command of the language; the memory holds the project's decisions |
| `partial` | 30–65 | Bern German (`close_to: Standard German`) | write the variety as the corpus writes it, look up what they are unsure of, never fall back on the standard language |
| `unknown` | below 30 | Kuni | model every word on the corpus, search what the verse pack lacks, record every finding |

The probe's figures for the three pilots are in *Calibration* below. Read the answer as well as the score:
an answer in fluent Standard German for a Bernese probe is what `partial` means.

`python3 scripts/modes.py <project>` prints the resulting mode and what it switches on.

## 3. What the mode switches on

| | known | partial | unknown |
|---|---|---|---|
| Language memory (store `profile/` + `wiki/`) | the project's decisions: terms, formulas, names, style | the variety's grammar and forms, and the decisions | the grammar, the forms, a term base, the gaps |
| Alignment lexicons (`scripts/align.py`) | for corpus lookups | yes | yes |
| Verse pack per chapter (`scripts/verse_pack.py`, level) | `memory`: the decisions that touch each verse | `dialect`: + lexicon renderings and the corpus's phrases | `full`: + similar verses and what still needs a search |
| Rule bundle in the chapter prompt (`docs/prompts/modes.md`) | use and extend the memory | + "the variety, not the standard language"; every checked form ends in the store | + "no knowledge assumed"; every search ends in the store; names by the letter rules |
| Style check against the human translators (`scripts/style.py`) | off | on | on |
| A held-out test book (`learn-language` skill) | no | optional | yes, if the corpus has an OT book |

The licence class adds, independently: quarantine for books a non-free edition has, the quotation rule in
every prompt, `CREDITS.md`, and which generated files stay local (`docs/licensing.md`).

## 4. Steps

1. **Import the editions** (`import-edition` skill): the licence folder, `credit`, and for a working copy
   newer than the published text, `published_text`. The texts are never in git, only `edition.yaml`:
   set `get_text` to how a clone gets the text (a command, or why it isn't available). Fetch what can be fetched
   (`python3 scripts/fetch_edition.py --find <iso>`).
2. **Probe the familiarity** (`scripts/probe_language.py write`, `read`, `tell --write-answer`): set `familiarity`, and
   `close_to` for a variety.
3. **Create the project** (`new-project` skill): `project.yaml` from `export/_template/`, the style guide,
   the divine names; `python3 scripts/modes.py <project>` to check the mode.
4. **Build the memory:**
   - `python3 scripts/align.py <project>` (the lexicons; eflomal if installed). The English and Greek sides take
     seconds (Danish: 17,162 verses in 16 s). The Hebrew side first fetches every OT chapter of the corpus from
     the scaffold API (MACULA lexemes, cached in `download/scaffold/`): about 2 s a chapter (216 in 7.5 min for
     Danish), so a whole OT corpus takes 15–20 minutes the first time, seconds after;
   - `python3 scripts/memory_prompt.py <project> --init` creates the empty store and wiki and prints the prompt for a fresh agent that builds the store
     and the wiki from the corpus, the drafts and the decisions so far, focused by the mode;
   - for `unknown`, follow the `learn-language` skill instead (a test chapter first, a held-out book,
     the curation step);
   - `python3 scripts/wiki.py view <project>` gives the team a page to read it; they correct it in the wiki.
   - for a known or partly known language, `python3 scripts/priors.py write <project>` (the wizard's step after the
     probes) has the model write down what it believes about the language's grammar: word-forming affixes,
     inflection with the grammatical value each marks, function words. `lang.py derive` leaves the word-forming affixes
     out of its hypotheses, and `priors.py check` tests every item against the corpus; for a partial language it shows
     where the standard language or another dialect leaks in (Bern German: the model's *dr*, *wüu*, *u* for "and" are
     absent from Bietenhard, who writes *der*, *wil*, *und*).
5. **Draft**: a reference chapter first, reviewed with the team; then waves (`draft-chapter` skill). Per
   chapter the pack (`verse_pack.py`, level by the mode), for the OT the clause packages (`package.py`: per Hebrew
   clause line the tokens with their numbers, the BSB words, the project's earlier renderings, and for an unknown
   language the NT's words through the LXX bridge) and the prompt (`make_prompt.py`, rules by the mode) are
   generated; the agent writes the draft tagged (`word^n`) and `full_align.py split` makes the draft and its word
   alignment; agents extend the memory as they go.
6. **Check** after every wave: `python3 scripts/check_project.py <project>` (drafts, store, wiki,
   quotations, status). The agents keep to the rules as they write; this is the double check.
7. **Review and publish**: the team reads the drafts and the wiki; `scripts/status.py` marks chapters
   `in-review` and `published` (date, who, statement). Everything is online as drafts from the start,
   marked as drafts (`docs/workflow.md`, *Draft status*).

## 5. What is published

Everything we make is CC0 (CC BY-SA where it builds on share-alike data), for every licence class: drafts,
notes, the store, the wiki's prose, lexicons, statistics. Quotations from non-free editions stay short and
credited; their texts and the generated files that print them (verse packs, alignment links, style
reports) stay local. Where an edition already has a book we draft, `docs/workflow.md` (*When an edition
already has the book*) gives the four cases: continue, test, independent, alongside.

## Calibration

Three probes (`scripts/probe_language.py`), each a fresh agent with no tools; results per project in
`_learn/probe.json` (figures only):

- **write** (production): 16 BSB verses into the language, chrF against the edition;
- **read** (understanding): 16 corpus verses into English, chrF against the BSB, verse by verse. Verses with a
  name are left out: from a name the model recognises the verse in any language and recalls its English (Kuni
  with names: 59; without: 32);
- **tell apart**: 24 pairs of a corpus verse and a copy with one change (the model's own slips from its write
  answer, a word ending, two words swapped); which is the published one? Chance 50%.

| Project | write (pooled / by verse; floor) | read (floor) | tell apart (slips) | Familiarity |
|---|---|---|---|---|
| Danish | 68.4 / 64.4 (21) | 67.0 (20) | 100% (2/2) | `known` |
| Bern German | 56.7 / 48.2 (22) | 57.4 (20) | 100% (5/5: *öich*, *der*, *Söu* …) | `partial` |
| Kuni | 15.2 / 12.0 (27) | 32.4 (22) | 79% (6/7) | `unknown` |

The floor is unrelated text: each verse scored against another one. What the three show:

- **read** separates understanding from none (Kuni barely above the floor), but not Danish from Bern German:
  both are understood, and the read score also depends on how freely the edition translates (Bietenhard
  paraphrases more than Den Frie Bibel).
- **write** is what separates Danish from Bern German; by verse it is the clearer figure (Kuni's invented
  text scores below a random Kuni verse).
- **tell apart** is at the ceiling for both known languages: shown the corpus form beside its own slip, the
  model picks the corpus form every time (*öich*, not *euch*). Bern German's slips are production errors,
  not gaps in knowledge, so a form check against the corpus catches them; the slips themselves are the first
  store entries. Kuni's 79% comes from surface cues (spelling of names, word shapes), not knowledge, so it
  says little; its misses are mostly word order.

Provisional reading of the scores (`probe_language.py`, `suggest`):

- read less than 15 above its floor → `unknown`: the model doesn't understand it (Kuni);
- write by verse less than 10 above its floor → `unknown` for writing, though it may read it: the first run of the
  wizard on a new language, Bodo Parja (helloAO, Odia script), read 70.6 (floor 20) and wrote 22.6 (floor 27): the
  model understands it, likely through a related language it knows (Odia), but can't write it. The wizard then
  asks for that language (`close_to`);
- write by verse 58 and up → `known` (Danish);
- in between → `partial`: understood, written with slips (Bern German).

A fourth and fifth language will move the thresholds.

**Planned, not built:** a language with no corpus of its own (only related varieties, or none). Then neither
read nor tell apart can be scored, and write only by a speaker; the wizard asks the speaker to judge the write
answer, and the related varieties enter as editions of their own kind (`role: related`).
