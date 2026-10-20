# Memory set-up prompt

`scripts/memory_prompt.py <project>` fills in the `{…}` fields and prints the prompt for one fresh agent
that builds (or extends) a project's memory: the language store (`profile/`) and the wiki (`wiki/`), from
the style corpus and the project's own drafts and decisions (`docs/onboarding.md`, step 4). The focus
depends on the project's familiarity (`scripts/modes.py`). Everything below the line is the prompt.

---

Work in {root}. You are building the **language memory** of the project `{project}`: **{language_name}**,
drafted from the Hebrew and Greek with the BSB as the only assisting translation. Later drafting agents
read this memory before every chapter; the language team reads and edits the wiki. {language_rule}

**What the memory is** (read first): `docs/proposals/language-profile/README.md` (the store: entry kinds,
fields, evidence; the wiki section at the end) and `scripts/wiki.py` (page format).{example_line}

**Focus ({familiarity}):**
{focus}

**Sources:**
- The style corpus, {corpus}: {corpus_dirs}. Search it with `python3 scripts/concord.py {project} <cmd>`
  (`eng`, `{lang}`, `forms`, `like`, `lex`, `gloss`; read its docstring); count with Python
  (`collections.Counter`) over the files where a figure helps.
- The alignment lexicons in `{project_dir}/_learn/` (`lexicon_eng.tsv`, `lexicon_grc.tsv`; built by
  `scripts/align.py`): how English and Greek words are rendered, with counts.
{derived_lines}
{drafts_line}
{decisions_line}

**Do NOT open:** `download/`, `scratch/`{do_not_open}.

**Write:**
1. `{store_dir}/observations.json` (`feature`, `letter`, `gap` entries) and
   `{store_dir}/decisions.json` (`term`, `formula`, `name`): every entry with evidence (`"BOOK C:V"`, verses of
   the corpus or of the project's drafts), `confidence`, `method` (`corpus-observed` for what the corpus
   shows, `project-decision` for what the project decided), `by: agent:memory-setup`, today's date
   {date}. Give terms and formulas `words` (the BSB words they answer, lower case).
2. Wiki pages in `{wiki_dir}/` (frontmatter `title`, `entries`: the store ids each page shows),
   one per topic, prose with short examples and references{pages_hint}. `index.md` says what the wiki is
   and links the pages; add a page of numbered questions for the language team (titled in {school_language},
   frontmatter `kind: questions`) with what you could not settle.
3. Run `python3 scripts/language_profile.py check {store_dir} --project {project}`{wiki_check}, and fix every
   problem.

**Rules:**
- Every claim rests on the corpus or the project's drafts: give references, and counts where a choice
  between forms is at stake ("wo 1,240× as relative particle, das 12×"). Mark what you infer.
- Describe how the language works, so that a drafting agent can apply it: the form, when it is used,
  the counter-cases. Not a grammar of the standard language: only what holds in this corpus.
{quotation_rule}

Report in under 200 words: entries written by kind, the wiki pages, the five findings a drafting agent
most needs, and the open questions.
