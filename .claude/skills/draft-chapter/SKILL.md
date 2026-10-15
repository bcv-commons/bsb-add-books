---
name: draft-chapter
description: Draft one or more Bible chapters for a project in export/<project>/, from the Hebrew or Greek with the BSB/MSB as the only assisting translation, one fresh agent per chapter. Use when asked to draft, translate or continue chapters, or to run a drafting wave.
---

# Draft chapters

The full way of working is `docs/workflow.md`; this is the procedure.

## Before the first chapter

1. **Sources built?** `reference/BSB/`, `reference/MSB/` and `orig/` must exist. If not: `python3 scripts/setup.py`
   (for the OT also `--heb bhsa,bcv-query`: agents draft on the BHSA layout in `orig/heb/`; ask the user if
   the project is commercial, then `--drafting bcv-query`).
2. **Project resolved?** `python3 scripts/project.py <project> <code>` shows the original,
   the assisting translation, the style corpus and the quarantine. Check it with the user if
   anything looks unexpected (e.g. the wrong `nt_basis`).
3. **Style guide and decisions:** `export/<project>/style_guide.md` must exist (see the
   new-project skill). If the project has no finished chapter yet, draft a single reference
   chapter first and review it with the user before any wave.

## A wave (about ten chapters)

1. **Fix shared terms first.** Chapters in the same wave can't see each other. List the names,
   titles and recurring terms the chapters will share, agree them with the user (or take them
   from `style_guide.md` / `review_overview.md`), and add them to the prompts.
2. **One fresh agent per chapter.** For each chapter:
   - `python3 scripts/verse_pack.py <project> <code> <chapter>` builds the verse pack first, at the level the project's
     mode sets (`memory`, `dialect` or `full`; `python3 scripts/modes.py <project>`). The prompt points the agent to it,
     and its rules apply only when the pack exists;
   - for an OT chapter, `python3 scripts/package.py <project> <code> <chapter>` builds the clause packages (it needs
     `orig/heb.sqlite`: `python3 scripts/src.py build` once; for an unknown language with an NT, the occurrence index
     `python3 scripts/lang.py build <project>` after `align.py`). `make_prompt.py` refuses an OT prompt without them;
   - `python3 scripts/make_prompt.py <project> <code> <chapter>` prints the prompt (OT: tagged drafting; `--end-align`
     gives the old way, the draft first and the alignment at the end);
   - give it, unchanged except for the shared terms, to a **new** agent (Agent tool, not a
     fork of this conversation: a fork has seen other chapters, and for a quarantined book it
     may have seen the existing translation);
   - agents of one wave can run in parallel.
   - If an agent stops on a rate limit, resume that agent; don't start a new one.
   - When an agent finishes, log what it cost from its usage report: `python3 scripts/usage.py <project> add
     <code><NNN> --tokens N --calls N --minutes M`. The wizard's estimates per mode come from these logs.
3. **Check each result** when the agent reports:
   - `python3 scripts/check_draft.py <project> <code>`: verse markers against the original,
     no inline notes, balanced quotes, line length, notes and footnote files;
   - `python3 scripts/wrap_draft.py export/<project>/<code>/<code>NNN.txt` if lines are long;
   - OT chapters whose verses fall into other BSB chapters are reported as information: the
     draft keeps the Hebrew numbering.
   - OT chapters: the agent writes `<code>NNN.tagged` (its words with the Hebrew token numbers) and `full_align.py
     split` makes the `.txt` and the `.align` (the bcv-commons format, profile `b`) from it; the `.tagged` file is the
     working copy (git-ignored): a correction goes into it, then `split` again (`full_align.py tag` rebuilds it from the
     `.txt` and `.align` when it is gone). `python3 scripts/full_align.py check <project> <code> <chapter>` must say ok;
     the website's clause views are built from the `.align`. An existing chapter without one: `python3
     scripts/bridge_align.py` (script, profile `a`), then optionally `python3 scripts/full_align.py prompt <project>
     <code> <chapter>` for a fresh agent that checks it.
   - The prompt already makes the agent keep to the quotation rules (`docs/licensing.md`) and check its
     own files; at the end of the wave run `python3 scripts/check_project.py <project>` (drafts, store,
     wiki, quotations, status) as the double check, and fix the cause in the prompt or the rules when
     it finds something the agents should have avoided.

## After the wave: consistency pass, then review

- Count the key terms across all chapters (one regex per term, chapter by chapter).
- Make only **mechanical** fixes yourself: where the original is identical and only the drafts
  differ. Note each fix in that chapter's `_notes.md`.
- Every **real choice** goes into `export/<project>/review_overview.md` as a table
  (topic · passages · draft · alternative), with the chapters' open questions below it. The
  user decides; decided items are binding for later waves.
- Update `style_guide.md` with each decision.
- **Offer the review:** ask the user whether the wave's chapters go to the team now. If so,
  `python3 scripts/status.py <project> set <code>:<first>-<last> in-review --by <who>` marks them (and rewrites
  `STATUS.md`); the team reads them with `python3 scripts/wiki.py view <project>` and the draft files. Publishing
  is the team's decision: `status.py publish … --by NAME` only when they say so.

## Rules that always hold

- The original is what is translated; the BSB (or MSB) is a guide to it, never the source.
- Existing editions in `import/` are style, not source. A book that a non-free edition has is drafted
  only in quarantine (`python3 scripts/quarantine.py <project> <code>`; `make_prompt.py` refuses
  otherwise), and a quarantined book must never be opened by a drafting agent (`docs/workflow.md`).
- Clean text: no inline notes. Translator notes go to `_notes.md`, reader footnotes to
  `_footnotes.txt` (`vN Keyword: text`).
- Clause lines from `orig/heb` are guidance, not a law: a draft may keep a natural word order
  and render two Hebrew clauses in one line.
- Don't commit; the user commits.
