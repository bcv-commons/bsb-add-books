#!/usr/bin/env python3
"""Build the public website from the repository: static pages, no server, nothing fetched at view time.

The site holds what git tracks in export/ and nothing else (docs/licensing.md: no edition texts, packs, style
reports, probe answers or anything in _eval/local/): for every project a home page (its STATUS.md, with the draft
statement), the language memory (the wiki viewer of scripts/wiki.py view) and the credits; and a page listing the
projects. Every page carries the project's draft statement. A file that git doesn't track is never read: the build
stops if a project's pages would need one.

This is the first version of the site; the planned app (internal planning notes) replaces the pages one by one and
keeps the same data rules.

Usage: python3 scripts/build_site.py [--out DIR] [--preview]   (default build/site/, git-ignored)
       --preview: also new files not yet committed, for a local look; never deployed
Deploy: scripts/deploy_site.py builds it and stages it on the `site` branch, which Netlify publishes.
"""
import glob, html as H, json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import wiki  # noqa: E402
import status  # noqa: E402
from project import project, edition, LICENCE_CLASS, project_dir, project_rel  # noqa: E402
project_edition = edition

UI = {   # interface strings by school language; the content stays as written
    "English": {"next_steps": "Next steps", "projects": "Projects", "status": "Status", "memory": "Language memory", "credits": "Credits",
                "chapters": "chapters", "draft": "draft", "review": "in review", "published": "published",
                "built": "Built from commit", "all": "All projects", "mode": "Model knowledge",
                "read": "Read", "language": "Language", "book": "Book", "chapter": "Chapter", "prev": "Previous", "next": "Next", "notes": "Notes", "tests": "Test drafts", "test": "Test draft", "test_banner": "An experiment with the drafting method, kept for comparison: not the project's draft of this chapter.", "reports": "Reports", "tests_intro": "Chapters drafted to test the method (held-out books, variants of the tools). They are separate from the project's drafts and are never published as its text.", "nodrafts": "no drafts yet", "choose": "Choose a language", "status_word": "Status",
                "v_verse": "Verse by verse", "n_verse": "Hebrew: Westminster Leningrad Codex (public domain), via MACULA Hebrew (CC BY 4.0, Clear Bible); Greek: Berean Greek Bible; English: Berean Standard Bible (both public domain). The comments are the drafting agent's notes.", "notes_more": "More from the notes", "v_std": "Text", "v_bhsa": "BHSA clauses", "v_hcl": "MACULA/UHB clauses", "v_none": "no clause layout for this chapter",
                "n_bhsa": "Clause layout: ETCBC, BHSA 2021, licensed CC BY-NC 4.0. This view of our draft on that layout is CC BY-NC 4.0 too: non-commercial use only, with credit to the ETCBC.",
                "n_hcl": "Clause layout: bcv-commons Hebrew clause layout v0.35 (MACULA Hebrew, UHB), CC BY-SA 4.0. This view of our draft on that layout is CC BY-SA 4.0."},
    "Standard German": {"next_steps": "Nächste Schritte", "projects": "Projekte", "status": "Stand", "memory": "Sprachgedächtnis", "credits": "Nachweise",
                        "chapters": "Kapitel", "draft": "Entwurf", "review": "in Prüfung", "published": "veröffentlicht",
                        "built": "Erstellt aus Commit", "all": "Alle Projekte", "mode": "Sprachkenntnis des Modells",
                "read": "Lesen", "language": "Sprache", "book": "Buch", "chapter": "Kapitel", "prev": "Zurück", "next": "Weiter", "notes": "Anmerkungen", "tests": "Testentwürfe", "test": "Testentwurf", "test_banner": "Ein Versuch mit der Arbeitsweise, zum Vergleich aufbewahrt: nicht der Entwurf des Projekts für dieses Kapitel.", "reports": "Berichte", "tests_intro": "Kapitel, die zum Prüfen der Arbeitsweise übersetzt wurden (zurückgehaltene Bücher, Varianten der Werkzeuge). Sie sind von den Entwürfen des Projekts getrennt und werden nie als sein Text veröffentlicht.", "nodrafts": "noch keine Entwürfe", "choose": "Sprache wählen", "status_word": "Stand",
                "v_verse": "Vers für Vers", "n_verse": "Hebräisch: Westminster Leningrad Codex (gemeinfrei), über MACULA Hebrew (CC BY 4.0, Clear Bible); Griechisch: Berean Greek Bible; Englisch: Berean Standard Bible (beide gemeinfrei). Die Kommentare sind die Notizen des Übersetzungsagenten.", "notes_more": "Weiteres aus den Notizen", "v_std": "Fliesstext", "v_bhsa": "BHSA-Sätze", "v_hcl": "MACULA/UHB-Sätze", "v_none": "für dieses Kapitel kein Satzlayout",
                "n_bhsa": "Satzlayout: ETCBC, BHSA 2021, Lizenz CC BY-NC 4.0. Diese Darstellung unseres Entwurfs auf diesem Layout steht ebenfalls unter CC BY-NC 4.0: nur nicht kommerzielle Nutzung, mit Nennung des ETCBC.",
                "n_hcl": "Satzlayout: bcv-commons Hebrew clause layout v0.35 (MACULA Hebrew, UHB), CC BY-SA 4.0. Diese Darstellung unseres Entwurfs auf diesem Layout steht unter CC BY-SA 4.0."},
    "Danish": {"next_steps": "Næste skridt", "projects": "Projekter", "status": "Status", "memory": "Sproghukommelse", "credits": "Kilder",
               "chapters": "kapitler", "draft": "udkast", "review": "til gennemsyn", "published": "udgivet",
               "built": "Bygget fra commit", "all": "Alle projekter", "mode": "Modellens kendskab",
                "read": "Læs", "language": "Sprog", "book": "Bog", "chapter": "Kapitel", "prev": "Forrige", "next": "Næste", "notes": "Noter", "tests": "Testudkast", "test": "Testudkast", "test_banner": "Et forsøg med arbejdsmetoden, gemt til sammenligning: ikke projektets udkast til dette kapitel.", "reports": "Rapporter", "tests_intro": "Kapitler oversat for at afprøve metoden (tilbageholdte bøger, varianter af værktøjerne). De er adskilt fra projektets udkast og udgives aldrig som dets tekst.", "nodrafts": "ingen udkast endnu", "choose": "Vælg sprog", "status_word": "Status",
                "v_verse": "Vers for vers", "n_verse": "Hebraisk: Westminster Leningrad Codex (fri af ophavsret), via MACULA Hebrew (CC BY 4.0, Clear Bible); græsk: Berean Greek Bible; engelsk: Berean Standard Bible (begge fri af ophavsret). Kommentarerne er oversætteragentens noter.", "notes_more": "Mere fra noterne", "v_std": "Løbende tekst", "v_bhsa": "BHSA-sætninger", "v_hcl": "MACULA/UHB-sætninger", "v_none": "intet sætningslayout for dette kapitel",
                "n_bhsa": "Sætningslayout: ETCBC, BHSA 2021, licens CC BY-NC 4.0. Denne visning af vores udkast på det layout er også CC BY-NC 4.0: kun ikke-kommerciel brug, med kreditering af ETCBC.",
                "n_hcl": "Sætningslayout: bcv-commons Hebrew clause layout v0.35 (MACULA Hebrew, UHB), CC BY-SA 4.0. Denne visning af vores udkast på det layout er CC BY-SA 4.0."},
}
FAMILIARITY = {"known": "known", "partial": "partial", "unknown": "unknown"}

CSS = """
:root { --bg:#fbfaf7; --panel:#ffffff; --ink:#1f2328; --muted:#646b73; --line:#e2ded6; --accent:#2f5d8a;
  --accent-soft:#e8eff6; --q:#fff4dc; --q-line:#d9a640; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#16181b; --panel:#1e2125; --ink:#e4e6e8;
  --muted:#9aa1a8; --line:#33373c; --accent:#8fb8e0; --accent-soft:#24303c; --q:#3a3120; --q-line:#c99a3a; } }
:root[data-theme="dark"] { --bg:#16181b; --panel:#1e2125; --ink:#e4e6e8; --muted:#9aa1a8; --line:#33373c;
  --accent:#8fb8e0; --accent-soft:#24303c; --q:#3a3120; --q-line:#c99a3a; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif; }
header { background:var(--panel); border-bottom:1px solid var(--line); padding:10px 16px; display:flex; flex-wrap:wrap;
  gap:6px 18px; align-items:baseline; }
header .site { font-weight:600; color:var(--ink); text-decoration:none; }
header nav { display:flex; flex-wrap:wrap; gap:4px; }
header nav a { padding:4px 10px; border:1px solid var(--line); border-radius:6px; color:var(--ink); text-decoration:none; font-size:14px; }
header nav a.on { background:var(--accent-soft); border-color:var(--accent); color:var(--accent); }
main { max-width:960px; margin:0 auto; padding:18px 16px 40px; }
h1 { font-size:24px; margin:8px 0 12px; } h2 { font-size:19px; margin:26px 0 8px; }
a { color:var(--accent); }
.banner { background:var(--q); border-left:4px solid var(--q-line); padding:10px 14px; border-radius:4px; margin:12px 0 18px; }
table { border-collapse:collapse; width:100%; display:block; overflow-x:auto; font-size:15px; }
th, td { border-bottom:1px solid var(--line); padding:6px 10px; text-align:left; vertical-align:top; }
th { color:var(--muted); font-weight:600; }
blockquote { margin:12px 0; padding:8px 14px; background:var(--q); border-left:4px solid var(--q-line); border-radius:4px; }
.cards { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:14px; padding:0; list-style:none; }
.cards li { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px 16px; }
.cards h2 { margin:0 0 4px; font-size:18px; } .cards h2 a { text-decoration:none; }
.muted { color:var(--muted); font-size:14px; }
footer { max-width:960px; margin:0 auto; padding:0 16px 30px; color:var(--muted); font-size:13px; }
code { font-size:90%; } .path { font-family:ui-monospace,monospace; font-size:90%; }
.pick { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:4px 0 14px; }
.pick select { font:inherit; font-size:15px; padding:5px 8px; border:1px solid var(--line); border-radius:6px; background:var(--panel); color:var(--ink); max-width:100%; }
.text { font-size:18px; line-height:1.7; max-width:42em; }
.text h2 { font-size:17px; margin:22px 0 6px; color:var(--muted); }
.text sup.v { font-size:11px; color:var(--muted); font-weight:600; margin:0 2px 0 4px; }
.text sup.n a, .notes .k { font-size:11px; text-decoration:none; color:var(--accent); font-weight:600; }
.notes { font-size:14px; color:var(--muted); border-top:1px solid var(--line); margin-top:26px; padding-top:8px; max-width:42em; }
.notes p { margin:4px 0; } .notes .k { margin-right:6px; }
.modes { display:flex; flex-wrap:wrap; gap:4px; margin:0 0 12px; }
.modes button { font:inherit; font-size:14px; padding:4px 12px; border:1px solid var(--line); border-radius:6px; background:transparent; color:var(--ink); cursor:pointer; }
.modes button.on { background:var(--accent-soft); border-color:var(--accent); color:var(--accent); }
.modes button:disabled { opacity:.45; cursor:default; }
.view[hidden] { display:none; }
.banner .tm { background:var(--q-line); color:#1f2328; font-weight:700; padding:1px 8px; border-radius:4px; text-transform:uppercase; font-size:13px; letter-spacing:.04em; }
.vv { border-bottom:1px solid var(--line); padding:10px 0; }
.vv-t { font-size:17px; }
.vv-o { font-family:'SBL Hebrew','Ezra SIL','Times New Roman',serif; font-size:19px; color:var(--muted); margin:4px 0; }
.vv-e, .vv-c { font-size:14px; margin:3px 0; }
.vv-c { border-left:3px solid var(--accent-soft); padding-left:8px; }
.vv-more { margin-top:24px; }
.step { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px 16px; margin:12px 0; }
.step h3 { margin:0 0 6px; font-size:17px; }
.step.done { border-left:4px solid #4a9a5b; } .step.todo { border-left:4px solid var(--accent); }
.say { display:flex; gap:8px; align-items:center; background:var(--bg); border:1px solid var(--line); border-radius:6px;
  padding:6px 10px; margin:8px 0; font-family:ui-monospace,Menlo,monospace; font-size:14px; }
.say code { flex:1; } .say button { font-size:13px; padding:3px 10px; border:1px solid var(--line); border-radius:5px;
  background:var(--panel); color:var(--ink); cursor:pointer; }
.lic { background:var(--q); border:2px solid var(--q-line); border-radius:6px; padding:10px 14px; margin:0 0 14px; font-size:14px; font-weight:600; }
.cls .l { padding-left:min(calc(var(--lv) * 1.6em), calc(var(--lv) * 3.5vw)); text-indent:-0.6em; margin:0 0 2px 0.6em; }
.cls h2 { font-size:17px; margin:22px 0 6px; color:var(--muted); }
.pager { display:flex; justify-content:space-between; gap:12px; margin:26px 0 0; max-width:42em; }
.books { list-style:none; padding:0; } .books li { margin:10px 0; }
.books .chs { display:flex; flex-wrap:wrap; gap:6px; margin-top:4px; }
.books .chs a { min-width:2.4em; text-align:center; padding:3px 6px; border:1px solid var(--line); border-radius:6px; text-decoration:none; background:var(--panel); }
"""


def git_tracked(preview=False):
    """The files the site may read: tracked ones; with --preview also untracked, not ignored ones (a local look at
    uncommitted work, never deployed: scripts/deploy_site.py builds without it from a clean tree)."""
    out = subprocess.run(["git", "ls-files", "-z", "export"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    files = {f for f in out.split("\0") if f}
    if preview:
        new = subprocess.run(["git", "ls-files", "-z", "--others", "--exclude-standard", "export"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        files |= {f for f in new.split("\0") if f}
    return files


def page(title, body, nav, banner, built, depth, ui, lang="en"):
    up = "../" * depth
    links = "".join(f'<a href="{up}{href}"{" class=on" if on else ""}>{H.escape(label)}</a>' for label, href, on in nav)
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{H.escape(title)}</title><link rel="stylesheet" href="{up}style.css"></head>
<body><header><a class="site" href="{up}index.html">bsb-add-books</a><nav>{links}</nav></header>
<main>{f'<div class="banner">{banner}</div>' if banner else ''}{body}</main>
<footer>{H.escape(ui['built'])} <code>{H.escape(built)}</code> · bcv-commons/bsb-add-books · CC0</footer></body></html>
"""


def lang_code(school):
    return {"Standard German": "de", "Danish": "da"}.get(school, "en")


def need(tracked, path):
    rel = os.path.relpath(path, ROOT)
    if rel not in tracked:
        raise SystemExit(f"{rel} is not tracked by git: the site shows only tracked files (commit it, or leave it out)")
    return path


def build(out, built, preview=False):
    tracked = git_tracked(preview)
    projects = sorted(os.path.dirname(f)[len("export/"):] for f in tracked
                      if re.fullmatch(r"export/[^_/][^/]*/[^/]+/project\.yaml", f))
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    open(os.path.join(out, "style.css"), "w", encoding="utf-8").write(CSS.strip() + "\n")
    cards, readers = [], {}
    for pname in projects:
        pdir = project_dir(pname)
        p = project(pname)
        if p.get("site") is False:
            continue
        school = p.get("school_language") or "English"
        ui = UI.get(school, UI["English"])
        lc = lang_code(school)
        draft_st, _ = status.statements(p)
        rows = status.state(pdir, p)
        n = {s: sum(1 for _, _, r in rows if r["status"] == s) for s in ("draft", "in-review", "published")}
        name = p.get("language_name") or pname
        od = os.path.join(out, pname)
        os.makedirs(od)
        has_drafts = any(os.path.relpath(f, ROOT) in tracked for _, f, _ in rows)
        has_tests = bool(test_drafts(pname, tracked))
        nav = lambda on: [(ui["read"], f"{pname}/read/index.html", on == "r")] * has_drafts + [
                          (ui["tests"], f"{pname}/tests/index.html", on == "t")] * has_tests + [
                          (ui["status"], f"{pname}/index.html", on == "s"), (ui["memory"], f"{pname}/memory.html", on == "m"),
                          (ui["credits"], f"{pname}/credits.html", on == "c"), (ui["next_steps"], f"{pname}/next.html", on == "n"),
                          (ui["all"], "index.html", False)]
        first = re.match(r"([^\s.]+)\.\s*", draft_st)       # the statement's first word ("Draft.", "Udkast.")
        rest = draft_st[first.end():] if first and first[1].lower() in ("draft", ui["draft"].lower()) else draft_st
        banner = f"<strong>{H.escape(ui['draft'].capitalize())}.</strong> {H.escape(rest)}"
        # home: STATUS.md as committed; stop if it no longer matches status.yaml and the drafts (the build changes no
        # tracked file: regenerate it with scripts/status.py and commit)
        sf = need(tracked, os.path.join(pdir, "STATUS.md"))
        before = open(sf, encoding="utf-8").read()
        status.write_status_md(pname, pdir, p)
        after = open(sf, encoding="utf-8").read()
        if after != before:
            open(sf, "w", encoding="utf-8").write(before)
            raise SystemExit(f"{project_rel(pname)}/STATUS.md is out of date: run python3 scripts/status.py {pname} and commit it")
        md = wiki.read_page(sf)[1]
        md = re.sub(r"^> \*\*(Drafts?\.)\*\*.*\n?", "", md, flags=re.M)        # the banner is shown above instead
        md = re.sub(r"^> \*\*Draft\.\*\*.*\n?", "", md, flags=re.M)
        fam = p.get("familiarity")
        probe = os.path.join(pdir, "_learn", "probe.json")
        about = ""
        if fam:
            about = f'<p class="muted">{H.escape(ui["mode"])}: <strong>{H.escape(fam)}</strong>'
            if os.path.relpath(probe, ROOT) in tracked:
                d = json.load(open(probe, encoding="utf-8"))
                w, r = d.get("write", {}), d.get("read", {})
                if w and r:
                    about += f" (write {w.get('chrf_by_verse', w.get('chrf'))}, read {r.get('chrf')})"
            about += "</p>"
        body = wiki.md_html(md, "STATUS.md") + about
        open(os.path.join(od, "index.html"), "w", encoding="utf-8").write(page(f"{name}: {ui['status']}", body, nav("s"), banner, built, pname.count("/") + 1, ui, lc))
        # credits
        cf = os.path.join(pdir, "CREDITS.md")
        cbody = wiki.md_html(wiki.read_page(need(tracked, cf))[1], "CREDITS.md") if os.path.exists(cf) else "<p>—</p>"
        open(os.path.join(od, "credits.html"), "w", encoding="utf-8").write(page(f"{name}: {ui['credits']}", cbody, nav("c"), banner, built, pname.count("/") + 1, ui, lc))
        # memory: the wiki viewer, with a bar back to the site and the draft statement
        if os.path.isdir(os.path.join(pdir, "wiki")):
            for f in os.listdir(os.path.join(pdir, "wiki")):
                if f.endswith(".md"):
                    need(tracked, os.path.join(pdir, "wiki", f))
            mem = os.path.join(od, "memory.html")
            wiki.view(pname, mem)
            h = open(mem, encoding="utf-8").read()
            up = "../" * (pname.count("/") + 1)
            bar = (f'<div style="background:var(--q);border-bottom:1px solid var(--q-line);padding:6px 16px;font-size:14px">'
                   f'<a href="{up}{pname}/index.html">{H.escape(name)}</a> · {banner}</div>')
            h = h.replace("<body>", "<body>" + bar, 1).replace('<html lang="en">', f'<html lang="{lc}">', 1)
            open(mem, "w", encoding="utf-8").write(h)
        rd = reader(pname, p, tracked, od, ui, banner, built, nav, lc, rows)
        next_steps(pname, p, tracked, od, ui, banner, built, nav, lc, rows, preview)
        if has_tests:
            tests(pname, p, tracked, od, ui, banner, built, nav, lc)
        if rd:
            readers[pname] = rd
        counts = ", ".join(f"{n[k]} {ui[l]}" for k, l in (("draft", "draft"), ("in-review", "review"), ("published", "published")) if n[k])
        lic = sorted({LICENCE_CLASS.get(edition(e)["licence_folder"], "non-free") for e in p.get("style_from") or []})
        cards.append(f'<li><h2><a href="{pname}/index.html">{H.escape(name)}</a></h2>'
                     f'<div class="muted">{len(rows)} {H.escape(ui["chapters"])}: {H.escape(counts or "—")}</div>'
                     f'<div class="muted">{H.escape(fam or "")}{" · " if fam else ""}{H.escape(", ".join(lic))} · '
                     f'<a href="{pname}/memory.html">{H.escape(ui["memory"])}</a>'
                     + (f' · <a href="{pname}/read/index.html">{H.escape(ui["read"])}</a>' if rd else f' · {H.escape(ui["nodrafts"])}')
                     + '</div></li>')
    open(os.path.join(out, "nav.js"), "w", encoding="utf-8").write("window.NAV = " + json.dumps(readers, ensure_ascii=False) + ";\n" + NAV_JS)
    en = UI["English"]
    langs = "".join(f'<li><a href="{p_}/read/index.html">{H.escape(r_["name"])}</a> <span class="muted">'
                    f'({sum(len(b[2]) for b in r_["books"])} {H.escape(en["chapters"])})</span></li>' for p_, r_ in readers.items())
    open(os.path.join(out, "read.html"), "w", encoding="utf-8").write(page("bsb-add-books: read", f"<h1>{en['choose']}</h1><ul class=books>{langs}</ul>",
        [(en["read"], "read.html", True), (en["projects"], "index.html", False)], "", built, 0, en))
    intro = ("<p>Bible translations drafted chapter by chapter from the Hebrew and Greek, with the Berean Standard Bible as "
             "the only assisting translation. Everything here is a <strong>draft</strong> until a language team publishes it; "
             "each chapter's status is on its project page.</p>")
    body = f"<h1>{en['projects']}</h1>{intro}<ul class=cards>{''.join(cards)}</ul>"
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(page("bsb-add-books: draft translations", body,
        [(en["read"], "read.html", False), (en["projects"], "index.html", True)], "", built, 0, en))
    open(os.path.join(out, "BUILT_FROM"), "w").write(built + "\n")
    open(os.path.join(out, "netlify.toml"), "w").write(NETLIFY)
    leak_test(out)
    print(f"{os.path.relpath(out, ROOT)}/: {len(cards)} projects, built from {built}")


def test_drafts(pname, tracked):
    """Test drafts: tracked chapter files under export/<project>/_eval/<…>-test/ (never _eval/local/), by folder."""
    pre = f"{project_rel(pname)}/_eval/"
    out = {}
    for f in sorted(tracked):
        m = re.fullmatch(re.escape(pre) + r"((?:[^/]+/)*[^/]*-test(?:/[^/]+)*)/([0-9a-z]{3})(\d{3})\.txt", f)
        if m and not m[1].startswith("local"):
            out.setdefault(m[1], []).append((m[2], int(m[3]), f))
    return out


def tests(pname, p, tracked, od, ui, banner, built, nav, lc):
    """The project's test drafts, apart from its drafts: an index (folders, chapters, the reports in _eval/) and one
    page per test chapter, each under a test banner. They are not in the reader's selectors (nav.js)."""
    from books import BY_CODE
    depth = pname.count("/") + 1
    td = os.path.join(od, "tests")
    os.makedirs(td, exist_ok=True)
    tb = f'<span class="tm">{H.escape(ui["test"])}</span> {H.escape(ui["test_banner"])} ' + banner
    pre = f"{project_rel(pname)}/_eval/"
    reports = sorted(f for f in tracked if re.fullmatch(re.escape(pre) + r"[^/]+\.md", f))
    items = []
    for folder, chs in test_drafts(pname, tracked).items():
        links = []
        for code, n, f in sorted(chs, key=lambda x: (list(BY_CODE).index(x[0]), x[1])):
            title, blocks, notes = parse_chapter(p, open(os.path.join(ROOT, f), encoding="utf-8").read(), "")
            name = book_title(p, code, title)
            slug = folder.replace("/", "_") + f"_{code}{n:03d}"
            text = "".join(f"<h2>{h}</h2>" if k == "h" else f"<p>{h}</p>" for k, h in blocks)
            nt = "".join(f'<p id="n{j}"><a class="k" href="#r{j}">{j}</a>{h}</p>' for j, h in enumerate(notes, 1))
            nf = f[:-4] + "_notes.md"
            extra = ""
            if nf in tracked:
                vv = verse_view(p, code, n, os.path.join(ROOT, f), open(os.path.join(ROOT, nf), encoding="utf-8").read(), ui)
                extra += f'<details class="notes"><summary><strong>{H.escape(ui["v_verse"])}</strong> ({H.escape(os.path.basename(nf))})</summary>' \
                         + (vv or wiki.md_html(wiki.read_page(os.path.join(ROOT, nf))[1], os.path.basename(nf))) + "</details>"
            rf = f"{pre}{code}{n:03d}_report.md"
            if rf in tracked:
                extra += f'<p><a href="{os.path.basename(rf)[:-3]}.html">{H.escape(ui["reports"])}: {H.escape(os.path.basename(rf))}</a></p>'
            body = (f'<p class="muted"><a href="index.html">{H.escape(ui["tests"])}</a> · {H.escape(folder)}</p>'
                    f'<h1>{H.escape(name)} {n} <span class="muted">({H.escape(ui["test"].lower())}, {H.escape(folder)})</span></h1>'
                    f'<div class="text">{text}</div>'
                    + (f'<div class="notes"><strong>{H.escape(ui["notes"])}</strong>{nt}</div>' if notes else "") + extra)
            open(os.path.join(td, slug + ".html"), "w", encoding="utf-8").write(
                page(f"{name} {n} ({ui['test'].lower()}) · {p.get('language_name')}", body, nav("t"), tb, built, depth + 1, ui, lc))
            links.append(f'<a href="{slug}.html">{H.escape(name)} {n}</a>')
        items.append(f'<li><strong>{H.escape(folder)}</strong><div class="chs">{"".join(links)}</div></li>')
    reps = []
    for f in reports:
        b = os.path.basename(f)[:-3]
        open(os.path.join(td, b + ".html"), "w", encoding="utf-8").write(page(
            f"{b} · {p.get('language_name')}", f'<p class="muted"><a href="index.html">{H.escape(ui["tests"])}</a></p>'
            + wiki.md_html(wiki.read_page(os.path.join(ROOT, f))[1], b + ".md"), nav("t"), tb, built, depth + 1, ui, lc))
        reps.append(f'<li><a href="{b}.html">{H.escape(b)}</a></li>')
    body = (f'<h1>{H.escape(p.get("language_name") or pname)}: {H.escape(ui["tests"])}</h1>'
            f'<div class="lic">{H.escape(ui["tests_intro"])}</div><ul class="books">{"".join(items)}</ul>'
            + (f'<h2>{H.escape(ui["reports"])}</h2><ul>{"".join(reps)}</ul>' if reps else ""))
    open(os.path.join(td, "index.html"), "w", encoding="utf-8").write(
        page(f"{p.get('language_name')}: {ui['tests']}", body, nav("t"), tb, built, depth + 1, ui, lc))


def open_questions(notes_md, limit=6):
    """The list items under a notes heading about open questions (Open questions, Offene Fragen, Åbne spørgsmål …)."""
    out, on = [], False
    for l in notes_md.splitlines():
        if re.match(r"^#{1,6} ", l):
            on = bool(re.search(r"open|question|offen|frage|åbne|spørgsm|least sure", l, re.I))
            continue
        m = re.match(r"^\s*(?:[-*]|\d+\.)\s+(.*)", l)
        if on and m:
            if len(out) >= limit:
                break
            out.append(m[1].strip())
        elif on and out and l.strip() and re.match(r"^\s+\S", l):      # an item wrapped over several lines
            out[-1] += " " + l.strip()
    return out


def next_steps(pname, p, tracked, od, ui, banner, built, nav, lc, rows, preview):
    """The project's 'next steps' page: what is done (editions, language memory, chapters) and what comes next, each
    with the sentence to give Claude Code and a copy button, and how the website is published. The wizard opens it."""
    import json as J
    from books import BY_CODE
    import modes
    name = p.get("language_name") or pname
    pdir = project_dir(pname)
    E = lambda t: H.escape(str(t))

    def say_box(text):
        return (f'<div class="say"><code>{E(text)}</code><button type="button" onclick="navigator.clipboard.writeText('
                f'this.previousElementSibling.textContent);this.textContent=\'copied\'">copy</button></div>')
    done, todo = [], []
    eds = []
    for e in p.get("style_from") or []:
        try:
            ed = project_edition(e)
            eds.append(f"<strong>{E(ed.get('name') or e)}</strong> ({E(ed.get('licence_folder', ''))}; {len(ed.get('books') or [])} books)")
        except SystemExit:
            eds.append(E(e))
    if eds:
        done.append(("The translation the drafts learn from", "<p>" + "<br>".join(eds) + "</p>"))
    n = 0
    for part in ("observations", "decisions"):
        f = os.path.join(pdir, "profile", f"{part}.json")
        if os.path.exists(f):
            n += len(J.load(open(f, encoding="utf-8")).get("entries", []))
    pages = len([f for f in glob.glob(os.path.join(pdir, "wiki", "**", "*.md"), recursive=True)])
    if n:
        done.append(("The language memory", f"<p>{n} entries about the language and {pages} wiki pages, each with its "
                     f"evidence from the corpus. <a href='memory.html'>Read it</a>.</p>"))
    drafted = [(ch, f, r) for ch, f, r in rows if os.path.exists(f)]
    if drafted:
        ch, f, r = drafted[-1]
        code, k = ch[:3], int(ch[3:])
        notes = f[:-4] + "_notes.md"
        qs = open_questions(open(notes, encoding="utf-8").read()) if os.path.exists(notes) else []
        links = ", ".join(f"<a href='read/{c[:3]}/{int(c[3:]):03d}.html'>{E(BY_CODE[c[:3]][1])} {int(c[3:])}</a>" for c, _, _ in drafted[-6:])
        done.append((f"{len(drafted)} chapter{'s' if len(drafted) > 1 else ''} drafted", f"<p>{links}. Every chapter is a "
                     "<strong>draft</strong> until the team publishes it.</p>"))
        todo.append((f"Read {BY_CODE[code][1]} {k} with someone who knows {name}",
                     f"<p>Open <a href='read/{code}/{k:03d}.html'>the chapter</a> and switch to <em>Verse by verse</em>: each verse "
                     "with the Hebrew, the BSB and the drafting agent's comments. The open questions from its notes:</p>"
                     + ("<ul>" + "".join(f"<li>{inline_md(q)}</li>" for q in qs) + "</ul>" if qs else "<p>(none listed)</p>")
                     + "<p>Corrections go into the chapter or the language memory; Claude Code makes them when asked:</p>"
                     + say_box(f"Correct {BY_CODE[code][1]} {k} in {pname}: …")))
    todo.append(("Write the style guide", "<p>The team's decisions, settled once and binding for every later chapter: how to "
                 "write the divine names and the names, the quote marks, how formal the language is. Start from the first "
                 "chapter's open questions. In Claude Code, in this folder:</p>" + say_box(f"Write the style guide for {pname} with me")))
    seq = modes.mode(p).get("drafting") == "sequential"
    todo.append(("Draft the next chapters", "<p>" + ("One chapter after another, never several at once: each chapter's "
                 "agent reads what the earlier chapters decided (names, word forms, spelling) and adds its own decisions to the "
                 "memory, so the chapters stay consistent. One agent drafts a book, chapter by chapter, and checks each."
                 if seq else "") + " In Claude Code:</p>"
                 + say_box(f"Draft the next chapters of {pname}" if not drafted else
                           f"Draft {BY_CODE[drafted[-1][0][:3]][1]} {int(drafted[-1][0][3:]) + 1} for {pname}")))
    todo.append(("Show it to others: the website", "<p>" + ("<strong>This is a local preview</strong> on your computer "
                 "(built from the files as they are now, including ones not yet in git); nobody else sees it. "
                 if preview else "") + "The public website shows every project's drafts, marked as drafts, with the "
                 "language memory and the credits; the text of a non-free translation never appears there, only short quotes "
                 "within the limits. To put this project there, the files go into git and the site is deployed:</p>"
                 + say_box("git add export/ import/ && git commit -m \"…\" && git push")
                 + say_box("python3 scripts/deploy_site.py")
                 + "<p>Or ask Claude Code to prepare it (it stages the files and gives you a commit message; you commit):</p>"
                 + say_box(f"Stage {pname} for the website and give me a commit message")))
    cards = lambda items, cls: "".join(f'<div class="step {cls}"><h3>{"✓ " if cls == "done" else ""}{E(t)}</h3>{b}</div>'
                                       for t, b in items)
    body = (f"<h1>{E(name)}: {E(ui['next_steps'])}</h1><h2>Done</h2>{cards(done, 'done')}<h2>Next</h2>{cards(todo, 'todo')}")
    open(os.path.join(od, "next.html"), "w", encoding="utf-8").write(page(f"{name}: {ui['next_steps']}", body, nav("n"), banner,
                                                                         built, pname.count("/") + 1, ui, lc))


NOTE = re.compile(r"\{([A-Z]):\s*(.*?)\}", re.S)
VERSE = re.compile(r"(?<![\w>.\x00])v(\d+(?:-\d+)?)(?=\s)")


def quotes_of(p, t):
    """Den Frie Bibel's own markup >>…<< (nested >…<) as the printed »…« / ›…‹."""
    if ">>" in (p.get("quotes") or ""):
        t = t.replace(">>", "»").replace("<<", "«")
        t = re.sub(r"(?<![\w])>", "›", t)
        t = t.replace("<", "‹").replace(">", "›")
    return t


def inline_md(t):
    t = H.escape(t, quote=False)
    t = re.sub(r"\*\*(?!\s)(.+?)(?<!\s)\*\*", r"<strong>\1</strong>", t)
    return re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)


def parse_chapter(p, text, footnotes):
    """-> (title, [blocks], [notes]): blocks are ('h', html) or ('p', html); notes [html]. Inline notes {T: …} and the
    footnote file's entries become numbered notes; verse markers become superscripts."""
    lines = [l for l in text.splitlines() if not l.startswith("!!<")]
    title, body = "", []
    for l in lines:
        m = re.match(r"^===(.*)===\s*$", l)
        if m and not title:
            title = m[1].strip()
        else:
            body.append(l)
    notes = []
    fn = footnotes_of(footnotes)
    blocks = []
    for blk in re.split(r"\n\s*\n", "\n".join(body)):
        blk = blk.strip()
        if not blk:
            continue
        m = re.match(r"^==(.*)==$", blk)
        if m:
            blocks.append(("h", inline_md(quotes_of(p, m[1].strip()))))
            continue
        t = re.sub(r"\s*\n\s*", " ", blk)
        blocks.append(("p", render(p, t, fn, notes)))
    return title, blocks, notes


def footnotes_of(footnotes):
    fn = {}
    for l in footnotes.splitlines():
        m = re.match(r"^v(\d+)\s+(.+?):\s*(.+)$", l)
        if m:
            fn.setdefault(m[1], []).append((m[2].strip(), m[3].strip()))
    return fn


def render(p, t, fn, notes, ids=True):
    """One run of draft text to HTML: the footnote file's entries placed after their keyword, inline notes numbered
    (continuing `notes`), quotes, emphasis, verse numbers."""
    if True:
        # footnotes: a marker after the keyword in its verse (or after the verse number)
        for v, items in fn.items():
            mv = re.search(rf"(?<![\w>.])v{v}(?=\s)", t)
            if not mv:
                continue
            nxt = VERSE.search(t, mv.end())
            seg_end = nxt.start() if nxt else len(t)
            for kw, note in items:
                i = t.find(kw, mv.end(), seg_end)
                at = i + len(kw) if i >= 0 else mv.end()
                t = t[:at] + "{F: " + note + "}" + t[at:]
                seg_end += len(note) + 5
        def note(m):
            notes.append(inline_md(quotes_of(p, m[2].strip())))
            return f"\x00{len(notes)}\x00"
        t = NOTE.sub(note, t)
        t = inline_md(quotes_of(p, t))
        vid = (lambda n: f' id="v{n}"') if ids else (lambda n: "")
        t = VERSE.sub(lambda m: f'<sup class="v"{vid(m[1].split("-")[0])}>{m[1]}</sup>', t)
        rid = (lambda n: f' id="r{n}"') if ids else (lambda n: "")
        t = re.sub(r"\x00(\d+)\x00", lambda m: f'<sup class="n"><a href="#n{m[1]}"{rid(m[1])}>{m[1]}</a></sup>', t)
        return t


def parse_clauses(p, text, footnotes):
    """A clause-line file -> [('h', html) | ('l', level, html)]: the same rendering as the prose, line by line (merged
    lines, '//N =', are shown inside the line above and get no line of their own)."""
    fn = footnotes_of(footnotes)
    parts = []
    for l in text.splitlines():
        if l.startswith(("!!<", "===")) or not l.strip():
            continue
        m = re.match(r"^==(.*)==\s*$", l)
        if m:
            parts.append(("h", m[1].strip()))
            continue
        m = re.match(r"//(\d+) (.*)$", l)
        if m and not (m[2].strip() == "=" or m[2].startswith("= ")):
            parts.append((int(m[1]) - 1, m[2].strip()))
    joined = "".join(f"\x01{'H' if k == 'h' else k}\x02{t}" for k, t in parts)
    html = render(p, joined, fn, [], ids=False)
    out = []
    for seg in html.split("\x01")[1:]:
        k, t = seg.split("\x02", 1)
        out.append(("h", t) if k == "H" else ("l", int(k), t))
    return out


def book_title(p, code, title):
    bt = (p.get("book_titles") or {}).get(code)
    if bt:
        return bt
    m = re.match(r"^(.*?),\s*\S+\s+\d+$", title)
    return m[1] if m else title or code


from notes_hebrew import notes_table, verse_numbers, original_verses as source_verses  # noqa: E402


def bsb_verses(p, code, ch, verses):
    """{verse: (BSB reference, text)} for the draft's verses (OT: Hebrew numbering, mapped through orig/vrs)."""
    from books import BY_CODE
    import langtools as LT
    import vrs
    from project import sources
    nt, adir, out, cache = BY_CODE[code][2] == "nt", sources(p, code)[2], {}, {}
    for v in verses:
        bc, bv = (ch, v) if nt else vrs.to_bsb(code, ch, v)
        if bc not in cache:
            f = os.path.join(ROOT, adir, f"{code}{bc:03d}.txt")
            cache[bc] = LT.verses_of(f) if os.path.exists(f) else {}
        if (bc, bv) in cache[bc]:
            out[v] = (f"{bc}:{bv}", cache[bc][(bc, bv)])
    return out


def verse_view(p, code, n, draft_file, notes_md, ui):
    """The chapter verse by verse: each verse of the draft with the original, the BSB and the notes' rows for it, then
    the rest of the notes. -> html ('' without notes)."""
    import langtools as LT
    if not notes_md:
        return ""
    rows, head, rest, _ = notes_table(notes_md)
    draft = {v: t for (c, v), t in LT.verses_of(draft_file).items()}
    src, bsb = source_verses(code, n), bsb_verses(p, code, n, sorted(draft))
    by_v = {}
    for r in rows:
        for v in verse_numbers(r[0]):
            by_v.setdefault(v, []).append(r)
    per_verse = rows and len(rows) >= 0.8 * len(draft) and all(len(by_v.get(v, [])) <= 1 for v in draft)
    rtl = ' dir="rtl" lang="he"'
    from books import BY_CODE
    nt = BY_CODE[code][2] == "nt"
    items = []
    for v in sorted(draft):
        cell = [f'<div class="vv-t"><sup class="v">{v}</sup> {inline_md(draft[v])}</div>']
        if src.get(v):
            cell.append(f'<div class="vv-o"{"" if nt else rtl}>{H.escape(src[v])}</div>')
        if bsb.get(v):
            cell.append(f'<div class="vv-e"><span class="muted">BSB {H.escape(bsb[v][0])}</span> {H.escape(bsb[v][1])}</div>')
        for r in by_v.get(v, []):
            if per_verse:
                cm = r[-1] if len(r) > 1 else ""
                if cm:
                    cell.append(f'<div class="vv-c">{inline_md(cm)}</div>')
            else:
                heb, tgt = (r[1] if len(r) > 1 else ""), (r[2] if len(r) > 2 else "")
                eng, cm = (r[3] if len(r) > 4 else ""), (r[-1] if len(r) > 3 else "")
                line = (f'<span{"" if nt else rtl}>{inline_md(heb)}</span> → <strong>{inline_md(tgt)}</strong>'
                        + (f' <span class="muted">({inline_md(eng)})</span>' if eng else ""))
                cell.append(f'<div class="vv-c">{line}' + (f'<br>{inline_md(cm)}' if cm else "") + "</div>")
        items.append(f'<div class="vv" id="vv{v}">' + "".join(cell) + "</div>")
    more = wiki.md_html(rest, "notes") if rest.strip() else ""
    return (f'<div class="lic">{H.escape(ui["n_verse"])}</div><div class="vvs">{"".join(items)}</div>'
            + (f'<div class="notes vv-more"><h2>{H.escape(ui["notes_more"])}</h2>{more}</div>' if more else ""))


def reader(pname, p, tracked, od, ui, banner, built, nav, lc, rows):
    """The project's reader: a page of books and chapters, and one page per chapter."""
    from books import BY_CODE
    depth = pname.count("/") + 2
    chapters = [(ch, f, r) for ch, f, r in rows if os.path.relpath(f, ROOT) in tracked]
    if not chapters:
        return None
    books, pages = {}, []
    for ch, f, r in chapters:
        code, n = ch[:3], int(ch[3:])
        fnf = f[:-4] + "_footnotes.txt"
        foot = open(fnf, encoding="utf-8").read() if os.path.relpath(fnf, ROOT) in tracked else ""
        title, blocks, notes = parse_chapter(p, open(f, encoding="utf-8").read(), foot)
        views = {}
        # the clause views: derived here from the draft and its .align on the local layouts (never stored, and the
        # layout files never published; scripts/clause_lines.py)
        if os.path.relpath(f[:-4] + ".align", ROOT) in tracked:
            import bridge_align as BA
            for lay, lines in (BA.clauses(pname, code, n) or {}).items():
                views[lay] = parse_clauses(p, "\n".join(lines), foot)
            if not views:
                print(f"  note: no clause views for {pname} {code}{n:03d} (.align stale, or no layouts: setup.py --heb bhsa,bcv-query)")
        books.setdefault(code, {"title": book_title(p, code, title), "chs": []})["chs"].append(n)
        nf = f[:-4] + "_notes.md"
        views["verse"] = verse_view(p, code, n, f, open(nf, encoding="utf-8").read()
                                    if os.path.relpath(nf, ROOT) in tracked else "", ui)
        pages.append((code, n, title, blocks, notes, r, views))
    rd = os.path.join(od, "read")
    os.makedirs(rd, exist_ok=True)
    order = [c for c in BY_CODE if c in books]
    # the book list
    items = []
    for c in order:
        b = books[c]
        chs = "".join(f'<a href="{c}/{n:03d}.html">{n}</a>' for n in b["chs"])
        items.append(f'<li><strong>{H.escape(b["title"])}</strong><div class="chs">{chs}</div></li>')
    body = f'<h1>{H.escape(p.get("language_name") or pname)}: {H.escape(ui["read"])}</h1><ul class="books">{"".join(items)}</ul>'
    open(os.path.join(rd, "index.html"), "w", encoding="utf-8").write(page(f"{p.get('language_name')}: {ui['read']}", body, nav("r"), banner, built, depth, ui, lc))
    # one page per chapter
    seq = [(c, n) for c in order for n in books[c]["chs"]]
    for code, n, title, blocks, notes, r, views in pages:
        i = seq.index((code, n))
        prev = seq[i - 1] if i else None
        nxt = seq[i + 1] if i + 1 < len(seq) else None
        rel = lambda c, k: f"../{c}/{k:03d}.html"
        pick = (f'<form class="pick" onsubmit="return false">'
                f'<select aria-label="{H.escape(ui["language"])}" data-pick="lang"></select>'
                f'<select aria-label="{H.escape(ui["book"])}" data-pick="book"></select>'
                f'<select aria-label="{H.escape(ui["chapter"])}" data-pick="ch"></select></form>')
        text = "".join(f"<h2>{h}</h2>" if k == "h" else f"<p>{h}</p>" for k, h in blocks)

        def clause_view(lay):
            rows = views.get(lay)
            if not rows:
                return ""
            body_ = "".join(f"<h2>{x[1]}</h2>" if x[0] == "h" else f'<div class="l" style="--lv:{x[1]}">{x[2]}</div>' for x in rows)
            notice = ui["n_bhsa"] if lay == "bhsa" else ui["n_hcl"]
            return f'<div class="lic">{H.escape(notice)}</div><div class="text cls">{body_}</div>'
        modes = [("std", ui["v_std"], True), ("verse", ui["v_verse"], bool(views.get("verse"))),
                 ("bhsa", ui["v_bhsa"], "bhsa" in views), ("hcl", ui["v_hcl"], "bcv-query" in views)]
        none = H.escape(ui["v_none"])
        switch = ('<div class="modes" role="tablist">' + "".join(
            f'<button type="button" data-mode="{m}"' + ("" if ok else f' disabled title="{none}"') + f">{H.escape(lab)}</button>"
            for m, lab, ok in modes) + "</div>")
        text = (f'<div class="view" data-view="std">{text}</div>'
                f'<div class="view" data-view="verse" hidden>{views.get("verse", "")}</div>'
                f'<div class="view" data-view="bhsa" hidden>{clause_view("bhsa")}</div>'
                f'<div class="view" data-view="hcl" hidden>{clause_view("bcv-query")}</div>')
        nt = "".join(f'<p id="n{j}"><a class="k" href="#r{j}">{j}</a>{h}</p>' for j, h in enumerate(notes, 1))
        link = lambda x, arrow_first: (f'<a href="{rel(*x)}">' + (f"← {H.escape(books[x[0]]['title'])} {x[1]}" if arrow_first
                                       else f"{H.escape(books[x[0]]['title'])} {x[1]} →") + "</a>") if x else ""
        pager = f'<nav class="pager"><span>{link(prev, True)}</span><span>{link(nxt, False)}</span></nav>'
        if r.get("status") == "published":
            bn = f"<strong>{H.escape(ui['published'].capitalize())}.</strong> {H.escape(r.get('statement', ''))}"
        else:
            bn = banner + (f" <em>({H.escape(ui['review'])})</em>" if r.get("status") == "in-review" else "")
        body = (pick + f'<h1>{H.escape(title or books[code]["title"] + " " + str(n))}</h1>{switch}<div class="text">{text}</div>'
                + (f'<div class="notes"><strong>{H.escape(ui["notes"])}</strong>{nt}</div>' if notes else "") + pager
                + f'<script>window.HERE={json.dumps({"p": pname, "b": code, "c": n})}</script>'
                + f'<script src="{"../" * (depth + 1)}nav.js"></script>')
        os.makedirs(os.path.join(rd, code), exist_ok=True)
        open(os.path.join(rd, code, f"{n:03d}.html"), "w", encoding="utf-8").write(
            page(f"{title} · {p.get('language_name')}", body, nav("r"), bn, built, depth + 1, ui, lc))
    return {"name": p.get("language_name") or pname, "books": [[c, books[c]["title"], books[c]["chs"]] for c in order]}


NAV_JS = """// The reader's selectors: language, book, chapter (scripts/build_site.py writes window.NAV below).
(function () {
  var N = window.NAV, H = window.HERE, root = document.currentScript.src.replace(/nav\\.js.*$/, "");
  function opt(sel, v, t, on) { var o = document.createElement("option"); o.value = v; o.textContent = t; o.selected = on; sel.appendChild(o); }
  var L = document.querySelector('[data-pick="lang"]'), B = document.querySelector('[data-pick="book"]'), C = document.querySelector('[data-pick="ch"]');
  if (!L) return;
  Object.keys(N).forEach(function (p) { opt(L, p, N[p].name, p === H.p); });
  N[H.p].books.forEach(function (b) { opt(B, b[0], b[1], b[0] === H.b); });
  function chs() { C.innerHTML = ""; var b = N[H.p].books.filter(function (x) { return x[0] === B.value; })[0];
    b[2].forEach(function (n) { opt(C, n, n, B.value === H.b && n === H.c); }); }
  chs();
  function go(p, b, c) { location.href = root + p + "/read/" + (b ? b + "/" + String(c).padStart(3, "0") + ".html" : "index.html"); }
  L.onchange = function () { var b = N[L.value].books[0]; go(L.value, b[0], b[2][0]); };
  B.onchange = function () { chs(); go(H.p, B.value, C.value); };
  C.onchange = function () { go(H.p, B.value, C.value); };
})();
// The view switch: text, BHSA clauses, MACULA/UHB clauses; no reload, the choice remembered across pages.
(function () {
  var bs = document.querySelectorAll(".modes button"), vs = document.querySelectorAll(".view");
  if (!bs.length) return;
  function get() { try { return localStorage.getItem("view") || "std"; } catch (e) { return "std"; } }
  function set(m) { try { localStorage.setItem("view", m); } catch (e) {} }
  function show(m, keep) {
    var b = document.querySelector('.modes button[data-mode="' + m + '"]');
    if (!b || b.disabled) m = "std";
    bs.forEach(function (x) { x.classList.toggle("on", x.dataset.mode === m); x.setAttribute("aria-selected", x.dataset.mode === m); });
    vs.forEach(function (v) { v.hidden = v.dataset.view !== m; });
    if (!keep) set(m);
  }
  bs.forEach(function (b) { b.onclick = function () { show(b.dataset.mode); }; });
  show(get(), true);
})();
"""


NETLIFY = """# The `site` branch is the finished site (scripts/build_site.py, staged by scripts/deploy_site.py on the
# maintainer's machine): Netlify builds nothing and publishes the branch as it is.
[build]
  command = ""
  publish = "."

[[headers]]
  for = "/*"
  [headers.values]
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
"""


def leak_test(out):
    """No local path or private detail in the site. (Text of the editions is the quotation check's job, run before a
    deploy by scripts/check_project.py; and the build reads only tracked files.)"""
    bad = re.compile(r"(?<![\w/])/Users/|(?<![\w/])/home/[a-z]|/private/tmp|\bC:\\\\|(?<!\.)\b(?:10\.\d{1,3}|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])|192\.168)\.\d{1,3}\.\d{1,3}\b(?!\.\d)|sk-ant-")  # a path, not 'house/home/…'
    for d, _, files in os.walk(out):
        for f in files:
            t = open(os.path.join(d, f), encoding="utf-8", errors="replace").read()
            m = bad.search(t)
            if m:
                raise SystemExit(f"leak test: {os.path.relpath(os.path.join(d, f), out)} contains {m[0]!r}")


def main():
    a = sys.argv[1:]
    out = os.path.join(ROOT, a[a.index("--out") + 1]) if "--out" in a else os.path.join(ROOT, "build", "site")
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    date = subprocess.run(["git", "log", "-1", "--format=%cs"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    preview = "--preview" in a
    build(out, f"{sha} ({date})" + (" + uncommitted (preview)" if preview else ""), preview)


if __name__ == "__main__":
    main()
