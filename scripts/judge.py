#!/usr/bin/env python3
"""A meaning judge for drafts: N versions of one chapter checked against the original by a fresh agent
(the drafting study's judge, made a standard tool).

Two modes:
  blind        the versions are shuffled and labelled A, B, C ...; quotation marks are normalised; the key is kept apart
               (`_eval/local/judge-keys/`), so the agent can't tell whose text is whose. The agent lists the meaning
               errors per verse and version, rates naturalness, and names the best starting point. `tally` unblinds.
  corrections  one or more named versions, not blinded (e.g. a team's own chapter, F12): the agent writes a per-verse
               report a translation team can work through (problem, why, a suggestion), beside the same JSON.

Every version is any chapter file with vN markers (a draft, a human chapter, an NLLB or in-context draft, a
back-translation into English for a language the judge can't read: give --lang accordingly). The case folder holds
only the versions and is all the agent may open besides the original and the BSB; it lives under the project's
`_eval/local/judge/` (never in git: it holds edition text).

Usage:
  python3 scripts/judge.py prepare <project> <code> <ch> NAME=FILE [NAME=FILE ...] [--case ID] [--corrections] [--lang L]
                                   [--seed N] [--note TEXT]   # --note: a paragraph for the judge (e.g. "these are
                                   back-translations: ignore their roughness")       # writes the case folder and the key, prints the agent's prompt
  python3 scripts/judge.py prompt <project> <case>  # the prompt again
  python3 scripts/judge.py tally <project> [case ...] [--by-version]  # unblinded figures per case, and in total

Costs about 80-100k tokens a chapter for three versions. Noise (three near-identical drafts, two judges, other label
orders): the error counts agree; the "best" pick and the top naturalness mark can follow the label (position bias). So compare versions by their errors, and trust a ranking only when it holds across two judgements
with different label orders (prepare the case twice, another --seed).
"""
import collections, json, os, random, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import langtools as LT  # noqa: E402
from books import BY_CODE  # noqa: E402
from project import project, project_dir, sources  # noqa: E402

QUOTES = str.maketrans({c: '"' for c in "„“”«»‹›"})
TYPES = "omission|addition|referent|sense|polarity|tam|structure|choice"


def dirs(pname):
    base = os.path.join(project_dir(pname), "_eval", "local")
    return os.path.join(base, "judge"), os.path.join(base, "judge-keys")


def lines_of(path, ch, code):
    raw = open(path, encoding="utf-8").read().splitlines()
    cv = [l for l in raw if re.match(r"\d+:\d+\s", l)]
    if cv and len(cv) >= len([l for l in raw if l.strip()]) / 2:    # already "chapter:verse text" lines (a judge case,
        out = []                                                     # a back-translation)
        for l in cv:
            m = re.match(r"(\d+):(\d+)\s+(.*)", l)
            if int(m[1]) == ch:
                out.append(f"{m[1]}:{m[2]} {m[3].translate(QUOTES)}")
        return out
    if not re.fullmatch(r"[0-9a-z]{3}(\d{3})?\.txt", os.path.basename(path)):   # any file name: read it as <code><ch>.txt
        import shutil, tempfile
        tmp = os.path.join(tempfile.mkdtemp(), f"{code}{ch:03d}.txt")
        shutil.copy(path, tmp)
        path = tmp
    vs = LT.verses_of(path)
    return [f"{c}:{v} {t.translate(QUOTES)}" for (c, v), t in sorted(vs.items()) if c == ch]


def prompt(pname, case):
    jdir, kdir = dirs(pname)
    meta = json.load(open(os.path.join(kdir, f"{case}.json"), encoding="utf-8"))
    cdir = os.path.join(jdir, case)
    labels = sorted(meta["labels"])
    files = ", ".join(f"{l}.txt" for l in labels)
    head = (f"Case folder: {cdir}/  ({files}: one verse per line, \"chapter:verse text\"; quotation marks were normalised to "
            f"plain quotes).\nLanguage of the versions: {meta['lang']}.\n"
            f"The original: {meta['orig']} ({meta['orig_form']}). The BSB English for orientation: {meta['bsb']}.\n")
    note = (meta.get("note") + "\n\n") if meta.get("note") else ""
    errors = note + (f"For every verse and every version, list the MEANING errors against the original: omission (something in the "
              "original is missing), addition (something not in the original and not implied), wrong referent (who does what "
              "to whom), wrong sense of a word or phrase, polarity/negation, wrong tense/aspect/mood where it changes the "
              "meaning, and wrong structure (a question made a statement, a condition made a fact). Do NOT count style, word "
              "order, spelling, dialect choices or legitimate interpretive choices that a careful translator could make (mark "
              "these as 'choice' only if you think a reader would be misled). Severity: 'major' (a reader gets a different "
              "meaning) or 'minor' (a nuance lost or added).")
    if meta["mode"] == "blind":
        n = len(labels)
        return (f"You are reviewing {n} translations of one Bible chapter ({meta['ref']}) for meaning accuracy. They are labelled "
                f"{', '.join(labels)}; you are not told who made them, and you must not try to find out: open ONLY the files "
                "named below (no other folder of this repository, no search for these texts).\n\n" + head + "\n" + errors +
                f"\n\nThen rate each version's naturalness in {meta['lang']} for the whole chapter (1-5, 5 = reads like a fluent "
                "native text) with one sentence of reason, and say which version you'd give to a review team as the best "
                "starting point, and why (two sentences).\n\n"
                f"Write your result as JSON to {cdir}/review.json:\n"
                f'{{"errors": [{{"verse": "{meta["ch"]}:3", "label": "A", "type": "{TYPES}", "severity": "major|minor", '
                '"note": "..."}], "naturalness": {"A": [n, "reason"], ...}, "best": {"label": "A", "why": "..."}}\n'
                "Check every verse of every version; be consistent between them (the same deviation counts the same way in "
                "each). Reply with a three-line summary when done.")
    names = ", ".join(f"{l}.txt = {meta['labels'][l]}" for l in labels)
    return (f"You are checking a translation of one Bible chapter ({meta['ref']}) for meaning against the original, for the "
            f"translation team. The versions are: {names}. Open ONLY the files named below.\n\n" + head + "\n" + errors +
            "\n\nThe team reads your report: write it so they can act on it. Per finding give the verse, what the original says, "
            "what the version says (quote at most a few words of it), why it matters, and a suggestion in plain words (not a "
            "rewritten verse). Say also what the version does well, in two or three sentences. Where you are unsure whether "
            "something is an error, say so and phrase it as a question.\n\n"
            f"Write {cdir}/review.json (same shape: {{\"errors\": [{{\"verse\", \"label\", \"type\": \"{TYPES}\", \"severity\", "
            "\"note\", \"suggestion\"}], \"naturalness\": {label: [n, reason]}, \"summary\": \"...\"}) and "
            f"{cdir}/corrections.md (the readable report, verse by verse, in English). Reply with a three-line summary.")


def prepare(a):
    pname, code, ch = a[0], a[1], int(a[2])
    opts = {k: a[a.index(k) + 1] for k in ("--case", "--lang", "--seed", "--note") if k in a}
    pairs = [x for i, x in enumerate(a[3:], 3) if "=" in x and a[i - 1] not in opts.keys() and not x.startswith("--")]
    if not pairs:
        raise SystemExit("prepare: give the versions as NAME=FILE")
    p = project(pname)
    mode = "corrections" if "--corrections" in a else "blind"
    case = opts.get("--case") or f"{code}{ch:03d}-{mode}"
    jdir, kdir = dirs(pname)
    cdir = os.path.join(jdir, case)
    if os.path.exists(os.path.join(kdir, f"{case}.json")):
        raise SystemExit(f"case {case} exists (give --case)")
    versions = [(n, os.path.join(ROOT, f) if not os.path.isabs(f) else f) for n, f in (x.split("=", 1) for x in pairs)]
    for n, f in versions:
        if not os.path.exists(f):
            raise SystemExit(f"{n}: no file {f}")
    if mode == "blind":
        random.Random(int(opts.get("--seed", random.randrange(10 ** 6)))).shuffle(versions)
    labels = {chr(65 + i): n for i, (n, _) in enumerate(versions)}
    os.makedirs(cdir, exist_ok=True); os.makedirs(kdir, exist_ok=True)
    counts = {}
    for i, (n, f) in enumerate(versions):
        ls = lines_of(f, ch, code)
        if not ls:
            raise SystemExit(f"{n}: no verses of chapter {ch} in {f}")
        counts[n] = len(ls)
        open(os.path.join(cdir, f"{chr(65 + i)}.txt"), "w", encoding="utf-8").write("\n".join(ls) + "\n")
    od, _, ad = sources(p, code)
    ot = BY_CODE[code][2] == "ot"
    meta = {"case": case, "mode": mode, "project": pname, "code": code, "ch": ch, "ref": f"{BY_CODE[code][1]} {ch}",
            "lang": opts.get("--lang") or (p.get("language_name") or p.get("language") or "the target language").split(" (")[0],
            "orig": os.path.join(ROOT, od, f"{code}{ch:03d}.txt"), "bsb": os.path.join(ROOT, ad, f"{code}{ch:03d}.txt"),
            "orig_form": ("the Hebrew in clause lines, \"verse:level text\"; OT verse numbers are the Hebrew ones" if ot
                          else "the Greek, \"chapter:verse text\""),
            "labels": labels, "sources": {n: os.path.relpath(f, ROOT) for n, f in versions}, "verses": counts,
            "note": opts.get("--note", "")}
    json.dump(meta, open(os.path.join(kdir, f"{case}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"# case {case}: {os.path.relpath(cdir, ROOT)} ({', '.join(f'{n} {c} verses' for n, c in counts.items())})",
          file=sys.stderr)
    print(prompt(pname, case))


def tally(a):
    pname = a[0]
    jdir, kdir = dirs(pname)
    cases = [x for x in a[1:] if not x.startswith("--")] or sorted(
        f[:-5] for f in os.listdir(kdir) if f.endswith(".json")) if os.path.isdir(kdir) else []
    tot = collections.defaultdict(lambda: collections.Counter())
    print("| case | version | major | minor | choice | naturalness | best |\n|---|---|---|---|---|---|---|")
    for case in cases:
        meta = json.load(open(os.path.join(kdir, f"{case}.json"), encoding="utf-8"))
        rf = os.path.join(jdir, case, "review.json")
        if not os.path.exists(rf):
            print(f"| {case} | (no review.json yet) | | | | | |")
            continue
        r = json.load(open(rf, encoding="utf-8"))
        best = (r.get("best") or {}).get("label")
        for lab, name in sorted(meta["labels"].items()):
            es = [e for e in r.get("errors", []) if e.get("label") == lab]
            maj = sum(1 for e in es if e.get("severity") == "major" and e.get("type") != "choice")
            mnr = sum(1 for e in es if e.get("severity") != "major" and e.get("type") != "choice")
            cho = sum(1 for e in es if e.get("type") == "choice")
            nat = (r.get("naturalness") or {}).get(lab, [None])[0]
            t = tot[name]; t["major"] += maj; t["minor"] += mnr; t["choice"] += cho; t["cases"] += 1
            t["best"] += best == lab
            if nat is not None:
                t["nat"] += nat; t["nat_n"] += 1
            print(f"| {case} | {name} | {maj} | {mnr} | {cho} | {nat if nat is not None else '–'} | {'yes' if best == lab else ''} |")
    if len(cases) > 1 or "--by-version" in a:
        print("\n| version | cases | major | minor | choice | naturalness (mean) | best |\n|---|---|---|---|---|---|---|")
        for name, t in sorted(tot.items()):
            nat = f"{t['nat'] / t['nat_n']:.1f}" if t["nat_n"] else "–"
            print(f"| {name} | {t['cases']} | {t['major']} | {t['minor']} | {t['choice']} | {nat} | {t['best']} |")


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    cmd, rest = a[0], a[1:]
    if cmd == "prepare" and len(rest) >= 4:
        prepare(rest)
    elif cmd == "prompt" and len(rest) == 2:
        print(prompt(*rest))
    elif cmd == "tally" and rest:
        tally(rest)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
