---
name: new-project
description: Set up a new drafting project in export/<project>/ (target language, textual basis, style corpus, style guide, reference chapter). Use when the user wants to start translating into a new language or style, or asks to create a project.
---

# Start a drafting project

The whole path, for a new language or client, is `docs/onboarding.md`; fields are in
`docs/configuration.md`; the template has comments. Two settings decide how every tool works
(`scripts/modes.py`): the **familiarity** (how well the model knows the language) and the **licence class**
of the editions.

0. **For a new language, start with the wizard:** `python3 scripts/onboard.py` (ask the user the questions,
   write their answers to a YAML file and run it with `--answers FILE --yes`; `--dry-run` first). It imports and
   fetches the editions, writes `project.yaml` and the empty memory; then continue at step 3 below.
1. **Ask what is needed** (don't guess):
   - target language and its code (BCP 47), the language of the translator notes;
   - whether it continues or imitates an existing edition (then that edition must be in
     `import/` first; see the import-edition skill). The drafts in `export/` are public
     domain (CC0), so a project can **revise** only a CC0 edition; continuing an edition
     with new books, or using it as a style corpus, is fine with any licence;
   - for the NT, the textual basis: `critical` (BGB + BSB), `majority` (RP 2018 + MSB) or
     `tr` (RP 2018 + MSB, the closest available). It is inherited from `based_on` unless set;
   - books to quarantine (an independent translation of a book that exists in the corpus);
   - the team's **school language** (`school_language`: the wiki, the store's notes and the analysis are written
     in it; only quotations are in the target language).
   Then probe the familiarity: `python3 scripts/probe_language.py <project>` gives a prompt for a fresh agent
   (no tools); save its answer and score it with `--score`. Set `familiarity` (and `close_to` for a variety).
2. **Create it:** copy `export/_template/` to `export/<project>/` and fill in `project.yaml`:
   `language`, `language_name`, `notes_language`, `based_on` / `style_from`, `nt_basis` if
   needed, `quarantine`, `do_not_open`, `quotes`, `chapter_word`, `book_titles`, `rules`.
3. **Check it:** `python3 scripts/project.py <project> <code>` prints the resolved sources,
   `python3 scripts/modes.py <project>` the mode and what it switches on.
   Make sure the sources exist (`python3 scripts/setup.py`, and `--heb ...` for the OT).
4. **Write a short `style_guide.md`** with the user: divine names, quote style, numbers and
   measures, poetry layout, spelling of names, and a table of fixed renderings. Take what you
   can from the style corpus, with frequency counts, and mark what the user must decide.
5. **Build the memory** (`docs/onboarding.md`, step 4): `python3 scripts/align.py <project>`, then a fresh agent
   with the prompt from `python3 scripts/memory_prompt.py <project>`. For `familiarity: unknown` use the
   `learn-language` skill instead.
6. **Reference chapter:** draft one chapter with the draft-chapter skill, review it with the
   user, and adjust the style guide before the book agent drafts the rest, chapter after chapter.

Don't commit; the user commits.
