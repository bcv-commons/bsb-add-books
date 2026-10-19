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
> experiment in a language with no LLM exposure (Kuni, `kvg`, Papua New Guinea).
> Proposed as a sibling of lexeme-aligner's `gram-struct`, `target-morphology`
> and `lexeme-alignments`, which it builds on and cross-checks.

## What it adds to what exists

| dataset | layer | example for Kuni |
|---|---|---|
| `gram-struct` (lexeme-aligner) | typological slots from Grambank, WALS and alignment statistics | postpositions; verb-final; possessor before the noun; no bound article |
| `target-morphology` | unsupervised affix inventories and stems | suffixes `-am`, `-át`, `-ɨn`; prefixes `vø-`, `ndø-`, `ge-` |
| `lexeme-alignments` | surface forms per Strong's number, with counts | `grc:2316` → mbumbukiam 1207 |
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
(`dan_dfb`, `kvg_wbt`); a draft project that has no published edition uses its
project id (`kvg_BSB`).

## The entry contract

Every entry, whatever its kind:

| field | meaning |
|---|---|
| `id` | stable within the profile (`speech_frame`, `term:H7458`, `name:naomi`) |
| `kind` | `feature`, `letter`, `gap` (observations); `term`, `formula`, `name` (decisions) |
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

In bsb-add-books this replaces the prose "learning notes" of the first Kuni run
and extends the style guides of the other projects; `project.yaml` points the
chapter prompt at the profile.

## Publishing

Proposed as `bcv-commons/language-profiles` on Hugging Face, one folder per
language and edition, `observations.json` for every language (CC0) and
`decisions.json` for every language too (single words and short phrases, with references).
Quotations in notes and patterns carry the edition's credit line. First candidates: Danish
(Den Frie Bibel, public domain) and Kuni (both partitions, credit: Wycliffe Switzerland).

## Open questions

- Whether `gram-struct` should import the `feature` entries that carry codes as a
  new partition (`observed/`, CC0), closing the loop.
- A shared id list for features beyond the recommended ones, so that profiles of
  unrelated languages stay comparable.
- Tone and other diacritics: whether the validator's "ignore tone marks" switch
  should be a profile-level declaration (`orthography.ignore_marks`).

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

