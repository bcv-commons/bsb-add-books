#!/usr/bin/env python3
"""Seeds: what the model knows of a related language (the donor) planted in a project as hypotheses, never as facts.

A project whose language the model doesn't know may have a relative it knows well (`donor.known` in project.yaml; the
same choice as `donor.nllb_init`, the language the second-draft model starts from). A seed agent writes, from memory
only, the donor's grammar as entries of `profile/seeds.json` (docs/language-store.md, *Seeds*): status `seed`, method
`donor:<iso>`, the donor's form (never a form of the target language), and in plain words what to look for (`test`).

Seeds sit in a file of their own, so nothing that checks or splits the language reads them: not the morph view, the
cell check, the binding pack block, Grambank, the glosses or the concordance. Where they appear:
  - the verse pack (scripts/verse_pack.py): a seed whose category (`cells`, `pos`) occurs in the chapter, once in the
    header, marked "(unconfirmed, from <donor>; check)";
  - scripts/morphs.py try --seeds: the morph seeds measured against the Greek, as if they were in the store;
  - scripts/memory_prompt.py: the memory agent tests them;
  - scripts/check_project.py: how many are still untested.
A seed is tested once a live store entry names it (`seed: <seed id>`): the observed form (confirmed or corrected), or a
claim with verdict `contradicted` (refuted). The seed itself never changes.

Usage: python3 scripts/seeds.py prompt <project>     the seed agent's prompt (docs/prompts/seed_prompt.md), from the
                                                   project's donor: block (scripts/donor.py); for a fresh agent
       python3 scripts/seeds.py status <project>     the seeds and their test state
       python3 scripts/seeds.py check <project>      the seed file's format (also run by language_profile.py check)
       python3 scripts/seeds.py brief <project>      the family brief's research agent's prompt (scripts/brief.py)
       python3 scripts/seeds.py brief --check <project>   the brief's points: tested, confirmed, contradicted
Seeds from the family brief carry `method: brief:<source language iso or glottocode>` and `brief: <point id>`.
"""
import collections, json, os, re, sys

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))

FILE = "seeds.json"
KINDS = {"morph", "feature"}
REQUIRED = ["id", "kind", "value", "confidence", "method", "by", "date", "status", "donor_form", "test"]
SLOTS = {"prefix", "suffix", "infix", "clitic", "free", "tone"}
CELL = re.compile(r"^(verb\.[a-z.]+|pronoun\.[a-z]+): ([A-Z0-9]+(?:\.[A-Z0-9]+)*)$")
CODE = re.compile(r"^(GB\d{3}|WALS:\d{1,3}[A-Z])$")


def norm_form(e):
    """an affix seed's form as the store writes it (prefix ta-, suffix -ibw, infix -ir-), or None where it isn't one form
    (a zero, an alternation, several forms)"""
    f = (e.get("form") or "").strip()
    core = f.strip("-=")
    if not core or re.search(r"[\s/,|0Ø∅()]", core):
        return None
    return {"prefix": core + "-", "suffix": "-" + core, "infix": "-" + core + "-"}.get(e.get("slot"), f)


def path(profile):
    return os.path.join(profile, FILE)


def load(profile):
    """the seed file: {"donor", "template", "entries"}, or None"""
    f = path(profile)
    return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else None


def of_project(pname):
    from project import project_dir
    return load(os.path.join(project_dir(pname), "profile"))


def check(profile, store=None):
    """problems of the seed file (none without one); store: {id: entry} of the live store, for ids and `seed:` links"""
    d, problems = load(profile), []
    store = store or {}
    seeded = {e.get("seed"): eid for eid, e in store.items() if e.get("seed")}
    if d is None:
        return [f"{eid}: seed {s} is not in profile/{FILE}" for s, eid in seeded.items()]
    donor = d.get("donor")
    from_donor = any(str(e.get("method", "")).startswith("donor:") for e in d.get("entries", []))
    if (from_donor or donor) and not re.fullmatch(r"[a-z]{3}", str(donor or "")):
        problems.append(f"{FILE}: donor {donor!r} (the ISO 639-3 code of the language the seeds come from)")
    ids = set()
    for e in d.get("entries", []):
        eid = e.get("id", "?")
        where = f"{FILE} {eid}"
        problems += [f"{where}: missing {k}" for k in REQUIRED if not e.get(k)]
        if not str(eid).startswith("seed:"):
            problems.append(f"{where}: a seed's id starts with seed:")
        if eid in ids or eid in store:
            problems.append(f"{where}: id used twice")
        ids.add(eid)
        if e.get("status") != "seed":
            problems.append(f"{where}: status {e.get('status')!r} (a seed stays a seed; its test is a store entry with "
                            "seed: <id>)")
        if e.get("method") != f"donor:{donor}" and not re.fullmatch(r"brief:[a-z0-9]{3,8}", str(e.get("method"))):
            problems.append(f"{where}: method {e.get('method')!r} (donor:{donor}, or brief:<iso> for a brief's seed)")
        elif str(e.get("method")).startswith("brief:") and not e.get("brief"):
            problems.append(f"{where}: a brief's seed names its point (brief: b.<id>)")
        if e.get("kind") not in KINDS:
            problems.append(f"{where}: kind {e.get('kind')!r} ({', '.join(sorted(KINDS))})")
        if e.get("confidence") not in ("high", "medium", "low"):
            problems.append(f"{where}: confidence {e.get('confidence')!r}")
        if e.get("kind") == "morph":
            problems += [f"{where}: a morph needs {k}" for k in ("form", "slot", "host") if not e.get(k)]
            if e.get("slot") and e["slot"] not in SLOTS:
                problems.append(f"{where}: slot {e['slot']!r}")
            if e.get("form") and e.get("slot") in ("prefix", "suffix", "infix"):
                nf = norm_form(e)
                if not nf:
                    problems.append(f"{where}: form {e['form']!r} is not one form (a zero or an alternation: write it as "
                                    "a feature)")
                elif nf != e["form"]:
                    problems.append(f"{where}: form {e['form']!r}: a {e['slot']} is written {nf!r}")
        for c in e.get("cells") or []:
            if not CELL.match(c):
                problems.append(f"{where}: cell {c!r} (paradigm: TAGS, as scripts/source_cells.py names them, "
                                "verb.polarity: NEG)")
        problems += [f"{where}: code {c!r}" for c in e.get("codes") or [] if not CODE.match(c)]
    for slot in (d.get("template") or {}).get("verb") or []:
        problems += [f"{FILE} template: {slot.get('slot')}: {m} is not a seed" for m in slot.get("morphs") or []
                     if m not in ids]
    problems += [f"{eid}: seed {s} is not in profile/{FILE}" for s, eid in seeded.items() if s not in ids]
    return problems


def tested(pname):
    """{seed id: [(store entry id, verdict)]}: the live store entries that settle a seed: the language's own entry naming
    it, or a claim that confirms or contradicts it (an open claim, a thin or unmeasurable seed, leaves it untested)"""
    from verse_pack import load_profile
    from project import project_dir
    out = {}
    for e in load_profile(os.path.join(project_dir(pname), "profile")):
        if e.get("seed"):
            v = e.get("verdict") or ("confirmed" if e.get("status") in ("observed", "decided") else e.get("status"))
            if e.get("kind") != "claim" or v in ("confirmed", "contradicted"):
                out.setdefault(e["seed"], []).append((e["id"], e.get("result") or v))
    return out


def untested(pname):
    d = of_project(pname)
    if not d:
        return None, []
    t = tested(pname)
    return d, [e for e in d.get("entries", []) if e["id"] not in t]


def match_cell(want, cells):
    """a seed's cell 'verb.polarity: NEG' against a token's cells [(paradigm, bundle)]: the paradigm, and every tag"""
    m = CELL.match(want)
    if not m:
        return False
    tags = set(m[2].split("."))
    return any(par == m[1] and tags <= set(b.split(".")) for par, b in cells)


def for_chapter(pname, code, ch):
    """(donor, [seed]) whose category occurs in the chapter (a cell of one of its tokens, or its part of speech), and
    untested; seeds without `cells` or `pos` are left out (word order, how tone is written: the memory agent's)"""
    d = of_project(pname)
    if not d:
        return None, []
    from books import BY_CODE
    import sqlite3
    import source_cells as SC
    nt = BY_CODE[code][2] == "nt"
    db = sqlite3.connect(os.path.join(ROOT, "orig", "grc.sqlite" if nt else "heb.sqlite"))
    keys = [k for (k,) in db.execute("select key from tokens where book = ? and ch = ?", (code.upper(), ch))]
    toks = SC.cells_of(code.upper(), "nt" if nt else "ot")
    cells, pos = [], set()
    for k in keys:
        t = toks.get(k)
        if t:
            cells += t.cells
            pos.add((t.feats.get("pos") or "").lower())
    t = tested(pname)
    out = [e for e in d.get("entries", []) if e["id"] not in t and (
        any(match_cell(c, cells) for c in e.get("cells") or []) or (e.get("pos") or "").lower() in pos - {""})]
    return d.get("donor"), out


def pack_lines(pname, code, ch, names=None):
    """the pack's lines for the chapter's untested seeds: one line per category (a source cell's paradigm, else the
    part of speech, else the seed's kind), the donor's forms with their glosses"""
    donor, es = for_chapter(pname, code, ch)
    if not es:
        return []
    name = (names or {}).get(donor) or donor
    groups = collections.OrderedDict()
    for e in es:
        cat = ((e.get("cells") or [""])[0].split(":")[0] or (e.get("pos") and f"{e['pos']}s") or e["kind"] + "s")
        groups.setdefault(cat, []).append(e)
    L = [f"## Hypotheses from {name} (seeds: unconfirmed; the corpus decides)", "",
         f"What the model knows of {name}, a related language, for the categories in this chapter: the {name} forms, not "
         "this language's. Use a form only where the corpus or the store attests it; where the corpus has another, follow "
         "it and say so in the notes (`seed <id>: <what the corpus shows>`). `concord.py <project> store <id>` shows a "
         "seed's test.", ""]
    for cat, xs in groups.items():
        L.append(f"- {cat}: " + "; ".join(f"{e.get('form') or e.get('donor_form')} {e['value'] if e.get('kind') == 'morph' else ''}".strip()
                                          + f" [{e['id'].removeprefix('seed:')}]" for e in xs))
    return L + [""]


def prompt(pname):
    """the seed agent's prompt for the project, from its donor: block: memory only, one file to read, one to write"""
    import datetime
    import donor as D
    from project import project, project_dir
    p = project(pname)
    dn = p.get("donor") or {}
    if not dn.get("known") or dn["known"] == "none":
        raise SystemExit(f"{pname}: no known donor (donor.known; python3 scripts/donor.py run {pname} --write): "
                         "no seeds from memory")
    gb = os.path.join(ROOT, "download", "grambank", "v1.0.3", "parameters.csv")
    if not os.path.exists(gb):
        raise SystemExit("the Grambank questions are missing: python3 scripts/setup.py --only grambank")
    iso = str(p.get("language") or "").split("-")[0].lower()
    T = D.Tree()
    g, levels = T.walk(iso)
    k = dn["known"]
    lv = next(((T.name(anc), d) for anc, d, new in levels if T.by_iso.get(k) in new), None)
    names = lambda isos: ", ".join(f"{T.name(T.by_iso[i])} ({i})" for i in isos if i in T.by_iso)
    sc = dn.get("candidates") or {}
    better = [i for i, v in sc.items() if i != k and v > sc.get(k, 0)]
    cross = (f"\n- Cross-check: the probes say you write **{names(better)}** better (write {', '.join(str(sc[i]) for i in better)}"
             f" against {sc.get(k)}), though further away. Where it helps, say in `donor_note` what it has; the forms "
             f"stay {dn.get('name') or k}'s." if better else "")
    fill = {"language_name": p.get("language_name") or iso, "iso": iso,
            "classification": " > ".join(T.name(x) for x in T.l[g][3]) + " (Glottolog)",
            "structure_names": names(dn.get("structure") or []) or "not recorded",
            "donor_name": dn.get("name") or T.name(T.by_iso.get(k, k)), "donor": k,
            "donor_level": f"{lv[0]}, {lv[1]} level{'s' if lv[1] > 1 else ''} up" if lv else "outside the family",
            "cross_check": cross, "grambank": gb,
            "out": os.path.join(project_dir(pname), "profile", FILE), "date": datetime.date.today().isoformat()}
    text = open(os.path.join(CODE, "docs", "prompts", "seed_prompt.md"), encoding="utf-8").read()
    text = re.sub(r"^<!--.*?-->\n", "", text, flags=re.S)
    for key, v in fill.items():
        text = text.replace("{" + key + "}", v)
    return text


def main(a):
    if len(a) < 2 or a[0] not in ("status", "check", "prompt", "brief"):
        raise SystemExit(__doc__)
    if a[0] == "brief":
        import brief
        return brief.main(a[1:])
    if a[0] == "prompt":
        print(prompt(a[1]))
        return
    from project import project_dir
    prof = os.path.join(project_dir(a[1]), "profile")
    if a[0] == "check":
        from verse_pack import load_profile
        ps = check(prof, {e["id"]: e for e in load_profile(prof)})
        print(f"{a[1]}: {len(ps)} problems in {FILE}")
        for p in ps:
            print("  problem:", p)
        sys.exit(1 if ps else 0)
    d = of_project(a[1])
    if not d:
        print(f"{a[1]}: no seeds (profile/{FILE})")
        return
    t = tested(a[1])
    es = d.get("entries", [])
    print(f"{a[1]}: {len(es)} seeds from {d.get('donor')}, {sum(e['id'] in t for e in es)} tested")
    for e in es:
        res = "; ".join(f"{v} by {i}" for i, v in t.get(e["id"], [])) or "untested"
        print(f"  {e['id']:34} {e['kind']:7} {str(e.get('form') or e['value'])[:24]:24} {res}")


if __name__ == "__main__":
    main(sys.argv[1:])
