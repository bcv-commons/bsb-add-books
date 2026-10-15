# Genesis test drafts against Den Frie Bibel

Two sets of our Danish drafts of chapters that Den Frie Bibel (DFB) has published, kept as tests and scored against DFB's
own chapters (chrF, `python3 scripts/score.py dan/dan_BSB <draft> --reference import/CC0/dan/den-frie-bibel/text/<code>NNN.txt`;
the floors' corpus leaves Genesis out). DFB is public domain; credited in `CREDITS.md`.

## genesis-test/: Gen 1–19 and 28

Drafted before DFB published these chapters; kept in `quarantine/` (out of the agents' reach) until 2026-10-15. Each chapter
by one fresh agent, prose with notes, without the clause packages (the first way of working).

| | mean | range |
|---|---|---|
| our draft | **75.3** | 69.7–81.2 |
| retrieval floor (nearest DFB verse) | 52.6 | 37.5–58.9 |
| lexical floor (word by word) | 59.8 | 53.9–63.1 |

Our drafts are on average 15.6 points above the better floor. Highest Gen 2 (81.2), Gen 8 (80.1), Gen 12 (80.0); lowest Gen 16
(69.7), Gen 18 (70.6), Gen 5 (71.4, the genealogy: number words and names). Independence was measured separately: 20% of
5+-word runs shared with DFB, the baseline for two independent translations (`docs/workflow.md`).

## variance-test/: Gen 18 and 28, repeated

The runs that tested the tagged drafting and the clause packages (internal plan, part B): each a fresh agent on the same
chapter, varying one thing.

| run | way of working | chrF |
|---|---|---|
| genesis-test gen018 | first way (prose, notes) | 70.6 |
| gen018-A | prose, alignment at the end | 70.7 |
| gen018-B | tagged with the full package | 69.4 |
| genesis-test gen028 | first way (prose, notes) | 75.4 |
| gen028-A, A2 | prose, alignment at the end | 75.9, 75.3 |
| gen028-B, B2 | tagged, full package | 75.3, 75.2 |
| gen028-B3 | tagged, full package, revised prompt | 75.1 |
| gen028-B4 | tagged, lean package (known language) | 75.6 |
| gen028-B5 | tagged, lean package with function-word glosses | 76.0 |

The spread between runs of the same set-up (about ±0.5) is as large as the differences between set-ups: tagging costs no
quality, and the lean package matches the full one at fewer tokens (179–188k against 201–246k).

These are tests, not the project's drafts of these chapters: DFB's chapters are the text this project continues.
