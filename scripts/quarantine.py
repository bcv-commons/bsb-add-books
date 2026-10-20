#!/usr/bin/env python3
"""Quarantine a book for independent drafting, or release it.

Rule (binding for every project): a book that a non-free style edition has is drafted only in quarantine,
so that no agent sees or copies that edition's text of it. An attributable edition (CC BY, CC BY-SA)
needs it only when the project sets `quarantine_attributable: true`; a public-domain edition never.
scripts/make_prompt.py refuses to write a prompt until the quarantine is in place.

Quarantine moves the book's files out of each such edition's text folder into
<edition>/quarantined/<code>/ (so no tool's corpus has them: concord, packs, aligner) and adds the book
to the project's `quarantine:` list. --release moves them back and removes the book from the list.
Afterwards, re-run scripts/align.py for a project whose lexicons were built with the book in the corpus.

A chapter that the edition doesn't have needs no quarantine, though the edition has other chapters of the book
(Genesis 31-50 beside an edition's Genesis 1-30): make_prompt.py checks it per chapter; --chapter N says
whether chapter N needs one.

Usage: python3 scripts/quarantine.py <project> <code> [--release] [--all-editions] [--chapter N]
       --all-editions: quarantine the book in every style edition, public domain ones included
       --chapter N: only report whether chapter N needs a quarantine (nothing is moved)
"""
import os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from project import project, edition, book_files, must_quarantine, LICENCE_CLASS, project_dir  # noqa: E402


def set_list(path, code, add):
    """Add or remove a code in the project.yaml `quarantine: [...]` line, keeping the rest of the file."""
    text = open(path, encoding="utf-8").read()
    m = re.search(r"^quarantine:\s*\[(.*?)\]", text, re.M)
    if not m:
        raise SystemExit(f"{path}: no 'quarantine: [...]' line; add one (e.g. quarantine: [])")
    codes = [c.strip() for c in m[1].split(",") if c.strip()]
    codes = sorted(set(codes) | {code}) if add else [c for c in codes if c != code]
    open(path, "w", encoding="utf-8").write(text[:m.start()] + f"quarantine: [{', '.join(codes)}]" + text[m.end():])


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    pname, code, release = a[0], a[1], "--release" in a
    p = project(pname)
    # on a derived path the derived-from editions need no quarantine, except a book held out on purpose, which is what
    # this call asks for: count it as listed in the project's own quarantine
    p["own_quarantine"] = list(dict.fromkeys(list(p.get("own_quarantine") or []) + [code]))
    if "--chapter" in a:
        ch = int(a[a.index("--chapter") + 1])
        need = must_quarantine(p, code, ch)
        print(f"{code} {ch}: " + (f"quarantine needed ({', '.join(e for e, _, _ in need)} has it, or can't be checked here)"
                                  if need else "no quarantine needed: no non-free style edition has this chapter"))
        return
    eds = [(e, LICENCE_CLASS.get(edition(e)["licence_folder"], "non-free")) for e in p["style_from"]] if "--all-editions" in a \
        else [(e, cls) for e, cls, _ in must_quarantine(p, code)]
    if not eds and not release:
        print(f"{code}: no style edition of {pname} needs a quarantine (public domain, or the book isn't there)")
        return
    for e, cls in eds:
        ed = edition(e)
        held = os.path.join(ROOT, ed["dir"], "quarantined", code)
        text = os.path.join(ROOT, ed["dir"], ed.get("text_dir", "text"))
        if release:
            if os.path.isdir(held):
                for f in sorted(os.listdir(held)):
                    shutil.move(os.path.join(held, f), os.path.join(text, f))
                os.rmdir(held)
                if not os.listdir(os.path.dirname(held)):
                    os.rmdir(os.path.dirname(held))
                print(f"{e}: {code} released into {os.path.relpath(text, ROOT)}/")
        else:
            files = book_files(ed, code)
            os.makedirs(held, exist_ok=True)
            for f in files:
                shutil.move(f, os.path.join(held, os.path.basename(f)))
            print(f"{e} ({cls}): {len(files)} file(s) of {code} moved to {os.path.relpath(held, ROOT)}/")
    set_list(os.path.join(project_dir(pname), "project.yaml"), code, not release)
    print(f"{pname}: {code} {'removed from' if release else 'added to'} quarantine")
    if os.path.isdir(os.path.join(project_dir(pname), "_learn")):
        print(f"re-run python3 scripts/align.py {pname} so the lexicons match the corpus")


if __name__ == "__main__":
    main()
