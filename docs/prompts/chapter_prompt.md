# Chapter prompt template

`scripts/make_prompt.py <project> <code> <chapter>` fills in the `{…}` fields from
`export/<project>/project.yaml` and the edition configs, and prints the prompt
for one drafting agent. Edit this template to change the instructions for
all projects. Everything below the line is the prompt.

---

Work in {root}. You are drafting **{book_title}, chapter {chapter}** (`{code}{nnn}`, {n_verses} verses) in **{language_name}**, translated directly from the {orig_language}.

{quarantine_block}

**Contract**, read fully first:
{contract_lines}

**STYLE MODEL, the most important part:** the chapters already drafted in `export/{project}/{code}/` ARE the style. If there are any, read IN FULL before translating:
- chapter 1 of this book;
- the highest-numbered finished chapter below yours;
- one more finished chapter of similar genre (narrative, dialogue, discourse or poetry);
- their `_notes.md`{footnotes_files}.

{style_model_fallback}

Your chapter must read like a direct continuation, by the same translator. Match:
- sentence rhythm and tenses;
- particles and dialogue style;
- headings, quotes and footnote style;
- every recurring formula and name form.

Where your source repeats a phrase that an earlier chapter already rendered, reuse that rendering verbatim.

**Sources:**
- `{orig_path}`: the {orig_name}. This is what you translate.{orig_notes_line}{package_line}
- {assist_files}: the {assist_name}, the ONLY assisting translation. Use no other translation. Consult it verse by verse as a guide to the {orig_language}, and follow its interpretation when the source allows more than one reading. Do not translate from it.{numbering_block}
{style_lines}

**Do NOT open:** {do_not_open}

**Rules:**
{inline_notes_rule}
{notes_rule}
{footnotes_rule}
{header_rule}
{extra_rules}

**Finally:**{tagged_first}
- Run `python3 scripts/wrap_draft.py export/{project}/{code}/{code}{nnn}.{draft_ext}`{tagged_split}.{style_step}
- Run `python3 scripts/check_draft.py {project} {code}` and fix every problem reported for your chapter.{numbering_note}{align_step}

Write only your chapter's files. Report in under 150 words: verse check, {report_items}, new name forms or fixed renderings, top open questions.
