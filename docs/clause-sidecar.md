# Clause sidecars

A clause sidecar records which words of a translated verse render which Hebrew clause segment. A client can then show
the translation as running prose or as clause lines: one line per Hebrew clause, indented by its level. The
translation text itself is unchanged; the sidecar is a separate JSON file per book, like the alignments of
bcv-commons/compact-alignments.

Clause lines are guidance, not a law: a draft may render two Hebrew clauses in one line or move words between the
clauses of a verse. The sidecar only records which words render which clause; whether two clauses get one line or two
is a display choice.

`scripts/clause_sidecar.py` builds the files for one chapter draft:

```
python3 scripts/clause_sidecar.py <draft> <orig/heb file> <BOOK> [--out DIR] [--index-dir DIR]
```

- `<draft>`: a chapter in clause-line or overlay form (see *Authoring format*), one segment per line of the layout.
- `<orig/heb file>`: the chapter's layout file (`orig/heb-<layout>/<code>NNN.txt`); the levels come from it.
- `<BOOK>`: the book code in the keys (`RUT`).
- Without `--out` it prints `{"index", "entries", "sha256"}` as JSON. With `--out DIR` it writes the sidecar to
  `DIR/` and the index to `DIR/_index/` (or `--index-dir`).
- It stops if a verse of the draft has a different number of segments than the layout.

## Files

### Index: `_index/<BOOK>_clauses.json`

Per verse, the levels of its Hebrew clause segments, in order:

```json
{"RUT 1:1": [0, 2, 1, 1, 5, 4], "RUT 1:2": [3, 4, 4, 5, 2, 2]}
```

- Keys are `BOOK C:V` in Hebrew verse numbering; their order is the verse list of the sidecar.
- Entry `k` of a verse is segment `k` (0-based); its value is the layout's level.

### Sidecar: `<BOOK>_<hash>.clauses.json`

One string per verse, parallel to the index keys:

```json
["0:0 1:1-5 2:6-11 3:12-20 4:21-28 5:29-35",
 "0:0-4 1:5-7 2:8-14 3:15-22 4:23-29 5:30-33"]
```

| token | meaning |
|---|---|
| `k:a-b` | segment `k` covers target tokens `a` to `b` (inclusive, 0-based in the verse) |
| `k:a` | segment `k` is the single token `a` |
| `k:a-b,c` | scattered: `k` covers `a`–`b` and `c`. The first range is where the clause's line begins; a word of `k` that stands in another clause's line is a *moved* word |
| `k:=` | segment `k` has no words of its own (e.g. an untranslated כִּי); it is shown with the line before it |
| *(k absent)* | segment `k` has a line but no tokens on it (e.g. only punctuation) |

- **Tokens:** the compact-alignments tokenizer v2 (`scripts/full_align.py`, `tokenize`): NFC, combining marks dropped,
  maximal runs of letters and marks; digits, punctuation and spaces separate; scripts without spaces are segmented by
  rule. Inline notes `{…}` are not counted.
- **Hash:** the compact-alignments text fingerprint v1, its first 8 hex characters. Per chapter, the SHA-256 of the
  verse lines `"{v}:{tokens joined by a space}"`; then the SHA-256 of the `"{c}:{chapter digest}"` lines. The script
  hashes the verses of the given draft only, so a file for one chapter matches a whole book only if the book has one
  chapter. If the text changes, the hash no longer matches and the file is not used.
- **Path:** the sidecar takes the place of the edition's alignment file in the compact-alignments scheme,
  `<iso[0]>/<iso>/<edition>/<BOOK>_<hash>.clauses.json` (e.g. `d/dan/<edition>/`), with the index in `_index/`.

### Reading a sidecar

Start a new line at the first token of each entry's first range, in order; `k:=` adds no line. Text before that token
stays on the previous line. Indent each line by its level from the index; a client may compress the levels for display
(e.g. relative to the verse's smallest level). Prose mode ignores the sidecar.

## Authoring format

Two equivalent forms of the same draft. `clause_sidecar.py` reads both; for the same draft both give the same sidecar.

**Clause lines**: one line per line of the layout file, in order. `scripts/clause_lines.py` writes this form for the
website's clause views, and `scripts/relayout.py` moves it between layouts.

```
//1 v1 In the days
//3 when the judges ruled,
//2 there was a famine in the land.
//2 =
```

- `//N`: N is the Hebrew line's level + 1.
- `vK` marks the first line of verse K.
- `//N =`: this Hebrew segment is rendered inside the line above, with no words of its own.
- `//N = words`: the same, naming the words of the line above that render it, in order. In the sidecar these words
  become the segment's own range, and the line above keeps its start.
- Headings (`==…==`), the title and header lines (`!!<…>!!`) are left out of the segments.

**Overlay**: running prose with a marker before each segment.

```
v1 |0 In the days |2 when the judges ruled, |1 there was a famine in the land. ...
```

- `|N` starts the next segment (N is its level; the sidecar takes the levels from the layout).
- `|=(words)`: a segment rendered inside the preceding text by these words; `|=` alone: no words of its own.
- Removing the markers gives the prose.

## Licence

The sidecar holds integers only, but it and the index follow the clause layout they were built on, and neither goes
into `export/` (`export/README.md`):

- **BHSA layout** (`orig/heb-bhsa/`, CC BY-NC 4.0): the index carries BHSA's levels. Keep these files private, never
  published. `clause_sidecar.py` warns when the layout is BHSA or has no `_source.json`.
- **bcv-query layout** (`orig/heb-bcv-query/`, CC BY-SA 4.0): for published sidecars. Move a BHSA clause-line draft
  first with `python3 scripts/relayout.py <draft> --from orig/heb-bhsa --to orig/heb-bcv-query`.
