# Clause overlay: roles and formats

**Status:** proposal, 2026-10-12. Written in bsb-add-books, for discussion with
bcv-commons (bcv-query, lexeme-aligner).

## Goal

A Bible app shows a translation either as **running prose** or, at the press of
a button, as **clause lines**: one line per clause of the Hebrew original,
indented by the clause's level in the text hierarchy. The reader then sees which
clause depends on which, for example:
- a speech under the narrative that introduces it;
- a circumstantial clause under its main line;
- a relative or conditional clause under its main clause.

Example, Ruth 1,1 (the BSB's words on the pilot's clause lines):

```
In the days
    when the judges ruled,
  there was a famine in the land.
  And a man from Bethlehem in Judah went
          to reside in the land of Moab,
        he and his wife and his two sons.
```

Three decisions shape the design:

1. **The translation text is not changed.** The clause information lives in a
   separate JSON file per edition and book (a *sidecar*), like the alignments in
   `bcv-commons/compact-alignments`. A client that ignores it shows prose as before.
2. **The source side and the edition side are separate.** Which clauses the Hebrew
   has, and how deep each sits, is published once per book. An edition's sidecar
   only says which of its words belong to which Hebrew clause.
3. **The clause lines are guidance, not a law.** A translation may merge two
   Hebrew clauses into one line, or move words between clauses within a verse,
   where its language requires it. The format records this; it does not forbid it.

## Roles

| | bcv-query | lexeme-aligner | bsb-add-books |
|---|---|---|---|
| **Delivers** | the source side: clause segments and their levels for every Hebrew verse | edition sidecars for every aligned edition, derived from the alignments | new translations drafted along the clause lines, with exact sidecars |
| **Needs** | MACULA Hebrew, UHB, a rule for the text-level hierarchy | the source side from bcv-query, its alignments and function-word index | the source side from bcv-query (BHSA privately until then) |
| **Publishes** | `hebrew-clause-layout` and the clause index | `<BOOK>_<hash>.clauses.json` | sidecars for its own drafts |
| **Licence** | CC BY-SA 4.0 (from MACULA CC BY 4.0, UHB CC BY-SA 4.0) | CC0 (integers only, no text) | its own; sidecars CC0 |

### bcv-query: the source side

- Build clause segments from MACULA Hebrew over the UHB text. The detailed card is in `../hebrew-clause-layout/`.
- **Derive the text-level hierarchy** (`discourse_parent`, `text_depth`). MACULA itself has no structure above the verse:
  - a MACULA sentence is one verse;
  - main clauses inside a verse stand side by side.

  The hierarchy therefore has to be derived. The ingredients are in MACULA:
  - verb forms (wayyiqtol, weqatal, …);
  - conjunctions and subordinators in the tokens;
  - infinitive and participle clauses;
  - participant references (`subjref`).

  A first rule set is in the clause-layout card.
- **If the derivation turns out not to be feasible**, ask how the ETCBC derives its
  `tab` feature (from its clause relations `mother` / `code`). Reimplementing a
  documented *rule* on MACULA data is fine. Copying BHSA *values* is not: BHSA is
  CC BY-NC 4.0.
- **Freeze the segmentation and stamp it** before anything else builds on it
  (see `_source.json` below). Every edition sidecar refers to segment numbers, so a
  change of segmentation invalidates them. A change of levels does not.

### lexeme-aligner: sidecars for existing editions

Once the source index exists, a sidecar can be derived for every edition from its alignments:

1. Each aligned target token inherits the segment of its source token, through the
   MACULA keys in `_index/<BOOK>_keys.json` and the segment keys in
   `_index/<BOOK>_clause_keys.json`.
2. Unaligned target tokens join the segment of their neighbour. A token that
   renders a clause-opening function word (ו, כִּי, אֲשֶׁר, אִם, the function-word
   index `_fn.json`) starts the segment of that word.
3. A segment whose tokens are not contiguous gets a scattered span; a segment with
   no tokens of its own is written as merged (`=`).

Expected quality:
- **Highest** for editions with a hand-made full alignment (BSB tables, Clear,
  HELFI, Door43): these come first and serve as reference.
- **Good** where statistical alignment is good (English, Hindi in the published
  measurements).
- **Weaker** for languages with a very different word order (verb-final languages,
  relative clauses before the noun). There, scattered segments and merges are the
  normal case, not an error.

A `method` / `conf` channel (below) lets a client decide per edition whether to
offer the toggle.

### bsb-add-books: new translations along the clause lines

- During drafting the agents see the Hebrew clause segments with their levels and
  write the translation with **inline markers** (authoring format below).
- **Rule for the agents:** follow the segments where the language allows it. Merging
  and moving words between segments of the same verse are allowed and get a short
  note. The pilot (Ruth 1 and Genesis 1 in two languages, 53 verses) needed
  3 merges and 5 word-order changes in 255 segments.
- The draft check reports merges and moves as information. It fails only on hard
  errors: a wrong number of segments in a verse, a wrong verse.
- On export the markers are removed from the text and turned into a sidecar. These
  sidecars are exact, because the translator set the boundaries. lexeme-aligner can
  use them as reference for its derived sidecars.
- Until bcv-query publishes the source side, bsb-add-books uses the BHSA layout
  privately (non-commercial use). Its levels are replaced when the CC BY-SA index exists.

### Order

1. **bcv-query:** freeze and publish the segmentation (index + keys + stamp), then
   `text_depth`.
2. **bsb-add-books:** keeps drafting with BHSA privately, then switches to the published index.
3. **lexeme-aligner:** derives sidecars, starting with the hand-aligned editions;
   measures against them and against the bsb-add-books drafts.

**New Testament:** MACULA Greek is anchored to Nestle 1904. bsb-add-books translates
the NT from the BGB or Robinson-Pierpont. A clause overlay for the NT needs a mapping
between these texts. Start with the Old Testament.

## Formats

The formats follow `bcv-commons/compact-alignments` wherever possible:
- the same path scheme;
- the same verse keys (spine verses, Hebrew/WLC numbering);
- the same tokenizer;
- the same book content hash;
- the same span syntax.

A client that already reads the alignments needs very little more.

### 1. Source index (bcv-query, once per book)

**`_index/<BOOK>_clauses.json`**: per verse, the levels of its Hebrew clause segments in order.

```json
{"RUT 1:1": [0, 2, 1, 1, 5, 4], "RUT 1:2": [3, 4, 4, 5, 2, 2], ...}
```

- Entry `k` of a verse is segment `k` (the *segment ordinal*, 0-based).
- The value is its level: `text_depth`, or `depth` until `text_depth` exists.
- The ordered keys are the verse list. Every sidecar is position-parallel to them.

**`_index/<BOOK>_clause_keys.json`**: per verse, the MACULA keys of each segment, as `first-last`.

```json
{"RUT 1:1": ["080010010011-080010010022", "080010010031-080010010042", ...], ...}
```

This is what lexeme-aligner needs to map aligned tokens to segments.

**`_index/_clauses_source.json`**: version stamp.

```json
{"segmentation": "macula-uhb-1", "levels": "text_depth-rules-1",
 "macula_hebrew": "<commit>", "uhb": "<commit>", "built": "2026-…",
 "books": {"RUT": {"verses": 85, "segments": 410, "segments_sha256": "…"}}}
```

`segmentation` changes only when segment boundaries change. That is the version
sidecars refer to. `levels` can change without invalidating any sidecar.

`segments_sha256` is a hash of exactly what sidecars depend on: the book's
`_clause_keys.json` content, as one line per verse in index order,
`"<BOOK C:V>\t<first-last> <first-last> …"`, newline-joined, SHA-256. A rebuild that
moves a boundary changes the hash even if nobody bumps `segmentation`.
- **Why both:** lexeme-aligner pinned the spine by a version hash that stayed the same
  while bcv-query republished the spine with 209 more Psalm-title tokens flagged
  (2026-10). The compact files then no longer matched. Since then it also publishes
  `spine_index_sha256`, a hash of the columns its index is built from. This is the
  same idea for clause segments.
- **Sidecars record it:** a sidecar dataset's `manifest.json` lists, per book, the
  `segments_sha256` its files were built against. A client that finds a different
  hash in `_clauses_source.json` shows prose instead of clause lines for that book.

### 2. Edition sidecar (lexeme-aligner or bsb-add-books)

**`<iso[0]>/<iso>/<edition>/<BOOK>_<hash>.clauses.json`**: same path and hash as the
edition's alignment file. It can live in its own sibling dataset (for example
`bcv-commons/clause-overlays`) under the identical relative path.

```json
["0:0 1:1-5 2:6-11 3:12-20 4:21-28 5:29-35",
 "0:0-4 1:5-7 2:8-14 3:15-22 4:23-29 5:30-33",
 ...]
```

One string per verse, parallel to the index keys:

| token | meaning |
|---|---|
| `k:a-b` | segment `k` covers target tokens `a` to `b` (inclusive) |
| `k:a` | segment `k` is the single token `a` |
| `k:a-b,c` | scattered: segment `k` covers `a`-`b` and `c`. The **first range is where the clause's line begins** (normally its longest run); a word of `k` standing in another clause's line is a *moved* word |
| `k:=` | segment `k` has no words of its own (e.g. an untranslated כִּי); it is shown with the line before it |
| *(k absent)* | segment `k` could not be placed (derived sidecars only) |
| `""` | no clause information for this verse |

Rules:
- **Tokens** are counted with the compact-alignments tokenizer: maximal runs of
  Unicode letters and marks, NFC, combining marks dropped; digits and punctuation
  are separators. Punctuation therefore stays at the end of the line before a
  break, as in the prose.
- **Verse numbering:** keys are spine verses (Hebrew numbering). An edition with
  different numbering reads its words from the mapped verse, using the existing
  `_index/_versification_<scheme>.json` of compact-alignments.
- **Hash:** the book content hash of compact-alignments (`"{c}:{v}:{text}"` per verse,
  newline-joined, SHA-256, last 5 hex in the filename). If the edition's text
  changes, the file no longer matches and is not used.
- **Licence:** integers only, no text. CC0.

### 3. Provenance channel (optional)

**`<BOOK>_<hash>.clauses.meta.json`**, parallel arrays as in compact-alignments-meta:

```json
{"method": ["MMMMMM", "MMMMMM", ...], "conf": ["222222", ...]}
```

One character per segment entry of the verse:

| method | meaning |
|---|---|
| `M` | manual: set by the translator (bsb-add-books) or from a hand-made full alignment |
| `F` | derived from a statistical full alignment (with function words) |
| `S` | derived from the compact (content-word) alignment only |

`conf` holds the share of the segment's target tokens that were aligned, in
tenths, capped at 9.

### 4. Rendering in a client

1. Tokenize the verse text with the tokenizer above, keeping the character offsets of each token.
2. For each segment entry in order, start a new line at the first token of its span.
   - Punctuation glued to that token goes with it to the new line (an opening quote „ » >>).
   - A free-standing dash just before it (`morgen – første dag`) also opens the new line.
   - Any other text before the token stays on the previous line.
   - `k:=` adds no line.

   With these rules the demo client rebuilds all 252 clause lines of the pilot exactly.
3. Indent each line by its level from the source index.
4. **Compress the levels for display**, for example:
   - relative to the smallest level in the verse;
   - capped at 4-5 steps on a phone.

   The data keeps the true levels. In Ruth 1 they reach 13, which no phone can show.
5. **Moved words:** a token displayed in a line whose clause is not its own is a moved
   word. The demo underlines it in colour, with an arrow towards its own line.
6. **Interleaved clauses: split or merge.** The sidecar does not decide whether two
   clauses get one line or two; it only says which words render which clause. When the
   words of two neighbouring clauses interleave, a client offers two displays:
   - **split** (default): each clause gets its line; the words standing in the other
     line are shown as moved words;
   - **merge**: the two lines become one. The two parts are told apart quietly (two
     dotted underline colours), the line is marked "+1 clause", and an empty ghost line
     at the second clause's level shows its words (`↑ at … var godt`).

   Where the words do not interleave, both displays give two lines. A clause written `k:=` has no words; it is shown as a
   ghost line "no words of its own" under the line before it.

Prose mode ignores all of this.

### 5. Authoring format (bsb-add-books)

**Merges are a display, not a translation decision.** The translator (or an aligner)
only says which words render which Hebrew clause. Two neighbouring clauses whose words
interleave can then be shown as one line or as two (see "Rendering in a client"), for example
Genesis 1,4 "Gud så at lyset var godt": *at … var godt* and *Gud så … lyset* interleave.

The pilot drafts were first written with these as merges (`//N =`); the line was kept
and the words of the second clause named, which is all the sidecar needs.

Two equivalent forms of the same draft, convertible both ways:

**Clause lines**: one line per Hebrew segment.

```
//1 v1 In the days
//3 when the judges ruled,
//2 there was a famine in the land.
//2 =
```

- `//N` means level N-1.
- `vK` marks the first line of a verse.
- `//N = at var godt`: the Hebrew segment is rendered inside the line above; the words
  named (in order, as they stand there) are its words. `//N =` alone: no words of its own.

**Overlay**: running prose with inline markers.

```
v1 |0 In the days |2 when the judges ruled, |1 there was a famine in the land. ...
```

- `|N` gives the level of the following segment.
- `|=(at var godt)`: the segment is rendered inside the preceding text, by these words;
  `|=` alone: no words of its own.

The overlay costs 8-11 % more characters than plain prose in the pilot. Removing the
markers gives the prose.

`scripts/clause_sidecar.py` turns either form into the index and the sidecar. For
Ruth 1 both forms give the identical sidecar.

## Examples

`examples/` holds the pilot's Danish chapter and the source indexes (locally):

```
examples/_index/RUT_clauses.json                          source index, Ruth 1
examples/_index/GEN_clauses.json                          source index, Genesis 1
examples/d/dan/dan_draft/GEN_2714e.clauses.json           Danish draft, Genesis 1
```

Notes on the examples:
- **The levels are BHSA values** (CC BY-NC). These files are for illustration only
  and must not be published, so `examples/` is not in the public repository
  (`.gitignore`). The segment boundaries are those of the BHSA, not yet
  of MACULA.
- **The hashes cover chapter 1 only**, not the whole book.
- **Size:** a sidecar is about 1 KB per chapter; an index about 0.7-0.8 KB per chapter.

The pilot texts and a side-by-side view of prose and clause lines are kept locally
(not in git).

## Open questions

1. **Segmentation:** *decided with bcv-query:* MACULA's own segments, tied
   to the aligner's word keys. Segments and clauses are identified by word keys (a
   segment by its `first` key, a clause by `clause_key`), never by the build's row ids.
2. **Who owns the index?** *Decided:* bcv-query publishes it with
   `hebrew-clause-layout`; lexeme-aligner mirrors it into its `_index/` with its spine pin.
3. **Function words:** the derivation in lexeme-aligner is much better with the
   function-word alignments, which are only published for hand-aligned editions so far.
4. **Poetry:** many poetic lines are already clauses. Should a client in clause mode
   use the clause lines for poetry too, or keep the edition's poetry lines?
5. **New Testament:** mapping between Nestle 1904 (MACULA Greek) and the BGB / RP texts.
