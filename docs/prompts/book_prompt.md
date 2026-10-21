# Book prompt template

`scripts/make_prompt.py <project> <code> --book [<first>-<last>] [--handoff N]` fills in the `{…}` fields and prints the prompt
for one book agent: it drafts the book's chapters one after another (docs/workflow.md, *The book agent*), each with
the chapter prompt it prints itself, and hands over to a fresh agent after `{handoff}` chapters. Edit this template to
change the loop for all projects. Everything below the line is the prompt.

---

Work in {root}. You are the book agent for **{book_title}** in the project `{project}`, into {language_name}. You draft
chapters {first} to {last}, in that order, one after the other, as the same translator: what you decide in one chapter
holds in the next. {resume}

For each chapter N:
1. Read `{state}` if it exists: your state file (below), and the one a former agent of this book left you.
2. Build the chapter's materials just in time, after the previous chapter's store entries:
   {materials}
3. Print the chapter's prompt: `python3 scripts/make_prompt.py {project} {code} N`. It is your contract for the chapter:
   follow every rule in it (sources, {draft_kind}, notes, footnotes, the quotation rule, the files it names as not to
   be opened). Where it speaks of the style model, the earlier chapters are your own.
4. Check before you go on: `python3 scripts/chapter_check.py {project} {code} N`. Fix every `FIX` line (it fails
   until none is left). Look at every `REVIEW` line: fix the draft where it is wrong; where you keep it, say why in
   the chapter's `_notes.md` in one line.
5. Write what the chapter taught: the store entries the chapter prompt asks for, and `{state}` (short, in
   {notes_language}): name forms, recurring formulas and their fixed wording, the register decisions (tenses in
   narrative, how speech is introduced, forms of address), terms, the open threads of the story, the last verse
   drafted, and open questions, each with its chapter. Add each fixed rendering also to the table "Fixed
   renderings" in `{style_guide}`.

**Handover.** After {handoff} chapters, or earlier if this conversation has grown long, stop after a finished
chapter (step 5 done): what matters is in the files, not in this conversation. A fresh agent continues from the state
file, the store and your last chapter. Don't start a chapter you can't finish.

Rules that hold throughout:
- The original is what you translate; the assisting translation is only the check for the meaning. Use no other
  translation, no web search, and nothing outside the sources the chapter prompts name.
- Write only the files of this book (and the style guide's table, the store).{extra_rules}

At the end, report in under 250 words: per chapter its `chapter_check.py` summary line and the main decisions; then
the last chapter done, whether you handed over, and the open questions for the user.
