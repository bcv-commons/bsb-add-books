# Sources

No source folder (`reference/BSB/`, `reference/MSB/`, `orig/`, `download/`) is in git. `python3 scripts/setup.py`
downloads each source at the version below into `download/` and builds the folders. Pinned files are checked by
SHA-256; for the BGB .docx, which has no versioned home, `setup.py` only warns if it differs.

## reference/BSB/ and reference/MSB/

- **What:** Berean Standard Bible (whole Bible); Majority Standard Bible (NT; its OT is the BSB).
- **From:** github.com/BSB-publishing/bsb2usfm, release **v5.16**, `BSB_usj.zip` and `MSB_usj.zip`.
- **Licence:** public domain (CC0) since 2023-04-30 (berean.bible/licensing.htm).
- **Build:** `setup.py --only bsb,msb` (`convert_usj.py BSB`, `convert_usj.py MSB --nt`).
- **Format:** `!!<…>!!` header, `===Book, chapter N===`, `==headings==`, inline `vN`, poetry lines `//1 …`,
  footnotes `{T: …}`. Verse markers and footnotes inside `\wj` are kept: don't use BSB files from other converters.

## orig/grc/: Berean Greek Bible (BGB)

- **What:** the Greek NT the BSB is translated from (Berean's eclectic text).
- **From:** https://greekbible.org/bgb.docx (dated 2016), SHA-256 `56eb9ba0…eac7` in `setup.py`.
- **Licence:** public domain (CC0) since 2023-04-30; the file's old copyright line no longer applies.
- **Build:** `setup.py --only bgb` (`extract_bgb.py`).
- **Format:** first line `<code> <chapter>`, then `chapter:verse text`; `<code>NNN_notes.txt` holds the footnotes
  as `<verse> [<letter>] <text>`. The signs ‹…› and ⇔ are kept. Same verses as the BSB in every chapter.

## orig/grc-rp/: Robinson-Pierpont 2018

- **What:** The New Testament in the Original Greek: Byzantine Textform 2018 (Robinson, Pierpont), the MSB's basis.
- **From:** github.com/byztxt/byzantine-majority-text, `csv-unicode/ccat/`, commit `27a45ff1b7be`.
- **Licence:** public domain (the repository uses the Unlicense).
- **Build:** `setup.py --only rp` (`extract_rp.py`).
- **Format:** as `orig/grc/`, without ¶; `<code>NNN_notes.txt` lists the differences from Nestle-Aland as
  `<verse> NA: <RP words> > <NA words>`. John 7:53–8:11 is included; Acts 24:6-8's other form is in
  `act024_notes.txt`. Same verses as the MSB, except four the MSB adds from the TR: Lk 17:36; Acts 8:37; 15:34; 24:7.

## orig/heb/: Hebrew and Aramaic OT clause layouts

`--heb bhsa,bcv-query` builds the layouts side by side in `orig/heb-<layout>/` and copies the drafting layout
(BHSA by default; `--drafting LAYOUT`) to `orig/heb/`. All share one format: first line `<code> <chapter>`, then one
clause per line as `verse:level text`, in **Hebrew verse numbering** (Gen 31:55 BSB = 32:1 Hebrew). Agents consult
the drafting layout as a reference work; the drafts are our own text (CC0). Published clause structure is built on
bcv-query; `scripts/relayout.py <draft> --from orig/heb-bhsa --to orig/heb-bcv-query` moves a clause-line draft. A
commercial user drafts on bcv-query (`--drafting bcv-query`).

- **BHSA** (`orig/heb-bhsa/`): ETCBC BHSA 2021 (github.com/ETCBC/bhsa) via Text-Fabric: `--heb bhsa` or
  `scripts/build_heb_bhsa.py [--tf DIR] [--out DIR] [code ...]` (needs `text-fabric`; downloads BHSA to
  `~/text-fabric-data` on first use). One line per clause atom; the level is BHSA's `tab`; the text is BHSA's
  surface text (the BHS). **CC BY-NC 4.0**, Eep Talstra Centre for Bible and Computer, VU Amsterdam; cite DOI
  10.17026/dans-z6y-skyh; no commercial use without consent (ask the ETCBC and the Deutsche Bibelgesellschaft, the final rights holder). Its files, levels
  and anything laid out on them are never published (`CLAUDE.md`, *Pitfalls*).
- **bcv-query** (`orig/heb-bcv-query/`): the released dataset **bcv-commons/hebrew-clause-layout** (Hugging Face),
  tag **v0.37**, archive SHA-256 `02f90e95caf01b941136fe2f03826f6dcdb93551dd6a78d86aa792235a864791`: `--heb bcv-query`
  or `scripts/build_heb_bcvquery.py <unpacked release> [--law] [--out DIR]`. MACULA Hebrew syntax over the UHB text,
  segmentation `8977039d6ddb5383`. One line per clause segment; the level is `text_depth`, the text-level hierarchy,
  with speeches from the speaker layer (`--law`: `text_depth_law`). `orig/heb-bcv-query-keys/<code>NNN.json` keeps
  each segment's word keys; `_source.json` is the stamp. **CC BY-SA 4.0** (MACULA Hebrew CC BY 4.0, UHB CC BY-SA
  4.0). The dataset card gives the rules.
- **MACULA** (`orig/heb-macula/`): `--heb macula`, or `scripts/fetch_heb_macula.py <code>` for one book. MACULA
  Hebrew (CC BY 4.0) over the UHB (CC BY-SA 4.0) via bcv-query's shoresh API, one slow call per chapter (cached in
  `download/scaffold/`). The level is MACULA's tree depth within the sentence, flatter than the others.

## orig/heb.sqlite and orig/grc.sqlite: the prepared source structures

- **What:** every MACULA Hebrew (WLC) and Greek (Nestle 1904) token with morphology, glosses, LXX equivalent,
  referents, semantic frames and syntax tree, joined with the compact-alignments numbering and the BSB Translation
  Tables; speaker quotations; each token's line in the clause layouts; for Greek the BGB/RP mapping to MACULA's keys.
  Built by `scripts/src.py`; read by `scripts/package.py` and `scripts/lang.py`.
- **From:** bcv-query's cache **source-structure v1** (`https://files.qombi.com/files/source-structure-v1-…`:
  `heb-open.sqlite.gz`, `grc-open.sqlite.gz`, `heb-bcv-query.sqlite.gz`; SHA-256 pinned in `setup.py`), built from
  MACULA Hebrew `47db250bd55d`, MACULA Greek `8423afe47b9e`, compact-alignments `7982b3d9feda` and
  full-alignments-manual `1d845bf91390`. Its layout rows are hebrew-clause-layout v0.22's; when `orig/heb-bcv-query/`
  exists, `setup.py` replaces them from the pinned release (same segmentation). 8 requests per hour per address.
- **Build:** `setup.py --only src`; it adds locally, never published, the BHSA layout rows (`src.py layouts --layout
  bhsa`) and the BGB/RP mapping (`src.py map`). `scripts/src.py build [code ...]` builds all from MACULA instead
  (about 50 minutes), with the UBS columns (SDBH, Louw–Nida) the cache leaves empty.
- **Licences:** MACULA Hebrew and Greek CC BY 4.0; MACULA Quotation and Speaker Data CC BY 4.0 (Clear Bible) with
  SIL Glyssen / FCBH character data (MIT); compact-alignments and the BSB tables CC0; the bcv-query rows CC BY-SA 4.0.
- **Speaker layer:** Hugging Face **bcv-commons/hebrew-speaker-layer**, tag **v0.11**, archive SHA-256
  `68ec601e456d535ca56bbada485153aa645da67947055c73b8bf372978843b16`, **CC BY 4.0** (bcv-commons, on Clear's MACULA
  Quotation and Speaker Data, CC BY 4.0, with SIL Glyssen / FCBH data, MIT). Each bcv-query segment's quotation,
  level (2+ = nested) and speaker, and a chapter's frame (a psalm's psalmist), in tables `speaker_segments` and
  `speaker_quotations`; the clause packages show it per line. `setup.py --only spk` (`src.py speaker-layer DIR`).

## orig/vrs/: Hebrew to BSB verse numbering

- **What:** maps from Hebrew (`org`) to English/KJV numbering (`eng`), which the BSB follows: `org-to-eng.json`
  (single verses, `JOL 3:1 → JOL 2:28`) and `org-to-eng.multiverse.json` (merged or split verses,
  `1SA 20:42-21:1 → 1SA 20:42`). A verse not listed keeps its number.
- **From:** bcv-commons/bibles, `https://cdn.bibel.wiki/_vrs/map/` (its `doc/vrs-maps.md`), from STEPBible TVTMS.
- **Licence:** CC BY 4.0, STEPBible.org (`attribution` field in both files).
- **Build:** `setup.py --only vrs` (`vrs.py --fetch`). `scripts/vrs.py <code> <ch>` prints a chapter's mapping.
  Neh 7:68, which most Hebrew manuscripts lack, is the one BSB verse no Hebrew verse maps to; Psalm superscriptions
  are part of the BSB's verse 1.

## Imported editions

`scripts/fetch_edition.py --find <iso>` lists a language's editions; `fetch_edition.py <edition>` (or
`setup.py --only editions` for all) fetches one into `import/` by the `fetch:` recipe in its `edition.yaml`. Sources:
the bcv-commons/bibles catalogue (`https://cdn.bibel.wiki/catalog/index.json`: helloAO, openbible, DBT with your own
API key) and eBible (`ebible.org/Scriptures/`). `fetch.lock.json` keeps the source version and a SHA-256 per file.
Each edition keeps its own licence and credit (`import/README.md`).

The source edition of the second-draft model, `import/CC0/ell/vamvas/` (Vamvas 1850, modern Greek, public domain), is
read from CrossWire's SWORD module GreVamvas 1.0.3 (zip SHA-256 pinned) by its own `fetch_vamvas.py` (needs `pip
install pysword==0.2.8` and `orig/`); its OT is renumbered to the Hebrew verses, psalm titles to the title verses.

## Alignment datasets (bcv-commons, Hugging Face)

**compact-alignments**, **full-alignments-llm** and **full-alignments-manual**: editions aligned word by word to the
Hebrew and Greek, in compact-alignments' format; CC0 (token positions only). `scripts/lang.py layers <project>
[--write]` lists the layers built on exactly the style edition's text, found by the text fingerprint in their file
names; `--write` sets the best as `lexeme_aligner` in `project.yaml`, and `lang.py build` adds its links.

**The Vamvas alignment** (`download/full-alignments-llm/e/ell/ell_GreVamvas+llm+jev-v4/`): bcv-commons
**full-alignments-llm**, layer `ell_GreVamvas+llm+jev-v4` (the Vamvas Bible of 1850 aligned to MACULA Hebrew and Greek,
proposed by eflomal and other methods, every verse checked by a model, TypeSafe Jev 1.13.0; machine alignments, no
person has checked them; CC0 1.0, as its dataset card says), at commit
**49f2972c6201f39ccc90f2a9bcf236a8272362d0** (2026-10-21): `manifest.json`, the layer's `_layer.json` and its 39 OT book
files with their `.meta.json`; the SHA-256 of the files' `SHA256SUMS` lines is pinned in `setup.py`
(`5ab99b6f…`). Only on request: `setup.py --only vamvas-align`. It is the audit's Vamvas route (`scripts/ot_routes.py`,
`morphs.py audit --route vamvas`): the modern Greek word(s) of each OT Hebrew word, read on our copy of the text
(`import/CC0/ell/vamvas/`, built by its `fetch_vamvas.py`). The layer's file names carry the fingerprint of the SWORD
module's text in its own (KJV) numbering; our copy is filed in the Hebrew numbering, so `ot_routes.py` puts it back
(`english_rows`) before comparing. Measured 2026-10-22: 36 of 39 OT books match; Isaiah, Nehemiah and the Psalms don't
(verses the renumbering merges or splits) and are skipped. Positions count compact-alignments' tokens in our
Hebrew-numbered verse (checked on Jonah 2:1 = 1:17).

## download/grambank/: Grambank feature questions

- **What:** Grambank's 195 feature questions (`parameters.csv`) and value codes (`codes.csv`), for the typology in a
  project's language store (format: `docs/language-store.md`).
- **From:** github.com/grambank/grambank, tag **v1.0.3**, `cldf/parameters.csv` (SHA-256 `ff5a675e…dc80`) and
  `cldf/codes.csv` (SHA-256 `cdcf17f5…3263`), pinned in `setup.py`.
- **Licence:** CC BY 4.0. Credit: Skirgård, H. et al. 2023, *Grambank reveals the importance of genealogical
  constraints on linguistic diversity and highlights the impact of language loss*, Science Advances 9; Grambank v1.0.3.
- **Build:** `setup.py --only grambank` (on request). `scripts/grammar.py plan|run|status` show each feature's
  question; the recipes in `docs/language-store/grambank_recipes.tsv` decide features from a Bible corpus. No
  Grambank language values enter a store.

## download/glottolog/: the Glottolog family tree

- **What:** every languoid's name, ISO 639-3 code and level (`languages.csv`) and its classification, the path of its
  ancestors (`values.csv`, parameter `classification`), for a language's relatives (`scripts/donor.py`).
- **From:** github.com/glottolog/glottolog-cldf, tag **v5.3**, `cldf/languages.csv` (SHA-256 `1a50a393…bb89`) and
  `cldf/values.csv` (SHA-256 `a8601cb0…ea25`), pinned in `setup.py`.
- **Licence:** CC BY 4.0. Credit: Hammarström, H., Forkel, R., Haspelmath, M. & Bank, S. *Glottolog 5.3*, Leipzig:
  Max Planck Institute for Evolutionary Anthropology.
- **Build:** `setup.py --only glottolog` (on request; the wizard fetches it for an unknown language). `donor.py`
  caches the tree in `download/glottolog/v5.3/tree.json`. A project's `donor:` block names relatives by ISO code.

## download/stepbible/: STEPBible TIPNR proper names

- **What:** TIPNR (Translators' Individualised Proper Names with all References): every person and place name with its
  disambiguated Strong's number and the verses of each individual (two Nahors, the Zechariahs), for
  `scripts/participants.py`.
- **From:** github.com/STEPBible/STEPBible-Data, commit **1f3423d4** (2026-10-05), `Proper Nouns/TIPNR - Translators
  Individualised Proper Names with all References - STEPBible.org CC BY.txt` (SHA-256 `aaec5b0a…358e`), pinned in
  `setup.py`. (An older JSON copy of TIPNR, from 2019, was released under CC BY-NC; this file is the CC BY one.)
- **Licence:** CC BY 4.0. Credit: "TIPNR, STEPBible.org, based on work at Tyndale House Cambridge (CC BY 4.0)".
  STEPBible asks that the data be fetched from its repository, not redistributed: it stays in `download/`.
- **Build:** `setup.py --only names` (in the default set). Read only; nothing from it enters a store or a draft.

## books.tsv

Written by `scripts/books.py`: BSB code, English name, testament, chapter count, RP file code (NT).
