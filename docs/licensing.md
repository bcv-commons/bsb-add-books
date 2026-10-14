# Licensing: what we derive is free, what we quote is credited

Aim: everything this repository makes is public domain (CC0), and only what builds on share-alike
data carries CC BY-SA. Other people's texts stay theirs: we learn from them and quote from them in
short, credited passages, and we never republish them in bulk. This applies to every edition in
`import/`, the non-free ones included. (Our reading of copyright law, not legal advice.)

## Ours, CC0

Copyright protects the wording of a text, not facts about a language or the ideas in it. So all of
this is our own work and is CC0, whatever the licence of the edition it was learned from:

- **drafts**: new translations from the Hebrew and Greek; a style edition is a model, not a source
  (the drafts are not adaptations of it, so a "no derivatives" licence does not touch them);
- **notes, style guides, the wiki's prose**: descriptions of the language;
- **the language store** (`profile/`): grammar features, letter correspondences, gaps, and the terms,
  formulas and name forms, which are single words and short phrases;
- **statistics**: lexicons (word pairs with counts), alignment figures, style norms, chrF scores.

**CC BY-SA** applies where we build on share-alike data: clause structure from bcv-query
(`orig/heb-bcv-query/`). **CC BY** data (MACULA) keeps its credit line. **BHSA** (CC BY-NC) is consulted
and never republished (CLAUDE.md, Pitfalls).

## Quoting an edition

The limits below are for **non-free** editions. A public-domain edition (Den Frie Bibel) needs nothing;
we credit it anyway, as a courtesy. A CC BY or CC BY-SA edition needs its credit line, which its licence
asks for.

The quotation right (Berne Convention Art. 10; e.g. Swiss URG Art. 25, Danish ophavsretslov § 22, US
fair use) lets us quote a **published** work to explain or illustrate, if the amount fits the purpose
and the source is named. The eBible licences add more: most let anyone share extracts unchanged,
with credit. We quote:

- **short**: a word, a phrase, at most a verse for one point, never a run of verses or a chapter;
- **few**: a published file (a wiki page, a report) quotes at most 10% of the verses of any one book
  of the edition, and the project's published files together at most 2% of the edition's words;
- **unchanged**: as the edition writes it (tone marks, punctuation), with `…` for a left-out part;
- **from the published text**: where the working copy is newer than the published edition
  (`published_text` in `edition.yaml`), quote only what the published text has;
- **with the reference** (`LUK 2:4`) and **the edition's credit line** (`credit` in `edition.yaml`)
  on the page or with the files.

Quotations are not ours and are not covered by our CC0; each published place that has them says so.
The agents keep to these rules as they write: their prompts carry them, and the store validator and
`wiki.py lint` enforce them. `python3 scripts/check_project.py <project>` double-checks every
publishable file (shares per book and in all, quotes that differ from the published text or drop its
marks, the credit line) at the end of a wave and before a commit (`docs/workflow.md`).

## Kept local

Bulk text stays out of git and off any public site:

- the editions' texts in `import/non-free/` (and their `source/` files);
- quarantined books and the drafts made while a book was quarantined, until the quarantine ends;
- **generated files that print corpus verses**: verse packs (`_learn/packs/`), per-verse alignment
  links (`_learn/links_*.tsv`), style reports (`*_style.md`), and comparison reports that quote a
  held-out book at length (`_eval/local/`);
- BHSA data and anything laid out on it.

These can all be rebuilt from the sources with the scripts.

## Drafts and publishing

Our drafts are CC0 from the first line, and they can be online as drafts, also beside a non-free
edition of the same book when they were drafted independently of it (in quarantine, with the overlap
measured: `docs/workflow.md`, *When an edition already has the book*): every chapter has a status
(`draft` until a team publishes it), and every published place shows it (`docs/workflow.md`,
*Draft status*). Courtesy is not law: we tell the editions' publishers and the language teams what we
learned from their work and ask for their review, and publish the drafts as drafts meanwhile.
