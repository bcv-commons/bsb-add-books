# The language store

What a drafting agent has to know about a target language, recorded with evidence, so that the next chapter, book and
project start from it. Each project keeps its store in `export/<project>/profile/`. Every entry cites the verses it
was read off. Entries are appended, never silently overwritten. The store is CC0 for any edition, non-free ones
included (`docs/licensing.md`); its quotations are short and credited.

The schema, a Danish example (Den Frie Bibel) and the Grambank recipes are in `docs/language-store/`.

## Files

| file | `partition` | holds |
|---|---|---|
| `observations.json` | `observations` | features, letters, gaps, morphs, cells, claims; the `orthography` and `analysis` settings |
| `decisions.json` | `decisions` | terms, formulas, name forms (target words and short phrases) |
| `external.json` | `external` | optional: entries from a published dataset, never written by an agent |

Each file has `iso`, `edition`, `partition`, `entries`, and may have `licence` and `orthography`. `edition` is the
edition id, or the project id for a project without a published edition. Observations belong to the edition,
decisions to the project. (`priors.yaml` beside them is the model's beliefs about the language, `scripts/priors.py`.)

## Entries

Required in every entry: `id`, `kind`, `value`, `confidence`, `method`, `by`, `date`, `status`.

| field | values |
|---|---|
| `id` | unique among live entries (`speech_frame`, `term:H7458`, `name:naomi`, `m:<form>:<host>`, `c:<paradigm>:<bundle>`, `claim:<name>`) |
| `kind` | `feature`, `letter`, `gap`, `morph`, `cell`, `claim`; `term`, `formula`, `name` |
| `value` | the finding: a string, or a small object for a formula; for terms, formulas and names the target language only |
| `gloss` | terms, formulas, names (and their `alternatives`): the Greek or Hebrew word the value renders (below) |
| `interlinear` | optional, a form built by rule with no source word: a Leipzig line, `1PL.HORT-go` |
| `evidence` | `[{"ref": "BOOK C:V", "form": ..., "n": ...}]`: USFM code, the edition's numbering; `form` the attested word or phrase, `n` a count |
| `confidence` | `high`, `medium`, `low` |
| `method` | `corpus-observed` (read off the edition), `corpus-derived` (a statistic by script, confirmed by an agent), `project-decision`, `external` (needs `external_source`), `team-decision` |
| `by` | `agent:rut001`, a person, a script, or `team:<who>` |
| `date` | `YYYY-MM-DD` |
| `status` | `observed`, `decided`, `open`, `superseded` |
| `supersedes` | optional: the id of an existing entry this one replaces |
| `codes` | optional, features: `GBnnn` or `WALS:nnX` |
| `note` | why, alternatives rejected, what to check |
| `words` | optional: the BSB words the entry answers (`["sandal"]`), for the verse packs; on a `gap`, a search found no model |
| `source` | required for terms, formulas, names: `H7458`, `G2316`, a phrase or a name |
| `attested` | required for terms, formulas, names: `attested` (occurs in a cited verse) or `by-rule` (built by analogy; the verses hold the models) |

Rules:

- `feature`, `term`, `formula`, `name` and `morph` need evidence.
- Absent means not looked at; `open` means looked at and not settled.
- To change an entry, add one with `supersedes`.
- **Team decisions** (`method: team-decision`, `by: team:<who>`, `team_source: wiki/team-input.md#T3`) need no
  evidence and are binding: an entry by anyone else that supersedes one, or reuses its id, is an error.
  `scripts/team_input.py` turns the team's plain-language items into such entries.

## Kinds

- **`feature`**: a grammatical or orthographic regularity; `pattern` (optional) a schematic form,
  `"<speaker> sagde: <quote>"`. Recommended ids: `constituent_order`, `adposition`, `possessor`, `article`,
  `case_marking`, `negation`, `prohibitive`, `narrative_tense`, `speech_frame`, `quotation_marks`,
  `connective_sequence`, `relative_clause`, `conditional`, `vocative`, `numerals`, `pronouns`, `plural`, `tone_marks`.
  A Grambank feature: id `gb:GBnnn`, `codes: [GBnnn]`, value starting with its value (`1 (present): ...`); never a 0
  for "not found".
- **`letter`**: one correspondence of the name-transliteration table (`"j → z"`), with the names it was read off.
- **`gap`**: something the corpus has no model for, with the source verse and the solution adopted, if any. It may
  cite a verse the edition doesn't have.
- **`term`**, **`formula`**, **`name`**: a source lexeme, phrase or name → the target form. A `by-rule` name cites
  the letter entries' names; `by-rule` entries are for a speaker's review.

### Glosses

A term, formula or name says what its target form means with a `gloss` in Greek or Hebrew, never in English: the
bridge between an NT translated from the Greek and the Hebrew OT being drafted.

```json
"gloss": [
  {"lang": "hbo", "form": "נֵלְכָ֖ה", "lemma": "הָלַךְ", "ref": "GEN 37:17"},
  {"lang": "grc", "form": "Ἄγωμεν", "lemma": "ἄγω", "ref": "MRK 1:38"}
]
```

- `lang`: `grc`, `hbo`, or `arc` (Aramaic). `form`: the word or phrase as the verse `ref` writes it. `lemma`: as
  `orig/grc.sqlite` or `orig/heb.sqlite` writes it (for Hebrew the consonants are enough).
- Greek from an NT verse (the project's Greek text, BGB or RP, or MACULA's); Hebrew and Aramaic from the WLC (MACULA
  Hebrew), never BHSA: a form with accents is the WLC word as written; one may leave out the accents, or all marks.
- Order: Hebrew first in a decision about the OT drafts; otherwise the language of the evidence first.
- `"proposed": true`: proposed by `scripts/gloss.py propose`, to be checked by an agent or the team.
- English is for people and generated, never stored: the wiki, `concord.py store` and `gloss.py show` add the BSB
  words aligned to the gloss's form in its verse (the `bsb` tables), labelled *English (generated)*. Notes stay
  English.
- The verse packs match entries by gloss: a Hebrew gloss by the lemmas of the verse drafted, a confirmed Greek gloss
  also through the LXX (`orig/heb.sqlite` `lxx`: the Greek words that usually render the verse's Hebrew words).
- `morph`, `cell` and `claim` entries keep their Leipzig glosses (2.SG, NEG.IND).

### Morphs

| field | values |
|---|---|
| `form` | required: as written, hyphen on the attaching side (`ka-`, `-a`, `=te`); a tone morph's form is a name (`tone-proh`) |
| `slot` | required: `prefix`, `suffix`, `infix`, `clitic`, `free`, `tone` |
| `host` | required: `verb`, `noun`, `pron`, `any` |
| `value`, `unimorph` | the Leipzig gloss (`2.PL`); optionally the UniMorph tags |
| `position` | optional: the place in an affix chain (prefixes from the word's start, suffixes from the stem outward); one form can hold two (subject *mu-* at 2, object *mu-* at 4) |
| `greek` | optional: the Greek feature it marks, as `lang.py report` names them (`{"person+number": "fp"}`; a list for several values) |
| `tone_pattern` | a grammatical tone morph's marks by position from the word's end: `[{"at": "-2", "mark": "U+0300"}, {"at": "-1", "mark": "U+1DC4"}]`; `"<-1"` any unit before the last |
| `productive` | from `morphs.py try`: `true` where the affix, taken off every word, still marks its Greek feature (confirmed, with at least half its odds ratio) (its words split without a stem attested elsewhere); `false` where it doesn't |
| `stats` | from scripts: `count`, `hosts`, `lift`, `test_lift`, `odds`, `test_odds`; `productive_count`, `productive_hosts`, `productive_odds`, `productive_test_odds` |

The form must occur on its side of a word in at least one cited verse (tone morphs are not matched). Only a tone morph
with a `tone_pattern` is grammatical and taken out of the word; other tone is lexical and stays in the stem.

### Cells

| field | values |
|---|---|
| `paradigm`, `bundle` | required: `verb.subject`, `verb.polarity`, `poss.pronoun` (`scripts/source_cells.py`); the tags, `3.SG.IND` |
| `value` | the pattern (`z…-ap`; `Ø` for no mark; a form without hyphens is a separate word) |
| `morphs` | the morph ids that build it (each a morph entry) |
| `alternatives` | other forms with counts (a tone morph's form: the cell is marked by tone); `method: tested` on those a test added |
| `stats`, `gap` | `count`, `share` of the bundle's tokens; `gap: true` when the corpus has no case (no evidence needed) |

### Claims

| field | values |
|---|---|
| `value`, `area`, `source` | the claim; what it is about; where it came from (wiki, analysis, grammar sketch, team) |
| `tests` | any of `corpus`, `greek`, `hebrew`, `nllb`, `team` |
| `verdict` | required: `confirmed`, `corpus-only`, `contradicted`, `new`, `open` |
| `figures`, `next` | the results in short; what to do next |
| `rerun`, `rerun_method` | for a script's test: the command (`["cell_check.py", "try", paradigm, bundle, form]`) and the method's version |
| `basis`, `basis_corpus` | a fingerprint of what the result depends on (the settings, every live morph, the cell's value) and the style corpus |

## Settings

Top-level fields of `observations.json`. A change makes the tests that depended on it stale: `grammar.py retest
<project>` lists them, `--run` reruns them.

- **`orthography.ignore_marks`**: combining marks (`"U+0301"`) that search, alignment and the validator's matching
  ignore. Checks of the store's own spellings keep every mark.
- **`orthography.tone`**: `{"written": "marks" | "digits" | "letters" | "none", "marks": [...], "vowels": "...",
  "absent": "unknown" | "neutral"}`. With `digits` (Jyutping *si1*) the syllable is the unit; `letters` and `none`
  give no tone morphs; `absent: neutral` makes an unmarked vowel a tone of its own. `morphs.py tone --write` detects
  and stores it (kept unless `--force`).
- **`analysis.match`**: `strings` (default: affixes matched at a word's edges) or `morphs` (on the morph view).
- **`analysis.align`**: `parts+fill` (the default once the store has confirmed affixes), `parts` or `words` (the
  default without them): `align.py` aligns the target as the words' parts (an affix by its store form, the stem, a
  grammatical tone by its label) and maps each link back to its word; `+fill` adds a word link where neither its source
  nor its target word got one by parts. It also writes `lexicon_<side>_parts.tsv`, the source words each affix links
  to. Rerun `lang.py build` after it.
- **`analysis.model_text`**: `words` (default) or `morphs`: the second-draft model's target as words or parts
  (`be+`, `+gu`, `~PROH` for grammatical tone, `~H1` for lexical tone; `scripts/nllb/model_text.py`).
  `analysis.model_join` and `analysis.model_tone` change the signs `+` and `~`.

## The morph view

`scripts/morphs.py` splits each word into prefix, stem, grammatical tone and suffix, from the store's morphs.

- Without `position` in the store: one affix of each slot, longest first, word-class blind, only where what remains
  is attested.
- **Affix chains** (with `position`): several affixes, each position once, in order (*tu-ka-mu-bon-a*). An affix
  comes off only where another form of the stem lacks those letters; the parse with most letters in fewest pieces
  wins.
- **Host view**: with the NT aligned to the Greek (`lang.py build`), a verb's affixes come off words linked to Greek
  verbs in at least half their tokens, or that leave such a word's stem; nouns keep their class prefixes.
- **Tone-marked affixes**: an affix told apart by tone alone keeps its mark (*aá-* past beside *aa-*): the parse runs
  on plain letters, the label follows the mark as written.
- **`try [id ...] [--write]`**: each affix measured on the NT aligned to the Greek (n, stems, lift and odds ratio of
  its `greek` feature, on all verses and even verses). Kept: n ≥ 20, stems ≥ 5, both odds ratios ≥ 2. `--write` sets
  `stats`, status `observed` or `open` (`decided` stays), and a claim `claim:morph.<id>`.
- **The loop**: `rates` lists the features the confirmed affixes mark; one is checked where the human NT marks it on
  60% or more of 20 or more Greek verbs that have it. `review <code> <ch>` (run by `chapter_check.py`) flags OT verbs
  whose draft word lacks the part for the Hebrew verb's person and number, negation, object or mood.
- `check` rebuilds every corpus token from its parts; `show <word>` shows one.

## The validator

`python3 scripts/language_profile.py check <profile dir> [--text-dir DIR | --project ID]` checks:

1. required fields, kinds, enums, reference and date formats, codes;
2. every reference resolves to a verse of the edition (with `--project`, also of the project's drafts);
3. every `attested` term, formula and name occurs in a cited verse (case, `ignore_marks` and `<slots>` ignored);
4. live ids are unique; `supersedes` points to an existing entry;
5. morph, cell and claim fields as above; team decisions as above;
5a. glosses: `lang`, script, the lemma in the source database, the form in its verse (the WLC for Hebrew); English in
   a term's or formula's value (in brackets, or with `--project` words of the BSB the corpus never writes) is a
   warning, and left out of the value's checks and of the attested forms (`langtools.store_forms`);
6. with `--project`, for a non-free style edition: an evidence `form` is at most 4 words; a `note`, `pattern` or
   `value` quotes at most 15 words, from the published text, as written;
7. reported only: agreement with lexeme-aligner's `gram-struct` (`download/lexeme-aligner/grammar/gs_<iso>.json`).

It also lists value words the edition writes only with other marks.

## Commands

| command | does |
|---|---|
| `memory_prompt.py <project> [--init]` | the prompt for the agent that builds store and wiki; `--init` creates an empty store |
| `grammar.py status\|plan\|show` | what the store holds; what to settle next |
| `grammar.py run --write` | writes `gb:GBnnn` features the store's morphs answer (`grambank_recipes.tsv`, `from_store: yes`): by tag or `greek`; S and A indexing (GB089-GB092) measured on the NT's intransitive and transitive clauses; the chain's order in the note; `plan` lists the rest |
| `grammar.py from-tsv` | writes morphs, cells, claims from a working store's TSV files (other entries kept) |
| `morphs.py try --write`, `tone --write` | affix stats and claims; `orthography.tone` |
| `cell_check.py try --write` | kept forms as cell alternatives; a claim per form tried |
| `team_input.py prompt` | the curation agent's prompt for new team items |
| `verse_pack.py` | reads the store into the per-verse pack (team decisions first) |
| `gloss.py propose [--write]` | glosses for entries without one, from the alignment lexicons and the entry's source; English in a value to its note |
| `gloss.py check\|show\|words` | the store's glosses checked; an entry's glosses with the generated English; a verse's words and lemmas |
| `wiki.py sync\|lint` | the wiki's generated store blocks; links and quotations |

`grambank_recipes.tsv` columns: `gb_id`, `method`, `inputs`, `test`, `decide`, `relevance`, `from_store`, `note`.

## The wiki

The project's `wiki/` holds what entries can't: how a construction works, the best models, what was tried.

- A page names its entries in its frontmatter (`entries: [possessor, term:*]`); `wiki.py sync` writes them into a
  generated block (`store:begin` / `store:end`). Unclaimed entries go to `inbox.md`; `log.md` records changes.
- Facts change in the store. A reader who doesn't edit JSON writes `> **Correction (name, date):** …` on the page or
  an item on `wiki/team-input.md`.
- The prose is CC0; quotations follow `docs/licensing.md`.
