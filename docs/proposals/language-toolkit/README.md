# Drafting in a language the model doesn't know: the toolkit

Status: 2026-10-14, the general tools are in `scripts/` (below); the Kuni project uses them. Worked out on Kuni (kvg), a language without LLM exposure, where the drafting
agents learned the language from its NT alone. The tools are meant for any language with an existing
translation (a style corpus) and no other resources. Kuni is the first user.

## The pieces

| piece | what it does | tool |
|---|---|---|
| shared core | the style corpus paired with the BSB (OT through `orig/vrs`), the project's tokeniser, chrF | `scripts/langtools.py` |
| aligner | word alignment of the corpus with the BSB (eng), MACULA Hebrew lexemes (hbo, OT books) and the NT Greek (grc); eflomal when installed, a built-in IBM Model 2 otherwise; glossary and name checks | `scripts/align.py <project>` → `_learn/lexicon_*.tsv`, `links_*.tsv`, `align_report.txt` |
| concordance | the agents' search tool: `eng`, `tgt` (or the language code), `like`, `lex`, `hlex`, `forms`, `gloss`, `store` | `scripts/concord.py <project> …` |
| language store | checked facts with evidence: features, letters, gaps; terms, formulas, names | `export/<project>/profile/`, `scripts/language_profile.py` (`docs/proposals/language-profile/`) |
| verse pack | per chapter: store hits, lexicon, phrases found in the corpus, similar verses, what still needs a search; never the book being drafted | `scripts/verse_pack.py` |
| wiki | explanations next to the store, edited by agents and people | `scripts/wiki.py` |
| evaluation | chrF of a draft against a human translation, with retrieval and word-by-word floors (the scored book left out) | `scripts/score.py <project> <draft>` |
| style | the draft against the human translations: for each verse the human verses most like it (BSB tf-idf), expected counts of the corpus's style items (words and pairs found in most books, not renderings of one content word), flagged only beyond the spread of the human chapters themselves; with model verses; `style_check: true` puts it into the chapter prompt | `scripts/style.py <project> <draft> [--brief]` |
| workflow | the steps for a new language | skill `learn-language` |

The Kuni-only predecessors in `scratch/kvg/` (`align.py`, `align2.py`, `score.py`) and
`export/kvg/kvg_BSB/_learn/concord.py` are superseded by these.

## What makes a tool language-neutral

- **Tokenising and normalising** come from the store's `orthography` (marks to ignore) and the project's
  `tokenise:` (`split_hyphens` for suffixes such as Kuni's `-qa`, `-te`; `word_chars` such as Kuni's `꞉`).
  No language is hard-coded.
- **Corpus pairing** goes through `orig/vrs`: OT editions keep the Hebrew numbering, the BSB the English.
- **Paths** come from the project (`style_from`, `based_on`, `do_not_open`), never from a language code.
- **Licences:** the code is MIT. What it produces is ours and CC0 for any edition, non-free ones
  included: lexicons, the store, the wiki, statistics. Quotations keep to `docs/licensing.md`
  (`scripts/quotes.py` checks them); generated files that print corpus verses (packs, alignment links,
  style reports) stay local.

## External tools

- **eflomal** (GPL-3.0, Östling & Tiedemann): it is run as a program, not bundled. On macOS, Apple
  clang has no OpenMP: `brew install libomp`, then build `src/` with `-Xpreprocessor -fopenmp
  -I$(brew --prefix libomp)/include` and link `-lomp` (done in this working copy's scratchpad venv).
- **lexeme-aligner's datasets** (bcv-commons): its alignments, gram-struct, target-morphology and
  stopwords can seed the store as `external` entries, under their licence.

## The workflow for a new language

1. Import the edition (`import-edition`), with a test book held out where the edition has one.
2. Align: `scripts/align.py <project>`.
3. Seed the store and the wiki: grammar sketch by a first agent; lexeme-aligner data as `external`.
4. Test: draft the held-out chapters with fresh agents, score them, compare cost and quality.
5. Lift the holdout and learn from the human translation (an audit of the store, gaps solved,
   style figures, the alignment retrained with it).
6. Draft new books with the pack and the wiki; every search ends in the store.

The Kuni test series (Ruth 1–4) and its reports are in `export/kvg/kvg_BSB/_eval/` (quotations credited in its `CREDITS.md`).
