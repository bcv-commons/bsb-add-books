# Genesis 1: our draft against the human Kuni Genesis

Our draft (`genesis-test/gen001.txt`) was made on 2026-10-15 by one fresh agent with the tagged clause packages, before the
Kuni team's Genesis 1–30 arrived (2026-10-15, `source/` of the edition). It is a clean test: no agent had seen the human text.
Since then Genesis is part of the corpus, and the draft is kept here as a test.

| | chrF (marks ignored) | as written |
|---|---|---|
| our draft | **65.8** | 62.8 |
| retrieval floor (nearest Kuni verse) | 56.8 | 55.1 |
| lexical floor (word by word) | 40.2 | 38.7 |

The best Kuni test so far (Ruth 1–4: 60.1–64.3) and the widest margin over the retrieval floor (+9.0; Ruth +5.9 to +8.5).
Per verse 38.6–81.3; 1:1 is 81.3.

Where it differs, in three systematic places:

1. **The day formula** ("and there was evening, and there was morning: the Nth day", 1:5, 8, 13, 19, 23, 31) is the
   lowest group (1:13 42.4, 1:19 38.7, 1:23 39.8). Our draft built the ordinal on Luke 24:21's "the third day"
   (*Khøuwa mø̀ndømø-misika-éz*), rated "high" because the NT phrase matched exactly; the human text uses another
   construction (*gè-* with the number) and another wording for evening and morning. A store correction; it recurs
   in the genealogies.
2. **The name given to the light** ("he called the light Day"): the human text uses another word than *Khøuwa*.
3. **1:2** (38.6): the human text explains and is about twice as long, as the Ruth translators do.

Score: `python3 scripts/score.py kvg/kvg_BSB export/kvg/kvg_BSB/_eval/genesis-test/gen001.txt` (the scored book is
left out of the floors' corpus).
