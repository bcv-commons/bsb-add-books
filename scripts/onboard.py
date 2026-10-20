#!/usr/bin/env python3
"""Set up a new language project step by step: the wizard for a new team (docs/onboarding.md).

    python3 scripts/onboard.py                        # asks every question, with a default for each
    python3 scripts/onboard.py --answers FILE.yaml    # takes the answers it finds there, asks the rest
    python3 scripts/onboard.py --answers FILE.yaml --yes   # no questions: the file's answers, else the defaults
    python3 scripts/onboard.py ... --dry-run          # shows what it would write and fetch, changes nothing

The common case is a language that has an NT and no (or only part of the) OT, and a team that wants OT books.
The steps:

 1. the language: code, name, the team's school language;
 2. the existing editions of the language, from the bcv-commons/bibles catalogue and the sources behind it
    (helloAO, openbible, eBible, DBT with your key; scripts/fetch_edition.py): pick the ones to use as style corpus.
    A language only on DBT without a key: the wizard says so and waits for DBT_API_KEY in .env;
 3. each picked edition goes to import/<licence>/<language>/<edition>/ with a fetch recipe in edition.yaml and is
    downloaded. Its text is git-ignored in every licence folder, CC0 and CC BY included: what can be fetched from
    a URL is fetched again, not kept in git. The NT basis is read from the fetched text (test verses);
 4. the project: export/<language>/<project>/project.yaml; the books to draft, and a quarantine where a non-free
    edition has one of them (before the probes, so they don't use it);
 5. how the AI work runs: the API (ANTHROPIC_API_KEY in the environment or .env, billed per token) or Claude Code
    (claude -p, no tools);
 6. the probes (scripts/probe_language.py run): write, read, tell apart; the scores, the model's slips, one verse
    beside the edition, and a suggested familiarity the user accepts or overrides (close_to where it applies);
 7. the tools that familiarity switches on, with the tokens per chapter logged so far in that mode (scripts/usage.py);
 8. the sources (scripts/setup.py; for OT books the Hebrew layout and scripts/src.py's prepared structure), the
    alignment lexicons (scripts/align.py; for an unknown language also the NT occurrence index, scripts/lang.py), the
    empty memory (scripts/memory_prompt.py --init) with the probe's slips as its first entries;
 9. what comes next, asked for in Claude Code: the memory, the style guide, a reference chapter, the chapters.

An edition that isn't in any of these sources (copied in by hand, or synced from its own repository like Den
Frie Bibel) is imported with the import-edition skill; the wizard can still create the project on it
(answer `editions` with its id).

Answers (all optional; the wizard prints the file it used, so a run can be repeated):
    language: jam                  language_name: Jamaican Creole English   school_language: English
    dialect_id: null               # an interim id instead of the ISO code, for a variety without one
    editions: [dbt:JAMBSWN_ET]     # source:id from the list, or the id of an edition already in import/
    licence_folder: {dbt:JAMBSWN_ET: non-free}   # only where the licence can't be read; default non-free
    project: jam_BSB               books: [gen, exo]            familiarity: null (set by the probe)
    quotes: "“”"                   chapter_word: Chapter
    ai_route: api | claude-code    probe_model: claude-opus-5-5 (API route)   close_to: null   go_ahead: true
    run_setup: true                run_align: true              init_memory: true
"""
import collections, datetime, glob, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import yaml  # noqa: E402
from books import BOOKS, BY_CODE  # noqa: E402
import fetch_edition as FE  # noqa: E402
import project as P  # noqa: E402
from project import project_dir, project_rel  # noqa: E402
import probe_language as PL  # noqa: E402
import usage  # noqa: E402

OPEN = FE.OPEN
ARGS = sys.argv[1:]
DRY = "--dry-run" in ARGS
YES = "--yes" in ARGS
ANSWERS = {}
USED = {}
# --redo STEP[,STEP]: do these steps again although their result is there (probes, priors, lexicons, database, memory);
# --fresh: don't use the answers an earlier run saved in the project (_onboard_answers.yaml)
REDO = set(ARGS[ARGS.index("--redo") + 1].split(",")) if "--redo" in ARGS else set()
FRESH = "--fresh" in ARGS


def done(step, what):
    """A step whose result is already there: one line, and skip it (unless --redo names it)."""
    if step in REDO:
        say(f"  {what}: done before, done again (--redo {step})")
        return False
    say(f"  done: {what} (skipped; --redo {step} does it again)")
    return True


def save_answers(pdir):
    """The answers so far into the project, after every step, so a stopped run keeps them."""
    if DRY or not os.path.isdir(pdir):
        return
    with open(os.path.join(pdir, "_onboard_answers.yaml"), "w", encoding="utf-8") as w:
        w.write("# The answers of scripts/onboard.py; a new run uses them (--fresh: ask again)\n")
        yaml.safe_dump({**{k: v for k, v in ANSWERS.items() if k not in USED}, **USED}, w, allow_unicode=True, sort_keys=False)


def set_project_lines(pf, values):
    """Set top-level fields in an existing project.yaml (familiarity, close_to), keeping everything else as it is."""
    text = open(pf, encoding="utf-8").read()
    for k, v in values.items():
        if v is None:
            continue
        line = f"{k}: {v}"
        if re.search(rf"^{k}:.*$", text, re.M):
            text = re.sub(rf"^{k}:.*$", line, text, count=1, flags=re.M)
        elif re.search(rf"^# {k}:.*$", text, re.M):
            text = re.sub(rf"^# {k}:.*$", line, text, count=1, flags=re.M)
        else:
            text = re.sub(r"^(school_language:.*)$", rf"\1\n{line}", text, count=1, flags=re.M)
    open(pf, "w", encoding="utf-8").write(text)
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

def edition_text_complete(eid):
    """Whether an imported edition has its text (a text/ folder with chapter files; a stopped fetch leaves none)."""
    d = os.path.join(ROOT, FE.edition_dir(eid), "text")
    return os.path.isdir(d) and any(f.endswith(".txt") for f in os.listdir(d))


def imported_recipes(iso):
    """{(source, id): edition id} of this language's editions already in import/ that have a fetch recipe."""
    out = {}
    for f in glob.glob(os.path.join(ROOT, "import", "*", iso, "*", "edition.yaml")):
        r = (yaml.safe_load(open(f, encoding="utf-8")) or {}).get("fetch") or {}
        if r.get("source") and r.get("id"):
            out[(r["source"], r["id"])] = os.path.basename(os.path.dirname(f))
    return out


def language_editions(iso):
    """Edition ids already in import/ for this language (import/<licence>/<iso>/<edition>/)."""
    return sorted(os.path.basename(os.path.dirname(f)) for f in glob.glob(os.path.join(ROOT, "import", "*", iso, "*", "edition.yaml")))


SOURCE_NAME = {"helloao": "helloAO (bible.helloao.org)", "openbible": "openbible", "ebible": "eBible.org",
               "dbt": "the Digital Bible Platform, with your key"}
LICENCE_MEANS = {"CC0": "public domain", "CC-BY": "free to use with credit (CC BY)",
                 "CC-BY-SA": "free with credit, share-alike (CC BY-SA)",
                 "non-free": "not free: the text stays on this computer, quoted only in short pieces"}


def coverage(c):
    if c.get("coverage"):
        return c["coverage"]
    if "ot_books" in c:
        return " + ".join(x for x in ((f"OT {c['ot_books']} books" if c["ot_books"] else ""),
                                      (f"NT {c['nt_books']} books" if c["nt_books"] else "")) if x) or "no books"
    if c.get("books"):
        return f"{c['books']} books" + (" (NT)" if c.get("nt") and not c.get("ot") else "")
    return "New Testament" if c.get("nt") and not c.get("ot") else "books: read when fetched"


def existing_ids():
    base = os.path.join(ROOT, "import")
    return {os.path.basename(os.path.dirname(f)) for f in glob.glob(os.path.join(base, "*", "*", "*", "edition.yaml"))}


ISO_TABLE = "https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab"


def iso_names():
    """{code: reference name} from SIL's ISO 639-3 code table (downloaded once into download/_iso639/); {} offline."""
    try:
        raw = FE.get(ISO_TABLE, os.path.join(ROOT, "download", "_iso639", "iso-639-3.tab")).decode("utf-8")
    except Exception:
        return {}
    return {r[0]: r[6] for r in (l.split("\t") for l in raw.splitlines()[1:]) if len(r) > 6}


def pick_language():
    """-> (ISO 639-3 code, its reference name or None). A name typed instead of a code is looked up in the code table."""
    names = iso_names()
    say("  Which language will you translate Bible books into?\n"
        "  Either its ISO 639-3 code (three letters) or else just type its name (in English).")
    while True:
        v = str(ask("language", "Language") or "").strip()
        code = v.lower()
        if not v:
            say("  Type a code (three letters) or a name.")
            continue
        if re.fullmatch(r"[a-z]{3}", code) and (code in names or not names):
            say(f"  {code}: {names.get(code, '(no code table offline: the code is taken as given)')}")
            return code, names.get(code)
        hits = [(c, n) for c, n in names.items() if v and v.lower() in n.lower()] if len(v) >= 3 else []
        if "language" in ANSWERS or YES or not sys.stdin.isatty():
            raise SystemExit(f"language: {v!r} is not an ISO 639-3 code" + (f"; maybe {hits[0][0]} ({hits[0][1]})" if hits else ""))
        if re.fullmatch(r"[a-z]{3}", code) and not hits:
            say(f"  {code!r} is not an ISO 639-3 code; type the language's name to look it up")
        elif not hits:
            say(f"  no language name contains {v!r}; try another spelling or the code")
        else:
            say(f"  Languages whose name contains {v!r}" + (f" (the first 15 of {len(hits)})" if len(hits) > 15 else "") + ":")
            for c, n in sorted(hits, key=lambda x: (not x[1].lower().startswith(v.lower()), len(x[1])))[:15]:
                say(f"    {c}  {n}")
            say("  Type the code of the one you mean.")


def pick_editions(iso, listed, name=None):
    say(f"\n== 2. Bible translations in {name or iso}")
    say("  looking up what exists: the bcv-commons/bibles catalogue, helloAO, openbible, eBible, the Digital Bible "
        "Platform (about 10 seconds)")
    while True:
        try:
            found, catalog = FE.candidates(iso)
        except Exception as e:
            say(f"  the sources can't be reached ({e}); import editions by hand (import-edition skill)")
            found, catalog = [], []
        if not any(c["source"] == "dbt" and not c.get("id") for c in found) or "editions" in ANSWERS:
            break
        say(f"  {iso!r} is on the Digital Bible Platform (DBT), which needs your own API key (free at https://4.dbt.io).\n"
            "  Put a line DBT_API_KEY=... in .env in this folder (git-ignored; or set the environment variable).")
        unattended = YES or not sys.stdin.isatty()          # nobody to put the key in place: go on without DBT
        if str(ask("dbt_retry", "Press Enter when the key is in place to look again, or type 'skip' to go on without DBT",
                   "skip" if unattended else "")).strip().lower() == "skip":
            break
    listed.extend(found)
    have = imported_recipes(iso)
    for c in found:                       # the same text as an edition already imported: continue with that one
        if (c["source"], c.get("id")) in have:
            c["existing"] = have[(c["source"], c["id"])]
    usable = [c for c in found if c.get("id")]
    say(f"  Found {len(usable)}:" if usable else "  None found that the wizard can fetch.")
    for i, c in enumerate(found, 1):
        if not c.get("id"):
            continue
        say(f"  {i}. {c['title'][:90]}\n"
            f"     {coverage(c)}; from {SOURCE_NAME.get(c['source'], c['source'])}; "
            f"{LICENCE_MEANS.get(c['cls'], 'licence read when fetched')}" + (f"\n     {c['note']}" if c.get("note") else "")
            + (f"\n     already imported as {c['existing']}: {'its text is here' if edition_text_complete(c['existing']) else 'the fetch continues where it stopped'}"
               if c.get("existing") else ""))
    here = [e for e in language_editions(iso) if e not in {c.get("existing") for c in found}]
    if here:
        say(f"  Already imported for {iso}: {', '.join(here)}")
    if len(usable) != 1 or here:
        say("  m. Your own files" + (" instead or as well" if usable else "") +
            " (USFM or SFM, e.g. from Paratext): the wizard says where to put them")
    say("  (searched: the bcv-commons/bibles catalogue, helloAO, openbible, eBible"
        + (", the Digital Bible Platform" if FE.dbt_key() else "; the Digital Bible Platform needs your key") + ")")
    default = []
    if found:   # prefer an edition with an NT; among them the most open, then the most books
        usable = [c for c in found if c.get("id")] or found   # a DBT line without a key can't be fetched
        best = sorted(usable, key=lambda c: (not c.get("existing"), not c.get("nt"),          # already imported first
                                             OPEN.index(c["cls"]) if c["cls"] else 3, -(c["books"] or 0)))[0]
        default = [str(found.index(best) + 1)]
        for c in found:
            if c is not best and c.get("ot") and not best.get("ot"):
                say(f"  note: {c['source']}:{c['id']} has OT books too ({c['books']} books, {c['cls'] or '?'}); the sources often carry"
                    " the same translation: add it if it is another text, or for its OT books (they are then corpus,"
                    " and drafting them is the case 'an edition already has the book')")
        if len(usable) > 1:
            say("  The sources often carry the same translation: pick one per text.")
    if len(usable) == 1 and not here and "editions" not in ANSWERS:
        say(f"  The only one: the drafts learn {name or iso} from it. (Your own files can be added later: the import-edition skill.)")
        picked = [{"existing": usable[0]["existing"]}] if usable[0].get("existing") else default
    else:
        picked = ask("editions", "Which should the drafts learn the language from? (numbers, m for your own files; several possible)",
                     default, parse=words)
    out = []
    for p in picked:
        if isinstance(p, dict):           # chosen already (the only one, already imported)
            out.append(p)
            continue
        p = str(p)
        if p.isdigit() and 1 <= int(p) <= len(found):
            if not found[int(p) - 1].get("id"):
                say(f"  {p}: {found[int(p) - 1].get('note') or 'not fetchable'}; skipped")
                continue
            c = found[int(p) - 1]
            out.append({"existing": c["existing"]} if c.get("existing") else c)
        elif ":" in p:
            src, sid = p.split(":", 1)
            hit = next((c for c in found if c["source"] == src and c["id"] == sid), None)
            out.append(hit or {"source": src, "id": sid, "title": sid, "cls": None, "licence": "", "books": 0})
        elif p in here:
            out.append({"existing": p})
        elif p.lower() in ("m", "own", "manual"):
            out.append({"manual": True})
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
        eid = c["existing"]
        if edition_text_complete(eid):
            say(f"  {eid}: already in import/, with its text")
            return eid
        say(f"  {eid}: already in import/; fetching its text (continues from what was downloaded)")
        FE.fetch_edition(eid, checked=True)
        path = os.path.join(ROOT, FE.edition_dir(eid))
        y = yaml.safe_load(open(os.path.join(path, "edition.yaml"), encoding="utf-8"))
        text = os.path.join(path, "text")
        y["books"] = sorted({f[:3] for f in os.listdir(text) if f.endswith(".txt")}, key=lambda b: [x[0] for x in BOOKS].index(b))
        basis, why = nt_basis(text)
        if basis:
            y["nt_basis"] = basis
        raw = open(os.path.join(path, "edition.yaml"), encoding="utf-8").read()
        head = "".join(l for l in raw.splitlines(True) if l.startswith("#"))
        open(os.path.join(path, "edition.yaml"), "w", encoding="utf-8").write(head + "\n" + yaml.safe_dump(y, allow_unicode=True, sort_keys=False, width=110))
        say(f"  {len(y['books'])} books; nt_basis {y['nt_basis']} ({why})")
        return eid
    if c.get("manual"):
        return import_own_files(iso, lang_dir)
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
        "licence_source": "fetched",      # fetch_edition.py writes licence and credit from the source's copyright line
        "fetch": {"source": c["source"], "id": c["id"], **({"language": c["language"]} if c.get("language") else {})},
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
    y = yaml.safe_load(open(os.path.join(path, "edition.yaml"), encoding="utf-8"))   # with what the fetch wrote (licence)
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


def import_own_files(iso, lang_dir):
    """An edition from the user's own files (USFM or SFM, e.g. a Paratext project): the folder, its edition.yaml with the
    recipe `source: local`, the instructions, then the conversion when the files are in place. -> edition id."""
    say("  Your own files: one USFM or SFM file per book (.usfm, .sfm; from Paratext, a publisher, a team).")
    name = ask("own.name", "  The translation's name (e.g. its title)", f"{iso} translation")
    eid = edition_id({"id": re.sub(r"[^a-z0-9]+", "-", name.lower())}, iso)
    cls = ask("own.licence_folder", "  Its licence: CC0 (public domain), CC-BY, CC-BY-SA, or non-free (anything else, or unsure)",
              "non-free", OPEN)
    statement = ask("own.licence", "  The licence or permission, in a few words (as the publisher states it)",
                    "private use only" if cls == "non-free" else cls)
    rel = os.path.join("import", cls, lang_dir, eid)
    path = os.path.join(ROOT, rel)
    y = {"name": name, "language": iso, "role": "style", "text_dir": "text",
         "format": "one file per chapter (<code>NNN.txt), the format of the BSB files, converted by scripts/fetch_edition.py",
         "nt_basis": "critical", "books": [], "quarantine": [], "source": "the team's own files (source/)",
         "licence": statement, "attribution": f"{name}, {statement}" if cls in ("CC-BY", "CC-BY-SA") else "",
         "credit": f"{name}, {statement}", "fetch": {"source": "local", "id": "source"}}
    head = (f"# Imported {datetime.date.today().isoformat()} by scripts/onboard.py from the team's own files.\n"
            "# The files (source/) and the converted text (text/) stay out of git (.gitignore here).\n\n")
    if DRY:
        say(f"  would create {rel}/ and wait for the files in {rel}/source/")
        return eid
    os.makedirs(os.path.join(path, "source"), exist_ok=True)
    open(os.path.join(path, ".gitignore"), "w").write("# the team's files and the text made from them stay local\nsource/\ntext/\n.text.new/\n")
    open(os.path.join(path, "edition.yaml"), "w", encoding="utf-8").write(head + yaml.safe_dump(y, allow_unicode=True, sort_keys=False, width=110))
    while True:
        files = [f for f in os.listdir(os.path.join(path, "source")) if f.lower().endswith((".usfm", ".sfm"))]
        if files:
            break
        say(f"  Copy the files into {rel}/source/ (one per book, .usfm or .sfm).")
        if str(ask("own.ready", "  Press Enter when they are there, or type 'skip' to go on without them", "")).strip().lower() == "skip" \
                or "own.ready" in ANSWERS:
            say(f"  later: copy them there and run python3 scripts/fetch_edition.py {eid}")
            return eid
    say(f"  {len(files)} files found; converting")
    FE.fetch_edition(eid, checked=True)
    y = yaml.safe_load(open(os.path.join(path, "edition.yaml"), encoding="utf-8"))
    text = os.path.join(path, "text")
    y["books"] = sorted({f[:3] for f in os.listdir(text) if f.endswith(".txt")}, key=lambda c: [b[0] for b in BOOKS].index(c))
    basis, why = nt_basis(text)
    if basis:
        y["nt_basis"] = basis
    open(os.path.join(path, "edition.yaml"), "w", encoding="utf-8").write(head + yaml.safe_dump(y, allow_unicode=True, sort_keys=False, width=110))
    say(f"  {len(y['books'])} books; nt_basis {y['nt_basis']} ({why})")
    return eid


# ---------- step 4: the project ----------

def write_project(pdir, fields, books, overlap):
    lines = [
        "# Written by scripts/onboard.py; fields: docs/configuration.md. Everything in export/ is CC0 (export/README.md).",
        f"# Books planned at onboarding: {' '.join(books) or 'none yet'}"
        + (f"; first chapter: {fields['first_chapter']}" if fields.get("first_chapter") else ""),
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
        f"do_not_open: [download/, scratch/, {project_rel(fields['pname'])}/_eval/local/]   # _eval/local/: the probes, local only",
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

    say("== 1. The language")
    iso, iso_name = pick_language()
    def load_saved(d):
        f = os.path.join(ROOT, "export", d, ANSWERS.get("project") or f"{d}_BSB", "_onboard_answers.yaml")
        if os.path.exists(f) and not FRESH:
            prev = yaml.safe_load(open(f, encoding="utf-8")) or {}
            ANSWERS.update({k: v for k, v in prev.items() if k not in ANSWERS})
            say(f"  an earlier run's answers are used: {os.path.relpath(f, ROOT)} (--fresh asks again)")
            return True
    found_saved = load_saved(iso)                 # a re-run: the project by the language code, answers and all
    lang_dir = ask("dialect_id", "Dialect id (optional)", None,
                   check=lambda v: None if not v else ID(v)) or iso
    if lang_dir != iso and not found_saved:
        load_saved(lang_dir)
    found = []
    picked = pick_editions(iso, found, iso_name)
    known = next((c["language_name"] for c in found if c.get("language_name")), None)
    say("")
    name = ask("language_name", "Name of the language (as the project and the website show it)", known or iso_name or iso)
    school = ask("school_language", "The team's school language (the wiki and the notes are written in it)", "English")
    say("\n== 3. Import and fetch")
    eds = [import_edition(c, iso, lang_dir) for c in picked]
    if not eds:
        say("  no edition: the project starts without a style corpus (add one later with the import-edition skill)")

    say("\n== 4. The project")
    pid = ANSWERS.get("project") or f"{lang_dir}_BSB"     # always on the BSB: <language>_BSB
    pdir = os.path.join(ROOT, "export", lang_dir, pid)
    pname = f"{lang_dir}/{pid}"
    pf = os.path.join(pdir, "project.yaml")
    have = {}
    for e in eds:
        try:
            ed = P.edition(e)
            have[e] = set(ed.get("books") or []) | {os.path.basename(f)[:3] for f in glob.glob(os.path.join(ROOT, ed["dir"], ed.get("text_dir", "text"), "*.txt"))}
        except SystemExit:
            have[e] = set()
    all_have = set().union(*have.values()) if have else set()
    dirs = []
    for e in eds:
        try:
            ed = P.edition(e)
            dirs.append(os.path.join(ROOT, ed["dir"], ed.get("text_dir", "text")))
        except SystemExit:
            pass
    from books import chapters as n_chapters
    if os.path.exists(pf):            # never rewritten: later edits by the team or the agents stay
        old = yaml.safe_load(open(pf, encoding="utf-8")) or {}
        m = re.search(r"first chapter: (\w+) (\d+)", open(pf, encoding="utf-8").read())
        book, chapter = (m[1], int(m[2])) if m else ("gen", 1)
        say(f"  done: {project_rel(pname)}/project.yaml is there (first chapter {BY_CODE[book][1]} {chapter}); it is kept as it is")
        fields = {"pname": pname, "language": iso, "language_name": old.get("language_name") or name,
                  "school_language": old.get("school_language") or school, "familiarity": old.get("familiarity"),
                  "close_to": old.get("close_to"), "style_from": old.get("style_from") or eds, "quotes": old.get("quotes"),
                  "chapter_word": old.get("chapter_word"), "first_chapter": f"{book} {chapter}"}
        books, overlap = [book], []
    else:
        say(f"  {project_rel(pname)}/")
        ot_missing = [b[0] for b in BOOKS if BY_CODE[b[0]][2] == "ot" and b[0] not in all_have]
        if all_have:
            say(f"  the editions have {len(all_have)} books: NT {sum(BY_CODE[c][2] == 'nt' for c in all_have)}, "
                f"OT {sum(BY_CODE[c][2] == 'ot' for c in all_have)} ({' '.join(c for c in sorted(all_have) if BY_CODE[c][2] == 'ot') or 'none'})")
        say("  The first chapter to draft (more come later, chapter by chapter, in Claude Code):")
        book = str(ask("first_book", "Book (its code: gen, rut, jhn …)", (ot_missing[:1] or ["gen"])[0],
                       check=lambda v: None if str(v).lower() in BY_CODE else "a book code from books.tsv (gen, exo, rut, jhn …)")).lower()
        chapter = int(ask("first_chapter", "Chapter", 1, parse=lambda v: int(v) if str(v).isdigit() else v,
                          check=lambda v: None if isinstance(v, int) and 1 <= v <= n_chapters(book)
                          else f"1 to {n_chapters(book)} ({BY_CODE[book][1]})"))
        books = [book]
        overlap = [b for b in books if b in all_have]
        fields = {"pname": pname, "language": iso, "language_name": name, "school_language": school, "familiarity": None,
                  "close_to": None, "style_from": eds, "quotes": ANSWERS.get("quotes") or quotes_of(dirs),
                  "chapter_word": ANSWERS.get("chapter_word") or "Chapter", "first_chapter": f"{book} {chapter}"}
        say(f"  quote marks {fields['quotes']} (read from the text); the language memory can refine them and the word for 'chapter'")
        write_project(pdir, fields, books, overlap)
        say(f"  {project_rel(pname)}/project.yaml")
        for b in overlap:
            nonfree = [e for e in eds if b in have.get(e, ()) and P.edition(e)["licence_folder"] == "non-free"]
            if nonfree:
                say(f"  {b}: {', '.join(nonfree)} (non-free) has it: quarantine")
                run("scripts/quarantine.py", pname, b)
            else:
                say(f"  {b}: an open edition has it: the drafts continue or stand alongside it (docs/workflow.md)")
    save_answers(pdir)

    say("\n== 5. AI work")
    route = pick_route()
    save_answers(pdir)

    say(f"\n== 6. How well does the model know {name}?")
    probe = os.path.join(pdir, "_learn", "probe.json")
    slips = []
    if fields.get("familiarity") and os.path.exists(probe) and done(
            "probes", f"the probes ({probe_summary(probe)}); familiarity {fields['familiarity']}"):
        fam = fields["familiarity"]
    else:
        fam, slips = probe_step(pname, name, route, bool(eds))
        fields["familiarity"] = fam
        if fam == "partial" or (fam == "unknown" and READS_WELL[0]):
            fields["close_to"] = ANSWERS.get("close_to") or guess_close_to(name, iso, route, slips, fam)
        if not DRY:
            set_project_lines(pf, {"familiarity": fam, "close_to": fields.get("close_to")})
    priors = os.path.join(pdir, "profile", "priors.yaml")
    if fam in ("known", "partial") and route and ANSWERS.get("write_priors", True):
        if os.path.exists(priors) and done("priors", f"what the model believes about {name} (profile/priors.yaml)"):
            pass
        else:
            say(f"  the model writes down what it believes about {name}'s grammar (profile/priors.yaml, about 10k tokens);\n"
                "  the language study tests each item against the corpus, and the team can correct the file")
            run("scripts/priors.py", "write", pname, "--route", route, *(["--force"] if os.path.exists(priors) else []))
    save_answers(pdir)

    say(f"\n== 7. Tools for '{fam}'")
    if not tools_step(pname, fam):
        raise SystemExit("stopped before the set-up; the project.yaml is written, run the wizard's later steps by hand "
                         "(docs/onboarding.md, step 4)")
    save_answers(pdir)

    say("\n== 8. Sources, lexicons, memory")
    need_ot = any(BY_CODE[b][2] == "ot" for b in books)
    if ANSWERS.get("run_setup", True):
        say("  Fetching missing sources now")
        if os.path.isdir(os.path.join(ROOT, "reference", "BSB")):
            say("  - the BSB, MSB and the Greek NT: already here")
        else:
            say("  - the BSB, MSB and the Greek NT (a minute or two)")
            run("scripts/setup.py")
        if need_ot:
            if os.path.isdir(os.path.join(ROOT, "orig", "heb")):
                say("  - the Hebrew OT and its clause layouts: already here")
            else:
                say("  - the Hebrew OT and its clause layouts")
                try:
                    import text_fabric  # noqa: F401
                    run("scripts/setup.py", "--only", "none", "--heb", "bhsa,bcv-query")
                except ImportError:
                    say("    text-fabric isn't installed: the open layout (bcv-query) becomes the drafting layout")
                    run("scripts/setup.py", "--only", "none", "--heb", "bcv-query", "--drafting", "bcv-query")
        if os.path.exists(os.path.join(ROOT, "orig", "heb.sqlite")) and os.path.exists(os.path.join(ROOT, "orig", "grc.sqlite")):
            say("  - the prepared Hebrew and Greek structures: already here")
        else:
            say("  - the prepared Hebrew and Greek structures (bcv-query's published cache, about 60 MB)")
            run("scripts/setup.py", "--only", "src")
    learn = os.path.join(pdir, "_learn")
    text_time = max([os.path.getmtime(os.path.join(d, f)) for d in dirs if os.path.isdir(d) for f in os.listdir(d)] or [0])
    if eds and ANSWERS.get("run_align", True):
        corpus_ot = any(BY_CODE[c][2] == "ot" for c in all_have)
        lex = os.path.join(learn, "lexicon_eng.tsv")
        if os.path.exists(lex) and os.path.getmtime(lex) > text_time and done(
                "lexicons", "the alignment lexicons (newer than the edition's text)"):
            pass
        else:
            say(f"  Building the alignment lexicons now: {name} with the English"
                + (", the Greek and the Hebrew" if corpus_ot else " and the Greek") + " (a few minutes)")
            run("scripts/align.py", pname, "--sides", "eng,grc" + (",hbo" if corpus_ot else ""))
        if fam in ("partial", "unknown") and any(BY_CODE[c][2] == "nt" for c in all_have):
            db, links = os.path.join(learn, "lang.sqlite"), os.path.join(learn, "links_grc_pos.tsv")
            if os.path.exists(db) and os.path.exists(links) and os.path.getmtime(db) > os.path.getmtime(links) and done(
                    "database", "the language database and its statistics (newer than the lexicons)"):
                pass
            else:
                say("  Building the language database: every word of the NT linked to the Greek, and the statistics the "
                    "language study starts from")
                run("scripts/lang.py", "build", pname)
                run("scripts/lang.py", "derive", pname)
    if ANSWERS.get("init_memory", True) and not DRY:
        if os.path.isdir(os.path.join(pdir, "profile")) and os.path.isdir(os.path.join(pdir, "wiki")):
            say("  - the language memory (store and wiki): already here")
        else:
            say("  Creating the empty language memory (store and wiki)")
            subprocess.run([sys.executable, "scripts/memory_prompt.py", pname, "--init"], cwd=ROOT, stdout=subprocess.DEVNULL)
            say(f"  - {project_rel(pname)}/profile/ and wiki/")
        if slips:
            n = slips_to_store(pname, slips, school)
            say(f"  - {n} of the probe's slips written to the store as forms to check (profile/observations.json)")
    if not DRY:
        for script, args, what in (("scripts/quotes.py", ["--credits"], "quotations and credits"), ("scripts/status.py", [], "status")):
            r = subprocess.run([sys.executable, script, pname, *args], cwd=ROOT, capture_output=True, text=True)
            last = (r.stdout.strip().splitlines() or [""])[-1]
            say(f"  - {what}: {last}" if r.returncode == 0 else f"  - {what}: problem: {(r.stderr or r.stdout).strip()[-200:]}")
    save_answers(pdir)
    first, first_ch = (fields.get("first_chapter") or "gen 1").split()
    first_ch = int(first_ch)
    say(f"\n== 9. The language memory and the first chapter ({BY_CODE[first][1]} {first_ch})")
    built = memory_built(pdir)
    chapter_file = os.path.join(pdir, first, f"{first}{first_ch:03d}.txt")
    drafted = os.path.exists(chapter_file)
    if built and "memory" not in REDO:
        done("memory", "the language memory (the store has entries beyond the probe's slips)")
    if drafted and "chapter" not in REDO:
        done("chapter", f"{BY_CODE[first][1]} {first_ch} ({os.path.relpath(chapter_file, ROOT)})")
    todo = [x for x, d in (("the language memory", built and "memory" not in REDO),
                           (f"{BY_CODE[first][1]} {first_ch}", drafted and "chapter" not in REDO)) if not d]
    if todo and not DRY and eds and shutil_which("claude"):
        est = "about 40 minutes and 500k tokens" if len(todo) == 2 else "about 15-30 minutes and 200-350k tokens"
        go = ask("build_and_draft", f"Build {' and draft '.join(todo)} now? (agents in Claude Code, one after the other: {est})", True)
        guide = go and not (built and "memory" not in REDO) and ask(
            "style_guide", "Optional, in between: a style guide conversation in Claude Code with someone who knows the language? "
            "(you talk it through, then close Claude Code and the wizard goes on)", False)
        if go and not (built and "memory" not in REDO):
            built = build_memory(pname)
        if guide:
            say("  the style guide: Claude Code opens for the conversation; close it (/exit) to go on with the chapter")
            subprocess.run(["claude", f"Write the style guide for {pname} with me"], cwd=ROOT)
        if go and not (drafted and "chapter" not in REDO):
            drafted = draft_first_chapter(pname, first, first_ch)
    elif todo and DRY:
        say(f"  would ask: build {' and draft '.join(todo)} now? (one confirmation; then the agents, one after the other;"
            " a style guide conversation in between only if asked for)")
    elif todo and not shutil_which("claude"):
        say("  Claude Code is not installed: the memory and the first chapter are made in Claude Code (https://claude.com/claude-code)")
    say("\n== Done")
    if DRY:
        say(f"  would build the website's local preview and open {project_rel(pname)}'s pages in the browser")
        return
    say("  building the website's local preview (build/site/; a minute)")
    r = subprocess.run([sys.executable, "scripts/build_site.py", "--preview"], cwd=ROOT, capture_output=True, text=True)
    site = os.path.join(ROOT, "build", "site", lang_dir, pid)
    pages = ([os.path.join(site, "read", first, f"{first_ch:03d}.html")] if drafted else []) + [os.path.join(site, "next.html")]
    pages = [x for x in pages if os.path.exists(x)]
    if r.returncode or not pages:
        say(f"  the preview could not be built: {(r.stderr or r.stdout).strip()[-300:]}")
        say(f"  the project is in {project_rel(pname)}/")
        return
    import webbrowser
    for x in pages:
        webbrowser.open("file://" + x)
    say(f"  {'%s %d is drafted; ' % (BY_CODE[first][1], first_ch) if drafted else ''}opened in your browser: "
        + " and ".join(("the chapter" if "read" in x else "the next steps") for x in pages))
    say(f"  the pages: {os.path.relpath(pages[-1], ROOT)}; the project: {project_rel(pname)}/")
    say("  to see them again: python3 scripts/build_site.py --preview; to put them online (Netlify): docs/website.md")

def guess_close_to(name, iso, route, slips, fam):
    """The standard language a partly known language is drafted against (the agents must not fall back on it), or for an
    unknown language that the model reads well, the related language it knows: one short question to a fresh model on
    the probes' route, shown with the probe's slips as evidence; the language memory can correct it. None without a route."""
    if not route or DRY:
        say("  close_to: not set (no model to ask); the language memory can set it")
        return None
    q = (f"Which standard written language would someone writing {name} (ISO 639-3 {iso}) most likely drift into, using its "
         "words or spellings instead of the language's own? Answer with that language's English name only."
         if fam == "partial" else
         f"{name} (ISO 639-3 {iso}): which widely written language is it most closely related to? Answer with that "
         "language's English name only, or 'none'.")
    try:
        text, _ = PL.ask_model(q, route)
    except SystemExit as e:
        say(f"  close_to: not set ({e}); the language memory can set it")
        return None
    ans = re.sub(r"[^\w\s()'-]", "", (text or "").strip().splitlines()[0] if text else "").strip()
    if not ans or ans.lower() == "none":
        return None
    ev = ", ".join(f"{m} for {c}" for c, m in slips[:6])
    say(f"  close to: {ans} (asked the model" + (f"; its slips: {ev}" if ev else "") + "); the language memory can correct it")
    return ans


def probe_summary(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
        return (f"{d.get('suggested', {}).get('date', '')}: write {d['write'].get('chrf_by_verse', d['write'].get('chrf'))}, "
                f"read {d['read']['chrf']}, tell apart {d['tell']['right']}/{d['tell']['n']}")
    except Exception:
        return "results in _learn/probe.json"


def memory_built(pdir):
    """Whether the store holds more than the probe's slips (the memory agent has run)."""
    n = 0
    for part in ("observations", "decisions"):
        f = os.path.join(pdir, "profile", f"{part}.json")
        if os.path.exists(f):
            n += sum(1 for e in json.load(open(f, encoding="utf-8")).get("entries", []) if not str(e.get("id", "")).startswith("slip:"))
    return n > 0


def shutil_which(name):
    import shutil
    return shutil.which(name)


def run_agent(prompt, label):
    """One fresh agent in Claude Code without a chat (claude -p, the tools it needs), its actions shown as they happen,
    one short line each, and a heartbeat every minute of silence: how long since the last action, and what it is doing
    meanwhile (writing a file, how much so far; thinking). -> (finished, tokens, minutes, calls)."""
    import threading, time
    cmd = ["claude", "-p", "--permission-mode", "acceptEdits", "--allowedTools", "Read,Write,Edit,Glob,Grep,Bash",
           "--output-format", "stream-json", "--verbose", "--include-partial-messages"]
    say(f"  {label}: an agent in Claude Code is working (its actions below; Ctrl-C stops it, a re-run continues)")
    t0 = time.time()
    st = {"last": t0, "calls": 0, "tokens": 0, "ok": False, "tool": None, "chars": 0, "thinking": 0, "end": False}
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=ROOT, text=True)
    p.stdin.write(prompt)
    p.stdin.close()

    def heartbeat():
        while not st["end"]:
            time.sleep(60)
            quiet = time.time() - st["last"]
            if st["end"] or quiet < 55:
                continue
            doing = (f"writing with {st['tool']}: {st['chars'] // 1000}k characters so far" if st["tool"] and st["chars"]
                     else "thinking" if st["thinking"] else "waiting for the model")
            say(f"    … {time.strftime('%H:%M')}  still working: {int(quiet // 60)} min since the last action ({doing})")
    threading.Thread(target=heartbeat, daemon=True).start()
    for line in p.stdout:
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        kind = ev.get("type")
        if kind == "stream_event":                       # partial output: what is being generated right now
            e = ev.get("event") or {}
            if e.get("type") == "content_block_start":
                cb = e.get("content_block") or {}
                st["tool"] = cb.get("name") if cb.get("type") == "tool_use" else None
                st["chars"] = 0
            elif e.get("type") == "content_block_delta":
                d = e.get("delta") or {}
                if d.get("type") == "input_json_delta":
                    st["chars"] += len(d.get("partial_json") or "")
                elif d.get("type") == "thinking_delta":
                    st["thinking"] += 1
        elif kind == "assistant":
            for c in (ev.get("message") or {}).get("content", []):
                if c.get("type") == "tool_use":
                    st["calls"] += 1
                    st["last"], st["tool"], st["chars"], st["thinking"] = time.time(), None, 0, 0
                    inp = c.get("input") or {}
                    what = inp.get("command") or inp.get("file_path") or inp.get("pattern") or ""
                    what = re.sub(r"\s+", " ", str(what)).replace(ROOT + "/", "")
                    say(f"    {time.strftime('%H:%M')}  {c.get('name')}: {what[:100]}")
        elif kind == "result":
            u = ev.get("usage") or {}
            # the tokens the agent newly processed (input, output, written to the cache), as the usage log counts them;
            # its re-reads of the cached context (every turn, millions over a chapter, at a fraction of the price) aside
            st["tokens"] = sum(int(u.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens"))
            st["cache_read"] = int(u.get("cache_read_input_tokens") or 0)
            st["ok"] = not ev.get("is_error")
    p.wait()
    st["end"] = True
    minutes = (time.time() - t0) / 60
    ok = st["ok"] and p.returncode == 0
    say(f"  {label}: {'finished' if ok else 'stopped'} after {minutes:.0f} minutes, {st['calls']} actions, "
        f"about {st['tokens'] // 1000}k tokens" + (f" (+ {st['cache_read'] // 1000}k re-read from the cache)" if st.get("cache_read") else ""))
    return ok, st["tokens"], minutes, st["calls"]


def build_memory(pname):
    """The memory agent (scripts/memory_prompt.py): it reads the corpus and writes the store and the wiki."""
    prompt = subprocess.run([sys.executable, "scripts/memory_prompt.py", pname], cwd=ROOT, capture_output=True, text=True).stdout
    if not prompt.strip():
        say("  the memory prompt is empty (scripts/memory_prompt.py); build it later in Claude Code")
        return False
    ok, *_ = run_agent(prompt, "the language memory")
    subprocess.run([sys.executable, "scripts/check_project.py", pname], cwd=ROOT)
    return ok


def draft_first_chapter(pname, code, ch):
    """The first chapter: its pack and (OT) clause packages, the prompt, one fresh agent, then the checks, the notes'
    original text, the status and the usage log; the chapter's first verses on screen. -> True when it is drafted."""
    nnn = f"{ch:03d}"
    say(f"  preparing {BY_CODE[code][1]} {ch}: the verse pack" + ("" if BY_CODE[code][2] == "nt" else " and the clause packages"))
    run("scripts/verse_pack.py", pname, code, str(ch))
    if BY_CODE[code][2] != "nt":
        run("scripts/package.py", pname, code, str(ch))
    r = subprocess.run([sys.executable, "scripts/make_prompt.py", pname, code, str(ch)], cwd=ROOT, capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        say(f"  the chapter prompt could not be made: {(r.stderr or r.stdout).strip()[-300:]}")
        return False
    ok, tokens, minutes, calls = run_agent(r.stdout, f"{BY_CODE[code][1]} {ch}")
    draft = os.path.join(project_dir(pname), code, f"{code}{nnn}.txt")
    if not os.path.exists(draft):
        say(f"  no draft was written ({os.path.relpath(draft, ROOT)}); a re-run of the wizard tries again")
        return False
    if os.path.exists(draft[:-4] + "_notes.md"):
        run("scripts/notes_hebrew.py", pname, code, str(ch))
    run("scripts/check_draft.py", pname, code)
    if BY_CODE[code][2] != "nt":
        run("scripts/full_align.py", "check", pname, code, str(ch))
    run("scripts/status.py", pname)
    if tokens:
        run("scripts/usage.py", pname, "add", f"{code}{nnn}", "--tokens", str(tokens), "--calls", str(calls),
            "--minutes", f"{minutes:.1f}", "--note", "drafted by the onboarding wizard")
    import langtools as LT
    vs = LT.verses_of(draft)
    say(f"\n  {BY_CODE[code][1]} {ch} is drafted: {len(vs)} verses, {os.path.relpath(draft, ROOT)} (notes beside it)")
    for (c, v), t in list(vs.items())[:4]:
        say(f"    {v}  {t[:110]}")
    return True


# ---------- step 1: how the AI work runs ----------

def pick_route():
    routes = PL.route_available()
    inside = bool(os.environ.get("CLAUDECODE"))
    say(f"  Claude Code: {'running inside it' if inside else 'installed' if 'claude-code' in routes else 'not found'}.   "
        f"ANTHROPIC_API_KEY: {'set' if 'api' in routes else 'not set'}.")
    say("  The probes (next step) send three short tests to a fresh model; drafting later runs in Claude Code.")
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
        return ask("familiarity", "Familiarity (known: like Danish, partial: like Jamaican, unknown: the model doesn't know it)",
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


def accelerator():
    """What this machine can train a model on, without importing torch: ('cuda', name, GB), ('mps', chip, GB of unified
    memory) or ('cpu', processor, GB of memory). Machine facts are only shown, never written to the project (it is in git)."""
    import platform, shutil
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=20).stdout.strip().splitlines()
            if out:
                name, mem = [x.strip() for x in out[0].split(",")]
                return "cuda", name, round(int(mem) / 1024)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    mem = 0
    try:
        mem = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30)
    except (ValueError, OSError, AttributeError):
        pass
    if sys.platform == "darwin" and platform.machine() == "arm64":
        chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
        return "mps", chip or "Apple silicon", mem
    return "cpu", platform.processor() or platform.machine(), mem


def training_offer(fam):
    """The second-draft model (a fine-tuned NLLB-600M, for review triage: a second opinion,
    not a drafter): what this machine can do with it, a rented GPU where it can't, and the question. Offered in the
    unknown mode; in the partial mode it is still being tested; a known language doesn't need it. Returns the answer, or
    None when not offered."""
    kind, name, gb = accelerator()
    usable = (kind == "cuda" and gb >= 8) or (kind == "mps" and gb >= 32)
    if kind == "cuda" and gb >= 8:
        here = f"this machine's GPU ({name}, {gb} GB): one run of about 5-7 hours (measured on an 8 GB card)"
    elif kind == "cuda":
        here = f"this machine's GPU ({name}, {gb} GB) has less than the 8 GB a run needs"
    elif kind == "mps" and gb >= 32:
        here = (f"this Mac's GPU ({name}, {gb} GB shared memory): perhaps half a day to a day for one run (an estimate, "
                "not yet measured); the Mac is slow for other work meanwhile")
    elif kind == "mps":
        here = (f"this Mac ({name}, {gb} GB) has too little memory: training took about 20 GB on Apple's GPU (measured on a "
                "16 GB M1, which ran out), so about 32 GB is needed")
    else:
        here = f"no GPU ({name}); on the processor a run would take weeks (measured: about 4-5 minutes a step on an i7)"
    rent = ("your own GPU machine, or a cloud GPU by the hour (a 24 GB card at about $0.3-0.7 an hour: a few hours and a "
            "few dollars a run), through scripts/nllb/remote.py; the model then comes back here, where drafting runs on "
            "the processor")
    lines = [("Here: ", here + "."), ("Elsewhere (" + ("faster" if usable else "recommended") + "): ", rent + ".")]
    import textwrap
    show = lambda indent: [textwrap.fill(t, 118, initial_indent=indent + h, subsequent_indent=indent + "  ")
                           for h, t in lines]
    if fam == "known":
        say("  off  second-draft model: a known language doesn't need one (the agents' drafts are reviewed directly)")
        return None
    if fam == "partial":
        say("  off  second-draft model (fine-tuned NLLB, for review triage): still being tested for partly known languages.")
        say("\n".join(show("       ")))
        return None
    say("  Second-draft model (a fine-tuned NLLB, trained once on the corpus): it drafts every chapter a second time in")
    say("  minutes, and the verses where it and the agent's draft disagree are the ones a reviewer looks at first")
    say("  (scripts/triage.py). It is not a drafter: it translates the English, not the original, and makes meaning errors.")
    say("  Training it (scripts/nllb/: data.py, then train.py here or remote.py for another machine, then draft.py):")
    say("\n".join(show("    ")))
    return ask("second_draft", "Plan the second-draft model for this project?", True)


def tools_step(pname, fam):
    """What the familiarity switches on (scripts/modes.py), with the cost per chapter where it is known; confirm."""
    import modes
    if DRY and not os.path.exists(os.path.join(P.project_dir(pname), "project.yaml")):
        say(f"  (dry run: the project isn't written, so the tools for '{fam}' are listed in docs/onboarding.md)")
        return True
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
    sd = training_offer(fam)
    if sd is not None and not DRY:
        set_project_lines(os.path.join(P.project_dir(pname), "project.yaml"), {"second_draft": "nllb" if sd else "none"})
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
