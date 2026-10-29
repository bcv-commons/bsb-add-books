# Changelog

Tags are `vMAJOR.MINOR.PATCH`. A work copy merges a tag; make-tanakh-grammar pins one (`docs/related-repos.md`).
Each entry has a **Format changes** section for the stable formats listed in `docs/related-repos.md`, section 4:
what changed and how existing files move over. Before 1.0 a breaking format change raises the minor version.

## v0.2.0

**The Tanakh order by default.** A project's reading order is now its own setting, `book_order` in `project.yaml`:
`tanakh` (the default: Torah, Prophets, Writings, as in BHS), `protestant` (Genesis … Malachi, the BSB's order and
the one every list followed before) or `septuagint` (the Greek order of Orthodox Bibles). The setup wizard asks for it.
It orders `STATUS.md`, the site's book lists and the wizard's book ranges. Book codes, file names and the book numbers
for Paratext and MACULA keep the BSB's numbering order (`books.BOOKS`); the NT order is the same in all three.

**For an existing project:** without `book_order` it now lists its books in the Tanakh order. To keep the earlier
order, add `book_order: protestant` to `project.yaml`; run `scripts/status.py <project>` to rewrite `STATUS.md`.

**Format changes:** `project.yaml` gains the optional `book_order` (additive).

## v0.1.1

A fix: in v0.1.0 a store entry's `basis` had two meanings. `grammar.py run --write` put a Grambank answer's
team/derived/labelled there, and the validator accepted only those three values, but `basis` is also the settings
fingerprint that `morphs.py try --write` and `cell_check.py try` write on a measured claim and `grammar.py retest`
compares. Every store with measured claims failed validation.

**Format changes:**

- language store: a Grambank answer's (`gb:GBnnn`) team/derived/labelled moves from `basis` to **`answer_basis`**.
  `basis` is only the settings fingerprint (16 hex digits, `grammar.basis`), and the validator now checks that shape.
  **Migration:** `python3 scripts/grammar.py run <project> --write` rewrites the script's `gb:` entries with the new
  field; the validator names any old one left (`a Grambank answer's basis is answer_basis`). A `gb:` entry an agent or
  team wrote by hand needs the field renamed by hand. Measured claims need nothing.

New test: `scripts/tests/test_store_basis.py` (a measured claim and a Grambank answer side by side, a claim going
stale, the migration message).

## v0.1.0

The first tagged version: the baseline the work copy and make-tanakh-grammar start from.

**Formats at this version:**

- language store: `docs/language-store.md`, schema `docs/language-store/schema/language_profile.schema.json`;
- clause sidecars: `docs/clause-sidecar.md`;
- `.align` working format: `scripts/full_align.py`, on compact-alignments' `tokenizer_version` 2 and
  `text_fp_version` 1;
- compact-alignments layer: `_layer.json` `version` 3, layer id `<edition>+auto+make-tanakh`;
- `orig/heb.sqlite`, `orig/grc.sqlite`: the tables in `scripts/src.py`, from the source structure `v1`.

**In this version, from the work copy's reconciliation delivery:** NT word alignment (`bridge_align.py`,
`full_align.py`, Greek tokens from `orig/grc.sqlite`) and the site's Greek NT clause view (greek-nt-clause-layout
v0.5, `build_grc_gntl.py`); the speaker layer v0.14; alternations (`alternations.py`); store fields for hyphen
chains, harmony variants, word parts and tone `with`; `nllb/train.py --src-chars`.

**New here:** the data root setting `MAKE_TANAKH_ROOT` (`docs/configuration.md`): data from that folder, code from the
toolkit's own; without it, everything as before.

**Format changes:** none against earlier states, all additive:

- language store: optional `with`, `variants` and `parts` fields, and `feature` entries with an `alternation` block;
- `orig/heb.sqlite`: `speaker_quotations` gains `speaker_ref`, `speaker_basis`, `alt_eng`, `speaker_id`,
  `speaker_name`, `speaker_name_ref` (`setup.py --only spk` rebuilds it);
- `.align`: now also for NT chapters, in the same format, on the Greek of compact-alignments' index;
- the layer id was `<edition>+auto+bsb-add-books` before the rename; no layer with the old id was published.
