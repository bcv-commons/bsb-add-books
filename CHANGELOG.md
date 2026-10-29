# Changelog

Tags are `vMAJOR.MINOR.PATCH`. A work copy merges a tag; make-tanakh-grammar pins one (`docs/related-repos.md`).
Each entry has a **Format changes** section for the stable formats listed in `docs/related-repos.md`, section 4:
what changed and how existing files move over. Before 1.0 a breaking format change raises the minor version.

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
