#!/usr/bin/env python3
"""Check (and later seed) a language profile: docs/language-store.md.

A profile folder holds observations.json, decisions.json and external.json for one language and
edition. `check` validates them against the contract without any library:
  1. the structure (required fields, kinds, enums, reference format; a lightweight reading of
     schema/language_profile.schema.json);
  2. every evidence reference resolves to a verse of the edition's text;
  3. every term, formula and name value occurs in at least one cited verse (case ignored; the
     combining marks named in `orthography.ignore_marks` ignored; a formula's <slots> ignored);
  4. ids are unique among live entries; `supersedes` points to an existing entry;
  5. feature codes match the Grambank/WALS pattern;
  5a. grammar entries (morph, cell, claim; README, *Kinds*): their fields and enums; a morph's form occurs in at least
     one cited verse on its side of a word (a prefix at the start, a suffix at the end, an infix inside; marks
     ignored as in 3; tone morphs are not matched); a cell's morphs are morph entries; a cell cites evidence unless
     it is a gap;
  5b. team decisions (`method: team-decision`, `by: team:<who>`) name their source (`team_source`, an item of the wiki's
     team-input page) instead of needing verse evidence, and are binding: an entry by anyone else that supersedes a team
     decision, or replaces it under the same id, is an error (only the team changes its own facts);
  6. with --project, for a non-free style edition: quotations keep to docs/licensing.md (evidence forms at
     most 4 words; a note, pattern or value quotes at most 15 words, from the published text, as written);
  7. agreement with lexeme-aligner's gram-struct where a feature id maps to one of its slots
     (reported, not enforced): --gram-struct <iso>.json, default download/lexeme-aligner/grammar/gs_<iso>.json.

The edition's text is found through its id (import/<licence>/<iso>/<edition>/text/, chapter files
<code>NNN.txt with vN markers) or given with --text-dir. --project <id> resolves a draft project's
style_from edition instead, and lets evidence cite the project's own drafts (export/<project>/<code>/).

Usage: python3 scripts/language_profile.py check <profile dir> [--text-dir DIR | --project ID] [--gram-struct FILE]
"""
import collections, glob, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from books import BY_CODE  # noqa: E402
from project import project_dir  # noqa: E402
from langtools import WORD_MARKS  # noqa: E402

KINDS = {"feature", "letter", "gap", "term", "formula", "name", "morph", "cell", "claim"}
NEEDS_EVIDENCE = {"feature", "term", "formula", "name", "morph"}
SLOTS = {"prefix", "suffix", "infix", "clitic", "free", "tone"}
VERDICTS = {"confirmed", "corpus-only", "contradicted", "new", "open"}
TESTS = {"corpus", "greek", "hebrew", "nllb", "team"}
ENUMS = {"confidence": {"high", "medium", "low"}, "method": {"corpus-observed", "corpus-derived", "project-decision", "external", "team-decision"},
         "status": {"observed", "decided", "open", "superseded"}, "partition": {"observations", "decisions", "external"}}
REQUIRED = ["id", "kind", "value", "confidence", "method", "by", "date", "status"]
REF = re.compile(r"^([1-3A-Z][A-Z0-9]{2}) (\d{1,3}):(\d{1,3})$")
CODE = re.compile(r"^(GB\d{3}|WALS:\d{1,3}[A-Z])$")
GRAM_SLOTS = {"constituent_order": None, "adposition": "adposition", "possessor": "possessor", "article": "article_bound"}


def verses_of(path):
    """{(chapter, verse): text} of a repo chapter file (vN markers, notes and headings removed)."""
    ch = int(os.path.basename(path)[3:6])
    body = [re.sub(r"^//\d+ ", "", l) for l in open(path, encoding="utf-8").read().splitlines()
            if not l.startswith(("!!", "===")) and not re.fullmatch(r"==.*==", l)]
    text = re.sub(r"\{[A-Z]:[^{}]*\}", " ", " ".join(body))
    parts = re.split(r"(?<![\w>.])v(\d+)(?:-\d+)?(?=\s)", text)
    return {(ch, int(parts[i])): re.sub(r"\s+", " ", parts[i + 1]).strip() for i in range(1, len(parts) - 1, 2)}


def load_text(text_dir):
    """Chapter files (<code>NNN.txt) and book files (<code>.txt, 'c:v<TAB>text' lines)."""
    import langtools as LT
    out = {}
    for f in glob.glob(os.path.join(text_dir, "*.txt")):
        b = os.path.basename(f)
        if re.fullmatch(r"[0-9a-z]{3}\d{3}\.txt", b):
            for (c, v), t in verses_of(f).items():
                out[(b[:3].upper(), c, v)] = t
        elif re.fullmatch(r"[0-9a-z]{3}\.txt", b) and b[:3] in BY_CODE:
            for (c, v), t in LT.verses_of(f).items():
                out[(b[:3].upper(), c, v)] = t
    return out


def text_dir_of(args, iso, edition):
    if "--text-dir" in args:
        return args[args.index("--text-dir") + 1]
    from project import edition as ed_cfg, project as proj_cfg
    if "--project" in args:
        p = proj_cfg(args[args.index("--project") + 1])
        edition = p["style_from"][0]
    e = ed_cfg(edition)
    return os.path.join(ROOT, e["dir"], e.get("text_dir", "text"))


def morph_in(form, slot, verse, marks, chain=False):
    """does the morph occur in the verse, on its side of a word (parts of a hyphenated word count as words); an affix
    of a chain (an entry with `position`) may stand inside the word, after (before) the chain's other affixes"""
    bare = normal(form.strip("-="), marks)
    if not bare:
        return False
    words = [w for t in re.findall(rf"[\w{WORD_MARKS}\ua789'-]+", normal(verse, marks)) for w in [t] + t.split("-")]
    if slot == "prefix":
        return any((bare in w[:-1] if chain else w.startswith(bare)) and len(w) > len(bare) for w in words)
    if slot == "suffix":
        return any((bare in w[1:] if chain else w.endswith(bare)) and len(w) > len(bare) for w in words)
    if slot == "infix":
        return any(bare in w[1:-1] for w in words)
    return any(w == bare or bare in w for w in words)


def normal(s, marks):
    s = unicodedata.normalize("NFD", s.lower())
    return unicodedata.normalize("NFC", "".join(c for c in s if c not in marks))


def main():
    args = sys.argv[1:]
    if len(args) < 2 or args[0] != "check":
        raise SystemExit(__doc__)
    folder = args[1]
    files = [f for f in ("observations.json", "decisions.json", "external.json") if os.path.exists(os.path.join(folder, f))]
    if not files:
        raise SystemExit(f"no profile files in {folder}")
    problems, notes = [], []
    entries, text, marks, links = {}, None, set(), []
    iso = edition = None
    team_ids, others, spelling = set(), [], []
    for fn in files:
        prof = json.load(open(os.path.join(folder, fn), encoding="utf-8"))
        for k in ("iso", "edition", "partition", "entries"):
            if k not in prof:
                problems.append(f"{fn}: missing {k}")
        if prof.get("partition") not in ENUMS["partition"]:
            problems.append(f"{fn}: partition {prof.get('partition')!r}")
        iso, edition = prof.get("iso", iso), prof.get("edition", edition)
        marks |= {chr(int(m[2:], 16)) for m in (prof.get("orthography") or {}).get("ignore_marks", [])}
        if text is None:
            try:
                text = load_text(text_dir_of(args, iso, edition))
            except Exception as e:  # noqa: BLE001
                notes.append(f"edition text not found ({e}); references and forms not checked")
                text = {}
            if text and "--project" in args:      # a project's decisions may cite its own drafts
                pd = project_dir(args[args.index("--project") + 1])
                for d in glob.glob(os.path.join(pd, "[0-9a-z][0-9a-z][0-9a-z]")):
                    for k, t in load_text(d).items():
                        text.setdefault(k, t)
        for e in prof.get("entries", []):
            eid = e.get("id", "?")
            where = f"{fn} {eid}"
            for k in REQUIRED:
                if k not in e:
                    problems.append(f"{where}: missing {k}")
            if e.get("kind") not in KINDS:
                problems.append(f"{where}: kind {e.get('kind')!r}")
            for k, allowed in ENUMS.items():
                if k in e and e[k] not in allowed:
                    problems.append(f"{where}: {k} {e[k]!r}")
            team = e.get("method") == "team-decision"
            if team:
                team_ids.add(eid)
                if not str(e.get("by", "")).startswith("team:"):
                    problems.append(f"{where}: a team decision needs by: team:<who>")
                if not e.get("team_source"):
                    problems.append(f"{where}: a team decision needs team_source (the team-input item)")
            else:
                others.append((where, e))
            k = e.get("kind")
            if k == "morph":
                for f in ("form", "slot", "host"):
                    if not e.get(f):
                        problems.append(f"{where}: a morph needs {f}")
                if e.get("slot") and e["slot"] not in SLOTS:
                    problems.append(f"{where}: slot {e['slot']!r}")
            if k == "cell":
                for f in ("paradigm", "bundle"):
                    if not e.get(f):
                        problems.append(f"{where}: a cell needs {f}")
                if not e.get("evidence") and not e.get("gap") and not team:
                    problems.append(f"{where}: no evidence (or gap: true)")
            if k == "claim":
                if e.get("verdict") not in VERDICTS:
                    problems.append(f"{where}: verdict {e.get('verdict')!r}")
                for t in e.get("tests", []):
                    if t not in TESTS:
                        problems.append(f"{where}: test {t!r}")
            if e.get("kind") in NEEDS_EVIDENCE and not e.get("evidence") and not team:
                problems.append(f"{where}: no evidence")
            if e.get("kind") in ("term", "formula", "name") and not e.get("source"):
                problems.append(f"{where}: no source")
            if e.get("kind") in ("term", "formula", "name") and e.get("attested") not in ("attested", "by-rule") and not team:
                problems.append(f"{where}: {e.get('kind')} needs attested: attested | by-rule")
            if e.get("method") == "external" and not e.get("external_source"):
                problems.append(f"{where}: external entry without external_source")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(e.get("date", ""))):
                problems.append(f"{where}: date {e.get('date')!r}")
            for c in e.get("codes", []):
                if not CODE.match(c):
                    problems.append(f"{where}: code {c!r}")
            found_form = False
            for r in e.get("evidence", []):
                m = REF.match(r.get("ref", ""))
                if not m:
                    problems.append(f"{where}: bad reference {r.get('ref')!r}")
                    continue
                if m[1].lower() not in BY_CODE:
                    problems.append(f"{where}: unknown book {m[1]}")
                    continue
                key = (m[1], int(m[2]), int(m[3]))
                if text and key not in text:
                    if e.get("kind") == "gap" or "draft" in e.get("note", ""):
                        continue      # a gap may cite a verse the edition doesn't have yet
                    problems.append(f"{where}: {r['ref']} is not in the edition")
                    continue
                if text and k == "morph" and e.get("slot") != "tone" and e.get("form"):
                    found_form = found_form or morph_in(e["form"], e.get("slot"), text[key], marks, bool(e.get("position")))
                if text and e.get("kind") in ("term", "formula", "name") and e.get("attested") != "by-rule":
                    form = r.get("form") or (e["value"] if isinstance(e["value"], str) else "")
                    form = re.sub(r"<[^>]*>", "", form).strip()
                    if form and normal(form, marks) in normal(text[key], marks):
                        found_form = True
            if text and e.get("kind") in ("term", "formula", "name") and e.get("attested") != "by-rule" and e.get("evidence") and not found_form and not team:
                problems.append(f"{where}: value {e.get('value')!r} not found in any cited verse")
            if text and k == "morph" and e.get("slot") != "tone" and e.get("evidence") and not found_form:
                problems.append(f"{where}: morph {e.get('form')!r} not found ({e.get('slot')}) in any cited verse")
            if text and marks and e.get("kind") in ("term", "formula", "name") and e.get("status") != "superseded" \
                    and isinstance(e.get("value"), str):
                spelling.append((where, e["value"]))
            if eid in entries and e.get("status") != "superseded" and entries[eid].get("status") != "superseded":
                problems.append(f"{where}: duplicate live id")
            entries[eid] = e
            if e.get("supersedes"):
                links.append((where, e["supersedes"]))
    for where, target in links:
        if target not in entries:
            problems.append(f"{where}: supersedes unknown entry {target}")
    for eid, e in entries.items():        # a cell's morphs are morph entries
        for m in e.get("morphs", []) if e.get("kind") == "cell" else []:
            if entries.get(m, {}).get("kind") != "morph":
                problems.append(f"{eid}: morph {m} is not a morph entry")
    for where, e in others:      # only the team changes a team decision
        if e.get("status") != "superseded" and (e.get("supersedes") in team_ids or e.get("id") in team_ids):
            problems.append(f"{where}: replaces a team decision ({e.get('supersedes') or e.get('id')}); "
                            "only the team changes it (write the question on the wiki's team-input page instead)")
    # quotations of non-free editions (docs/licensing.md): an evidence form is the attested word or phrase
    # (at most 4 words), a note, pattern or value quotes at most a phrase, from the published text, as written
    if "--project" in args:
        import quotes
        Q = quotes.Quotes(args[args.index("--project") + 1])
        if Q.limited_eds:
            for eid, e in entries.items():
                where = f"{eid}"
                for r in e.get("evidence", []):
                    if len((r.get("form") or "").split()) > 4:
                        problems.append(f"{where}: evidence form of {len(r['form'].split())} words for {r.get('ref')} "
                                        "(at most 4: the attested word or phrase, not the verse)")
                for k in ("note", "pattern", "value"):
                    if isinstance(e.get(k), str):
                        problems += [f"{where}: {k} {x}" for x in Q.check_snippet(e[k])]
    # gram-struct agreement
    gs_path = args[args.index("--gram-struct") + 1] if "--gram-struct" in args else os.path.join(ROOT, "download", "lexeme-aligner", "grammar", f"gs_{iso}.json")
    if os.path.exists(gs_path):
        gs = json.load(open(gs_path, encoding="utf-8"))
        for eid, slot in GRAM_SLOTS.items():
            e = entries.get(eid)
            if not e or not slot or slot not in gs:
                continue
            g = gs[slot]
            theirs = g.get("direction", g.get("bound"))
            notes.append(f"gram-struct {slot}: {theirs!r} ({g.get('source')}); profile {eid}: {e['value']!r}")
    print(f"{folder}: {len(entries)} entries in {len(files)} files, {len(problems)} problems")
    for p in problems:
        print("  problem:", p)
    for n in notes:
        print("  note:", n)
    # the value is what agents copy: a word the edition writes only with other marks is flagged (matching ignores them)
    if spelling and text:
        wrx = re.compile(rf"[\w{WORD_MARKS}\ua789]+")
        exact, plain = set(), {}
        for t in text.values():
            for w in wrx.findall(normal(t, ())):
                exact.add(w); plain.setdefault(normal(w, marks), collections.Counter())[w] += 1
        out = []
        for where, v in spelling:
            for w in wrx.findall(normal(re.sub(r"<[^>]*>", "", v), ())):
                if w not in exact and normal(w, marks) in plain:
                    out.append(f"{where}: {w} -> {', '.join(x for x, _ in plain[normal(w, marks)].most_common(3))}")
        if out:
            print(f"  {len(out)} words in store values that the edition writes only with other marks (check them):")
            for n in out:
                print("  spelling:", n)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
