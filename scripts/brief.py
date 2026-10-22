#!/usr/bin/env python3
"""The family brief: what a language's relatives mark, researched before the store work, so agents know what they are
looking for and where to look (docs/onboarding.md, *The family brief*; docs/language-store.md, *The brief*).

A research agent (effort high; about 20-30 minutes) reads the grammars of the language and its relatives and writes the
brief: per category the expected markers, each point with a status (attested in the language / in a close relative /
inferred from the family) and its sources with URL and licence. The corpus decides: each point becomes a test (a seed
in profile/seeds.json with `brief: <point id>`, an `agree:` claim, an affix candidate for `morphs.py try`), and a point
is settled only by a store entry that answers its seed.

Licence rule: a brief built on a source under NC or ND (or one whose licence is unknown) stays local,
`_eval/local/brief.md`; only corpus-confirmed results go to the store. A brief on open sources only: `profile/brief.md`.

Usage: python3 scripts/seeds.py brief <project>          the research agent's prompt (docs/prompts/brief_prompt.md)
       python3 scripts/seeds.py brief --check <project>  the brief's points: tested, confirmed, contradicted, open
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

STATUSES = ("attested", "relative", "family")
POINT = re.compile(r"^\s*-\s+\*\*(b\.[A-Za-z0-9_.-]+)\*\*\s+\[(\w+)\]")
CLOSED = re.compile(r"\b(?:CC[- ]BY(?:-SA)?-N[CD]|CC[- ]BY-NC-ND|NC|ND|non-free|all rights reserved|unknown licen[cs]e|"
                    r"licen[cs]e unknown|paywalled)\b", re.I)

# what every brief covers (the verb template and the noun), in this order
GENERAL = [
    ("nominal classification", "noun classes or genders: how many, their markers on the noun, how they pair for number"),
    ("agreement", "what agrees with what (verb, adjective, demonstrative, possessive) and by which feature"),
    ("person of actor and undergoer", "subject and object marking on the verb: prefixes, suffixes, clitics, their order"),
    ("tense, aspect, mood", "the TAM markers and their slots; which are told apart by tone or vowel length alone"),
    ("negation", "main and dependent clauses, imperative/prohibitive; position in the verb or a separate word"),
    ("mood and modality", "imperative, subjunctive, irrealis or conditional, hortative"),
    ("orientation", "motion and direction on the verb (hither/thither, up/down), associated motion"),
    ("valency", "causative, applicative, passive, reciprocal, reflexive"),
    ("clitics and particles", "second-position or phrase-final clitics, focus, question, quotative"),
    ("tone and length", "what tone does in the grammar (lexical only, or marking TAM/person) and how it is written"),
    ("clause linking", "relatives, complement and speech frames, conjunctions, chaining"),
]
# what particular families are known for, matched on a Glottolog ancestor's name (the brief must check them)
FAMILY = {
    "Bantu": ["noun classes 1-18 with the augment and their singular/plural pairs; locative classes 16-18",
              "subject and object concords per class; the object concord next to the stem",
              "tense by prefix and the final vowel or -ile/-ire (anterior); tone telling tenses apart",
              "verb extensions (-ir-/-il- applicative, -is- causative, -w- passive, -an- reciprocal)",
              "negation prefixes (pre-initial and post-initial); the copula; relatives built on concords"],
    "Atlantic-Congo": ["noun classes and concord; verb extensions"],
    "Trans-New Guinea": ["actor and undergoer marked on the verb (prefixes and suffixes); suppletive stems by number",
                         "medial vs final verbs, clause chaining and switch reference", "gender by vowel or ablaut"],
    "Anim": ["person prefixes for actor and undergoer and their order; gender by the prefix's vowel",
             "plural actor and durative as suffixes; suppletive stems by number or tense",
             "orientation (hither) in the verb; irrealis and negation prefixes; the focus prefixes of Marind"],
    "Austronesian": ["voice/focus system (actor, patient, locative, instrumental voice)", "clitic pronouns",
                     "reduplication for aspect or plurality", "inclusive/exclusive 'we'"],
    "Oceanic": ["possessive classes (direct vs indirect, food/drink)", "subject markers before the verb", "transitive suffix"],
    "Afro-Asiatic": ["root-and-pattern morphology", "gender in verbs and pronouns", "prefix and suffix conjugations"],
    "Sino-Tibetan": ["classifiers", "evidential or egophoric marking", "verb serialisation", "tone"],
    "Tai-Kadai": ["classifiers", "serial verbs", "aspect particles", "tone"],
    "Austroasiatic": ["infixes and prefixes for causative and nominalisation", "classifiers"],
    "Uto-Aztecan": ["incorporation", "applicative and causative suffixes", "absolutive noun suffix"],
    "Mayan": ["ergative and absolutive person markers", "status suffixes", "directionals"],
    "Quechuan": ["evidential enclitics", "switch reference", "person in verb and possessor"],
    "Otomanguean": ["tone for person and aspect", "aspect prefixes"],
    "Indo-European": ["case and gender", "person/number suffixes", "aspect"],
    "Dravidian": ["case suffixes", "negative conjugation", "clause chaining with converbs"],
    "Turkic": ["vowel harmony", "case suffixes", "evidential past", "converbs"],
    "Nilotic": ["tone for case and aspect", "number marking on nouns (singulative)", "verb-initial order"],
    "Mande": ["predicative markers for TAM and polarity", "postpositions", "tone"],
}


def lineage(iso, T=None):
    """(Tree, glottocode, [(level, distance, [language glottocodes])]) from Glottolog (scripts/donor.py)"""
    import donor as D
    T = T or D.Tree()
    g, levels = T.walk(iso)
    return T, g, levels


def family_points(T, g):
    """[(family name, [points])] for the language's ancestors in FAMILY (by name or last word: Narrow Bantu -> Bantu),
    each family once, nearest last"""
    out = []
    for a in T.l[g][3]:
        n = T.name(a)
        k = n if n in FAMILY else n.split()[-1] if n.split() and n.split()[-1] in FAMILY else None
        if k and k not in [x for x, _ in out]:
            out.append((k, FAMILY[k]))
    return out


def path(pdir, local=None):
    """the brief: profile/brief.md, or _eval/local/brief.md (local=True); with local None the one that exists"""
    pub, loc = os.path.join(pdir, "profile", "brief.md"), os.path.join(pdir, "_eval", "local", "brief.md")
    if local is None:
        return next((f for f in (loc, pub) if os.path.exists(f)), None)
    return loc if local else pub


def sources_closed(text):
    """the source lines of a brief whose licence keeps it local (NC, ND, non-free, unknown)"""
    m = re.search(r"^##\s+Sources\s*$(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    return [l.strip() for l in (m.group(1) if m else "").splitlines()
            if l.strip() and not set(l.strip()) <= set("|-: ") and CLOSED.search(l)]


def points(text):
    """[(point id, status, line)] of a brief"""
    return [(m.group(1), m.group(2), l.strip()) for l in text.splitlines() if (m := POINT.match(l))]


def problems(f):
    """a brief's format and licence problems"""
    text = open(f, encoding="utf-8").read()
    out, ids = [], set()
    if not re.search(r"^##\s+Sources\s*$", text, re.M):
        out.append("no ## Sources section (each source with URL and licence)")
    for pid, st, _ in points(text):
        if st not in STATUSES:
            out.append(f"{pid}: status [{st}] ({' | '.join(STATUSES)})")
        if pid in ids:
            out.append(f"{pid}: point id used twice")
        ids.add(pid)
    if not ids:
        out.append("no points (- **b.<id>** [attested|relative|family] ...)")
    if os.path.basename(os.path.dirname(f)) == "profile":
        out += [f"licence: the brief is in profile/ but a source is NC/ND/non-free/unknown ({l[:80]}): "
                "move it to _eval/local/brief.md" for l in sources_closed(text)]
    return out


def prompt(pname, T=None, p=None, pdir=None):
    """the research agent's prompt, from the project's language and donor: block"""
    import datetime
    from project import project, project_dir
    p = p if p is not None else project(pname)
    pdir = pdir or project_dir(pname)
    iso = str(p.get("language") or "").split("-")[0].lower()
    T, g, levels = lineage(iso, T)
    gname = lambda x: f"{T.name(x)} ({T.iso(x) or x})"
    rel = []
    for anc, d, new in levels:
        langs = [x for x in new if T.iso(x)]
        if langs:
            rel.append(f"  {d}. under {T.name(anc)} ({anc}): " + ", ".join(gname(x) for x in langs[:12])
                       + (f" and {len(langs) - 12} more" if len(langs) > 12 else ""))
        if len(rel) >= 3:
            break
    dn = p.get("donor") or {}
    known = dn.get("known") if dn.get("known") not in (None, "none") else None
    fam = family_points(T, g)
    cats = "\n".join(f"- **{c}**: {w}" for c, w in GENERAL)
    famtxt = "\n".join(f"- {name}: " + "; ".join(xs) for name, xs in fam) or \
        "- (no family-specific list here: find out from the comparative literature what this family is known to mark)"
    fill = {"language_name": str(p.get("language_name") or iso).split(" (")[0], "iso": iso, "glottocode": g,
            "classification": " > ".join(T.name(x) for x in T.l[g][3]) + " (Glottolog)",
            "family": T.name(T.l[g][3][0]) if T.l[g][3] else "an isolate",
            "relatives": "\n".join(rel) or "  (none recorded)",
            "structure": ", ".join(dn.get("structure") or []) or "not recorded",
            "known": (f"{dn.get('name') or known} ({known}): the related language you know best; "
                      "`python3 scripts/seeds.py prompt` covers it from memory, you cover it from sources")
                     if known else "none recorded (`python3 scripts/donor.py run <project> --write`)",
            "categories": cats, "family_points": famtxt,
            "glottolog_urls": "\n".join(f"  - https://glottolog.org/resource/languoid/id/{x}"
                                        for x in [g] + list(reversed(T.l[g][3]))[:3]),
            "project": pname, "pdir": os.path.relpath(pdir, ROOT),
            "corpus": ", ".join(p.get("style_from") or []) or "the project's style corpus",
            "date": datetime.date.today().isoformat()}
    text = open(os.path.join(ROOT, "docs", "prompts", "brief_prompt.md"), encoding="utf-8").read()
    text = re.sub(r"^<!--.*?-->\n", "", text, flags=re.S)
    for k, v in fill.items():
        text = text.replace("{" + k + "}", v)
    return text


def check(pname, pdir=None, seeds_data=None, tested=None):
    """[(point id, status, [(seed id, state)])], problems: each point's seeds and their state (tested by a store entry:
    confirmed or contradicted; untested); a point without a seed is 'no test'"""
    import seeds as S
    from project import project_dir
    pdir = pdir or project_dir(pname)
    f = path(pdir)
    if not f:
        return None, [f"no brief ({os.path.relpath(path(pdir, False), ROOT)} or _eval/local/brief.md): "
                      f"python3 scripts/seeds.py brief {pname}"]
    d = seeds_data if seeds_data is not None else (S.load(os.path.join(pdir, "profile")) or {})
    t = tested if tested is not None else S.tested(pname)
    by_point = {}
    for e in d.get("entries", []):
        for b in ([e["brief"]] if isinstance(e.get("brief"), str) else e.get("brief") or []):
            by_point.setdefault(b, []).append(e["id"])
    out = []
    pts = points(open(f, encoding="utf-8").read())
    for pid, st, _ in pts:
        res = []
        for sid in by_point.get(pid, []):
            vs = [str(v) for _, v in t.get(sid, [])]
            state = ("contradicted" if any("contradict" in v for v in vs) else "confirmed" if vs else "untested")
            res.append((sid, state))
        out.append((pid, st, res))
    ids = {pid for pid, _, _ in pts}
    probs = problems(f) + [f"seed names brief point {b}, not in the brief" for b in by_point if b not in ids]
    return out, probs


def summary(rows):
    def state(res):
        if not res:
            return "no test"
        ss = {s for _, s in res}
        return "contradicted" if "contradicted" in ss else "untested" if "untested" in ss else "confirmed"
    import collections
    return collections.Counter(state(r) for _, _, r in rows), state


def main(a):
    if not a:
        raise SystemExit(__doc__)
    if a[0] == "--check":
        rows, probs = check(a[1])
        if rows is None:
            raise SystemExit(probs[0])
        n, state = summary(rows)
        print(f"{a[1]}: {len(rows)} brief points: " + ", ".join(f"{v} {k}" for k, v in sorted(n.items())))
        for pid, st, res in rows:
            print(f"  {pid:30} [{st:8}] {state(res):12} " + "; ".join(f"{s} {x}" for s, x in res))
        for p in probs:
            print("  problem:", p)
        sys.exit(1 if probs else 0)
    print(prompt(a[0]))


if __name__ == "__main__":
    main(sys.argv[1:])
