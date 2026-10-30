# Workflow

## Your work copy

Projects live in a **work copy**, not in the template. A work copy is a clone of make-tanakh with the template as a
remote; it shares the template's history, merges its updates and has no tools of its own (`docs/related-repos.md`).

```
git clone https://github.com/bcv-commons/make-tanakh.git my-work && cd my-work
git remote rename origin template
git remote set-url --push template DISABLED     # the template is fetched, never pushed to
git remote add origin <your repo>               # where your work is kept
git push -u origin main
```

- **Updates:** `git fetch template --tags`, then `git merge template/main` or a tag (`git merge v0.1.0`;
  `CHANGELOG.md` says what changed). Afterwards run the contract test (`docs/related-repos.md`, section 7).
- **Tool changes don't happen here.** `scripts/`, `docs/` and `.claude/` stay identical to the template's: `git diff
  template/main -- scripts docs .claude` is empty. A fix goes to make-tanakh as a delivery: the patch (`git diff
  template/main -- <path>`) and what it fixes; it comes back with the next merge. New tools start in
  bcv-commons/make-tanakh-grammar.
- **Your content is data:** your projects in `export/`, your editions' metadata in `import/`, your website.
- **The demos** (`export/dan/`, `export/jam/` and their editions) may be deleted. A later merge that changes them
  then conflicts; keep them deleted (`git rm` the conflicting files).

## Principles

- **Translate from the original:** `orig/heb` (Hebrew/Aramaic), `orig/grc` or `orig/grc-rp` (Greek).
- **One assisting translation:** the BSB, or the MSB for a majority-text NT. It guides to the original and is never
  the text translated. Where the original allows more than one reading, follow the BSB's.
- **Editions are style, not source:** vocabulary, idiom, spelling, checked by frequency counts over the corpus. Where
  the corpus quotes the chapter (an NT quote of an OT verse), take over its wording.
- **The finished chapters are the style:** same tenses, particles, formulas and name forms; repeated phrases verbatim.
- **Clean text, separate notes:** translator notes in `_notes.md` (notes language), reader footnotes in
  `_footnotes.txt` (target language, one per line: `vN Keyword: text`).

## Per project

1. Write a short `style_guide.md`: divine names, quote style, numbers, poetry, name spelling, fixed renderings.
2. Draft one reference chapter, review it with the user, adjust the guide.
3. Draft the rest with one book agent per book (below).
4. A team's decision goes into the store or `style_guide.md` and binds from the next chapter.
5. After a handover or a book, a **consistency pass**: `python3 scripts/check_project.py <project>`; count key terms
   chapter by chapter; fix only **mechanical** differences yourself (identical original, different drafts) and note
   each in the chapter's notes; put every **real choice** in `review_overview.md` (topic · passages · draft ·
   alternative, open questions below) for the user to decide.

## The book agent

One agent per book drafts its chapters in order, in every mode. `python3 scripts/make_prompt.py <project> <code>
--book [a-b] [--handoff N]` prints its prompt (`docs/prompts/book_prompt.md`). Per chapter the agent:

- builds the verse pack and the clause packages just before drafting, so the last chapter's store entries reach them
  (`make_prompt.py` refuses a pack older than the store); the NT's clause packages are on the Greek NT clause layout,
  with the words of the project's Greek text (BGB, or RP for a majority text);
- drafts with the chapter prompt (`make_prompt.py <project> <code> <chapter>`), tagged, OT and NT: each word carries the
  numbers of the source words it renders, and `full_align.py split` makes the draft and its word alignment (`.align`);
- runs `python3 scripts/chapter_check.py <project> <code> <chapter>`: it fixes the format, alignment and quotation
  findings, and reviews the rest (negations, names, …), keeping one only with a line in the notes;
- writes the store entries and the state file `<code>/<code>_state.md` (name forms, formulas, register, open threads,
  last verse, open questions).

**Handover:** after `--handoff` chapters (default 10), or earlier if the conversation grows long, the agent stops after
a finished chapter. A fresh agent continues from the state file, the store and the last chapter; `--book` without a
range starts at the first chapter not drafted.

## Quarantine

Quarantine keeps an edition's text of a book away from the agents, so our draft of it is independent. It is
**required** for a non-free edition, never needed for a public-domain one, and for CC BY / BY-SA only with
`quarantine_attributable: true`.

- `python3 scripts/quarantine.py <project> <code>` moves the book from the edition's `text/` to
  `quarantined/<code>/` and lists it under `quarantine:` in `project.yaml`; `--release` undoes both; `--chapter N`
  says whether chapter N needs it (one the edition lacks doesn't); `--all-editions` includes public-domain editions.
- `make_prompt.py` refuses until it is done; the prompt keeps agents out of `quarantined/` and `source/`.
- Re-run `scripts/align.py` if the project has lexicons. Use **fresh** agents, not forks. Put reports that quote the
  book in `do_not_open:`.

## Draft status

Every chapter is a **draft** until a team publishes it. Drafts may be online, always marked as drafts.

- `status.yaml` lists the chapters that are not plain drafts; `STATUS.md` (generated) shows all, with the draft
  statement.
- `python3 scripts/status.py <project> set <code>[:ch[-ch]] in-review|draft [--by NAME] [--note TEXT]`.
- `python3 scripts/status.py <project> publish <code>[:ch[-ch]] --by NAME [--statement TEXT] [--date YYYY-MM-DD]`
  records the date, the approver, the statement (`publish_statement`) and the file's SHA-256.
- `python3 scripts/status.py <project> check` reports a published chapter changed since; publish it again or set it
  back to `in-review`. Publishing never changes the text.

## When an edition already has the book

`STATUS.md` shows per book which case applies ("Existing edition"):

| Case | Example | Our chapters | The existing edition |
|---|---|---|---|
| **continue** | Danish chapters Den Frie Bibel lacks | drafts in `<code>/` | shown; ours fill its gaps |
| **test** | a team's book held out of the corpus | `_eval/` only (*Test drafts*) | stands; supersedes ours |
| **independent** | an NT book a non-free edition has (Jamaican) | drafts, published as drafts | not shown |
| **alongside** | a book an open edition also has (default) | drafts in `<code>/` | shown beside ours, credited |

**Independent** needs quarantine, and evidence afterwards: `STATUS.md` gives the share of our words in 5+ word runs
found word for word in the edition. Independent literal translations share about 20%; over 40%, or more than 3 runs
of 15+ words per 1000 words, is marked **check** (`quotes.overlap`).

## Licences and quotations

The rules are in `docs/licensing.md`. Agents comply as they write: chapter prompts carry the quotation rule, other
agents' prompts include `python3 scripts/quotes.py <project> --rule`, and the store validator (`language_profile.py
check --project`), `wiki.py lint` and `quotes.py <project> FILE ...` check what they write.
`python3 scripts/check_project.py <project>` is the double check before a commit (`.githooks/pre-commit`; `git config
core.hooksPath .githooks`); when it finds something, fix the cause (prompt, rule, tool) as well as the file.

## Practical notes

- Count verses from `orig/heb` (Hebrew numbering); footnote the BSB numbering where a verse moves chapter.
  `make_prompt.py` lists the shifts (`python3 scripts/vrs.py <code> <chapter>`).
- If an agent stops on a rate limit, resume the same agent.
- Run `scripts/wrap_draft.py` on every draft (100 characters; keeps `vN` with its word; leaves `//` lines alone).
