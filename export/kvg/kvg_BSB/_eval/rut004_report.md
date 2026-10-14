# Ruth 4, Kuni drafting test 4 (verse pack v2), 2026-10-14

Evaluator-only file (agents must not open `_eval/`).

## Result

| | Ruth 1 | Ruth 2 | Ruth 3 | **Ruth 4** |
|---|---|---|---|---|
| chrF (tone marks ignored) | 63.6 | 64.3 | 60.1 | **63.2** |
| retrieval floor | 57.7 | 56.0 | 53.7 | 54.7 |
| lexical floor | 37.3 | 38.3 | 35.4 | 38.6 |
| margin over retrieval | +5.9 | +8.3 | +6.4 | **+8.5** |
| tool calls | 39 | 59 | 57 | **36** |
| NT searches | 21 | 31 | 79 | **33** (agent's count) |
| time | 25 min | 27 min | (cut, resumed) | **9.7 min** |
| tokens | 296k | 368k | 437k | **239k** |
| store after | 117 | 188 | 256 | 290 |

Verses: 4:19–22 (genealogy, names copied from Mat 1:3–6) score 76–78 and lift the chapter mean;
4:12 (37.0), 4:17 (37.2), 4:18 (34.2), 4:15 (41.7) and 4:7 (43.4, the sandal custom) are lowest.

## What changed

Pack v2 (phrases found in the NT per verse, lexicon count ≥3 / share ≥0.15, store index in the header,
*Still needs a search* line) replaced reading the store's JSON: the agent read the learning notes and
the pack (118 KB, in three parts) and nothing else of the store. Searches fell back to Ruth 2's level
for a chapter with 22 verses and a new domain (legal transaction, genealogy), and the cost fell to
about half of Ruth 3's tokens and a third of Ruth 1's time. Quality is the best margin so far.

## Open questions from the agent

Redeemer noun still missing ("ta ekeza ezoqam ndøgo"); "raise up the name of the dead" as a wish;
the v7 custom note (no past-habitual model); "famous" as a built optative; "city gate" vemiav mboqog
(the NT has taon mboqog). Lia (Leah) built; the learning notes' example "Leia" is not attested.

## Next

The search-result-to-store rule (`words` on entries) applies from the next run. Jonah 1 tests
transfer to a new book.
