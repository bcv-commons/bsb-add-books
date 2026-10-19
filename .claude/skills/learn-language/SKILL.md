---
name: learn-language
description: Prepare a project for a target language the model doesn't know (little or no LLM exposure), so drafting agents can learn it from an existing translation - alignment lexicons, concordance, language store, wiki, verse packs, and a held-out test. Use when the user wants to draft in a low-resource language, asks what is possible for an unknown language, or wants to set up the toolkit for a new language.
---

# Learn a language from its existing translation

The plan and the reasons are in `docs/proposals/language-toolkit/README.md`; a finished project
of another language in this working copy, if there is one, is the worked example. Fields: `docs/configuration.md`.

1. **Ask first:**
   - which edition is the corpus, its licence (this picks the import folder and whether lexicons, packs and
     the wiki can ever be published), and whether it has OT books;
   - whether a book with a human translation can be **held out** as a test (`python3 scripts/quarantine.py <project> <code>`, and keep its
     files out of the corpus until the test series is done);
   - who will review the drafts (the language team), and in which language the notes are written.
2. **Import and set up:** `import-edition`, then `new-project` with `style_from` the edition. In
   `project.yaml` add `tokenise:` (does the orthography write suffixes after a hyphen? characters such as
   `꞉` that belong to words?) and the rules of the Kuni project: no knowledge of the language assumed,
   everything modelled on the corpus, the verse pack first, searches only for what the pack lacks, every
   search ending in a store entry, the wiki, divine names, a notes file with the model verses.
3. **Align:** `python3 scripts/align.py <project>` (eflomal if installed; see the toolkit's *External
   tools* for macOS). Read `_learn/align_report.txt`: the glossary and name checks show how far to trust the
   lexicons. lexeme-aligner may already have the language: compare, and cite its data as `external`.
   Then the occurrence index and the derived products: the Greek structure
   (`orig/grc.sqlite`, fetched by `python3 scripts/setup.py --only src`), `python3 scripts/lang.py build <project>` (every NT token linked to a MACULA Greek
   token; `lang.py hbo <project> <lexeme>` shows how the NT renders any Hebrew word through the LXX) and
   `python3 scripts/lang.py derive <project>` + `report <project>`: word order, function words, connectors, affix
   hypotheses (endings against the Greek features), name letters, formulas, OT gaps. Give the report to the agent
   of step 4 as its starting point: `python3 scripts/memory_prompt.py <project>` does that by default when the
   occurrence index exists (`--no-derived` without it); the agent confirms or rejects each item against the corpus.
   Measured on Kuni (NT only): one such study run found 73% of the topics of the curated store, 195k tokens.
4. **Seed the store and the wiki:** a first agent drafts one chapter and writes a grammar sketch; turn it
   into `profile/observations.json` + `decisions.json` (`docs/proposals/language-profile/`, validate with
   `python3 scripts/language_profile.py check export/<project>/profile --project <project>`) and seed the
   wiki with `python3 scripts/wiki.py init <project> --from-notes FILE --map MAP.json`. For people who
   want to read it (and add what they know), `python3 scripts/wiki.py view <project>` builds one offline HTML
   file (pages, open questions, a searchable store); it is a copy, so edits go into the `.md` pages.
   Check the writing system first: which tone marks and accents the corpus uses, written into every store value
   exactly (`language_profile.py check` lists values with other marks). `orthography.ignore_marks` only loosens the
   search tools. The team's own facts come in through `wiki/team-input.md` (`python3 scripts/team_input.py <project>
   init`, then `prompt` for the curation agent); they are binding.
5. **Draft with packs:** for each chapter `python3 scripts/verse_pack.py <project> <code> <ch>`, then the
   `draft-chapter` skill (fresh agent per chapter; the pack and `wiki/index.md` in `style_guides`).
6. **Test** (if a book is held out): score each chapter with `python3 scripts/score.py <project> <draft>
   --reference <held-out file>` and compare with the floors (retrieval, word by word); record tool calls,
   searches, time and tokens per chapter. `python3 scripts/style.py <project> <draft>` measures the style
   against the human translations (no held-out book needed); `style_check: true` has the drafting agent run it. Write a report per chapter in `_eval/`.
7. **Lift the holdout** when the user decides (`python3 scripts/quarantine.py <project> <code> --release`): the book returns to the corpus; re-run `align.py`, let a
   curation agent audit the store and the wiki against the human text (the human version supersedes), and
   open `_eval/` to the agents.

What the toolkit derives is CC0 even from a non-free edition; the edition's text stays in `import/non-free/`, and
quotations keep to `docs/licensing.md`: give the edition a `credit` line and run `python3 scripts/quotes.py <project> --credits`.
Agents comply as they write: chapter prompts carry the quotation rule; for any other agent (curation, revision) put
the output of `python3 scripts/quotes.py <project> --rule` into its prompt, and have it run the store validator with
`--project`, `wiki.py lint` and `quotes.py` on its files. `python3 scripts/check_project.py <project>` is the double
check afterwards. Don't commit; the user commits.
