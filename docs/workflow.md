# Workflow

The way of working here, as the demo projects were drafted (Genesis, Joshua and Daniel in Danish; Genesis 1 in
Jamaican).

## Principles

- **Translate from the original.** The Hebrew/Aramaic (`orig/heb`) or Greek
  (`orig/grc`, `orig/grc-rp`) is the text being translated.
- **One assisting translation only:** the BSB, or the MSB for a majority-text NT.
  It is a guide to the original, never the text being translated. When the
  original allows more than one reading, follow its interpretation.
- **Existing translations are style, not source.** Imported editions give
  vocabulary, idiom and spelling. Check word choices with frequency counts over
  the corpus. Where the corpus quotes the chapter (e.g. an NT quote of an OT
  verse), take over its wording.
- **The finished chapters ARE the style.** Every new chapter must read like a
  continuation by the same translator: same tenses, particles, formulas, name
  forms. Repeated phrases are reused verbatim.
- **Clean text, separate notes.** The draft has no inline notes. Translator
  notes go to `_notes.md` (in the notes language), reader footnotes to
  `_footnotes.txt` (in the target language, one per line as `vN Keyword: text`).

## Per project

1. Write a short `style_guide.md` first: divine names, quote style, numbers,
   poetry, spelling rules for names, and a table of fixed renderings.
2. Draft one reference chapter, review it with the user, and adjust the guide.
3. Draft the rest **one chapter after another**, by **one book agent** per book, in every mode: `python3 scripts/make_prompt.py <project>
   <code> --book` prints its prompt (`docs/prompts/book_prompt.md`). The agent keeps the story, the characters and its
   own recent choices in view, and for each chapter
   - builds the chapter's verse pack and (OT) clause packages just in time, after the previous chapter's store
     entries, so what one chapter learns reaches the next (`make_prompt.py` refuses a pack older than the store);
   - drafts it with the chapter prompt (`make_prompt.py <project> <code> <chapter>`), its contract;
   - runs `python3 scripts/chapter_check.py <project> <code> <chapter>`: the format, alignment and quotation checks it
     must fix, and the lost negations, names that differ from the earlier chapters and (Hebrew) the copy check, which
     it reviews, keeping one only with a line in the notes;
   - writes the store entries and the book's **state file** (`<code>/<code>_state.md`): name forms, fixed formulas,
     register decisions, open threads, the last verse, open questions.

   **Handover:** after ten chapters (`--handoff N`), or earlier when its conversation grows long, the agent stops after
   a finished chapter, and a fresh one continues from the state file, the store and the last chapter
   (`make_prompt.py <project> <code> --book` starts at the first chapter not drafted). No waves: a wave builds its
   packs in advance and misses what its own chapters learn, and its chapters can't see each other's choices.
4. Watch each report; a team's decision enters the store or `style_guide.md` and binds from the next chapter on.
5. After a run of chapters (a handover, a book), a **consistency pass**:
   - `python3 scripts/check_project.py <project>`: drafts, store, wiki, quotations, status;
   - count key terms across all chapters (one regex per term, chapter by chapter);
   - make only **mechanical** fixes yourself: where the original is identical
     and only the drafts differ. Note each fix in the chapter's notes.
   - every **real choice** goes into `review_overview.md` as a table
     (topic · passages · draft · alternative), with the chapters' open
     questions collected below it. The user decides; decided items are binding
     for the chapters after.
6. Update `style_guide.md` with each decision.

## Quarantine

To translate a book independently of an existing translation of the same book
in the target language. **Required** when that edition is non-free: our drafts are public domain and
must not be built on its text. A public-domain edition may be used as it is; an attributable one
(CC BY, CC BY-SA) is the project's choice (`quarantine_attributable: true` to require it).

- `python3 scripts/quarantine.py <project> <code>` moves the book's files from
  `import/<licence>/<language>/<edition>/text/` to `<edition>/quarantined/<code>/` and lists the book
  under `quarantine:` in `project.yaml` (`--release` undoes both). `make_prompt.py` refuses to write a
  prompt for a book a non-free edition has until this is done, and the prompt keeps the agents out of
  `quarantined/` and the edition's `source/`. Re-run `scripts/align.py` for a project with lexicons;
- use **fresh** agents (not forks of a conversation that has seen the text);
- keep comparison reports and notes that quote the quarantined book out of the
  agents' reach (`do_not_open:` in `project.yaml`).

Afterwards the overlap can be measured verse by verse against the returned
book (exact matches, matches ignoring punctuation, mean similarity).

## Draft status

Every chapter is a **draft** until a team publishes it. Drafts can be online from the first day, always
marked as drafts; publishing is the team's act, recorded with a date and a statement.

- `status.yaml` in the project lists the chapters that are not plain drafts; `STATUS.md` (generated) shows
  every chapter's status and the draft statement, and is what readers of the repository and of a site see.
- `python3 scripts/status.py <project> set <code>[:ch[-ch]] in-review --by NAME [--note TEXT]` when a team
  starts on a chapter; `set … draft` takes it back.
- `python3 scripts/status.py <project> publish <code>[:ch[-ch]] --by NAME [--statement TEXT]` records the
  status `published`, the date, who approved it, the publishing statement (project `publish_statement`,
  with `{by}` and `{date}`) and the file's SHA-256.
- `python3 scripts/status.py <project> check` reports a published chapter whose file changed since; publish
  it again (a new date) or set it back to `in-review`.
- The texts themselves are not changed by publishing: the status lives beside them, so a draft and its
  published form are the same file.

## When an edition already has the book

Our drafts and an existing edition of the same book (or chapter) live side by side in one of four ways;
`STATUS.md` shows which, per book ("Existing edition").

| Case | Example | Our chapters | The existing edition |
|---|---|---|---|
| **continue** | Danish Genesis 20–50 after Den Frie Bibel's 1–19, 28 | drafts in `<code>/` | shown; ours fill its gaps |
| **test** | a book a language team has translated, held out of the corpus | `_eval/` only, never drafts | stands; the team's translation supersedes ours |
| **independent** | an NT book beside a non-free edition that has it (Jamaican) | drafts in `<code>/`, published as drafts | non-free: stays in `import/non-free/`, not shown |
| **alongside** | an open (CC0, CC BY, CC BY-SA) edition of a book we also draft | drafts in `<code>/` | shown next to ours, with its credit |

- **independent** needs the quarantine while drafting (*Quarantine* above), and evidence afterwards:
  `STATUS.md` gives the share of our words in runs of 5+ words that stand word for word in the edition's
  text of the book. Independent literal translations of the same source share about 20% (Danish Genesis
  drafted in quarantine against Den Frie Bibel: 20%); over 40%, or more than 3 runs of 15+ words per 1000 words, is marked **check**
  (`quotes.overlap`).
- **test** chapters are written to measure the method on a book a language team has translated
  (`learn-language`); they stay in `_eval/` with their reports and are listed under *Test drafts*.
- **alongside** is the default for an open edition; with `quarantine_attributable: true` an
  attributable one is treated like a non-free one.

## Licences and quotations

What we derive from an edition is ours and CC0; quotations from a non-free one are short, unchanged,
from the published text and credited (`docs/licensing.md`); public-domain and CC BY / BY-SA editions are
credited (`CREDITS.md`, `python3 scripts/quotes.py <project> --credits`).

The agents keep to this as they write, not afterwards:
- every chapter prompt carries the quotation rule (`make_prompt.py`, from `quotes.rule_text`); a prompt for
  any other agent (curation, revision, wiki work) includes `python3 scripts/quotes.py <project> --rule`;
- the tools enforce it where agents write: the store validator (`language_profile.py check --project`)
  rejects evidence forms over 4 words and quotations over 15 words, from the working copy or without
  the edition's marks; `wiki.py lint` checks the wiki; `quotes.py <files>` an agent's notes;
- `python3 scripts/check_project.py <project>` is the double check after a run of chapters and before a
  commit (`.githooks/pre-commit`, enabled with `git config core.hooksPath .githooks`). When it finds
  something, fix the cause (prompt, rule, tool) as well as the file.

## Practical notes

- Hebrew verse numbering differs from the BSB in places; always count verses
  from `orig/heb`. Mention the BSB numbering in a footnote where a verse moves to
  another chapter. `make_prompt.py` lists the shifted verses and the BSB chapters
  to consult, from `orig/vrs/` (`python3 scripts/vrs.py <code> <chapter>`).
- If an agent stops on a rate limit, resume the same agent rather than starting a new one.
- Run `scripts/wrap_draft.py` on every draft (100 characters, keeps `vN`
  attached to its word, leaves `//` poetry lines alone).
