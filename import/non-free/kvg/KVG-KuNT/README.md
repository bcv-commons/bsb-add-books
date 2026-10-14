# Kuni NT (kvg)

The New Testament (and Ruth, Jonah) in the Kuni dialect of Kuni-Boazi (Papua New Guinea), with its
glossary. The texts are not in git (`import/non-free/`); this README, `edition.yaml` and `build_text.py` are.

- `source/`: the Paratext SFM files as received (UTF-8 NFD; 27 NT books and the glossary `A9GLO`).
- `text/`: one file per chapter, built by `python3 build_text.py` (run it again after replacing a
  file in `source/`).
- `glossary.tsv`: 156 glossary terms with their English equivalents and the Kuni explanation.
- Ruth and Jonah in `text/` come from eBible `kvg` (`build_text.py --ot`), the 2015 state of the
  same translation. Until 2026-10-14 they were held out (`holdout/`) as the test set of the Ruth
  drafting test (`export/kvg/kvg_BSB/_eval/`).

The local NT is a newer working copy than eBible's: 785 of 7,934 verses differ.

**In a fresh clone** there is no `source/`: `python3 build_text.py` then builds `text/` (NT, Ruth, Jonah)
and `glossary.tsv` from eBible's published text (https://ebible.org/kvg/, CC BY-NC-ND 4.0), the
older state of the NT. The lexicons and the store in `export/kvg/kvg_BSB/` were built from the newer copy.
