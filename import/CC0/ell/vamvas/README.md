# Vamvas (1850), modern Greek

Neophytos Vamvas's translation of the Bible into modern Greek (katharevousa), published with the British and Foreign
Bible Society: the NT in 1833, the whole Bible in 1850. Public domain.

- **Source:** CrossWire's SWORD module `GreVamvas` 1.0.3, `DistributionLicense=Public Domain`, text from theword.gr.
  The zip's SHA-256 is pinned in `fetch_vamvas.py` (`3e1593fa…3b5d`).
- **Get the text:** `python3 import/CC0/ell/vamvas/fetch_vamvas.py` (needs `pip install pysword==0.2.8` and `orig/`
  from `scripts/setup.py`). It writes `text/<code>.txt`, one book per file, `chapter:verse<TAB>text`; `text/` stays
  out of git.
- **Numbering:** the module has the KJV versification. The Tanakh books are renumbered to the Hebrew verses (the repo's rule) by
  `orig/vrs`: Joel has 4 chapters and Malachi 3, as in `orig/heb`. Where several Hebrew verses make one English verse,
  the text goes to the first; a psalm superscription goes to the Hebrew title verse.
- **NT basis:** the Textus Receptus (`nt_basis: tr`).
- **Role:** `source`: the default source of the second-draft model (`scripts/nllb/source.py`; a project's
  `nllb_source`), trained on the NT pairs with the target and then given Vamvas' translation from the Hebrew. Not a style corpus.
