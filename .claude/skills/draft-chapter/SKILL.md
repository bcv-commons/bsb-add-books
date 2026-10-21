---
name: draft-chapter
description: Draft one or more Bible chapters for a project, from the Hebrew or Greek with the BSB/MSB as the only assisting translation, one book agent per book, chapter after chapter. Use when asked to draft, translate or continue chapters or a book.
---

# Draft chapters

The way of working is `docs/workflow.md`; this is the procedure.

## Before the first chapter

1. **Sources:** `reference/BSB/`, `reference/MSB/` and `orig/` must exist, else `python3 scripts/setup.py`; for the OT
   with `--heb bhsa,bcv-query` (a commercial project drafts with `--drafting bcv-query`: ask the user).
2. **Project:** `python3 scripts/project.py <project> <code>` shows the original, the assisting translation, the style
   corpus and the quarantine; check anything unexpected with the user (e.g. the wrong `nt_basis`).
3. **Style guide:** the project's `style_guide.md` must exist (new-project skill). With no finished chapter yet,
   draft one reference chapter first and review it with the user.

## The book agent

One agent per book drafts its chapters one after another, in every mode.

1. **The prompt:** `python3 scripts/make_prompt.py <project> <code> --book [<first>-<last>] [--handoff N]`
   (`docs/prompts/book_prompt.md`); without a range it starts at the first chapter not drafted. Per chapter the agent
   builds the materials just in time (`verse_pack.py`, for the OT also `package.py`), prints the chapter prompt
   (`make_prompt.py <project> <code> <ch>`; OT: tagged drafting), runs `python3 scripts/chapter_check.py <project>
   <code> <ch>` until nothing is left to fix, and writes the store entries and the state file `<code>/<code>_state.md`.
2. **Start it as a new agent** (Agent tool, not a fork: a fork has seen other chapters and, for a quarantined book,
   perhaps the existing translation). Give it the prompt unchanged. One book agent at a time per project: its
   chapters write the store that the next chapter's pack reads.
   - An agent stopped by a rate limit is resumed, not replaced.
   - **Handover:** when it stops after its chapters (ten by default), print the prompt again (it continues at the
     next chapter) and give it to a new agent.
   - Log what each agent cost from its usage report:
     `python3 scripts/usage.py <project> add <code><nnn> --tokens N --calls N --minutes M`.
3. **Check its report.** `chapter_check.py` already ran `check_draft.py` (verses, format), the alignment and the
   quotation checks, and the agent filled the notes' Hebrew/Greek from the WLC/BGB (`notes_hebrew.py`; never text
   from `orig/heb/`). OT drafts keep the Hebrew numbering. An OT correction goes into the git-ignored
   `<code>NNN.tagged`, then `python3 scripts/full_align.py split <project> <code> <ch>` (`tag` rebuilds a lost one);
   a chapter without an `.align` gets one from `python3 scripts/bridge_align.py <project> <code> <ch>`. After a
   handover or a book, `python3 scripts/check_project.py <project>` is the double check; when it finds something the
   agents should have avoided, fix the cause in the prompt or the rules.

## After a run of chapters

- Count the key terms across all chapters (one regex per term, chapter by chapter).
- Make only **mechanical** fixes yourself (the original is identical, only the drafts differ), each noted in that
  chapter's `_notes.md`.
- Every **real choice** goes into the project's `review_overview.md` as a table (topic · passages · draft ·
  alternative), with the open questions below it. The user decides; decisions bind the chapters after and go into
  `style_guide.md`.
- **Offer the review:** if the chapters go to the team now,
  `python3 scripts/status.py <project> set <code>:<first>-<last> in-review --by <who>` (rewrites `STATUS.md`); the
  team reads them with `python3 scripts/wiki.py view <project>` and the draft files. Publishing
  (`status.py publish … --by NAME`) only when the team says so.

## Rules that always hold

- The original is translated; the BSB (or MSB) is a guide to it, and editions in `import/` are style, never source.
- A book a non-free edition has is drafted only in quarantine (`python3 scripts/quarantine.py <project> <code>`;
  `make_prompt.py` refuses otherwise), and no drafting agent opens it.
- No inline notes: translator notes go to `_notes.md`, reader footnotes to `_footnotes.txt` (`vN Keyword: text`).
  Clause lines are guidance, not a law. Don't commit; the user commits.
