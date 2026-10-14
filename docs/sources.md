# Sources

None of the source folders (`reference/BSB/`, `reference/MSB/`, `orig/`, `download/`) is in git.
`python3 scripts/setup.py` downloads every source at the version given below into
`download/` and builds the folders with the scripts named in each section. It checks
the BGB .docx, which has no versioned home, against the SHA-256 of the copy this repo
was built with, and warns if it has changed. A rebuild from a clean checkout was
checked to give byte-identical files (2026-10-13).

The Hebrew is optional: `--heb bhsa,bcv-query` builds both clause layouts side by side (`orig/heb-bhsa/`,
`orig/heb-bcv-query/`) and copies the drafting layout (BHSA by default; `--drafting LAYOUT`) to `orig/heb/`;
`--heb macula` is a third, slow route (see orig/heb/ below).

## reference/BSB/ and reference/MSB/

- **What:** Berean Standard Bible (whole Bible) and Majority Standard Bible (NT only;
  its OT is the BSB).
- **From:** release v5.16 (2026-09-29) of github.com/BSB-publishing/bsb2usfm,
  files `BSB_usj.zip` and `MSB_usj.zip`.
- **Licence:** public domain, CC0, since 2023-04-30 (berean.bible/licensing.htm).
- **Rebuild:** `python3 scripts/setup.py --only bsb,msb` (downloads both zips to
  `download/`, unpacks them to `download/BSB/` and `download/MSB/`, then runs
  `convert_usj.py BSB` and `convert_usj.py MSB --nt`, which write `reference/BSB/` and
  `reference/MSB/`).
- **Format:** `!!<…>!!` header, `===Book, chapter N===`, `==headings==`, inline
  `vN`, poetry lines `//1 …`, footnotes inline as `{T: …}`.
- **Note:** older plain-text converters dropped verse markers, words and footnotes
  inside character styles (above all `\wj`, the words of Jesus). `convert_usj.py`
  keeps them. Don't use BSB text files from other converters.

## orig/grc/ — Berean Greek Bible (BGB)

- **What:** the Greek NT the BSB is translated from. It is Berean's own eclectic
  text, compiled from SBL, NA, Byzantine, Greek Orthodox, Tischendorf, TR and WH.
- **From:** https://greekbible.org/bgb.docx (linked from berean.bible/downloads.htm).
  The file is dated 2016; there is no machine-readable or newer edition.
- **Licence:** the file still prints "©2016 Bible Hub, All Rights Reserved", but
  that was superseded on 2023-04-30, when all Berean texts were placed in the
  public domain (CC0).
- **Rebuild:** `python3 scripts/setup.py --only bgb` (downloads the .docx to
  `download/berean/`, runs `extract_bgb.py`)
- **Format:** first line `<code> <chapter>`, then `chapter:verse text`.
  `<code>NNN_notes.txt` holds the BGB footnotes (variants, OT references) as
  `<verse> [<letter>] <text>`. The signs ‹…› and ⇔ of the BGB are kept.
- **Verses:** the BGB and the BSB have exactly the same verses in every chapter
  (checked). Verses the critical text omits (e.g. Mt 17,21) are missing in both.

## orig/grc-rp/ — Robinson-Pierpont 2018

- **What:** The New Testament in the Original Greek: Byzantine Textform 2018,
  Maurice A. Robinson and William G. Pierpont. The MSB's NT is translated from it.
- **From:** github.com/byztxt/byzantine-majority-text (official), `csv-unicode/ccat/`,
  commit `27a45ff1b7be` (2024-12-31).
- **Rebuild:** `python3 scripts/setup.py --only rp` (downloads that commit's archive,
  unpacks it to `download/rp/`, runs `extract_rp.py`).
- **Licence:** public domain (no copyright claimed; the repository uses the Unlicense).
- **Format:** as `orig/grc/`. The paragraph sign ¶ is removed.
  `<code>NNN_notes.txt` lists the differences from Nestle-Aland as
  `<verse> NA: <RP words> > <NA words>`. John 7,53–8,11 is included. The
  alternative form of Acts 24,6-8 is in `act024_notes.txt`.
- **Verses vs MSB:** the same in all chapters, except four verses the MSB adds
  from the TR: Lk 17,36; Acts 8,37; 15,34; 24,7.

## orig/heb/ — Hebrew/Aramaic OT

- **What:** the Hebrew and Aramaic OT, one clause per line, laid out by syntax.
  Lines are `verse:indent text`; the first line is `<code> <chapter>`.
  **Hebrew verse numbering** (it differs from the BSB in places, e.g.
  Gen 31,55 BSB = 32,1 Hebrew; Joel, Malachi, many Psalm headings).
- **Which layout for what:** agents draft on the BHSA layout (`orig/heb/` = `orig/heb-bhsa/`), which
  they consult as a reference work: the drafts are our own text and stay free (CC0). Published clause
  structure (sidecars, clause-line editions, pages) is built on the bcv-query layout; move a
  clause-line draft with `python3 scripts/relayout.py <draft> --from orig/heb-bhsa --to
  orig/heb-bcv-query`. A commercial user drafts on bcv-query (`--drafting bcv-query`).
- **The bcv-query Hebrew clause layout** (Hugging Face
  `bcv-commons/hebrew-clause-layout`, tag **v0.22**, archive SHA-256
  `624990dd9113d9309300e7755588569a6808774d49f969ecafb2f7c271166640`):
  `python3 scripts/setup.py --heb bcv-query` (into `orig/heb-bcv-query/`), or
  `python3 scripts/build_heb_bcvquery.py <unpacked release> [--law] [--out DIR]`.
  - **What it is:** MACULA Hebrew (CC BY 4.0) over the UHB text (CC BY-SA 4.0); the release is
    **CC BY-SA 4.0**. Segmentation `8977039d6ddb5383`, levels `0.22+76768237c912922e`.
  - **Lines:** one line per clause segment. The number after the colon is `text_depth`, the
    text-level hierarchy (`--law` uses `text_depth_law`, the law view).
  - **Keys:** `orig/heb-bcv-query-keys/<code>NNN.json` keeps each segment's word keys for the
    clause sidecars. The version stamp is `orig/heb-bcv-query/_source.json`.
  - **A new release:** a levels-only release keeps the segmentation and each book's boundary
    hash (`_clauses_source.json`), so drafts and sidecars stay valid; only the levels change.
  - **Checked:** all 929 chapters have the same verses as the BHSA build (2026-10-14). The
    levels were compared privately with BHSA during development; the dataset card gives the
    figures (step agreement 84% overall in `text_depth`, 85% in the law view).
- **The BHSA layout, for drafting:** the ETCBC BHSA 2021 (github.com/ETCBC/bhsa), via Text-Fabric:
  `python3 scripts/setup.py --heb bhsa` (into `orig/heb-bhsa/`) or
  `python3 scripts/build_heb_bhsa.py [--out DIR] [code ...]`
  (needs `pip install text-fabric`; BHSA is downloaded to `~/text-fabric-data` on first
  use, or read from `--tf <dir>`). One line per clause atom; the text is BHSA's pointed
  surface text with its trailing characters (`g_word_utf8` + `trailer_utf8`).
- **Origin:** the lines are the **clause atoms of the ETCBC database BHSA**
  (Biblia Hebraica Stuttgartensia Amstelodamensis, Eep Talstra Centre for Bible
  and Computer, VU Amsterdam). The number after the colon is the BHSA feature
  `tab`, the clause atom's level of embedding in the text hierarchy.
  The text itself is the BHS, i.e. the Leningrad Codex as edited by the
  Deutsche Bibelgesellschaft.
- **Licence:** **CC BY-NC 4.0.** Attribution is required (cite DOI
  10.17026/dans-z6y-skyh). No commercial use without consent from the Deutsche
  Bibelgesellschaft. Research and non-commercial use, copying and modification
  are allowed. This is the only source folder that is not public domain. Consulting it while
  drafting doesn't make the drafts derived from it; publishing its files, levels or a layout
  built on them would.
  A public-domain alternative would be the Westminster Leningrad Codex
  (e.g. via OSHB, Open Scriptures Hebrew Bible), but without the clause layout.
- **Openly licensed alternative:** `python3 scripts/setup.py --heb macula` (or
  `python3 scripts/fetch_heb_macula.py <code>` for one book) builds
  the same file layout from MACULA Hebrew (CC BY 4.0) over the UHB text (CC BY-SA 4.0),
  via the shoresh scaffold API of bcv-commons/bcv-query (into `orig/heb-macula/`). Its levels are
  MACULA's sentence-internal tree depth, flatter than both other layouts.

## orig/vrs/ — Hebrew to BSB verse numbering

- **What:** the verse maps from Hebrew (Masoretic, `org`) to English/KJV numbering
  (`eng`), which the BSB follows:
  - `org-to-eng.json`: single verses whose number differs (`JOL 3:1 → JOL 2:28`,
    `PSA 3:1 → PSA 3:title`). Every verse not listed keeps its number.
  - `org-to-eng.multiverse.json`: verses that are merged or split, with a range on
    one side (`1SA 20:42-21:1 → 1SA 20:42`, `ISA 63:19 → ISA 63:19-64:1`).
- **From:** bcv-commons/bibles, published at `https://cdn.bibel.wiki/_vrs/map/`
  (documented in its `doc/vrs-maps.md`). Derived from STEPBible TVTMS. Don't use
  `data/vrs/tvtms-org-to-eng.derived.tsv` from the bibles repo: it is an internal
  build file without the multiverse relations.
- **Licence:** CC BY 4.0, STEPBible.org (`attribution` field in both files).
- **Rebuild:** `python3 scripts/setup.py --only vrs` (runs `vrs.py --fetch`)
- **Use:** `scripts/vrs.py` reads both. `make_prompt.py` gives an OT agent every BSB
  chapter its Hebrew chapter falls in, with the shifted verses. `check_draft.py`
  reports such chapters as information. `python3 scripts/vrs.py jol 3` prints one
  chapter's mapping.
- **Checked** against `orig/heb` and `reference/BSB/` (2026-10-12): every Hebrew verse maps to
  a BSB verse, and every BSB verse is reached except Neh 7:68, which most Hebrew
  manuscripts lack (the bibles file lists it under `flagged_not_published`). Psalm
  superscriptions are part of the BSB's verse 1.
- **OT drafts keep the Hebrew numbering**; the maps make a BSB-numbered
  export possible later.

## books.tsv

Written by `python3 scripts/books.py`: BSB code, English name, testament, chapter
count and RP file code (NT).
