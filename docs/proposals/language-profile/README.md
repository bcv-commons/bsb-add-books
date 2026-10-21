---
license: cc0-1.0
license_name: CC0-1.0 (quotations credited to their editions)
pretty_name: Language profiles for Bible translation
tags:
  - bible
  - translation
  - typology
  - multilingual
  - grammar
---

# Language profiles for Bible translation

What an agent (or a translator) has to know about a language before drafting a
chapter in it, **recorded with evidence** so that the next chapter, the next book
and the next project start from it instead of rediscovering it.

One profile per language and edition. Every entry carries the verses it was read
off, a confidence, who recorded it and when. Entries are written by drafting
agents, checked by a validator, and never silently overwritten: a later entry
supersedes an earlier one and says so.

> **Status: proposal** from bcv-commons/bsb-add-books, after its first drafting
> experiment in a language with no LLM exposure.
> Proposed as a sibling of lexeme-aligner's `gram-struct`, `target-morphology`
> and `lexeme-alignments`, which it builds on and cross-checks.

## What it adds to what exists

| dataset | layer | example for Jamaican |
|---|---|---|
| `gram-struct` (lexeme-aligner) | typological slots from Grambank, WALS and alignment statistics | SVO; prepositions; no case on nouns or pronouns |
| `target-morphology` | unsupervised affix inventories and stems | word-forming `-nis`, `-ful`, `-li`; no verb endings |
| `lexeme-alignments` | surface forms per Strong's number, with counts | `grc:2316` → gad |
| **language profile** (this) | **usage-level, evidenced knowledge for drafting**: how speech is framed, which verb form carries narrative, what `-te` and `-qa` mark, which rendering to use for "famine" and why, how names are transliterated, what the corpus doesn't have | "direct speech: `āv gene-eín nqǽgo:` then the quote, 2,051× in the NT"; "YHWH → Evezøza, as the NT's κύριος for God"; "glean: no NT model, built from *gather* + *grain*, open" |

`gram-struct`'s own README lists what alignments can't tell: that is where a
profile starts. Where both say something about the same feature (word order,
adpositions, articles), the profile cites the Grambank/WALS code and the validator
reports agreement with `gram-struct`.

## Layout

```
profiles/<iso>/<edition>/
  observations.json     grammar features, letter correspondences, gaps  (CC0)
  decisions.json        terms, formulas, name forms                      (CC0: single words and short phrases)
  external.json         seeded from gram-struct, target-morphology …     (their licences, cited per entry)
  <edition>.json        merged view of the three                         (mixed)
```

The files differ by what they hold, not by licence; both are CC0 for any edition, including
non-free ones (bsb-add-books `docs/licensing.md`):

- **`observations.json`**: feature values, verse references, counts, letter correspondences, gap
  descriptions.
- **`decisions.json`**: target-language words and short phrases (the term base, the formulas, the
  name forms), each with references. Words and short phrases are not protected; a longer quotation
  in a note follows the quotation rules (short, unchanged, from the published text, credited).
- **`external.json`** is seeded by a script from the published datasets and cites
  each source and code; it is never written by an agent.

`<edition>` is the edition id as in bcv-commons/bibles or lexeme-aligner
(`dan_dfb`); a draft project that has no published edition uses its
project id (`jam_BSB`).

## The entry contract

Every entry, whatever its kind:

| field | meaning |
|---|---|
| `id` | stable within the profile (`speech_frame`, `term:H7458`, `name:naomi`) |
| `kind` | `feature`, `letter`, `gap`, `morph`, `cell`, `claim` (observations); `term`, `formula`, `name` (decisions) |
| `value` | the finding (a string, or a small object for formulas) |
| `evidence` | verse references in the edition, `"BOOK C:V"` (USFM code, the edition's numbering), each with an optional count `n` of occurrences in the corpus; at least one for `feature`, `term`, `formula`, `name` |
| `confidence` | `high`, `medium`, `low` |
| `method` | `corpus-observed` (read off the edition), `corpus-derived` (a statistic computed by script from the edition aligned to the source, confirmed against the corpus by an agent; the figure in `note`), `project-decision` (chosen for drafting among alternatives), `external` (from a published dataset), `team-decision` (the language team said so: `by: team:<who>`, `team_source` names the item on the wiki's team-input page, no verse evidence needed; binding: no later entry by anyone else may replace it; `scripts/team_input.py`) |
| `by` | who recorded it: a drafting run (`agent:rut001`), a person, or a script |
| `date` | ISO date |
| `status` | `observed`, `decided`, `open`, `superseded` |
| `supersedes` | the id of the entry this one replaces (optional) |
| `codes` | Grambank (`GB074`) or WALS (`WALS:85A`) codes the feature corresponds to (optional, `feature` only) |
| `note` | free text: why, alternatives rejected, what to check |
| `words` | optional: the assisting translation's words the entry answers (`["sandal"]`), so a verse pack matches it and no later chapter searches the word again; a `gap` with `words` records that a search found no model |

Rules:

- **No entry without evidence.** A `feature`, `term`, `formula` or `name` must cite
  verses; the validator resolves every reference and, for decisions, checks that
  the quoted form occurs in the cited verse.
- **Absent means unknown.** A feature not in the profile has not been looked at.
  A feature with `status: open` has been looked at and not settled.
- **Append, don't overwrite.** An agent adds entries; to change one it adds a new
  entry with `supersedes`. The merged view shows the latest.
- **Decisions are per project**, observations per edition: the term base of a
  Danish project continuing Den Frie Bibel may differ from another project's. The
  file says which project decided (`by`).

### Kinds

- **`feature`**: a grammatical or orthographic regularity. `value` is a short
  statement; `pattern` (optional) a schematic form with slots in angle brackets,
  e.g. `"<speaker> <addressee>-te āv gene-eín nqǽgo: <quote>"`. Recommended ids,
  so that profiles can be compared across languages: `constituent_order`,
  `adposition`, `possessor`, `article`, `case_marking`, `negation`, `prohibitive`,
  `narrative_tense`, `speech_frame`, `quotation_marks`, `connective_sequence`
  ("and then"), `relative_clause`, `conditional`, `vocative`, `numerals`,
  `pronouns`, `plural`, `tone_marks`.
  A Grambank feature has the id `gb:GBnnn` and `codes: [GBnnn]`; its value starts with the Grambank code (`1
  (present): qo-, ge-`). `grambank_recipes.tsv` (beside this file) says for each feature a Bible corpus can decide how
  it is decided (method, inputs, test, rule, relevance for drafting); `scripts/grammar.py run` writes those the store's
  own morphs answer, `grammar.py plan` lists the rest. Only features with evidence get an entry, never a 0 for "not
  found".
- **`letter`**: one correspondence of the name-transliteration table, from the
  source language's letter or sound to the edition's, with the names it was read
  off (`"j → z"`, evidence `Zuda`, `Zelusalem`).
- **`gap`**: a concept, word or construction the corpus has no model for, with the
  source verse that needs it, the solution adopted (if any) and `status`.
- **`term`**: a source lexeme (Strong's number or a gloss) → the rendering to use,
  with alternatives and counts. `source` is `H7458` / `G2316` / a gloss.
- **`formula`**: a recurring source phrase → the target phrase, with slots.
  `source` is the Hebrew/Greek or the BSB wording.
- **`name`**: a proper name → the form used, `attested` (in the edition, with
  evidence) or `by-rule` (built from the letter table; evidence then cites the
  letter entries).

- **`morph`**: a grammatical morph. `value` is its Leipzig gloss (`2.PL`, `NEG.IND`); `form` the morph as written,
  with a hyphen on the side it attaches (`ge-`, `-eav`, `-zø-`, `=te`); `slot` one of `prefix`, `suffix`, `infix`,
  `clitic`, `free`, `tone` (a tone pattern: `form` is then a name, `tone-proh`, and `tone` describes the pattern; a
  grammatical one also has `tone_pattern`, the marks by position from the word's end, `[{"at": "-2", "mark": "U+0300"},
  {"at": "-1", "mark": "U+1DC4"}]`, `"<-1"` any unit before the last: only such a morph is taken out of a word into its own
  morph, `scripts/morphs.py`; tone without one is lexical, part of the word);
  `host` the word class (`verb`, `noun`, `pron`, `any`); `unimorph` the same gloss in UniMorph tags; `stats` the
  figures a script computed (`count`, `hosts`, `lift`, `test_lift` on held-out books; `odds`, `test_odds` from
  `morphs.py try`); evidence verses where it occurs (the validator finds the form on its side of a word in at least
  one). Id `m:<form>:<host>[.<use>]`. Two fields for affix chains (several affixes per word, as in a Bantu verb,
  ni-tu-ka-mu-sohoz-a): `position`, the affix's place in its chain (prefixes counted from the word's start, suffixes
  from the stem outward; each position once per word, so one form can hold two, subject *mu-* at 2 and object *mu-*
  at 4), and `greek`, the Greek feature it marks, named as `lang.py report` names them (`{"person+number": "fp"}`;
  a list for several values). With any `position` in the store the morph view takes the chains off (`scripts/morphs.py`),
  by host where the NT is aligned to the Greek: a verb's affixes only off words linked to Greek verbs in at least half
  their tokens, or that leave such a word's stem; without `position`, one affix of each slot, word-class blind, as
  before. A chain affix told apart from another by tone alone is written with its mark (`aá-` past beside `aa-`): the
  view finds it on the plain letters and labels it by the mark as written. `python3 scripts/morphs.py <project> try [id ...] --write` measures the
  entries on the NT aligned to the Greek: n, stems, lift and odds ratio of the `greek` feature (all verses, even
  verses); kept: n ≥ 20, stems ≥ 5, both odds ≥ 2; it writes the stats, status `observed` or `open`, and a claim
  `claim:morph.<id>` with its rerun recipe and basis. Two parses that take off the same letters in the same number of
  pieces are told apart by the marks: the one whose affixes are written as store forms wins (*b-aá-zeend-a*, not
  *ba-á-zeend-a*).
  The drafting agents use the view: the verse pack lists the affixes and a rendering's parts, the concordance a stem's
  forms (`concord.py parts|stem|morph`), the spelling check accepts a form built from known parts, and the loop
  (`chapter_check.py`, `morphs.py review`) reviews a Hebrew verb whose word lacks the affix for its subject, object,
  negation or mood. The Hebrew verb gets the Greek feature names (person and number; a negation or an object pronoun in
  its clause; imperative, jussive and cohortative as subjunctive, infinitive, participle; wayyiqtol as an aorist
  indicative), and only words with a verb prefix count. A feature is checked where the human NT carries it on 60% or
  more of 20 or more Greek verbs that have it (`morphs.py rates`).
- **`cell`**: a paradigm cell, the form that fills one bundle of grammatical values. `paradigm` as the source-to-cell
  table names it (`verb.subject`, `verb.polarity`, `poss.pronoun`: `scripts/source_cells.py`), `bundle` its tags
  (`3.SG.IND`), `value` the form pattern (`z…-ap`, `Ø` for no mark; a form without hyphens is a separate word that marks the
  cell, a particle or auxiliary), `morphs` the morph ids that build it,
  `alternatives` other forms with counts (a tone morph's form, `tone-proh`, as one of them: the cell is marked by that tone;
  `method: tested` on those a test added), `stats` (`count`, `share` of the bundle's tokens), `gap: true` when the
  corpus has no case (then no evidence). Id `c:<paradigm>:<bundle>`.
- **`claim`**: a statement about the grammar (from the wiki, an analysis, a grammar sketch or the team) and how it
  was tested: `value` the claim, `area`, `source`, `tests` (`corpus`, `greek`, `hebrew`, `nllb`, `team`), `figures`
  (the results in short), `verdict` (`confirmed`, `corpus-only`, `contradicted`, `new`, `open`), `next`. Evidence
  optional. Id `claim:<name>`. A claim a script tested carries `rerun` (the command, `["cell_check.py", "try", paradigm,
  bundle, form]`), `rerun_method` and `basis` (a fingerprint of the store settings the result depends on, with
  `basis_corpus`): when the store learns something later, `scripts/grammar.py retest <project> --run` reruns it.

Profile-level settings that the tools read beside the entries:
- `orthography.ignore_marks`: marks the search and alignment tools ignore (a word's tonal variants are one form there);
  checks of the store's forms keep every mark.
- `orthography.tone`: how the language writes tone, `{"written": "marks" | "digits" | "letters" | "none", "marks": [...],
  "vowels": "...", "absent": "unknown" | "neutral"}` (digits: Jyutping *si1*; letters: Gwoyeu Romatzyh; none: characters or
  everyday Pinyin; `absent: neutral` where a missing mark is a tone of its own). `scripts/morphs.py <project> tone`
  detects it from the corpus: the tone marks are the layer of marks that never share a letter (a two-layer orthography's
  other layer, Vietnamese â ă ơ, Yoruba's dot below, is the vowel quality), spread over the vowels, and telling words apart
  (twins: ambá and amba); an orthography that marks one tone only (a high tone with the acute, the other unmarked) is
  told from a stress accent by the mark standing twice in a word, which a stress accent never does; `--write` stores
  it with `derived` (the figures). Checked on thirteen corpora: four found with their marks (a Papuan language,
  Vietnamese, Yoruba and Zinza, whose acute is high tone), none for French, Spanish, Danish, Jamaican Creole and five
  Bantu languages that don't write tone (Lingala, Kuhane, Kutu, Mwera, Yao).
- `analysis.match`: `strings` (default: a cell's affixes are matched at a word's edges) or `morphs` (on the morph view:
  prefix, stem, grammatical tone, suffix; `scripts/morphs.py`). Chosen by measurement (`cell_check.py`'s lifts on the
  human text), and like every setting, a change makes the tests that depended on it stale.
- `analysis.model_text`: `words` (default) or `morphs`: the second-draft model's target text
  (`scripts/nllb/model_text.py`) as written, or each word as its parts: a prefix ending in the joiner (`be+`), a suffix
  starting with it (`+gu`), the grammatical tone as one token after the stem (`~PROH`), lexical tone as a code after its
  part (`~H1`: an acute on the part's last tone-bearing unit). The decoder rebuilds the words exactly; names stay whole.
  `analysis.model_join` and `analysis.model_tone` change the two signs (`+`, `~`) for a corpus that uses them. Data and
  models record the store basis they were built on; `grammar.py retest` lists them when it has changed.

`scripts/grammar.py` reads the three kinds for the tools (`grammar.load(project)`: morphs, affixes by host and slot,
cells by paradigm) and writes them from a working store's TSV files (`from-tsv`).

`term`, `formula` and `name` carry `attested`: `attested` means the value occurs
as such in a cited verse (the validator checks it); `by-rule` means it was built
by analogy from the cited verses (a prefix swapped, a frame filled, a name
transliterated) and the cited verses hold the models, not the form. A `by-rule`
entry is a candidate for a speaker's review; the chapter notes say what was built.

A `feature`'s `pattern` may quote the function words of a frame
(`"<speaker> āv gene-eín nqǽgo, “<quote>”"`). Such patterns are short quotations:
unchanged, from the published text, credited.

## The validator

`python3 scripts/language_profile.py check profiles/<iso>/<edition>/` checks:

1. the schema (`schema/language_profile.schema.json`);
2. every reference resolves to a verse of the edition;
3. every `term`, `formula` and `name` value occurs in at least one cited verse
   (tone marks and case ignored where the profile says so);
4. `supersedes` points to an existing entry; no two live entries share an id;
5. `codes` match the Grambank/WALS pattern;
6. **agreement with `gram-struct`** where the profile's feature ids map to its
   slots (`constituent_order`, `adposition`, `possessor`, `article`): reported,
   not enforced.

## How drafting agents use it

- **Before the first chapter of a language:** `scripts/language_profile.py seed`
  writes `external.json` from `gram-struct`, `target-morphology` and
  `target-stopwords`, so the agent verifies rather than discovers. (For a held-out
  test, seed only from sources that didn't see the test chapters.)
- **Before every chapter:** read the merged view; use the terms, formulas and
  name forms as they stand; treat `open` entries as questions to settle.
- **After every chapter:** append what was learned, with evidence, and run the
  validator. The chapter's own notes keep the per-verse models and exegesis; the
  profile keeps only what carries over.

In bsb-add-books this replaces the prose "learning notes" of a language the model doesn't know
and extends the style guides of the other projects; `project.yaml` points the
chapter prompt at the profile.

## Publishing

Proposed as `bcv-commons/language-profiles` on Hugging Face, one folder per
language and edition, `observations.json` for every language (CC0) and
`decisions.json` for every language too (single words and short phrases, with references).
Quotations in notes and patterns carry the edition's credit line. First candidates: Danish
(Den Frie Bibel, public domain) and Jamaican (credit: Bible Society of the West Indies).

## Open questions

- Whether `gram-struct` should import the `feature` entries that carry codes as a
  new partition (`observed/`, CC0), closing the loop.
- A shared id list for features beyond the recommended ones, so that profiles of
  unrelated languages stay comparable.
- Tone and other diacritics: `orthography.ignore_marks` is the profile-level switch for finding; `orthography.tone`
  and the tone morphs' `tone_pattern` say what the marks mean (above).

## The wiki: explanations next to the store

The store records checked facts; a project's `wiki/` (Markdown) holds what entries can't: how a
construction works, which NT models are best, what was tried and rejected, open questions. Agents and
people both edit it. Each page names its store entries in its frontmatter (`entries: [possessor,
term:*]`), and `scripts/wiki.py sync <project>` writes them into a generated block at the end of the
page (marked `store:begin` / `store:end`, with a checksum); prose outside the block is the editors'.
Entries no page claims go to `inbox.md`; `log.md` records changes; `lint` checks links, page ids
and hand edits inside the generated blocks. A fact is changed in the store (an entry with
`supersedes`); a person who doesn't edit JSON writes `> **Correction (name, date):** …` on the page,
and the next agent carries it into the store. The wiki's prose is CC0; its quotations from the edition follow
`docs/licensing.md` in bsb-add-books (short, unchanged, from the published text, credited), and
`wiki.py lint` checks them, so a wiki can be published for a non-free edition too.

