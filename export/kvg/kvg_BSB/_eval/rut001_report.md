# Kuni Ruth 1: the first drafting test (2026-10-14)

Evaluator's report. This folder (`_eval/`) is on the agents' do-not-open list because it
holds scores against the held-out Kuni Ruth; the agents must not learn from it.

## Setup

- **Language:** Kuni (kvg), Kuni-Boazi, Papua New Guinea. No LLM exposure.
- **What the agent had:** the Kuni NT (`import/non-free/kvg/KVG-KuNT/text/`), its 156-term
  glossary, the baseline alignment lexicons (`_learn/lexicon_eng.tsv`, `lexicon_grc.tsv`, built
  from the NT only) and the learning tool `_learn/concord.py`. The Hebrew (`orig/heb/rut001.txt`,
  clause lines) and the BSB as the only assisting translation.
- **What it must not see:** the Kuni Ruth and Jonah (`holdout/`), lexeme-aligner's data,
  `scratch/`, `download/`, this folder.
- **Run:** one fresh agent, prompt from `make_prompt.py kvg/kvg_BSB rut 1`; 25 minutes, 39 tool
  calls. It first wrote a grammar sketch from the NT (`kvg_learning_notes.md`, 277 lines; superseded by `wiki/`, kept locally in `_eval/local/`), then
  the draft and its notes.
- **Score:** chrF (character n-grams 1–6, β=2) against the published Kuni Ruth 1
  (an early version of `scripts/score.py`), tone marks ignored unless stated.

## Result

| | chrF |
|---|---|
| BSB word by word through the lexicon (lexical floor) | 37.3 |
| copying the nearest NT verse for each verse (retrieval floor) | 57.7 |
| **the agent's draft** | **63.6** (60.9 with tone marks counted) |
| the published text against itself | 100 |

All 22 verses present; `check_draft.py` reports no problems. The draft beats the strongest
no-learning baseline by six points: the agent learned Kuni structure from the NT, not just words.

Per verse:

| verses | chrF | kind |
|---|---|---|
| 1:1, 1:2, 1:16, 1:19 | 60–64 | narrative, and Ruth's "where you go I will go" |
| 1:3, 1:7, 1:10, 1:15, 1:18, 1:22 | 50–57 | narrative with short speech |
| 1:4–6, 1:11, 1:14, 1:17, 1:20 | 42–47 | |
| 1:8, 1:9, 1:12, 1:13, 1:21 | 27–38 | Naomi's arguments and complaint |

Speech verses with little NT precedent are the weak part: conditionals ("if I should have a
husband tonight"), the oath of 1:17, "the LORD has testified against me". The agent's own
"least sure" list (1:13, 1:16a, 1:17, 1:21) overlaps with the low scorers, so its confidence is
informative.

## What the agent produced beyond the draft

- **Grammar sketch** (`kvg_learning_notes.md`): SOV, short sentences chained with "Yaq";
  subject prefixes ge-/gu-/gi- (gu- for a feminine participant); directionals; sequential
  vø̄-; perfective mø̀ndø-; negation -áv/-ák; prohibitive tone patterns; optative be-/bezø-;
  possessive suffixes agreeing with the possessed noun; the speech frame "āv gene-eín nqǽgo";
  name rules (r→l, j→z, th→t, h dropped). Each point with NT references.
- **Names:** Neomi, Elimelek, Malon, Kilion, Opa (Orpah), Mala; from the glossary/NT: Lut
  (Ruth), Moab, Betliem, Zuda. YHWH = Evezøza, Elohim = Mbumbukiam, Shaddai = Mbumbukiam
  Bazaføgakh-qape.
- **Open questions for a Kuni speaker:** *chesed* (tanakh vs kuku); "call me Mara" rendered as
  "my name shall be Mala" (Luke 1:60 pattern); "sister-in-law" as "qogu ezoqam"; Lut (glossary)
  vs Rut (book title); 1:13 comparative vs causal.

## Comparison with lexeme-aligner

Their `kvg_wbt` alignment is right on 69 of 77 one-word glossary terms (our baseline: 64);
corrected for errors of the English-to-Strong's bridge, about 73. Their NT alignment used some
statistics from the Kuni Ruth/Jonah, so the agent was given only our NT-only lexicon. Their
`constituent-order-profile` for Kuni is computed from Ruth and Jonah (130 verses) and is
therefore off limits for this test.

## Next

1. Turn the agent's notes into a language profile (`docs/proposals/language-profile/`), so
   the knowledge is evidenced and reusable: `export/kvg/kvg_BSB/profile/`.
2. Draft Ruth 2 against the profile and measure what the store saves (time, tool calls,
   score).
3. Later: Jonah, as a second book; the comparison with lexeme-aligner's data.
