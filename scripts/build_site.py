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
import html as H, json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import wiki  # noqa: E402
import status  # noqa: E402
from project import project, edition, LICENCE_CLASS  # noqa: E402

UI = {   # interface strings by school language; the content stays as written
    "English": {"projects": "Projects", "status": "Status", "memory": "Language memory", "credits": "Credits",
                "chapters": "chapters", "draft": "draft", "review": "in review", "published": "published",
                "built": "Built from commit", "all": "All projects", "mode": "Model knowledge",
                "read": "Read", "language": "Language", "book": "Book", "chapter": "Chapter", "prev": "Previous", "next": "Next", "notes": "Notes", "nodrafts": "no drafts yet", "choose": "Choose a language", "status_word": "Status",
                "v_std": "Text", "v_bhsa": "BHSA clauses", "v_hcl": "MACULA/UHB clauses", "v_none": "no clause layout for this chapter",
                "n_bhsa": "Clause layout: ETCBC, BHSA 2021, licensed CC BY-NC 4.0. This view of our draft on that layout is CC BY-NC 4.0 too: non-commercial use only, with credit to the ETCBC.",
                "n_hcl": "Clause layout: bcv-commons Hebrew clause layout v0.22 (MACULA Hebrew, UHB), CC BY-SA 4.0. This view of our draft on that layout is CC BY-SA 4.0."},
    "Standard German": {"projects": "Projekte", "status": "Stand", "memory": "Sprachgedächtnis", "credits": "Nachweise",
                        "chapters": "Kapitel", "draft": "Entwurf", "review": "in Prüfung", "published": "veröffentlicht",
                        "built": "Erstellt aus Commit", "all": "Alle Projekte", "mode": "Sprachkenntnis des Modells",
                "read": "Lesen", "language": "Sprache", "book": "Buch", "chapter": "Kapitel", "prev": "Zurück", "next": "Weiter", "notes": "Anmerkungen", "nodrafts": "noch keine Entwürfe", "choose": "Sprache wählen", "status_word": "Stand",
                "v_std": "Fliesstext", "v_bhsa": "BHSA-Sätze", "v_hcl": "MACULA/UHB-Sätze", "v_none": "für dieses Kapitel kein Satzlayout",
                "n_bhsa": "Satzlayout: ETCBC, BHSA 2021, Lizenz CC BY-NC 4.0. Diese Darstellung unseres Entwurfs auf diesem Layout steht ebenfalls unter CC BY-NC 4.0: nur nicht kommerzielle Nutzung, mit Nennung des ETCBC.",
                "n_hcl": "Satzlayout: bcv-commons Hebrew clause layout v0.22 (MACULA Hebrew, UHB), CC BY-SA 4.0. Diese Darstellung unseres Entwurfs auf diesem Layout steht unter CC BY-SA 4.0."},
    "Danish": {"projects": "Projekter", "status": "Status", "memory": "Sproghukommelse", "credits": "Kilder",
               "chapters": "kapitler", "draft": "udkast", "review": "til gennemsyn", "published": "udgivet",
               "built": "Bygget fra commit", "all": "Alle projekter", "mode": "Modellens kendskab",
                "read": "Læs", "language": "Sprog", "book": "Bog", "chapter": "Kapitel", "prev": "Forrige", "next": "Næste", "notes": "Noter", "nodrafts": "ingen udkast endnu", "choose": "Vælg sprog", "status_word": "Status",
                "v_std": "Løbende tekst", "v_bhsa": "BHSA-sætninger", "v_hcl": "MACULA/UHB-sætninger", "v_none": "intet sætningslayout for dette kapitel",
                "n_bhsa": "Sætningslayout: ETCBC, BHSA 2021, licens CC BY-NC 4.0. Denne visning af vores udkast på det layout er også CC BY-NC 4.0: kun ikke-kommerciel brug, med kreditering af ETCBC.",
                "n_hcl": "Sætningslayout: bcv-commons Hebrew clause layout v0.22 (MACULA Hebrew, UHB), CC BY-SA 4.0. Denne visning af vores udkast på det layout er CC BY-SA 4.0."},
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
        pdir = os.path.join(ROOT, "export", pname)
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
        nav = lambda on: [(ui["read"], f"{pname}/read/index.html", on == "r")] * has_drafts + [
                          (ui["status"], f"{pname}/index.html", on == "s"), (ui["memory"], f"{pname}/memory.html", on == "m"),
                          (ui["credits"], f"{pname}/credits.html", on == "c"), (ui["all"], "index.html", False)]
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
            raise SystemExit(f"export/{pname}/STATUS.md is out of date: run python3 scripts/status.py {pname} and commit it")
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
        modes = [("std", ui["v_std"], True), ("bhsa", ui["v_bhsa"], "bhsa" in views), ("hcl", ui["v_hcl"], "bcv-query" in views)]
        none = H.escape(ui["v_none"])
        switch = ('<div class="modes" role="tablist">' + "".join(
            f'<button type="button" data-mode="{m}"' + ("" if ok else f' disabled title="{none}"') + f">{H.escape(lab)}</button>"
            for m, lab, ok in modes) + "</div>")
        text = (f'<div class="view" data-view="std">{text}</div>'
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
    bad = re.compile(r"(?<![\w/])/Users/|(?<![\w/])/home/[a-z]|/private/tmp|\bC:\\\\|100\.86\.|sk-ant-")  # a path, not 'house/home/…'
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
