#!/usr/bin/env python3
"""The language team's input: a plain-language page in the project's wiki, and the step that turns it into binding store
entries.

The team (or someone writing for them) adds items to `wiki/team-input.md` in plain sentences, in the school language:
"for idols we use khape mbumbuk", "names new in the OT follow the spelling", "Genesis 2:5 should say Evezøza Mbumbukiam",
an answer to a numbered question on `wiki/questions.md`. Nobody has to know the store's JSON. Each item is

    ### T3 · 2026-10-22 · <who>
    Status: new
    <the team's words, any length>

A curation agent (`prompt`) then turns every `Status: new` item into store entries with `method: team-decision`,
`by: team:<who>`, `team_source: wiki/team-input.md#T3`, superseding the agents' entries it corrects, and sets the status
line to what it did. Team decisions are binding: the verse packs list them first, and the store validator
(scripts/language_profile.py, rule 5b) refuses any later entry by anyone else that replaces one. Only the status lines are
the curator's; the team's words stay as they wrote them.

Usage:
  python3 scripts/team_input.py <project> init     # create wiki/team-input.md (kept if it exists)
  python3 scripts/team_input.py <project> list     # the items and their status
  python3 scripts/team_input.py <project> add --who W [--date D] TEXT   # add an item (e.g. what the team said on a call)
  python3 scripts/team_input.py <project> prompt   # the prompt for a fresh curation agent, for the new items
"""
import datetime, glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from project import project, project_dir, project_rel  # noqa: E402

PAGE = "team-input.md"
ITEM = re.compile(r"^### (T\d+) · (\d{4}-\d{2}-\d{2}) · ([^\n]+?)[ \t]*\n(?:Status: ([^\n]*)\n)?(.*?)(?=^### T\d+ · |^## |\Z)", re.M | re.S)


def page_path(pname):
    return os.path.join(project_dir(pname), "wiki", PAGE)


def questions_page(pname):
    """The wiki's page of numbered questions for the team (frontmatter kind: questions), relative to wiki/."""
    w = os.path.join(project_dir(pname), "wiki")
    for q in sorted(glob.glob(os.path.join(w, "**", "*.md"), recursive=True)):
        if re.search(r"^kind: questions\s*$", open(q, encoding="utf-8").read().split("\n---", 1)[0], re.M):
            return os.path.relpath(q, w)
    return None


def template(pname, p):
    qp = questions_page(pname)
    qlink = lambda text: f"[{text}]({qp})" if qp else text
    lang = (p.get("language_name") or p.get("language") or "the language").split(" (")[0]
    school = p.get("school_language") or "English"
    return f"""---
title: The team's input
kind: team-input
---
# The team's input

**For the {lang} translation team.** Write here anything you want the drafts to get right: a word you use, a spelling, a
name, a rule, a correction to a draft verse, an answer to one of the {qlink('questions')}. Plain sentences in {school}
are enough; quotations in {lang} as you write them. Nobody needs to touch the store files.

How it works:
- add an item at the end, as `### T<next number> · <date> · <your name or "the team">`, then a line `Status: new`, then your
  words (as long as you like; examples help: chapter and verse, the wrong form, the right one);
- a curation step turns each new item into entries of the project's store and writes on the status line what it did
  (`entered: …`, or `question back: …` when something is unclear);
- from then on every drafting agent sees your decision first, marked as binding, and no agent may change it. If you change
  your mind, add a new item: only the team changes its own decisions.

Your words stay as you wrote them; only the status lines are written by the curation step.

## Requests from us

What would help the drafts most just now:
- **Spelling and tone marks:** examples of forms our drafts get wrong (chapter and verse, our form, your form). Each one
  becomes a rule every later chapter follows, and the drafting agents now check every word form against your published
  text, marks included.
- **The numbered {qlink('questions')}:** an answer to any of them, by number.

## Items

"""


def items(pname):
    s = open(page_path(pname), encoding="utf-8").read()
    i = s.find("## Items")
    return [dict(id=m[1], date=m[2], who=m[3], status=(m[4] or "").strip(), text=m[5].strip())
            for m in ITEM.finditer(s, i if i >= 0 else 0)]


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    pname, cmd = a[0], a[1]
    p = project(pname)
    path = page_path(pname)
    if cmd == "init":
        if os.path.exists(path):
            print(f"{os.path.relpath(path, ROOT)} exists; kept")
        else:
            open(path, "w", encoding="utf-8").write(template(pname, p))
            print(f"{os.path.relpath(path, ROOT)} written; run python3 scripts/wiki.py sync {pname}")
        return
    if not os.path.exists(path):
        raise SystemExit(f"no {os.path.relpath(path, ROOT)}: run python3 scripts/team_input.py {pname} init")
    its = items(pname)
    if cmd == "list":
        for it in its:
            print(f"{it['id']} {it['date']} {it['who']}: {it['status'] or '(no status)'} | {it['text'][:90]}")
        print(f"{len(its)} items, {sum(1 for it in its if it['status'] in ('', 'new'))} new")
    elif cmd == "add":
        who = a[a.index("--who") + 1] if "--who" in a else "the team"
        date = a[a.index("--date") + 1] if "--date" in a else datetime.date.today().isoformat()
        skip = {i + 1 for i, x in enumerate(a) if x in ("--who", "--date")} | {i for i, x in enumerate(a) if x in ("--who", "--date")}
        text = " ".join(x for i, x in enumerate(a[2:], 2) if i not in skip).strip()
        if not text:
            raise SystemExit("add: no text")
        n = max([int(it["id"][1:]) for it in its] or [0]) + 1
        s = open(path, encoding="utf-8").read().rstrip() + "\n"
        if "## Items" not in s:
            s += "\n## Items\n"
        s += f"\n### T{n} · {date} · {who}\nStatus: new\n{text}\n"
        open(path, "w", encoding="utf-8").write(s)
        print(f"T{n} added")
    elif cmd == "prompt":
        new = [it for it in its if it["status"] in ("", "new")]
        if not new:
            raise SystemExit("no new items")
        rel = project_rel(pname)
        school = p.get("school_language") or "English"
        print(f"""You curate the language team's input for the project {pname} (folder `{rel}/`). The team wrote items on
`{rel}/wiki/{PAGE}`; these are new: {', '.join(it['id'] for it in new)}.

Read first: `{rel}/wiki/{PAGE}`, `{rel}/wiki/index.md`, `{rel}/wiki/{questions_page(pname) or "questions.md"}`, and the store entries each item touches
(`python3 scripts/concord.py {pname} store "<regex>"`). Use `python3 scripts/concord.py {pname} forms|tgt|eng ...` to see the
corpus. Do not open: {', '.join(p.get('do_not_open') or [])}.

For each new item:
1. Work out what it decides. One item may give several facts (a term, a spelling, a rule), or none (a comment): then say
   so on its status line.
2. Write each fact as a store entry in `{rel}/profile/decisions.json` (terms, names, formulas) or `observations.json`
   (features, letters, gaps), with `method: "team-decision"`, `by: "team:<who>"` (the item's author, as one lower-case
   word or hyphenated), `team_source: "wiki/{PAGE}#<item id>"`, `date` = the item's date, `confidence: "high"`,
   `status: "decided"`, the form exactly as the team wrote it (every tone mark), a `note` in {school} saying what the team
   said, and evidence verses where the corpus has the form (team decisions need none). Where the item corrects an
   existing entry, give the new entry `supersedes: "<old id>"` (or the same id, and mark the old one superseded); keep the
   old entry. Never change or supersede an earlier team decision, unless this item is the team changing it.
3. If it answers a numbered question on `{questions_page(pname) or "the questions page"}`, add under that question an indented line
   `   **Answered (<item id>, <date>):** <one sentence>` and keep the question.
4. If the item names a spelling, check how often the corpus writes the other form (`concord.py {pname} forms`), and say in
   the note whether the team's form is the corpus's usual one.
5. Change the prose of the wiki page the fact belongs to (one or two sentences, with the item id), so a reader sees the
   team's decision where it matters.
6. Replace the item's `Status: new` line with `Status: entered: <ids> (<today>)`, or `Status: question back: <the
   question>` when you could not tell what the team means (write the question in {school}, short). Change nothing else
   the team wrote.

Then run, and fix until clean:
- `python3 scripts/language_profile.py check {rel}/profile --project {pname}`
- `python3 scripts/wiki.py sync {pname}` then `python3 scripts/wiki.py lint {pname}`
and add one line to `{rel}/wiki/log.md`.

Report in under 120 words: per item, what you entered (ids) or asked back.""")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
