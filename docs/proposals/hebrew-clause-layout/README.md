---
license: cc-by-sa-4.0
language:
  - hbo
  - arc
pretty_name: Hebrew Bible Clause Layout (MACULA + UHB)
tags:
  - bible
  - hebrew
  - aramaic
  - syntax
  - clauses
  - old-testament
  - translation
size_categories:
  - 10K<n<100K
configs:
  - config_name: clauses
    default: true
    data_files:
      - split: train
        path: data/clauses-*.parquet
---

# Hebrew Bible Clause Layout

The Hebrew Bible (with the Aramaic portions) laid out **one clause segment per
line**, with the clause's **depth of embedding**, chapter by chapter. It is
built from **MACULA Hebrew** syntax trees over the **unfoldingWord Hebrew
Bible (UHB)** text. It is meant for translators and for the tools and agents
that help them: a chapter can be read clause by clause, with subordinate
clauses indented under the clause they belong to.

It is a share-alike replacement for clause layouts derived from the ETCBC
BHSA (CC BY-NC 4.0); it contains no non-commercial data.

> **Status: proposal.** This card describes the dataset as proposed by a user
> of the shoresh `/scaffold` API (bcv-commons/bcv-query). Fields marked
> *(new)* are not in the API today. See "Requested changes" at the end.

## Contents

```
README.md
layout/<BOOK>/<BOOK>_<CCC>.txt      plain-text layout, one file per chapter
clauses/<BOOK>/<BOOK>_<CCC>.jsonl   one JSON object per clause segment, one file per chapter
data/clauses-<BOOK>.parquet         the same rows as clauses/, one file per book
schema/clause_segment.schema.json   JSON Schema of a row
build.json                          source versions and build date (new)
```

- `<BOOK>`: USFM book code (`GEN`, `RUT`, `PSA`, …).
- `<CCC>`: zero-padded chapter (`001`).
- 39 books, 929 chapters.

Chapters are the unit because translation, checking and review happen per
chapter, and per-chapter files are small to download and easy to compare
between versions. The Parquet files carry the same rows for the dataset viewer
and for `datasets.load_dataset`.

### Versification

Verses use the **Hebrew numbering** of the source text. It differs from
English Bibles in places: Gen 31,55 = Hebrew 32,1; Psalm superscriptions are
verse 1; Joel 3-4; Malachi 3,19-24; and others. Every row carries `verse_ref_en`
*(new)*, the corresponding reference in English (BSB/KJV) numbering, from the
bcv-commons/bibles verse map `org-to-eng` (`cdn.bibel.wiki/_vrs/map/org-to-eng.json`,
from STEPBible TVTMS, CC BY 4.0). That map lists single-verse renumbering only. A few
verses are split differently (Hebrew Num 25:19, 1 Sam 21:1, 1 Ki 22:44, 1 Chr 12:5,
Ps 13:6, Isa 63:19b); for these `verse_ref_en` names the English verse the segment
falls in.

## What a clause segment is

A **clause segment** is a maximal run of whole words, inside one verse, that
belongs to one clause:
- A clause interrupted by an embedded clause gives two segments, before and after the embedded one (as in BHSA "clause atoms").
- A clause that runs over a verse boundary gives one segment per verse.
- A word is assigned as a whole, including its prefixes (וְ, בְּ, לְ, הַ, …).

Two depths:
- **`depth`** is the number of clause ancestors in the MACULA tree (`parent`). It is
  0 for a clause not embedded in another clause, 1 for a clause embedded in a
  depth-0 clause, and so on. It only reaches up to the verse.
- **`tree_depth`** *(new)* is the number of links up the `discourse_parent` chain,
  every link counted: the text-level hierarchy across verses, BHSA-like.
- **`text_depth`** *(new)* is the flat view of the same tree: it counts only links whose
  `relation` is not in `build.json` `relations.flat` (and whose `discourse_rule` is not
  in `relations.flat_rules`). 0 = main line. See "Wanted: the text-level
  hierarchy" below.
- **`text_depth_law`** *(new, optional)* is the flat view with conditionals laid out as
  in BHSA: where a protasis comes before its apodosis, the protasis is indented one
  level from the clause the apodosis hung on, and the apodosis stands level beside it.
  A protasis whose apodosis continues the apodosis of an earlier protasis stands level
  with that protasis, so laws in a row stand side by side (`clause_layout.toml`
  `[depth.law]`). It matters mostly for law (Lev 1:
  the law's body one level deeper) and casuistic prophecy (Mal 2). Elsewhere it
  equals `text_depth`.

The tree itself keeps the protasis under its apodosis. A client that wants BHSA's
direction for conditionals in the tree inverts those links as `build.json`
`relations.conditional_inversion` describes; for a flat view it uses
`text_depth_law` instead of computing its own.

## layout/ — plain text

```
RUT 1
1:0 וַיְהִ֗י בִּימֵי֙
1:1 שְׁפֹ֣ט הַשֹּׁפְטִ֔ים
1:0 וַיְהִ֥י רָעָ֖ב בָּאָ֑רֶץ
1:0 וַיֵּ֨לֶךְ אִ֜ישׁ מִבֵּ֧ית לֶ֣חֶם יְהוּדָ֗ה
1:1 לָגוּר֙ בִּשְׂדֵ֣י מוֹאָ֔ב
```

The first line is `<BOOK> <chapter>`. Every other line is
`<verse>:<text_depth> <text>` (`depth` until `text_depth` exists). The text is the UHB surface text with vowels and
accents, words separated by single spaces, maqaf `־` and paseq ` ׀ ` kept,
sof pasuq `׃` at the verse end. The ketiv is not shown; the line shows the
vocalised (qere) reading, and the `clauses/` row has both.

The number can be shown as indentation by any reader: `"  " * n + text`.

## clauses/ and data/ — one row per segment

Full schema: `schema/clause_segment.schema.json`. Example (Ruth 1,1, fifth segment):

```json
{
  "book": "RUT", "chapter": 1, "verse": 1, "seg": 5,
  "verse_ref_en": "RUT 1:1",
  "clause": 119513, "parent": 119508, "sentence": 119498,
  "clause_key": "080010010131", "parent_key": "080010010081",
  "depth": 1, "discourse_parent": "080010010081", "discourse_attach": null, "text_depth": 1,
  "kind": "VC", "rule": "V-PP", "language": "hbo",
  "first": "080010010131", "last": "080010010151",
  "words": ["080010010131", "080010010132", "080010010141", "080010010142", "080010010151"],
  "text": "לָגוּר֙ בִּשְׂדֵ֣י מוֹאָ֔ב",
  "ketiv_qere": []
}
```

| Field | Meaning |
|---|---|
| `book`, `chapter`, `verse` | USFM code, chapter, verse (Hebrew numbering) |
| `seg` | position of the segment in the chapter, from 1 |
| `verse_ref_en` | *(new)* the same verse in English numbering; `PSA 3:title` for a Psalm superscription |
| `clause_key` | **stable clause id**: the first word key of the clause's first segment; the same for all segments of one clause |
| `parent_key` | `clause_key` of the nearest enclosing clause with words of its own, or `null`; coordination groups (MACULA `ClCl…`, no words of their own) are skipped |
| `clause`, `parent`, `sentence` | row ids of the tree build; they change when it is rebuilt, so never key on them |
| `depth` | *(new as a field)* embedding depth, computed from `parent` |
| `discourse_parent` | *(new)* `clause_key` of the clause this one depends on in the text-level hierarchy, also across verses; every clause has one, chain links included; `null` only for the first clause of a line (book, chapter, new Psalm, a reset after ס/פ) |
| `relation` | *(new)* type of the link to `discourse_parent` (`continuation`, `coordination`, `asyndetic`, `speech`, `inquit`, `causal`, `purpose`, `temporal`, `conditional`, `relative`, `circumstantial`, `complement`, `vocative`, `embedded`; the set is in `build.json` `relations.all`); `null` where `discourse_parent` is `null` |
| `discourse_attach` | *(new, optional)* word key of the word or phrase head inside the `discourse_parent` clause that this clause depends on (e.g. a relative clause on its antecedent); `null` if it depends on the clause as a whole. Does not change `text_depth` |
| `tree_depth` | *(new)* number of links up the `discourse_parent` chain (BHSA-like view) |
| `text_depth` | *(new)* the same, without links whose relation is in `relations.flat` (flat view); the number shown in `layout/` |
| `text_depth_law` | *(new, optional)* `text_depth` with a fronted protasis indented and its apodosis level beside it (BHSA's layout of conditionals) |
| `kind`, `rule` | MACULA clause kind (`VC` verbal, `NC` nominal, …) and constituent rule (`V-S-PP`) |
| `language` | `hbo` Hebrew or `arc` Aramaic |
| `first`, `last`, `words` | MACULA word keys (BBCCCVVVWWW + part digit, as in the scaffold API), words of this segment in order |
| `text` | surface text of the segment, as in `layout/` |
| `ketiv_qere` | *(new)* list of `{key, ketiv, qere}` for words in this segment that have a ketiv/qere; `ketiv` or `qere` is `null` where only one exists |
| `discourse_rule` | *(new, optional)* the rule that set `discourse_parent` (`embedded`, `main`, `sub_back`, `sub_fwd`, `circ`, as of rules 0.1); for information, `relation` is the field to use |

## Sources and licence

| Part | Source | Licence |
|---|---|---|
| Hebrew/Aramaic text | unfoldingWord Hebrew Bible (UHB), based on the Westminster Leningrad Codex | CC BY-SA 4.0 |
| Clauses, sentences, clause kinds and rules | MACULA Hebrew (Clear Bible / Biblica) | CC BY 4.0 |
| English versification mapping | bcv-commons/bibles `org-to-eng`, from STEPBible TVTMS | CC BY 4.0 |
| This compilation | bcv-commons | **CC BY-SA 4.0** |

**Attribution** when you use this dataset:

> Hebrew Bible Clause Layout, bcv-commons, CC BY-SA 4.0. Text: unfoldingWord
> Hebrew Bible (CC BY-SA 4.0). Syntax: MACULA Hebrew (CC BY 4.0).

### How the text-level hierarchy was checked

The hierarchy (`discourse_parent`, `relation`, `text_depth`, `text_depth_law`) is derived by
rules from MACULA Hebrew alone; the rules are listed, with examples and scope, in
`clause_layout.toml`. During development the rules were evaluated against the ETCBC's BHSA
(CC BY-NC 4.0) as a private reference, on sample chapters: agreement figures and failure
cases described in words, nothing else. No BHSA values, codes, links or files went into the
rules or into this dataset, and it contains no data under a non-commercial licence.

Where the layout follows a convention, it is chosen for readers and documented, and it
sometimes differs from BHSA on purpose. For example, the cases of a law stand side by side
rather than nested. The agreement with BHSA's own clause links, laid out the same way, is
given as a quality figure: the same line-to-line step in about 86% of line pairs (92% in
narrative and law, 83% in poetry and prophecy).

BHSA: Eep Talstra Centre for Bible and Computer, VU Amsterdam; DOI 10.17026/dans-z6y-skyh.

### Versions

To keep the chapter files simple they carry no version header. Instead
`build.json` at the root lists the commits of UHB and MACULA, the shoresh
version and the build date *(new)*. It also gives, per book, a `segmentation` version
and a `segments_sha256`: a hash of each verse's segment boundaries (`first`–`last` keys).
Sidecars depend on exactly these, so a rebuild that moves a boundary is visible even if
no version number changes. The definition is in the clause-overlay proposal, under
`_clauses_source.json`.

## Differences from BHSA clause atoms

| | BHSA (ETCBC) | This dataset |
|---|---|---|
| Licence | CC BY-NC 4.0 | CC BY-SA 4.0 |
| Segments | clause atoms | clause segments (very similar; 0–6 % more lines in the tested chapters) |
| Indentation | `tab`: text-level hierarchy, also across verses and sentences | `depth` inside the verse today; **`text_depth` from `discourse_parent` wanted** (see below) |
| Ketiv | shown unpointed in the text | qere in the text, both in `ketiv_qere` |
| Unicode | holam male as `ֹו` | standard order `וֹ` |

## Wanted: the text-level hierarchy (`discourse_parent`, `text_depth`)

**This is the main requirement of this dataset.** The value of a clause layout
for translators lies in the indentation: it shows at a glance which clause
depends on which, also across verse boundaries. Examples:
- a speech and the narrative that introduces it;
- a circumstantial clause and the main line it belongs to;
- a conditional, causal or relative clause and its main clause.

BHSA's `tab` gives this. MACULA's `parent` alone does not.

**What MACULA has (checked in WLC/lowfat, Ruth 1 and Dan 2, 2026-10-12):**
- A MACULA `sentence` is **exactly one verse** (Ruth 1: 22 sentences = 22 verses).
  There is no structure above the verse.
- Within the verse, the main clauses are siblings under an unlabelled group
  (coordination), with no relation between them. Only clauses embedded in a phrase
  (e.g. an infinitive inside a prepositional phrase) get a `parent`.
- There are participant references (`subjref`, `participantref`: who is the subject,
  across verses) and `clausetype="nominalized-clause"`, but no clause-to-clause
  relations across verses.

**So `discourse_parent` cannot be passed through from MACULA; it has to be derived.**
Proposal for a first, rule-based derivation in bcv-query, with all inputs CC BY / CC BY-SA:

| Clause | `discourse_parent` |
|---|---|
| wayyiqtol (narrative main line), and weqatal in procedural or predictive text | the previous clause of the same line, or `null` at the start: these stay at text level 0 |
| introduced by a subordinator (כִּי, אֲשֶׁר, אִם, לְמַעַן, פֶּן, כַּאֲשֶׁר, …) | the nearest preceding main-line clause |
| infinitive clause, participle clause, or verbless circumstantial clause with וְ + non-verb first | the clause it qualifies (preceding main-line clause) |
| direct speech after a verb of speaking (אָמַר, דִּבֶּר, צִוָּה, …, also after לֵאמֹר) | the speaking clause. All clauses of the speech go one level deeper, until the narrative resumes, usually with the next wayyiqtol whose subject (`subjref`) is a narrator-level participant. |
| clauses inside a phrase (MACULA `parent` today) | as now, the parent clause |

`text_depth` is then the length of the `discourse_parent` chain (0 = main line),
and it is the number shown in `layout/` files. Until it exists, `layout/` shows
`depth`.

Notes:
- The rules can be checked for quality against BHSA `tab` on a sample, privately and
  without republishing BHSA values. That keeps the result free of NC data.
- A rule version (`discourse_rules` in `build.json`) lets users see when the derivation changes.

## Requested changes to the source data / API

Found while testing `/scaffold/{book}/{chapter}` on Ruth 1, Gen 32, Ps 3, Dan 2 and
Judg 5, and checked against MACULA Hebrew `WLC/lowfat` (Ruth 1, Dan 2). The source
of each problem is given, so it can go to the right place.

1. **Ketiv/qere** *(source: MACULA)*. MACULA has no ketiv/qere attributes and gives one
   pointed form (Dan 2,9 `הִזְדְּמִנְתּוּן`, where BHSA has the ketiv `הזמנתון`). Take both
   readings from UHB, which marks them, and add `ketiv` and `qere` to the token.
2. **Missing trailer** *(source: MACULA)*. At exactly these ketiv/qere words MACULA has
   `after=""`, so two words run together (`הִזְדְּמִנְתּוּן֙לְמֵאמַ֣ר`). In Dan 2: 7 cases
   (2,9; 2,29.31.37 אַנְתְּה; 2,38; 2,39; 2,41). Fix in the build (a word-final token is
   always followed by a separator), and report upstream to Clear-Bible/macula-hebrew.
3. **Prefixes in the wrong clause** *(source: MACULA tree)*. A prefix token sometimes belongs
   to the higher clause (Ruth 1,1: the ל of לָגוּר in the clause of וַיֵּלֶךְ).
   Assign whole words to one clause in the build.
4. **Depth** *(API)*. Return `depth` per clause, so clients need not walk `parent`.
5. **Text-level hierarchy** *(new derivation)*: `discourse_parent` and `text_depth`, see
   the section above. **This is the change we want most.**
6. **API access** *(API)*. Python's default User-Agent gets HTTP 403. The first call for a
   chapter can take over a minute and once returned truncated JSON. A published
   dataset avoids both.
7. **Provenance** *(API)*. Responses carry no licence, version or source fields. Add them
   (or publish `build.json`).
8. **Aramaic is not marked** *(API)*. MACULA marks it (`lang="A"`: 1240 of 1321 words in
   Dan 2), but the API gives every lexeme the prefix `hbo:`. Pass the language through
   per token.

## Examples in this proposal

`examples/layout/` and `examples/clauses/` hold Ruth 1 and Daniel 2 (391
segments), built from the scaffold API with the reference script, and valid
against the schema:
- `language` in Daniel 2 is set from the known Aramaic range, because the API doesn't mark it (item 8).
- `verse_ref_en`, `discourse_parent` and `text_depth` are `null`, and `ketiv_qere` is empty, because the API has no data for them yet.
- Dan 2,9 still shows the glued words of item 2.

## Building it

The per-chapter layout can be built today from the scaffold API; a reference
implementation is `scripts/fetch_heb_macula.py` in the bsb-add-books repo
(words grouped per clause, depth from `parent`, paseq spacing). A build inside
bcv-query should instead read MACULA and UHB directly, fix items 1-3 in the
build, and add the derivation of `discourse_parent` / `text_depth` (item 5).
