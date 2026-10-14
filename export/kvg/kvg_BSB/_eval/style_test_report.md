# Style check and revision test, 2026-10-14

CC0; quotations from the Kuni texts credited in `../CREDITS.md`. Tool: `scripts/style.py` (docs/proposals/language-toolkit/). Drafts: the NT-only Ruth test drafts
(`ruth-test/`). Human Ruth: eBible kvg 2015, quarantined during the test and released afterwards.

## 1. Does the check find real deviations?

Each flag says "the draft has more (fewer) X than the human translators would". Checked against the human Ruth,
chapter by chapter: the human text lies in the flagged direction for 20 of 26 flags (77%) and for 49 of 60
flags + watch items (82%). Pooled over all four chapters the check is weaker (7 of 12): it is meant per chapter.

Wrong flags come from the gap between the NT and OT narrative, which the NT-based expectations can't see: land
phrases (*manqei -te*, "in the land of Moab"), *taon*, *ezoqam -te*; and from content the Hebrew requires
(*ndabua* clothes, *zenda* feet in Ruth 3). The human Ruth itself gets 6 flags, our four drafts 8.

## 2. Does revising with the report improve the drafts?

Four fresh agents revised Ruth 1 and Ruth 3, without access to the human Ruth, the store, the wiki or the
lexicons (only the NT and Jonah through `concord.py`). Two had the style report, two (control) only the instruction
to make the text read like the corpus.

| | chrF original | with report | control |
|---|---|---|---|
| Ruth 1 | 63.6 | 63.6 (7 verses changed) | 63.7 (8 changed) |
| Ruth 3 | 60.1 | 59.6 (13 changed) | 60.3 (4 changed) |

Counts of the flagged items, human / original / with report / control:

| Ruth 3 | human | original | report | control |
|---|---|---|---|---|
| yaq | 28 | 36 | **28** | 36 |
| yaq ndego | 2 | 10 | **3** | 10 |
| ndego | 13 | 22 | **15** | 22 |
| zapa ndǿgo | 2 | 5 | **3** | 5 |
| qo | 15 | 19 | **16** | 19 |
| qoqa | 2 | 6 | 5 | 6 |

In Ruth 1 the report agent moved *-qape* (Shaddai) 4 → 2 (human 1) and *ndego* 1 → 4 (human 3), but followed a
wrong flag on *manqei -te* (10 → 8, human 11).

- **The style moves to the human translators' figures** with the report, not without it: the control agents
  fixed word forms and verb choices and left the style as it was.
- **chrF does not rise.** Removing a connector or a pronoun changes only a few characters, and the agent's
  rewording of the rest of the sentence seldom matches the human words. chrF measures closeness to one human
  text; it can't show a gain in style.
- Cost: 100–120k tokens, 4–5 minutes per chapter for a separate revision agent.

## 3. Use

- Per chapter, as the drafting agent's last step (`style_check: true` in project.yaml), not as a separate agent.
- The agent should treat a flag as a question: keep the draft where the Hebrew needs the word (the Ruth 3 agent
  rightly kept *ndabua* and *zenda*).
- Whether the moved style reads better is for the Kuni team to judge: give them the original and the revised
  Ruth 3 (`style-test/report/rut003.txt`, with `rut003_revision.md`) side by side.
