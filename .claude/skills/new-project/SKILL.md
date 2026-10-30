---
name: new-project
description: Set up a new drafting project (target language, textual basis, style corpus, style guide, memory, reference chapter). Use when the user wants to start translating into a new language or style, or asks to create a project.
---

# Start a drafting project

The whole path is `docs/onboarding.md`; fields are in `docs/configuration.md` and the template's comments. Two
settings decide how every tool works (`scripts/modes.py`): the **familiarity** (how well the model knows the
language) and the **licence class** of the editions.

0. **A new language: the wizard.** `python3 scripts/onboard.py`: ask the user its questions, write the answers to a
   YAML file, run `--answers FILE --dry-run`, then `--answers FILE --yes`. It fetches and imports the editions, writes
   `project.yaml`, runs the probes and creates the empty memory; continue at step 3.
1. **Ask** (don't guess): the target language and its code (BCP 47); the team's `school_language` (wiki, store
   notes, analysis) and `notes_language`; which editions it continues or imitates (in `import/` first:
   import-edition skill); for the NT the basis (`critical`: BGB + BSB; `majority` or `tr`: RP 2018 + MSB),
   inherited from `based_on` unless set; the books to quarantine.
2. **Create it:** copy `export/_template/` to `export/<lang>/<project>/` (CC0: our own work, a revision only of a
   CC0 edition; continuing an edition or using it as style corpus is fine with any licence). Work derived from
   another edition goes to `export/CC-NC/` or `local_output/` (`docs/licensing.md`, *Three output paths*). Fill in
   `language`, `language_name`, `school_language`, `notes_language`, `based_on` / `style_from`, `nt_basis` if needed,
   `quarantine`, `do_not_open`, `quotes`, `chapter_word`, `book_titles`, `rules`.
3. **Familiarity:** `python3 scripts/probe_language.py <project> run` sends the probes (write, read, tell apart) to
   a fresh model with no tools and suggests a value; set `familiarity` (and `close_to` for a variety). Then
   `python3 scripts/project.py <project> <code>` (resolved sources) and `python3 scripts/modes.py <project>` (the mode
   and what it switches on). The sources must exist (`python3 scripts/setup.py`, `--heb ...` for the Tanakh).
4. **`style_guide.md`**, short, with the user: divine names, quotes, numbers, poetry, names, a table of fixed
   renderings; take what you can from the corpus, with counts, and mark what the user must decide.
5. **The memory** (`docs/onboarding.md`, step 4): `python3 scripts/align.py <project>`, then
   `python3 scripts/memory_prompt.py <project> --init` for a fresh agent. For `familiarity: unknown` use the
   `learn-language` skill instead.
6. **Reference chapter:** draft one with the draft-chapter skill, review it with the user and adjust the style guide;
   then a book agent drafts the rest, chapter after chapter.

Don't commit; the user commits.
