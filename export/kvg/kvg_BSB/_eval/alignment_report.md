# Kuni alignments with Ruth and Jonah: eflomal, IBM Model 2 and lexeme-aligner (2026-10-14)

CC0; quotations from the Kuni texts credited in `../CREDITS.md`. Made with local experiment scripts (eflomal built against Homebrew libomp), not in the repository;
they became `scripts/align.py`, which rebuilds the lexicons (`_learn/`).

## Corpora

- **eng:** BSB ↔ Kuni, NT + Ruth + Jonah: 8,065 verse pairs (133 from Ruth and Jonah). Kuni Jonah has
  the Hebrew verse numbering now and is paired with the BSB through `orig/vrs` (Hebrew 2:1 = BSB 1:17).
- **hbo:** MACULA Hebrew lexemes (`hbo:NNNN`, the scaffold API, the same ids as lexeme-aligner) ↔ Kuni,
  Ruth + Jonah only: 133 verse pairs. Small: these figures are rough.

Both models are symmetrised the same way (intersection + grow-diag). Kuni is tokenised with hyphen parts
split off and tone marks removed.

## Results

| check | eflomal | IBM Model 2 (ours) | lexeme-aligner |
|---|---|---|---|
| glossary: Kuni term is the top rendering of its one-word English equivalent | **85 / 114 (75%)** | 76 / 118 (64%) | (69 / 77 on the earlier check) |
| names of Ruth and Jonah (Hebrew lexeme → Kuni name, 30, gold from the human verses) | **24** | 23 | 22 |
| eflomal and IBM2 agree on the top English source of a Ruth/Jonah Kuni type (≥2) | 211 / 321 | | |
| … on the top Hebrew lexeme | 116 / 239 | | |
| top Hebrew lexeme = lexeme-aligner's top `hbo` lexeme (Ruth/Jonah types) | 75 / 232 | 70 / 311 | |
| top English word's BSB lexemes include lexeme-aligner's top lexeme (types ≥10 links) | 461 / 856 | 503 / 1,139 | |

The name gold has two wrong gold forms (Yahweh, Rachel), so 28 names really count.

- **eflomal is the better aligner** on both gold checks, and it is now the agents' lexicon:
  `_learn/lexicon_eng.tsv` (eflomal, NT + Ruth + Jonah) and `_learn/lexicon_hbo.tsv` (Hebrew lexeme →
  Kuni, Ruth + Jonah, with lemma and gloss; `concord.py hlex`). The NT-only lexicons are kept in
  `_learn/nt-only/`.
- **Agreement with lexeme-aligner is low on the Hebrew side** (about a third). The disagreements are
  mostly function words, and both sides have errors. lexeme-aligner aligns the whole corpus (Greek and
  Hebrew lexemes) jointly, and some of its Ruth rows look off: `lut` → "he said", `zo` → "person", `qo` →
  "covenant loyalty". Ours gives `manqei` → "earth" where theirs gives "Moab" (from *Moab manqei*). These
  rows are worth sending to lexeme-aligner as examples.
- **Names, where the models miss:**
  - Amittai: all three give *yo* (son), from *Amitai-ge yo*.
  - Joppa (*Ziopa*): all three miss.
  - Tamar (*Tama*): all three give *zi*.
  - Leah: only IBM2 is right (*Lia*).
  - Perez: lexeme-aligner gives *atanakha*.
  - Ruth: lexeme-aligner gives *moab*.

## For the general toolkit

`align2.py` becomes `scripts/align.py <project>` (`docs/proposals/language-toolkit/`): eflomal when
installed, IBM2 otherwise, a Hebrew-lexeme corpus wherever the edition has OT books, and the glossary and
name checks as its built-in report.
