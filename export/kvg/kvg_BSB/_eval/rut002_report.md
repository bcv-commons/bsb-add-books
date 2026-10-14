# Kuni Ruth 2: the second chapter, drafted against the language store (2026-10-14)

Evaluator's report (`_eval/` is on the agents' do-not-open list).

**Setup:** as for Ruth 1 (`rut001_report.md`), plus the language store built from the Ruth 1 agent's
notes (`profile/observations.json`, `profile/decisions.json`, 117 entries) and the rule to read it first
and append to it after.

| | Ruth 1 | Ruth 2 |
|---|---|---|
| chrF, tone marks ignored (as written) | 63.6 (60.9) | **64.3** (62.2) |
| retrieval floor (nearest NT verse) | 57.7 | 56.0 |
| lexical floor (BSB word by word) | 37.3 | 38.3 |
| margin over the retrieval floor | +5.9 | **+8.3** |
| verses | 22/22 | 23/23 |
| tool calls | 39 | 59 |
| duration | 25 min | 27 min |
| tokens | 296k | 368k |

**Quality:** slightly better than chapter 1 relative to its floors, in a harder chapter (farming
vocabulary the NT barely has: glean, sheaf, reaper, winnow, ephah). Best verses 2:1, 2:12, 2:23
(58–63); weakest 2:16, 2:10, 2:22 (33–38). The agent's own "least sure" list (2:9, 2:12, 2:14, 2:16,
2:20) overlaps with the low scorers except 2:12.

**Cost:** the store did not reduce the work. The agent read the store first (tool calls 4–5), then
still ran ~38 NT searches, as the prompt's "use the tool for every verse" rule asks. About a third of
the verses needed nothing beyond the store (its own estimate); the rest were field vocabulary,
blessing formulas, vocatives and 2nd-person verb forms, which chapter 1 had not met.

**Store:** 117 → 188 entries, validator clean. The agent corrected one chapter-1 feature with
`supersedes` (gu꞉-/gunu꞉- is a durative prefix, not a feminine marker) and added 2nd-person past,
imperative and optative patterns, 12 gaps and ~40 terms. Its open questions for a Kuni speaker:
real words for glean / reaper / sheaf, a kin-law term for goʾel, yakhav as a dry measure, the tones
of built 2sg optatives.

**Next:** precompile a verse pack per chapter (`scripts/verse_pack.py`), so the agent reads one
prepared file instead of running the searches, and draft Ruth 3 with it; compare calls, tokens and
score against chapters 1 and 2.
