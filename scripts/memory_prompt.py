#!/usr/bin/env python3
"""Print the prompt for a fresh agent that builds or extends a project's language memory (store + wiki),
focused by the project's familiarity (scripts/modes.py; docs/onboarding.md, step 4). Template:
docs/prompts/memory_prompt.md.

Usage: python3 scripts/memory_prompt.py <project> [--init] [--no-derived] [--out DIR] [--store-only]
       The study starts from the derived products whenever the project has its occurrence index
       (_learn/lang.sqlite; scripts/lang.py build): the derived products (scripts/lang.py derive + report, written to
                  _learn/derived_report.md, local) and uses the occurrence index (lang.py hbo / grc): the agent
                  confirms or rejects each item against the corpus instead of finding everything by reading
       --no-derived: without them (reading and searching only)
       --out DIR: write the store (and wiki) under DIR instead of the project's own (a test run)
       --store-only: no wiki (a test run)
       --init: first create an empty store (profile/observations.json, decisions.json) and wiki (index.md,
               log.md) where they don't exist yet
"""
import datetime, glob, os, sys, subprocess

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
EXAMPLES = ("jam/jam_BSB", "dan/dan_BSB")   # finished memories shown as a worked example, the first this working copy has
sys.path.insert(0, os.path.join(CODE, "scripts"))
from project import project, edition, project_dir, project_rel  # noqa: E402
import modes, quotes  # noqa: E402

MARKS = """
Tone marks, accents and other diacritics are part of the spelling. Survey which ones the corpus uses (count the combining
marks and the accented letters), describe them on the orthography page with examples, and write every form in the store
exactly as the corpus writes it, marks included. `orthography.ignore_marks` in the store only makes the search tools match
without those marks; it never makes them optional in a draft. Check your values with `python3 scripts/language_profile.py
check ... --project ...`: its `spelling:` lines are store words the corpus writes only with other marks."""

FOCUS = {
    "known": """You know this language well; the memory is not a grammar for you but the project's **decisions**, so that
every agent, book and wave renders the same things the same way. Collect them from the style guides and review
overviews (decided items are binding) and from the drafts: renderings of recurring Hebrew and Greek terms,
formulas (speech frames, "and it came to pass", oaths, genealogies), name forms, the divine names, numbers and
measures, headings, quotation and poetry layout. Add the corpus's house style where it bears on drafting
(features with counts: word order in narrative, connectives, how dialogue is introduced). Record a decision
that is still open as `status: open`.""",
    "partial": """You know {close_to} better than {label}. The memory must hold **{label} as the corpus writes it**, above all
where it differs from {close_to}, so that a drafting agent never falls back on the standard language:
- grammar features with counts and references: tenses (what replaces the preterite), the subjunctive,
  cases and their marking (dative, possession), articles and pronouns (clitic forms), relative clauses,
  word order in verb clusters, infinitive constructions, negation, diminutives, verb doubling, the
  particles that carry the narrative; each with the counter-cases;
- orthography: how the corpus spells (vowels, diphthongs, long and short, doubled consonants), as
  `letter`-style rules where they are regular;
- vocabulary that differs from {close_to} (`term` entries: the corpus word for an English concept, with
  counts against the standard form if the corpus has it);
- the project's decisions from the style guides and review overviews (terms, formulas, name forms, divine
  names, numbers), as `project-decision` entries;
- `gap` entries for what the corpus has no model for (concepts of the Tanakh in an NT corpus) and how the drafts solved it.""" + MARKS,
    "unknown": """You don't know this language. Build the memory from the corpus alone, as the first study of it: a grammar
sketch (verbs, pronouns, possession, postpositions, connectors, questions, speech framing, word order),
orthography and name transliteration (`letter` entries), frequent formulas, a term base for the concepts the
drafts will need, and `gap` entries for what the corpus has no model for. Never assume a form you haven't seen.""" + MARKS,
}
PAGES = {"known": " (decisions by topic: terms, formulas, names, style)",
         "partial": " (grammar by topic under `grammar/`, orthography, vocabulary, names, the project's decisions, gaps)",
         "unknown": " (grammar by topic under `grammar/`, orthography, vocabulary, names, gaps)"}


def init(pname, p):
    import json
    pdir = project_dir(pname)
    os.makedirs(os.path.join(pdir, "profile"), exist_ok=True)
    os.makedirs(os.path.join(pdir, "wiki"), exist_ok=True)
    lic = {"observations": "CC0-1.0 (feature values and references; quotations credited in ../CREDITS.md)",
           "decisions": "CC0-1.0 (single words and short phrases with references; quotations credited in ../CREDITS.md)"}
    for part in ("observations", "decisions"):
        f = os.path.join(pdir, "profile", f"{part}.json")
        if not os.path.exists(f):
            json.dump({"iso": p["language"].split("-")[0], "edition": os.path.basename(pname), "partition": part,
                       "licence": lic[part], "orthography": {"normalization": "NFC", "ignore_marks": []}, "entries": []},
                      open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    today = datetime.date.today().isoformat()
    for name, body in (("index.md", f"---\ntitle: {p.get('language_name')}: wiki\n---\n# {p.get('language_name')}: wiki\n\n"
                                    f"(To be written in {modes.school_language(p)} by the memory set-up agent.)\n"),
                       ("log.md", f"---\ntitle: Log\n---\n# Log\n\n- {today}, scripts/memory_prompt.py --init: empty store and wiki\n")):
        f = os.path.join(pdir, "wiki", name)
        if not os.path.exists(f):
            open(f, "w", encoding="utf-8").write(body)
    # the team's plain-language input page (binding team decisions; scripts/team_input.py)
    subprocess.run([sys.executable, os.path.join(CODE, "scripts", "team_input.py"), pname, "init"], stdout=subprocess.DEVNULL)
    print(f"{os.path.relpath(pdir, ROOT)}: store and wiki ready", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    pname = sys.argv[1]
    p = project(pname)
    if "--init" in sys.argv:
        init(pname, p)
    m = modes.mode(p)
    pdir = project_dir(pname)
    label = (p.get("language_name") or p["language"]).split(" (")[0]
    eds = [(e, edition(e)) for e in p.get("style_from") or []]
    corpus = p.get("corpus_name") or ", ".join(ed.get("name", e) for e, ed in eds)
    corpus_dirs = ", ".join(f"`{ed['dir']}/{ed.get('text_dir', 'text')}/`" for e, ed in eds)
    drafted = sorted({os.path.basename(os.path.dirname(f)) for f in glob.glob(os.path.join(pdir, "*", "*[0-9][0-9][0-9].txt"))
                      if os.path.basename(os.path.dirname(f)) not in ("quarantine", "_eval")})
    guides = sorted(os.path.relpath(f, ROOT) for pat in ("*style_guide.md", "*review_overview.md")
                    for f in glob.glob(os.path.join(pdir, "**", pat), recursive=True))
    fill = {"close_to": p.get("close_to") or "the standard language", "label": label}
    text = open(os.path.join(CODE, "docs", "prompts", "memory_prompt.md"), encoding="utf-8").read().split("\n---\n", 1)[1]
    qr = quotes.rule_text(pname)
    out_dir = os.path.abspath(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
    store_dir = os.path.relpath(os.path.join(out_dir, "profile"), ROOT) if out_dir else f"{project_rel(pname)}/profile"
    wiki_dir = os.path.relpath(os.path.join(out_dir, "wiki"), ROOT) if out_dir else f"{project_rel(pname)}/wiki"
    derived_lines = ""
    import lang
    if "--no-derived" not in sys.argv and os.path.exists(os.path.join(pdir, "_learn", "lang.sqlite")):
        rep_path = os.path.join(pdir, "_learn", "derived_report.md")
        os.makedirs(os.path.dirname(rep_path), exist_ok=True)
        import contextlib, io
        buf = io.StringIO()
        lang.derive(pname, quiet=True)
        with contextlib.redirect_stdout(buf):
            lang.report(pname)
        open(rep_path, "w", encoding="utf-8").write(buf.getvalue())
        rel = os.path.relpath(rep_path, ROOT)
        derived_lines = (
            f"- **Start here: the derived report** `{rel}`, computed by script from the corpus aligned to the Greek "
            "(every NT token linked to its MACULA Greek token): word order, function words and how often they have no "
            "word, clause-initial connectors, affix hypotheses (word endings or affix tokens against the Greek features "
            "they go with, with lift; also person+number, tense+mood, negation and the object's person), tone and other "
            "marks against the same features and against questions, letter correspondences in names, formulas, and the "
            "words of the Tanakh the NT hardly has (through the LXX and the BSB English). "
            "Each line is a hypothesis with counts, not a finding: confirm or reject it against the corpus (look at "
            "examples, find the counter-cases) and write what holds as a store entry, `method: corpus-derived` (statistic confirmed by you) where the "
            "statistic carries it, citing the report's figure. Then look for what statistics can't show.\n"
            "- **Affix chains** (a verb with several affixes in a row, subject, tense and object before the stem, as in "
            "many Bantu languages: the report's beginnings then overlap, ni- nit- nim- nib-): write the analysis as morph "
            "entries with `position` (prefixes counted from the word's start, suffixes from the stem outward) and `greek`, "
            "the Greek feature each marks, named as in the report (`{\"person+number\": \"fp\"}`, a list for several "
            "values), `status: open`; where the written tone tells two affixes apart, give each its own entry with the mark in "
            "its `form` (`aá-` past, `aa-`). Then `python3 scripts/morphs.py " + pname + " try --write` measures each one on the "
            "whole segmentation (n, stems, lift, odds ratio, on all verses and on the even ones) and keeps the confirmed "
            "as observed; revise or supersede the contradicted (a wrong feature, a wrong position, a form that is really "
            "two) and try them again. `python3 scripts/morphs.py " + pname + " show <word>` shows a word's parts. "
            "`python3 scripts/morphs.py " + pname + " audit` lists the words an affix only seems to carry (a noun that "
            "begins like a verb prefix): after a look at their verses, write them as `word` entries (protected words, "
            "never split; `.claude/skills/audit-store/`).\n"
            f"- **The occurrence index:** `python3 scripts/lang.py hbo {pname} <Hebrew Strong's, e.g. H2617>` shows how "
            "the NT renders a Hebrew word through the Septuagint (its Greek equivalents, the target words with counts, "
            f"example verses); `python3 scripts/lang.py grc {pname} <Greek Strong's>` the same for one Greek lemma. Use "
            "them for the term base: the concepts of the Tanakh the drafts will need.\n"
            f"- **The priors** `{project_rel(pname)}/profile/priors.yaml` (if the report ends with them): what the model believed "
            "about the language before the corpus was studied, each item checked against the corpus (confirmed, weak, "
            "not found, ABSENT). Correct the file where the corpus contradicts it (change the item, add `source: corpus` "
            "and the evidence), and don't carry an unconfirmed prior into the store.")
    import seeds
    sd = seeds.of_project(pname)
    if sd and derived_lines:
        dn = p.get("donor") or {}
        name = dn.get("name") or sd.get("donor")
        derived_lines += (
            f"\n- **Seeds** `{project_rel(pname)}/profile/seeds.json` ({len(sd.get('entries', []))}): what the model knows "
            f"of {name}, a related language, as hypotheses: the donor's forms and categories, each with a `test` in plain "
            "words, never a fact of this language. Test each against the corpus as you do the report's lines: "
            f"`python3 scripts/morphs.py {pname} try --seeds --write` measures the affix seeds against the Greek (a claim "
            "per seed). Where the corpus has the category, write the language's own entry with `seed: <seed id>` (the "
            "form as the corpus has it, whether it is the donor's or not); where it contradicts a seed, a claim with "
            "`verdict: contradicted` and `seed: <seed id>`. Never copy a seed's form into the store untested, and never "
            f"edit `seeds.json`. `python3 scripts/seeds.py status {pname}` lists what is still untested.")
    example = next((e for e in EXAMPLES if e != pname and os.path.isdir(os.path.join(ROOT, "export", e, "wiki"))), None)
    out = text.format(
        store_dir=store_dir, wiki_dir=wiki_dir, derived_lines=derived_lines,
        example_line=("" if not example else
                      " A worked example of a finished memory, for its form only: "
                      f"`export/{example}/wiki/` and `export/{example}/profile/` (a different language; take nothing "
                      "from its content)."),
        wiki_check=("" if "--store-only" in sys.argv else
                    f" and `python3 scripts/wiki.py sync {pname}`, then `python3 scripts/wiki.py lint {pname}`; add one line to `wiki/log.md`"),
        root=ROOT, project=pname, project_dir=project_rel(pname), language_name=p.get("language_name"),
        school_language=modes.school_language(p),
        language_rule=(f"Write the wiki and the store's notes in **{modes.school_language(p)}**."
                       if modes.school_language(p).split(" (")[0] == label else
                       f"Write the wiki and the store's notes in **{modes.school_language(p)}**: all text and analysis; "
                       f"only quotations and examples are in {label}."), label=label,
        familiarity=m["familiarity"], focus=FOCUS[m["familiarity"]].format(**fill), corpus=corpus, corpus_dirs=corpus_dirs,
        lang=p.get("language"), date=datetime.date.today().isoformat(),
        drafts_line=(f"- The project's drafts in `{project_rel(pname)}/<code>/` ({', '.join(drafted)}) with their `_notes.md`: "
                     "how the project has rendered things so far." if drafted else ""),
        decisions_line=("- The project's style guides and review overviews (decided items are binding): "
                        + ", ".join(f"`{g}`" for g in guides) if guides else ""),
        do_not_open="".join(f", `{d}`" for d in (p.get("do_not_open") or []) if d not in ("download/", "scratch/")),
        pages_hint=PAGES[m["familiarity"]],
        quotation_rule=(f"- {qr}" if qr else "- The corpus is public domain: quote it as you need, with references.")
        + "\n- Hebrew and Greek in the store and the wiki come from the open text, never from `orig/heb/` (our BHSA copy, not "
          "free): a phrase from a clause package, or a verse from `python3 scripts/notes_hebrew.py show <code> <ch>:<v>` (the "
          "WLC, or the BGB).")
    print(out.strip())


if __name__ == "__main__":
    main()
