#!/usr/bin/env python3
"""A project's mode: how well the model knows the target language, and how free the style editions are.
Every tool that depends on the situation asks here (docs/onboarding.md).

Two settings decide it:
  - `familiarity` in project.yaml (set it from scripts/probe_language.py):
      known     the model writes the language well (Danish): agents draft from their own command of it; the
                project's memory (store, wiki) keeps decisions consistent across agents, books and waves;
      partial   the model knows a close standard language but not this variety (Bern German, close to Standard
                German): agents check forms against the corpus, and the memory holds the variety's forms;
      unknown   the model can't write the language (Kuni): agents learn everything from the corpus, invent
                nothing, and the memory holds the grammar too;
  - the licence of the style editions (from their import/ folders): public-domain, attributable, non-free.
    Non-free brings quarantine (docs/workflow.md) and the quotation rule (docs/licensing.md).

What follows from the familiarity (FEATURES): the verse pack's level, whether the style check runs in the
chapter prompt, which rule bundle from docs/prompts/modes.md the prompt gets.

Usage: python3 scripts/modes.py <project>        print the project's mode and what it switches on
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from project import project, edition, missing_texts, LICENCE_CLASS  # noqa: E402

FAMILIARITY = ("known", "partial", "unknown")
FEATURES = {
    "known": {"pack": "memory", "style_check": False, "drafting": "waves",
              "summary": "drafts from the model's own command of the language; the memory keeps decisions consistent"},
    # partial, like unknown: one chapter after another (decided by the user, 2026-10-16, Jamaican pilot): its drafts drift in
    # forms and spelling, and each chapter's decisions reach the next one's pack
    "partial": {"pack": "dialect", "style_check": True, "drafting": "sequential",
                "summary": "drafts in the variety, not the standard language: forms checked against the corpus"},
    # unknown: one chapter after another (decided by the user, 2026-10-15, Kuni Genesis 31-40): each chapter's store
    # entries reach the next chapter's pack, which is built just in time; no waves
    "unknown": {"pack": "full", "style_check": True, "drafting": "sequential",
                "summary": "learns the language from the corpus while drafting; invents nothing"},
}
STRICTNESS = ("public-domain", "attributable", "non-free")


def mode(p):
    """{familiarity, licence, pack, style_check, drafting, quotation_rule, summary} for a project config."""
    fam = p.get("familiarity") or "known"
    if fam not in FAMILIARITY:
        raise SystemExit(f"familiarity {fam!r}: one of {', '.join(FAMILIARITY)}")
    eds = list(dict.fromkeys(([p["based_on"]] if p.get("based_on") else []) + list(p.get("style_from") or [])))
    classes = [LICENCE_CLASS.get(edition(e)["licence_folder"], "non-free") for e in eds]
    licence = max(classes, key=STRICTNESS.index) if classes else "public-domain"
    f = dict(FEATURES[fam])
    if "style_check" in p:
        f["style_check"] = bool(p["style_check"])
    return {"familiarity": fam, "familiarity_set": "familiarity" in p, "licence": licence, "editions": dict(zip(eds, classes)),
            "quotation_rule": licence == "non-free", **f}


def school_language(p):
    """The team's working language: the wiki, the store's notes and (unless notes_language is set) the
    translator notes are written in it; only quotations and examples are in the target language."""
    return p.get("school_language") or p.get("notes_language") or "English"


def mode_rules(pname, p, have):
    """The rule bundle for the project's familiarity (docs/prompts/modes.md), filled in; a rule tagged [store],
    [wiki], [pack] or [lexicon] only when the project has that (`have`: the set of those it has)."""
    m = mode(p)
    text = open(os.path.join(ROOT, "docs", "prompts", "modes.md"), encoding="utf-8").read()
    sec = re.search(rf"^## {m['familiarity']}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not sec:
        return []
    label = (p.get("language_name") or p.get("language")).split(" (")[0]
    corpus = p.get("corpus_name") or ", ".join(edition(e).get("name", e) for e in p.get("style_from") or [])
    fill = {"project": pname, "label": label, "lang": p.get("language", "tgt"), "corpus": corpus,
            "close_to": p.get("close_to") or "the standard language",
            "school_language": school_language(p)}
    out = []
    for m_ in re.finditer(r"^- (?:\[(\w+)\] )?(.*(?:\n  .*)*)", sec[1], re.M):
        tag, rule = m_[1], re.sub(r"\n\s+", " ", m_[2]).strip()
        if tag and tag not in have:
            continue
        out.append(re.sub(r"\{(\w+)\}", lambda x: fill.get(x[1], x[0]), rule))
    return out


def have_tools(pname):
    d = os.path.join(ROOT, "export", pname)
    out = set()
    if os.path.isdir(os.path.join(d, "profile")):
        out.add("store")
    if os.path.isdir(os.path.join(d, "wiki")):
        out.add("wiki")
    if os.path.exists(os.path.join(d, "_learn", "lexicon_eng.tsv")):
        out.add("lexicon")
    if "store" in out or "lexicon" in out:
        out.add("pack")
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    pname = sys.argv[1]
    p = project(pname)
    m = mode(p)
    have = have_tools(pname)
    print(f"{pname}: familiarity {m['familiarity']}" + ("" if m["familiarity_set"] else " (not set: assumed; run scripts/probe_language.py)"))
    print(f"  {m['summary']}")
    print(f"  licence: {m['licence']} ({', '.join(f'{e} {c}' for e, c in m['editions'].items()) or 'no edition'})"
          + ("; quarantine for books it has, quotation rule in the prompts" if m["quotation_rule"] else ""))
    print(f"  verse pack: {m['pack']}; style check in the prompt: {'yes' if m['style_check'] else 'no'}")
    print("  drafting: " + ("sequential: one chapter after another, its pack built just in time (no waves)"
                            if m["drafting"] == "sequential" else "waves of about ten chapters, shared terms fixed first"))
    print(f"  memory tools present: {', '.join(sorted(have)) or 'none'}"
          + ("" if {"store", "wiki"} <= have else f" (set up: docs/onboarding.md, step 4)"))
    for e, how in missing_texts(p):
        print(f"  text missing: edition {e} is not here (not in git); get it: {how}")
    for r in mode_rules(pname, p, have):
        print(f"  rule: {r[:110]}{'…' if len(r) > 110 else ''}")


if __name__ == "__main__":
    main()
