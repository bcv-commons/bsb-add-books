#!/usr/bin/env python3
"""Priors: what is believed about a language before its corpus is studied, as a list the derived products test
(internal-docs plan, section 25). For a known or partly known language the model knows things the statistics would
otherwise have to rediscover (Bern German: ver-, us-, uf- form words and carry no grammar; -sch is the 2nd singular).
Each item is a hypothesis with its source until the corpus or the team confirms it: for a partial language the risk is
the standard language leaking in, and the check below shows it item by item.

export/<project>/profile/priors.yaml (in git, CC0, editable by the team; a speaker's entry outranks the model's):
    source: "model knowledge (<route>, <date>)"
    language: <name>
    word_forming_prefixes: [ver-, ent-, ...]   # derivation: no inflectional meaning; left out of the affix hypotheses
    word_forming_suffixes: [-ig, -lech, ...]
    inflection:                                 # affix + the Greek feature value it should go with
      - {affix: -sch, expect: person+number=ss, note: "2sg present (du gosch)", confidence: high}
    function_words: {articles: [...], pronouns: [...], prepositions: [...], conjunctions: [...], negation: [...]}
    notes: ["...", ...]                         # other facts in words (word order, clitics), for the study agent
Feature values (the derived products' Greek features): person=first|second|third, number=singular|plural,
person+number=fs|ss|ts|fp|sp|tp, tense=present|aorist|imperfect|perfect|future, mood=indicative|subjunctive|
imperative|infinitive|participle, tense+mood=<tense>.<mood>, voice=active|passive|middle, gcase=nominative|genitive|
dative|accusative|vocative, degree=comparative|superlative, negated=yes, object=<person><number> (1s, 3p),
person+number+mood=<pn>.<mood> (fp.subjunctive = 'let us').

    python3 scripts/priors.py write <project> [--route api|claude-code] [--force]   ask a fresh model (no tools, no files)
    python3 scripts/priors.py check <project>                                       test them against the corpus
"""
import collections, datetime, json, os, re, sqlite3, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

PROMPT = """You are helping to set up the study of a language from its New Testament translation. Before the corpus is
studied, write down what you know about the language **{language}** ({iso}; close to {close_to}), as a YAML document in
exactly this shape, and nothing else (no prose before or after, no code fence):

source: "model knowledge"
language: "{language}"
word_forming_prefixes: [...]   # prefixes that form words (derivation), with no inflectional meaning, written as "x-"
word_forming_suffixes: [...]   # the same for suffixes, written as "-x"
inflection:                    # inflectional affixes, each with the grammatical value it marks
  - {{affix: "-x", expect: "<feature>=<value>", note: "...", confidence: high|medium|low}}
function_words:
  articles: [...]
  pronouns: [...]
  prepositions: [...]
  conjunctions: [...]
  negation: [...]
notes: ["...", ...]            # other facts that a translator needs: word order, clitics, verb forms, spelling

Rules:
- Write the forms **as this language writes them**, not as {close_to} does. Where you are not sure a form belongs to this
  language rather than to {close_to}, give it `confidence: low` or leave it out. Fewer, surer items are better.
- `expect` uses only these feature values (they are what the Greek source marks): person=first|second|third,
  number=singular|plural, person+number=fs|ss|ts|fp|sp|tp (first/second/third, singular/plural),
  tense=present|aorist|imperfect|perfect|future, mood=indicative|subjunctive|imperative|infinitive|participle,
  tense+mood=<tense>.<mood>, voice=active|passive|middle, gcase=nominative|genitive|dative|accusative|vocative,
  degree=comparative|superlative, negated=yes, object=<person><number> such as 3s, and
  person+number+mood=<person+number>.<mood> (fp.subjunctive is 'let us'). Map the language's own category to the
  nearest of these (a past participle formed with a prefix: tense+mood=perfect.participle).
- At most 25 inflection items, 15 word-forming affixes of each kind, 12 words per function-word list, 10 notes.
"""


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))


def path(pname):
    return os.path.join(ROOT, "export", pname, "profile", "priors.yaml")


def load(pname):
    import yaml
    f = path(pname)
    return (yaml.safe_load(open(f, encoding="utf-8")) or {}) if os.path.exists(f) else None


def word_forming(pname):
    """The affix candidates the priors say carry no grammar (folded), for lang.py derive to leave out."""
    p = load(pname) or {}
    return {fold(a) for a in (p.get("word_forming_prefixes") or []) + (p.get("word_forming_suffixes") or [])}


def inflection_affixes(pname):
    p = load(pname) or {}
    return {fold(str(it.get("affix", ""))) for it in p.get("inflection") or []}


def write(pname, route=None, force=False):
    import yaml
    from project import project
    import probe_language as PL
    f = path(pname)
    if os.path.exists(f) and not force:
        raise SystemExit(f"{os.path.relpath(f, ROOT)} exists (--force writes it again; the team's edits would be lost)")
    p = project(pname)
    route = route or (PL.route_available() or [None])[0]
    if not route:
        raise SystemExit("no model route: set ANTHROPIC_API_KEY or install Claude Code")
    prompt = PROMPT.format(language=p.get("language_name") or pname, iso=p.get("language"),
                           close_to=p.get("close_to") or "the related standard language")
    text, usage = PL.ask_model(prompt, route)
    text = re.sub(r"^```\w*\n|\n```\s*$", "", text.strip())
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or "inflection" not in data:
        raise SystemExit("the model's answer is not the YAML asked for:\n" + text[:500])
    data["source"] = f"model knowledge ({route}, {datetime.date.today().isoformat()}): hypotheses until the corpus or the team confirms them"
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w", encoding="utf-8") as w:
        w.write("# Priors: what was believed about the language before its corpus was studied (scripts/priors.py).\n"
                "# Each item is a hypothesis; `python3 scripts/priors.py check` tests it against the corpus. The team may\n"
                "# correct or add items (mark them `source: team`); a speaker's entry outranks the model's.\n")
        yaml.safe_dump(data, w, allow_unicode=True, sort_keys=False, width=110)
    n = len(data.get("inflection") or [])
    print(f"{os.path.relpath(f, ROOT)}: {n} inflection items, {len(data.get('word_forming_prefixes') or [])} word-forming "
          f"prefixes; {usage.get('input_tokens', 0) + usage.get('output_tokens', 0)} tokens")


def check(pname, out=print):
    """Each prior against the corpus: inflection items against the derived affix statistics (confirmed: the affix goes
    with the expected value at lift ≥ 1.5; weak; not found, with what the corpus has for that value instead), function
    words against the NT's word counts, word-forming affixes by how many words carry them."""
    import lang as L
    pri = load(pname)
    if not pri:
        out("no priors (python3 scripts/priors.py write <project>)")
        return {}
    P, con = L.connect(pname)
    forms = collections.Counter(dict(con.execute("select form, count(*) from nt_tokens group by form").fetchall()))
    ffold = collections.Counter()
    for f, n in forms.items():
        ffold[fold(f)] += n
    res = collections.Counter()
    out(f"## Priors ({pri.get('source', 'unknown source')}), checked against the corpus")
    out("  inflection:")
    for it in pri.get("inflection") or []:
        a, exp = fold(str(it.get("affix", ""))), str(it.get("expect", ""))
        f, _, v = exp.partition("=")
        row = con.execute("select n, lift from d_affix where affix=? and feature=? and value=?", (a, f, v)).fetchone()
        if row and row[1] >= 1.5:
            verdict = f"confirmed (n {row[0]}, lift {row[1]:.1f})"
            res["confirmed"] += 1
        else:
            alt = con.execute("select affix, n, lift from d_affix where feature=? and value=? order by lift * min(n, 300) desc "
                              "limit 2", (f, v)).fetchall()
            got = ", ".join(f"{x} ({l:.1f})" for x, n, l in alt) or "nothing"
            verdict = (f"weak (lift {row[1]:.1f})" if row else "not found") + f"; the corpus has for {exp}: {got}"
            res["weak" if row else "not found"] += 1
        out(f"    {it.get('affix')} = {exp} [{it.get('confidence', '?')}]: {verdict}")
    out("  function words (in the NT):")
    for cat, ws in (pri.get("function_words") or {}).items():
        if not isinstance(ws, list):
            continue
        cells = []
        for w in ws or []:
            n = ffold[fold(str(w))]
            cells.append(f"{w} {n}" if n else f"{w} ABSENT")
            res["fw attested" if n else "fw absent"] += 1
        out(f"    {cat}: " + ", ".join(cells))
    words = list(ffold.items())
    infl = inflection_affixes(pname)
    contra = []
    for a in (pri.get("word_forming_prefixes") or []) + (pri.get("word_forming_suffixes") or []):
        row = con.execute("select feature, value, n, lift from d_affix where affix=? order by lift desc limit 1", (fold(a),)).fetchone()
        if row and row[3] >= 5 and fold(a) not in infl:
            contra.append(f"{a} goes with {row[0]}={row[1]} (n {row[2]}, lift {row[3]:.1f})")
    if contra:
        out("  listed as word-forming, but the corpus ties it to a grammatical value (kept as a hypothesis): " + "; ".join(contra))
        res["word-forming contradicted"] += len(contra)
    for kind, key, test in (("prefixes", "word_forming_prefixes", lambda w, a: w.startswith(a[:-1])),
                            ("suffixes", "word_forming_suffixes", lambda w, a: w.endswith(a[1:]))):
        items = pri.get(key) or []
        if items:
            cells = [f"{a} {sum(1 for w, _ in words if test(w, fold(a)) and len(w) > len(a) + 2)}" for a in items]
            out(f"  word-forming {kind} (distinct words with it; left out of the affix hypotheses): " + ", ".join(cells))
    out("  summary: " + ", ".join(f"{k} {v}" for k, v in res.items()))
    return res


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("write", "check"):
        raise SystemExit(__doc__)
    if a[0] == "write":
        write(a[1], a[a.index("--route") + 1] if "--route" in a else None, "--force" in a)
    else:
        check(a[1])


if __name__ == "__main__":
    main()
