---
name: learn-language
description: Prepare a project for a target language the model doesn't know (little or no LLM exposure), so drafting agents can learn it from an existing translation - alignment lexicons, concordance, language store, wiki, verse packs, and a held-out test. Use when the user wants to draft in a low-resource language, asks what is possible for an unknown language, or wants to set up the toolkit for a new language.
---

# Learn a language from its existing translation

The path and its reasons: `docs/onboarding.md`; the store's format: `docs/language-store.md`; fields:
`docs/configuration.md`. A finished project of another language in this working copy, if there is one, is the
worked example.

1. **Ask first:** which edition is the corpus, its licence (the import folder, and whether lexicons, packs and wiki
   can be published), whether it has Tanakh books; whether a book with a human translation is **held out** as a test
   (`python3 scripts/quarantine.py <project> <code>`, out of the corpus until the tests are done); who reviews the
   drafts (the language team), and their school language.
2. **Import and set up:** `python3 scripts/onboard.py` (or the `import-edition` and `new-project` skills) with
   `familiarity: unknown`, which gives every chapter prompt the unknown-language rules (`docs/prompts/modes.md`), the
   full verse pack and the style check. In `project.yaml` add `tokenise:` (suffixes after a hyphen? characters such
   as `꞉` that belong to words?) and in `rules` only what is specific to the language (divine names).
3. **Align and derive:** `python3 scripts/align.py <project>` (eflomal if installed); read `_learn/align_report.txt`
   (the glossary and name checks show how far to trust the lexicons). `python3 scripts/lang.py layers <project>
   --write` sets a bcv-commons alignment layer built on exactly this text as `lexeme_aligner`. Then, with
   `orig/grc.sqlite` (`python3 scripts/setup.py --only src`): `python3 scripts/lang.py build <project>` (the NT
   occurrence index; `lang.py hbo <project> <lexeme>` shows how the NT renders a Hebrew word through the LXX) and
   `lang.py derive <project>` + `report <project>`: word order, function words, connectors, affix hypotheses, name
   letters, formulas, Tanakh gaps.
4. **Build the store and the wiki:** `python3 scripts/memory_prompt.py <project> --init` creates them empty and prints
   the prompt for a fresh agent, which starts from the derived report and confirms or rejects each item against the
   corpus. A first test chapter's grammar sketch can seed the wiki (`python3 scripts/wiki.py init <project>
   --from-notes FILE --map MAP.json`). Validate with `python3 scripts/language_profile.py check
   export/<lang>/<project>/profile --project <project>`.
   - **Writing system:** the tone marks and accents the corpus uses go into every store value exactly
     (`language_profile.py check` lists values with other marks). `python3 scripts/morphs.py <project> tone
     [--write]` detects how the corpus writes tone and stores it as `orthography.tone`; check it with the team or a
     grammar, and keep a two-layer orthography's quality marks out of it. `orthography.ignore_marks` only loosens
     the search tools.
   - **Glosses:** terms, formulas and names say what they mean in Greek or Hebrew (`gloss`), never in English inside
     the value (`docs/language-store.md`, *Glosses*). `python3 scripts/gloss.py propose <project> [--write]` proposes
     them from the alignment; the memory agent checks the proposals and glosses what is left.
   - **Grammar:** `python3 scripts/grammar.py run <project> --write` adds the Grambank features the store's morphs
     answer (questions: `setup.py --only grambank`); `grammar.py plan <project>` lists what to settle next, for the
     curation agent: it proposes, the corpus counts decide.
   - **Affix chains** (subject, tense, object before a verb stem, as in many Bantu languages): morph entries with
     `position` and `greek`; `python3 scripts/morphs.py <project> try --write` measures each against the Greek (the
     agent revises the rejected ones), and `morphs.py <project> check` must rebuild the corpus word for word. The
     packs, `concord.py`, the spelling check and `chapter_check.py` then work with the words' parts. Once the store has
     confirmed affixes, rerun `align.py <project>` (then `lang.py build`): it aligns the affixes themselves (by parts,
     gaps filled by word links); `morphs.py try` and `rates` before and after show what it changed. Words an affix
     only seems to begin or end (a noun beginning like a verb prefix): `morphs.py <project> audit` and the
     `audit-store` skill (protected words, kind `word`). Parts written with a hyphen (a person part in *x-stem*, a clitic
     after a noun): `written: hyphen` on the morph (`docs/language-store.md`); with Tanakh books, `audit --route all`.
   - **The family brief first** (before the store work): a fresh research agent, effort high, with
     `python3 scripts/seeds.py brief <project>` reads the grammars of the language, its relatives and the family and
     writes the brief (`docs/language-store.md`, *The brief*: `profile/brief.md`, or `_eval/local/brief.md` when a
     source is NC/ND/non-free) and a seed per testable point. The memory agent then tests the seeds on the corpus;
     `python3 scripts/seeds.py brief --check <project>` shows which points are confirmed, contradicted or open.
   - **A related language the model knows** (the project's `donor`: `python3 scripts/donor.py run <project> --write`,
     Glottolog and write probes; the wizard does it): a fresh agent with `python3 scripts/seeds.py prompt <project>`
     writes what the model knows of it, from memory, as seeds (`profile/seeds.json`, `docs/language-store.md`, *Seeds*):
     hypotheses that nothing enforces, which the memory agent tests (`morphs.py <project> try --seeds --write`) and
     answers with entries naming them (`seed: <id>`). `python3 scripts/seeds.py status <project>` shows what is left.
   - **The team:** `python3 scripts/team_input.py <project> init`, then `prompt` for a curation agent: their items
     become binding store entries. `python3 scripts/wiki.py view <project>` gives them one offline HTML file to read
     (a copy: edits go into the `.md` pages).
5. **Draft:** the `draft-chapter` skill, one book agent per book; it builds each chapter's verse pack (level `full`)
   and runs `chapter_check.py` in its loop.
6. **Test** (with a held-out book): `python3 scripts/score.py <project> <draft> --reference <held-out file>` per
   chapter against its floors; `python3 scripts/style.py <project> <draft>` measures the style against the human
   translations. Log tokens (`usage.py`) and write a report per chapter in `_eval/`.
7. **Lift the holdout** when the user decides (`quarantine.py <project> <code> --release`): re-run `align.py`, let a
   curation agent audit the store and the wiki against the human text (it supersedes), and open `_eval/` to the
   agents.

What the toolkit derives is CC0 even from a non-free edition; quotations keep to `docs/licensing.md` (a `credit`
line, `python3 scripts/quotes.py <project> --credits`). A curation or revision agent gets `quotes.py <project> --rule`
in its prompt and runs the store validator, `wiki.py lint` and `quotes.py` on its files; `check_project.py` is the
double check. Don't commit; the user commits.
