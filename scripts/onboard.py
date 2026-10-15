#!/usr/bin/env python3
"""Set up a new language project step by step: the wizard for a new team (docs/onboarding.md).

    python3 scripts/onboard.py                        # asks every question, with a default for each
    python3 scripts/onboard.py --answers FILE.yaml    # takes the answers it finds there, asks the rest
    python3 scripts/onboard.py --answers FILE.yaml --yes   # no questions: the file's answers, else the defaults
    python3 scripts/onboard.py ... --dry-run          # shows what it would write and fetch, changes nothing

The common case is a language that has an NT and no (or only part of the) OT, and a team that wants OT books.
The steps:

 1. how the AI work runs: the API (ANTHROPIC_API_KEY, billed per token) or Claude Code (claude -p, no tools);
 2. the language: code, name, the team's school language;
 3. the existing editions of the language, from the bcv-commons/bibles catalogue and the sources behind it
    (helloAO, openbible, eBible; scripts/fetch_edition.py): pick the ones to use as style corpus;
 4. each picked edition goes to import/<licence>/<language>/<edition>/ with a fetch recipe in edition.yaml and is
    downloaded. Its text is git-ignored in every licence folder, CC0 and CC BY included: what can be fetched from
    a URL is fetched again, not kept in git. The NT basis is read from the fetched text (test verses);
 5. the project: export/<language>/<project>/project.yaml; the books to draft, and a quarantine where a non-free
    edition has one of them (before the probes, so they don't use it);
 6. the probes (scripts/probe_language.py run): write, read, tell apart; the scores, the model's slips, one verse
    beside the edition, and a suggested familiarity the user accepts or overrides (close_to where it applies);
 7. the tools that familiarity switches on, with the tokens per chapter logged so far in that mode (scripts/usage.py);
 8. the sources (scripts/setup.py; for OT books the Hebrew layout and scripts/src.py's prepared structure), the
    alignment lexicons (scripts/align.py; for an unknown language also the NT occurrence index, scripts/lang.py), the
    empty memory (scripts/memory_prompt.py --init) with the probe's slips as its first entries;
 9. what comes next, asked for in Claude Code: the memory, the style guide, a reference chapter, waves.

An edition that isn't in any of these sources (copied in by hand, or synced from its own repository like Den
Frie Bibel) is imported with the import-edition skill; the wizard can still create the project on it
(answer `editions` with its id).

Answers (all optional; the wizard prints the file it used, so a run can be repeated):
    language: kvg                  language_name: Kuni          school_language: English
    dialect_id: null               # an interim id instead of the ISO code (ch-de-be)
    editions: [ebible:kvg]         # source:id from the list, or the id of an edition already in import/
    licence_folder: {ebible:kvg: non-free}   # only where the licence can't be read; default non-free
    project: kvg_BSB               books: [gen, exo]            familiarity: null (set by the probe)
    quotes: "“”"                   chapter_word: Chapter
    ai_route: api | claude-code    probe_model: claude-opus-5-5 (API route)   close_to: null   go_ahead: true
    run_setup: true                run_align: true              init_memory: true
"""
import collections, datetime, glob, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import yaml  # noqa: E402
from books import BOOKS, BY_CODE  # noqa: E402
import fetch_edition as FE  # noqa: E402
import project as P  # noqa: E402
import probe_language as PL  # noqa: E402
import usage  # noqa: E402

OPEN = FE.OPEN
ARGS = sys.argv[1:]
DRY = "--dry-run" in ARGS
YES = "--yes" in ARGS
ANSWERS = {}
USED = {}
# Verses a critical text leaves out and a majority / received text has (BSB codes, chapter, verse).
TEST_VERSES = [("mat", 17, 21), ("mat", 18, 11), ("mat", 23, 14), ("mrk", 7, 16), ("mrk", 9, 44), ("mrk", 11, 26),
               ("mrk", 15, 28), ("luk", 17, 36), ("luk", 23, 17), ("jhn", 5, 4), ("act", 8, 37), ("act", 15, 34),
               ("act", 24, 7), ("act", 28, 29), ("rom", 16, 24)]
QUOTE_PAIRS = ["“”", "„“", "«»", "»«", "‘’", "‚‘", "‹›", "「」", '""']


def say(text=""):
    print(text, flush=True)


def ask(key, question, default=None, choices=None, parse=None, check=None):
    """The answer from --answers, else from the user (or the default with --yes / without a terminal).
    A boolean default makes it a yes/no question; check(value) returns an error text or None."""
    yesno = isinstance(default, bool)
    while True:
        if key in ANSWERS:
            value = ANSWERS[key]
        elif YES or not sys.stdin.isatty():
            value = default
        else:
            hint = f" [{', '.join(choices)}]" if choices else ""
            shown = ("Y/n" if default else "y/N") if yesno else " ".join(map(str, default)) if isinstance(default, list) else default
            try:
                raw = input(f"{question}{hint}" + (f" ({shown})" if shown not in (None, "") else "") + ": ").strip()
            except EOFError:
                raise SystemExit("\nstopped (no more input); nothing after this step was done")
            if yesno and raw:
                value = raw.lower() in ("y", "yes", "j", "ja", "true", "1")
            else:
                value = parse(raw) if raw and parse else (raw or default)
        if isinstance(value, str) and yesno:
            value = value.lower() in ("y", "yes", "j", "ja", "true", "1")
        err = (f"not one of {choices}" if choices and value not in choices else None) or (check(value) if check else None)
        if not err:
            break
        if key in ANSWERS or YES or not sys.stdin.isatty():
            raise SystemExit(f"{key}: {value!r}: {err}")
        say(f"  {err}")
    USED[key] = value
    return value


ID = lambda v: None if v and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", str(v)) else "letters, digits, - _ . only"


def words(raw):
    return [w for w in re.split(r"[\s,]+", raw.strip()) if w]


def books_of(spec):
    """'ot', 'nt', 'gen-deu', 'rut jon' or a list -> BSB codes in canonical order."""
    order = [b[0] for b in BOOKS]
    out = set()
    for w in (spec if isinstance(spec, list) else words(spec or "")):
        w = str(w).lower()
        if w in ("ot", "nt"):
            out |= {c for c in order if BY_CODE[c][2] == w}
        elif "-" in w and all(x in BY_CODE for x in w.split("-", 1)):
            a, b = (order.index(x) for x in w.split("-", 1))
            out |= set(order[a:b + 1])
        elif w in BY_CODE:
            out.add(w)
        else:
            raise SystemExit(f"books: {w!r} is not a BSB book code (books.tsv), 'ot', 'nt' or a range like gen-deu")
    return [c for c in order if c in out]


def run(*cmd):
    say(f"  $ python3 {' '.join(cmd)}")
    if DRY:
        return 0
    return subprocess.run([sys.executable, *cmd], cwd=ROOT).returncode


# ---------- step 2: the editions ----------

def existing_ids():
    base = os.path.join(ROOT, "import")
    return {os.path.basename(os.path.dirname(f)) for f in glob.glob(os.path.join(base, "*", "*", "*", "edition.yaml"))}


def pick_editions(iso, listed):
    say(f"\n== 3. Existing editions of {iso!r} (bcv-commons/bibles catalogue, helloAO, openbible, eBible)")
    try:
        found, catalog = FE.candidates(iso)
    except Exception as e:
        say(f"  the sources can't be reached ({e}); import editions by hand (import-edition skill)")
        found, catalog = [], []
    listed.extend(found)
    cov = sorted({c for c, _ in catalog})
    say("  catalogue coverage: " + (", ".join(cov) or "nothing listed")
        + ("  (otp = part of the OT)" if "otp" in cov else ""))
    for i, c in enumerate(found, 1):
        parts = (f"OT {c['ot_books']} NT {c['nt_books']} books" if "ot_books" in c else f"{c['books']} books")
        say(f"  {i}. {c['source']}:{c['id']}  {c['title'][:90]}\n       [{c['cls'] or '? (read when fetched)'}: {c['licence'][:80]}] {parts}"
            + (f"  {c['note']}" if c.get("note") else ""))
    here = sorted(e for e in existing_ids())
    if here:
        say(f"  already in import/: {', '.join(here)}")
    default = []
    if found:   # prefer an edition with an NT; among them the most open, then the most books
        best = sorted(found, key=lambda c: (not c.get("nt"), OPEN.index(c["cls"]) if c["cls"] else 3, -c["books"]))[0]
        default = [f"{best['source']}:{best['id']}"]
        for c in found:
            if c is not best and c.get("ot") and not best.get("ot"):
                say(f"  note: {c['source']}:{c['id']} has OT books too ({c['books']} books, {c['cls'] or '?'}); the sources often carry"
                    " the same translation: add it if it is another text, or for its OT books (they are then corpus,"
                    " and drafting them is the case 'an edition already has the book')")
        say("  The listings often carry the same translation from different sources: pick one per text.")
    picked = ask("editions", "Editions to use as style corpus (numbers, source:id, or ids already in import/)", default,
                 parse=words)
    out = []
    for p in picked:
        p = str(p)
        if p.isdigit() and 1 <= int(p) <= len(found):
            out.append(found[int(p) - 1])
        elif ":" in p:
            src, sid = p.split(":", 1)
            hit = next((c for c in found if c["source"] == src and c["id"] == sid), None)
            out.append(hit or {"source": src, "id": sid, "title": sid, "cls": None, "licence": "", "books": 0})
        elif p in here:
            out.append({"existing": p})
        else:
            raise SystemExit(f"editions: {p!r} is neither a number from the list, a source:id nor an edition in import/")
    return out


def edition_id(c, iso):
    sid = re.sub(r"[^a-z0-9-]+", "-", c["id"].lower()).strip("-")
    base = sid if sid.startswith(iso) else f"{iso}-{sid}"
    name, n, have = base, 2, existing_ids()
    while name in have:
        name, n = f"{base}-{n}", n + 1
    return name


def nt_basis(text_dir):
    files = {}
    present = 0
    tested = 0
    for code, ch, v in TEST_VERSES:
        f = os.path.join(text_dir, f"{code}{ch:03d}.txt")
        if not os.path.exists(f):
            continue
        t = files.setdefault(f, open(f, encoding="utf-8").read())
        tested += 1
        m = re.search(rf"(?<![\w>.])v{v}(?=\s)(.*?)(?=(?<![\w>.])v\d+\s|\Z)", t, re.S)
        present += bool(m and len(m[1].strip()) > 3)
    if not tested:
        return None, "no NT test verses"
    basis = "critical" if present <= tested / 3 else "majority"
    return basis, f"{present} of {tested} test verses present (Mt 17:21, Acts 8:37 …)"


def quotes_of(text_dirs):
    n = collections.Counter()
    for d in text_dirs:
        for f in glob.glob(os.path.join(d, "*.txt"))[:400]:
            t = open(f, encoding="utf-8").read()
            for pair in QUOTE_PAIRS:
                n[pair] += min(t.count(pair[0]), t.count(pair[1]))
    n['""'] //= 2
    return n.most_common(1)[0][0] if n and n.most_common(1)[0][1] else "“”"


def import_edition(c, iso, lang_dir):
    """Write edition.yaml with the fetch recipe, fetch it, and fill in books and nt_basis. -> edition id."""
    if "existing" in c:
        say(f"  {c['existing']}: already in import/")
        return c["existing"]
    eid = edition_id(c, iso)
    cls = c["cls"]
    if cls is None:
        cls = ask(f"licence_folder.{c['source']}:{c['id']}", f"  {c['source']}:{c['id']}: licence folder "
                  f"(the licence reads: {c['licence'] or 'nothing'}; check it on the source)", "non-free", OPEN)
        checked = True
    else:
        checked = False
    rel = os.path.join("import", cls, lang_dir, eid)
    say(f"  {c['source']}:{c['id']} -> {rel}/")
    credit = f"{c['title']}, {c['licence']}" + (f" ({c['url']})" if c.get("url") else "")
    y = {
        "name": c["title"], "language": iso, "role": "style", "text_dir": "text",
        "format": "one file per chapter (<code>NNN.txt), the format of the BSB files, fetched by scripts/fetch_edition.py",
        "nt_basis": "critical", "books": [], "quarantine": [],
        "source": f"{c['source']} {c['id']}" + (f", {c['url']}" if c.get("url") else ""),
        "licence": c["licence"] or "unknown: check on the source", "attribution": credit if cls in ("CC-BY", "CC-BY-SA") else "",
        "credit": credit,
        "fetch": {"source": c["source"], "id": c["id"]},
    }
    path = os.path.join(ROOT, rel)
    head = (f"# Imported {datetime.date.today().isoformat()} by scripts/onboard.py from {c['source']} ({c['id']}).\n"
            "# The text is fetched (scripts/fetch_edition.py), never kept in git: text/ is git-ignored (.gitignore here),\n"
            "# in every licence folder. One edition = one existing translation.\n\n")
    if DRY:
        say(f"  would write {rel}/edition.yaml and fetch it")
        return eid
    os.makedirs(path, exist_ok=True)
    open(os.path.join(path, ".gitignore"), "w").write("# the text is fetched, not kept in git\ntext/\n.text.new/\n")
    open(os.path.join(path, "edition.yaml"), "w", encoding="utf-8").write(head + yaml.safe_dump(y, allow_unicode=True, sort_keys=False, width=110))
    try:
        FE.fetch_edition(eid, checked=checked)
    except SystemExit as e:
        say(f"  {e}")
        if "doesn't allow folder" in str(e) or "can't be read" in str(e):
            raise SystemExit(f"  stopped: fix the licence folder of {eid} (answer licence_folder), then run again")
        raise
    text = os.path.join(path, "text")
    codes = sorted({f[:3] for f in os.listdir(text) if f.endswith(".txt")}, key=lambda c: [b[0] for b in BOOKS].index(c))
    basis, why = nt_basis(text)
    y["books"] = codes
    if basis:
        y["nt_basis"] = basis
    note = f"# nt_basis read from the text by scripts/onboard.py: {why}. Check it (import-edition skill).\n"
    open(os.path.join(path, "edition.yaml"), "w", encoding="utf-8").write(head + note + yaml.safe_dump(y, allow_unicode=True, sort_keys=False, width=110))
    say(f"  {len(codes)} books; nt_basis {y['nt_basis']} ({why})")
    return eid


# ---------- step 4: the project ----------

def write_project(pdir, fields, books, overlap):
    lines = [
        "# Written by scripts/onboard.py; fields: docs/configuration.md. Everything in export/ is CC0 (export/README.md).",
        f"# Books planned at onboarding: {' '.join(books) or 'none yet'}",
        "",
        f"language: {fields['language']}",
        f"language_name: {fields['language_name']}",
        f"school_language: {fields['school_language']}      # the wiki, the store's notes and the analysis are in it",
        (f"familiarity: {fields['familiarity']}" if fields["familiarity"] else
         "# familiarity: known | partial | unknown   # set it from the probe: python3 scripts/probe_language.py <project>"),
        "",
        *([f"close_to: {fields['close_to']}               # the standard language the agents must not fall back on"]
          if fields.get("close_to") else []),
        "",
        "based_on: null",
        f"style_from: [{', '.join(fields['style_from'])}]",
        "",
        "# Books a non-free edition has are drafted in quarantine (scripts/quarantine.py writes this list).",
        "quarantine: []",
        f"do_not_open: [download/, scratch/, export/{fields['pname']}/_eval/local/]   # _eval/local/: the probes, local only",
        "",
        f"quotes: \"{fields['quotes']}\"                      # opening + closing quote marks (read from the corpus)",
        f"chapter_word: {fields['chapter_word']}",
        "# book_titles: {gen: …}   # titles for books the editions don't have; the others come from the edition",
        "",
        "rules:",
        "  - \"**Divine names:** (decide with the team: YHWH, Adonai YHWH, Elohim, El Shaddai)\"",
    ]
    if overlap:
        lines.insert(2, f"# The editions already have: {' '.join(overlap)} (docs/workflow.md: When an edition already has the book)")
    if DRY:
        say("  would write project.yaml:\n    " + "\n    ".join(lines))
        return
    os.makedirs(pdir, exist_ok=True)
    open(os.path.join(pdir, "project.yaml"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    if "--help" in ARGS or "-h" in ARGS:
        raise SystemExit(__doc__)
    if "--answers" in ARGS:
        ANSWERS.update(yaml.safe_load(open(ARGS[ARGS.index("--answers") + 1], encoding="utf-8")) or {})
    for k, v in list(ANSWERS.items()):          # licence_folder: {src:id: folder} -> licence_folder.src:id
        if isinstance(v, dict) and k == "licence_folder":
            ANSWERS.update({f"licence_folder.{a}": b for a, b in v.items()})

    say("== 1. AI work")
    route = pick_route()

    say("\n== 2. The language")
    iso = ask("language", "ISO 639-3 code of the language (e.g. kvg)",
              check=lambda v: None if v and re.fullmatch(r"[a-z]{3}", str(v)) else "three lower-case letters (ISO 639-3)")
    lang_dir = ask("dialect_id", "Interim id for a dialect, instead of the code (e.g. ch-de-be; empty for none)", None,
                   check=lambda v: None if not v else ID(v)) or iso
    found = []
    picked = pick_editions(iso, found)
    known = next((c["language_name"] for c in found if c.get("language_name")), None)
    say("")
    name = ask("language_name", "Name of the language", known or iso)
    school = ask("school_language", "The team's school language (the wiki and the notes are written in it)", "English")
    say("\n== 4. Import and fetch")
    eds = [import_edition(c, iso, lang_dir) for c in picked]
    if not eds:
        say("  no edition: the project starts without a style corpus (add one later with the import-edition skill)")

    say("\n== 5. The project")
    pid = ask("project", "Project id", f"{lang_dir}_BSB", check=ID)
    pdir = os.path.join(ROOT, "export", lang_dir, pid)
    pname = f"{lang_dir}/{pid}"
    if os.path.exists(os.path.join(pdir, "project.yaml")):
        raise SystemExit(f"export/{pname}/project.yaml exists already: the wizard doesn't overwrite a project")
    have = {}
    for e in eds:
        try:
            ed = P.edition(e)
            have[e] = set(ed.get("books") or []) | {os.path.basename(f)[:3] for f in glob.glob(os.path.join(ROOT, ed["dir"], ed.get("text_dir", "text"), "*.txt"))}
        except SystemExit:
            have[e] = set()
    all_have = set().union(*have.values()) if have else set()
    ot_missing = [b[0] for b in BOOKS if BY_CODE[b[0]][2] == "ot" and b[0] not in all_have]
    if all_have:
        say(f"  the editions have {len(all_have)} books: NT {sum(BY_CODE[c][2] == 'nt' for c in all_have)}, "
            f"OT {sum(BY_CODE[c][2] == 'ot' for c in all_have)} ({' '.join(c for c in sorted(all_have) if BY_CODE[c][2] == 'ot') or 'none'})")

    def bad_books(v):
        try:
            books_of(v)
        except SystemExit as e:
            return str(e)
    books = books_of(ask("books", "Books to draft (codes, ranges like gen-deu, 'ot')", ot_missing[:1] or ["gen"], parse=words,
                         check=bad_books))
    overlap = [b for b in books if b in all_have]
    dirs = []
    for e in eds:
        try:
            ed = P.edition(e)
            dirs.append(os.path.join(ROOT, ed["dir"], ed.get("text_dir", "text")))
        except SystemExit:
            pass
    fields = {"pname": pname, "language": iso, "language_name": name, "school_language": school, "familiarity": None, "close_to": None,
              "style_from": eds, "quotes": ask("quotes", "Quote marks", quotes_of(dirs)),
              "chapter_word": ask("chapter_word", "The word for 'chapter' in the language", "Chapter")}
    write_project(pdir, fields, books, overlap)
    say(f"  export/{pname}/project.yaml")
    for b in overlap:
        nonfree = [e for e in eds if b in have.get(e, ()) and P.edition(e)["licence_folder"] == "non-free"]
        if nonfree:
            say(f"  {b}: {', '.join(nonfree)} (non-free) has it: quarantine")
            run("scripts/quarantine.py", pname, b)
        else:
            say(f"  {b}: an open edition has it: the drafts continue or stand alongside it (docs/workflow.md)")

    say(f"\n== 6. How well does the model know {name}?")
    fam, slips = probe_step(pname, name, route, bool(eds))
    fields["familiarity"] = fam
    if fam == "partial":
        fields["close_to"] = ask("close_to", "Which standard language does it slip into (the agents must not fall back on it)?",
                                 "")
    elif fam == "unknown" and READS_WELL[0]:
        fields["close_to"] = ask("close_to", "It reads the language well: which related language does it know (empty: none)?",
                                 "") or None
    write_project(pdir, fields, books, overlap)

    say(f"\n== 7. Tools for '{fam}'")
    if not tools_step(pname, fam):
        raise SystemExit("stopped before the set-up; the project.yaml is written, run the wizard's later steps by hand "
                         "(docs/onboarding.md, step 4)")

    say("\n== 8. Sources, lexicons, memory")
    need_ot = any(BY_CODE[b][2] == "ot" for b in books)
    if ask("run_setup", "Fetch the missing sources now (scripts/setup.py)?", True):
        if not os.path.isdir(os.path.join(ROOT, "reference", "BSB")):
            run("scripts/setup.py")
        if need_ot and not os.path.isdir(os.path.join(ROOT, "orig", "heb")):
            try:
                import text_fabric  # noqa: F401
                run("scripts/setup.py", "--only", "none", "--heb", "bhsa,bcv-query")
            except ImportError:
                say("  text-fabric isn't installed: the open layout (bcv-query) becomes the drafting layout")
                run("scripts/setup.py", "--only", "none", "--heb", "bcv-query", "--drafting", "bcv-query")
    if not os.path.exists(os.path.join(ROOT, "orig", "heb.sqlite")) and ask(
            "run_src", "Fetch the prepared Hebrew and Greek structures now (scripts/setup.py --only src: bcv-query's "
            "published cache, about 60 MB; the clause packages and the occurrence index need them)?", True):
        run("scripts/setup.py", "--only", "src")
    if eds and ask("run_align", "Build the alignment lexicons now (scripts/align.py; a few minutes)?", True):
        corpus_ot = any(BY_CODE[c][2] == "ot" for c in all_have)
        run("scripts/align.py", pname, "--sides", "eng,grc" + (",hbo" if corpus_ot else ""))
        if fam == "unknown" and any(BY_CODE[c][2] == "nt" for c in all_have):
            # the occurrence index: how the NT renders any Hebrew word, through the LXX (the packages use it)
            if not os.path.exists(os.path.join(ROOT, "orig", "grc.sqlite")):
                run("scripts/setup.py", "--only", "src")
            run("scripts/lang.py", "build", pname)
            run("scripts/lang.py", "derive", pname)  # the derived products: the memory agent starts from them
    if ask("init_memory", "Create the empty store and wiki (memory_prompt.py --init)?", True) and not DRY:
        subprocess.run([sys.executable, "scripts/memory_prompt.py", pname, "--init"], cwd=ROOT, stdout=subprocess.DEVNULL)
        say(f"  export/{pname}/profile/ and wiki/")
        if slips:
            n = slips_to_store(pname, slips, school)
            say(f"  {n} of the probe's slips written to the store as forms to check (profile/observations.json)")
    if not DRY:
        run("scripts/quotes.py", pname, "--credits")
        run("scripts/status.py", pname)
        out = os.path.join(pdir, "_onboard_answers.yaml")
        open(out, "w", encoding="utf-8").write("# The answers of scripts/onboard.py (rerun: --answers this file)\n"
                                               + yaml.safe_dump(USED, allow_unicode=True, sort_keys=False))
    first = books[0] if books else "gen"
    est = usage.estimate(fam)
    per = f"about {est[0] // 1000}k tokens a chapter ({est[1]} chapters logged in this mode)" if est else "no chapters logged in this mode yet"
    memory = "the learn-language skill" if fam == "unknown" else "the memory agent"
    say(f"""
== Done: export/{pname} is ready (familiarity {fam}; books planned: {' '.join(books) or 'none'})

Next, in Claude Code in this folder (claude), ask in your own words:
  1. "Build the language memory for {pname}"            ({memory}; once, the largest single job)
  2. "Write the style guide for {pname} with me"        (with someone who knows the language)
  3. "Draft {BY_CODE[first][1]} 1 for {pname} as reference chapter"  (one agent; {per})
     -> review it with the team, settle its open questions
  4. "Draft the next chapters" (a wave of about ten, agents in parallel)
For the team to read the memory: python3 scripts/wiki.py view {pname}   Status: export/{pname}/STATUS.md""" + ("" if DRY else f"""
The answers are in export/{pname}/_onboard_answers.yaml."""))


# ---------- step 1: how the AI work runs ----------

def pick_route():
    routes = PL.route_available()
    inside = bool(os.environ.get("CLAUDECODE"))
    say(f"  Claude Code: {'running inside it' if inside else 'installed' if 'claude-code' in routes else 'not found'}.   "
        f"ANTHROPIC_API_KEY: {'set' if 'api' in routes else 'not set'}.")
    say("  The probes (step 6) send three short tests to a fresh model; drafting later runs in Claude Code.")
    if not routes:
        say("  Neither is available: the probes are skipped and you set the familiarity yourself. Drafting needs Claude Code\n"
            "  (https://claude.com/claude-code) on a subscription or with an API key.")
        return None
    say("    api          through your API key, billed per token (Anthropic Console, or a cloud provider): ~10k tokens\n"
        "    claude-code  through Claude Code (claude -p, no tools): your subscription's usage, or Claude Code's key")
    return ask("ai_route", "How should the probes run?", routes[0], choices=routes)


# ---------- step 6: the probes ----------

READS_WELL = [False]


def probe_step(pname, name, route, have_corpus):
    """-> (familiarity, slips). Runs the three probes when there is a corpus and a route; shows the scores, the
    model's slips and one verse beside the edition; the user accepts or overrides the suggestion."""
    fams = ["known", "partial", "unknown"]
    if "familiarity" in ANSWERS and ANSWERS["familiarity"]:
        return ask("familiarity", "Familiarity", ANSWERS["familiarity"], choices=fams), []
    if not have_corpus or not route or DRY:
        why = "no corpus to score against" if not have_corpus else "no model to run them" if not route else "dry run"
        say(f"  the probes are skipped ({why}); docs/onboarding.md explains the three familiarities")
        return ask("familiarity", "Familiarity (known: like Danish, partial: like Bern German, unknown: like Kuni)",
                   "unknown", choices=fams), []
    say("  Three short tests, each a fresh model with no tools (about a minute):\n"
        f"    write: 16 verses into {name}   read: 16 verses into English   tell apart: 24 pairs, which is the published one")
    res, fam, why, slips, tokens = PL.run(pname, route, ANSWERS.get("probe_model"), say=say)
    w, r, t = res["write"], res["read"], res["tell"]
    READS_WELL[0] = r["chrf"] - r["floor"] >= 30
    sl = t["by_kind"].get("slip", [0, 0])
    say(f"""
                   score   floor
    write          {w['chrf_by_verse']:5.1f}   {w['floor']:5.1f}    (chrF by verse against the edition)
    read           {r['chrf']:5.1f}   {r['floor']:5.1f}    (chrF by verse against the BSB)
    tell apart     {100 * t['right'] // max(t['n'], 1):4d}%     50%    (its own slips recognised: {sl[0]} of {sl[1]})
    tokens: {tokens['input_tokens'] + tokens['output_tokens']}""")
    if slips:
        say("  Its slips (its form -> the corpus form): " + "   ".join(f"{m} -> {c}" for c, m in slips[:8]))
    ex = PL.example(pname)
    if ex:
        say(f"  Example ({ex[0]})  model:   {ex[1][:110]}\n{' ' * (13 + len(ex[0]))}edition: {ex[2][:110]}")
    say(f"\n  Suggested: {fam}. {why[:1].upper() + why[1:]}.\n"
        "  A speaker's judgement of the example counts more than the scores.")
    return ask("familiarity", f"Accept '{fam}'?", fam, choices=fams), slips


def tools_step(pname, fam):
    """What the familiarity switches on (scripts/modes.py), with the cost per chapter where it is known; confirm."""
    import modes
    p = P.project(pname)
    m = modes.mode(p)
    f = modes.FEATURES[fam]
    on = lambda x: "on " if x else "off"
    say(f"  {on(True)}  alignment lexicons (English, Greek; Hebrew where the corpus has OT books)")
    say(f"  {on(True)}  verse pack '{f['pack']}'" + {"memory": ": the decisions that touch each verse",
                                                      "dialect": ": + lexicon renderings and the corpus's phrases",
                                                      "full": ": + similar verses and what still needs a search"}[f["pack"]])
    say(f"  {on(f['style_check'])}  style check against the human chapters")
    say(f"  {on(fam != 'known')}  forms checked against the corpus; the probe's slips seed the store")
    say(f"  {on(fam == 'unknown')}  held-out test book and the learn-language skill (a test chapter before drafting)")
    say(f"  {on(m['quotation_rule'])}  quotation rule and quarantine ({m['licence']} edition)")
    est = usage.estimate(fam)
    say("  Each chapter runs one fresh agent in Claude Code: " + (f"about {est[0] // 1000}k tokens a chapter so far in this mode "
        f"({est[1]} chapters logged)." if est else "no chapters logged in this mode yet (scripts/usage.py)."))
    return ask("go_ahead", "Go ahead?", True)


def slips_to_store(pname, slips, school):
    """The probe's slips as `feature` entries: the corpus form with its count, the model's form never in the corpus.
    Status observed, confidence medium: a person or the memory agent checks that the two are the same word."""
    import json
    P2 = PL.LT.Project(pname)
    vocab = PL.corpus_vocab(P2)
    f = os.path.join(P2.profile, "observations.json")
    d = json.load(open(f, encoding="utf-8"))
    have = {e["id"] for e in d.get("entries", [])}
    text = SLIP_TEXT.get(school, SLIP_TEXT["English"])
    n = 0
    for corpus_form, mine in slips:
        eid = "slip:" + re.sub(r"[^a-z0-9_.-]+", "-", PL.fold(corpus_form).lower()).strip("-")
        ref = next((r[0] for r in P2.corpus() if corpus_form in P2.tok.tokens(r[4])), None)
        if not ref or eid in have or vocab.get(mine):
            continue
        form = next((w for w in PL.clean(next(r[4] for r in P2.corpus() if r[0] == ref)).split()
                     if P2.tok.tokens(w) == [corpus_form]), corpus_form)
        d.setdefault("entries", []).append({
            "id": eid, "kind": "feature", "value": text[0].format(c=corpus_form, n=vocab.get(corpus_form, 0), m=mine),
            "evidence": [{"ref": ref, "form": form.strip(".,;:!?«»„“”\"'()"), "n": vocab.get(corpus_form, 0)}],
            "confidence": "medium", "method": "corpus-observed", "by": "script:probe_language", "date": datetime.date.today().isoformat(),
            "status": "observed", "words": [], "note": text[1]})
        have.add(eid)
        n += 1
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return n


SLIP_TEXT = {
    "English": ("The corpus writes »{c}« ({n}×), never »{m}«: the model's form in the write probe.",
                "From the probe (scripts/probe_language.py): check that the two are the same word."),
    "Standard German": ("Das Korpus schreibt »{c}« ({n}×), nie »{m}«: die Form des Modells in der Schreibprobe.",
                        "Aus der Probe (scripts/probe_language.py): prüfen, ob beide dasselbe Wort sind."),
    "Danish": ("Korpusset skriver »{c}« ({n}×), aldrig »{m}«: modellens form i skriveproben.",
               "Fra proben (scripts/probe_language.py): kontrollér at de to er samme ord."),
}


if __name__ == "__main__":
    main()
