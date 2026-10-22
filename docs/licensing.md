# Licensing: what we derive is free, what we quote is credited

Everything this repository makes is CC0, except what builds on share-alike data (CC BY-SA). Other people's texts
stay theirs: we learn from them, quote short credited passages, and never republish them in bulk. This holds for
every edition in `import/`, non-free ones included. (Our reading of copyright law, not legal advice.)

## Ours, CC0

Copyright protects a text's wording, not facts about a language. Whatever the edition's licence, these are ours:

- **drafts**: new translations from the Hebrew and Greek; a style edition is a model, not a source, so a "no
  derivatives" licence doesn't touch them;
- **notes, style guides, the wiki's prose**;
- **the language store** (`profile/`): grammar, letter correspondences, gaps, terms, formulas, name forms;
- **statistics**: lexicons, alignment figures, style norms, chrF scores.

Source data keeps its terms:

- clause structure from bcv-query (`orig/heb-bcv-query/`) is **CC BY-SA**;
- MACULA (**CC BY**) keeps its credit line;
- **BHSA** (CC BY-NC) is consulted, never republished. Our drafts laid out on it (the website's BHSA view, derived at
  build time from the drafts and their `.align`, never stored) are **CC BY-NC 4.0**, the ETCBC credited and the
  licence shown at the top of the view.

## Quoting an edition

The limits are for **non-free** editions. A public-domain edition needs nothing (we credit it anyway); a CC BY or
CC BY-SA edition needs its credit line. Quotation rights (Berne Convention Art. 10 and national law) allow quoting a
published work to explain or illustrate, in a fitting amount, with the source named. We quote:

- **short**: a word, a phrase, at most a verse for one point; never a run of verses;
- **few**: a published file quotes at most 10% of the verses of any book of the edition; the project's published
  files together at most 2% of the edition's words;
- **unchanged**: as the edition writes it (tone marks, punctuation), `…` for a gap;
- **from the published text**: if the working copy is newer (`published_text` in `edition.yaml`), only what the
  published text has;
- **with the reference** (`LUK 2:4`) and **the edition's credit line** (`credit` in `edition.yaml`).

Quotations are not ours and not under our CC0; each place that has them says so. Agents keep to the rules as they
write (prompts, the store validator, `wiki.py lint`); `python3 scripts/check_project.py <project>` double-checks every
publishable file before a commit (`docs/workflow.md`).

**The original in notes** is quoted from the open texts, never from `orig/heb/` (BHSA): the WLC for Hebrew, the BGB
(`orig/grc`) for Greek; `scripts/notes_hebrew.py` fills the verses. A Greek **Majority Text variant** may be quoted
when it is Robinson-Pierpont (`orig/grc-rp`, public domain) word for word and its line names it: `RP`, `BYZ`,
`Robinson-Pierpont` or `Majority Text` (e.g. `8,59 | BYZ, TR + διελθὼν διὰ μέσου αὐτῶν …`). A TR-only
reading (not in RP) is described in words, not quoted at length: we have no open TR text to check it against. `…`
marks a gap and ends the run that is checked. `scripts/quotes.py` reports any other run of more than 6 words.

## Kept local

Out of git and off any site (all rebuildable with the scripts):

- the editions' texts in `import/non-free/` (also `import/CC-ND/`, `import/CC-NC/`) and their `source/` files;
- quarantined books, and drafts made during a quarantine until it ends;
- generated files that print corpus verses: verse packs (`_learn/packs/`), alignment links (`_learn/links_*.tsv`),
  style reports (`*_style.md`), reports in `_eval/local/`;
- BHSA data, and anything built on it except the website's BHSA view.

## Three output paths

Our own work goes to `export/` (CC0). Work **derived** from an edition has its own paths. The project's folder
decides (`scripts/project.py`); its `derived_from` lists the editions (a `based_on` edition with `role: revise`
always counts).

| Path | Project folder | For work derived from | In git | Published |
|---|---|---|---|---|
| **export** | `export/<lang>/<id>/` | CC0 editions only | yes | yes, CC0 |
| **export/CC-NC** | `export/CC-NC/<lang>/<id>/` | open (CC0, CC BY, CC BY-SA) and `import/CC-NC/` editions | yes | non-commercially, under the edition's licence (BY-NC, or BY-NC-SA if share-alike), its credit kept; not on the website |
| **local_output** | `local_output/<lang>/<id>/` | any edition; a non-free or `import/CC-ND/` one only with approval (`derived_work:` in its `edition.yaml`) | **never** | no: returned to the rights holder |

**Derived** means: a revision of the edition's chapters; a draft made with its text of the same book in view (no
quarantine); copying its wording beyond the quotation limits; a file in its own structure (their USFM/Paratext book);
a model fine-tuned on it, and its output; a back-translation, interlinear or verse concordance of it. **Not derived:**
our independent drafts (in quarantine), the store, the wiki's prose, lexicons and statistics.

- **ND wins:** an NC-ND edition is filed in `import/CC-ND/`, so its derived work goes only to `local_output/`.
- **Non-free** (`import/non-free/`) is treated like CC-ND.
- **Approval per edition:** `derived_work: {approved_by, date, form, for, returned_to}` (who, written or verbal, for
  what, who gets the output). The translation team's approval suffices for work returned only to them; anything
  shared beyond them needs the copyright holder's.
- **On a derived path** the editions it derives from need no quarantine and no quotation limits; every other edition
  keeps its rules. A held-out test lists its books in the project's own `quarantine`.
- **No leaks:** projects in `export/` and `export/CC-NC/` get `local_output/` in `do_not_open`; nothing derived is
  copied between projects. A deliverable carries the edition's credit and says it is derived and not under our CC0.

## Drafts and publishing

Drafts are CC0 from the first line and may be online as drafts, also beside a non-free edition of the same book when
drafted in quarantine with the overlap measured (`docs/workflow.md`, *When an edition already has the book*). Every
chapter is a `draft` until a team publishes it, and every published place shows its status (`docs/workflow.md`,
*Draft status*). We tell publishers and language teams what we learned from their work and ask for their review.
