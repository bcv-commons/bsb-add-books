# Kuni Ruth 3: the third chapter, drafted with a verse pack (2026-10-14)

Evaluator's report (`_eval/` is on the agents' do-not-open list).

**Setup:** as for Ruth 2, plus the precompiled verse pack `_learn/packs/rut003.md`
(`scripts/verse_pack.py`: per verse the store's matching entries, the lexicon's renderings of each BSB
word, the three most similar NT verses) and the rule to read the pack first and search only for what
it lacks. The run was interrupted once by a usage limit after the store had validated; the agent was
resumed for its report. Time is therefore not comparable.

| | Ruth 1 | Ruth 2 | Ruth 3 |
|---|---|---|---|
| chrF, tone marks ignored (as written) | 63.6 (60.9) | 64.3 (62.2) | 60.1 (57.4) |
| retrieval floor | 57.7 | 56.0 | 53.7 |
| margin over the retrieval floor | +5.9 | +8.3 | +6.4 |
| verses | 22/22 | 23/23 | 18/18 |
| tool calls | 39 | 59 | 57 |
| NT searches (concord.py invocations) | 21 | 31 | 79 (batched, one batch re-run) |
| tokens (harness total) | 296k | 368k | 437k |
| store after the chapter | 117 | 188 | 256 |

**Quality:** in the expected band. Ruth 3 is the hardest chapter for retrieval (the lowest floor) and
almost all dialogue (Naomi's instructions, the night scene, Boaz's speech); the margin sits between
chapters 1 and 2. Best verses 3:2, 3:11, 3:12 (57–59); weakest 3:15 (the six measures of barley), 3:10,
3:5 (32–38). The agent's "least sure" list (3:1, 3:3, 3:7, 3:9, 3:12–14, 3:18) overlaps only partly.

**The pack did not reduce the work.** The agent read it, then ran 79 searches, batched several per
Bash call. Its own account: about 6 of 18 verses came from the pack and chapters 1–2 alone; the rest
needed searches for the chapter's own vocabulary and constructions (lie down, wash, anoint, dress,
threshing floor, winnow, midnight, secretly, startled, cover, want, recognise, shawl, pour, the oath,
"whatever you say", the negative future). The query log confirms it: nearly all searches are English
phrase or construction patterns (`lie down|lay down|asleep`, `no one know|let no one`, `whatever
(you|He|I) (say|ask)`, `until (morning|daybreak)`), not single words.

**What was wrong with the pack (the agent's points, checked):**
1. The "most similar verses" (bag-of-words overlap on the BSB) find verses that share rare words
   (winnowing → Luke 3:17) but rarely the construction the verse needs. The agent's searches were
   phrase-level; the pack's retrieval is word-level.
2. Some lexicon rows were noise (lie, lies, midnight, threshing): low-count renderings shown as if
   usable.
3. Reading cost grew rather than fell: the pack (≈20k tokens) came on top of the store (256 entries)
   and the batched search outputs, so the agent ingested about twice as much new context as in Ruth 2.

**What worked:** the store keeps growing cleanly (49 decisions, 19 observations added; validator
clean); formulas from chapters 1–2 were reused verbatim; names stayed consistent.

**Next (pack v2):**
- phrase-level retrieval: for each verse, match 2–4-word BSB phrases against the corpus and show the
  verses that share a phrase, with the phrase named;
- the store's formulas matched by their English source phrases, now that there are ~30 of them;
- lexicon rows only with count ≥3 and share ≥0.15, with the share shown;
- the pack replaces reading the store (it carries every matched entry; a `store <id>` lookup for the
  rest), so the agent's context is the pack plus the earlier chapters only;
- an explicit "still needs a search" list per verse (words marked —, phrases with no corpus match),
  and a cap: searches only from that list.
Then Ruth 4 (a new domain again: the legal transaction) to see whether the growing store starts to
pay, and Jonah 1 for transfer to a new book.
