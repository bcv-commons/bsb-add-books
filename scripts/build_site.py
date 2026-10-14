#!/usr/bin/env python3
"""Build the public website from the repository: static pages, no server, nothing fetched at view time.

The site holds what git tracks in export/ and nothing else (docs/licensing.md: no edition texts, packs, style
reports, probe answers or anything in _eval/local/): for every project a home page (its STATUS.md, with the draft
statement), the language memory (the wiki viewer of scripts/wiki.py view) and the credits; and a page listing the
projects. Every page carries the project's draft statement. A file that git doesn't track is never read: the build
stops if a project's pages would need one.

This is the first version of the site; the planned app (internal planning notes) replaces the pages one by one and
keeps the same data rules.

Usage: python3 scripts/build_site.py [--out DIR]      (default build/site/, git-ignored)
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
                "built": "Built from commit", "all": "All projects", "mode": "Model knowledge"},
    "Standard German": {"projects": "Projekte", "status": "Stand", "memory": "Sprachgedächtnis", "credits": "Nachweise",
                        "chapters": "Kapitel", "draft": "Entwurf", "review": "in Prüfung", "published": "veröffentlicht",
                        "built": "Erstellt aus Commit", "all": "Alle Projekte", "mode": "Sprachkenntnis des Modells"},
    "Danish": {"projects": "Projekter", "status": "Status", "memory": "Sproghukommelse", "credits": "Kilder",
               "chapters": "kapitler", "draft": "udkast", "review": "til gennemsyn", "published": "udgivet",
               "built": "Bygget fra commit", "all": "Alle projekter", "mode": "Modellens kendskab"},
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
"""


def git_tracked():
    out = subprocess.run(["git", "ls-files", "-z", "export"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return {f for f in out.split("\0") if f}


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


def build(out, built):
    tracked = git_tracked()
    projects = sorted(os.path.dirname(f)[len("export/"):] for f in tracked
                      if re.fullmatch(r"export/[^_/][^/]*/[^/]+/project\.yaml", f))
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    open(os.path.join(out, "style.css"), "w", encoding="utf-8").write(CSS.strip() + "\n")
    cards = []
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
        nav = lambda on: [(ui["status"], f"{pname}/index.html", on == "s"), (ui["memory"], f"{pname}/memory.html", on == "m"),
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
        counts = ", ".join(f"{n[k]} {ui[l]}" for k, l in (("draft", "draft"), ("in-review", "review"), ("published", "published")) if n[k])
        lic = sorted({LICENCE_CLASS.get(edition(e)["licence_folder"], "non-free") for e in p.get("style_from") or []})
        cards.append(f'<li><h2><a href="{pname}/index.html">{H.escape(name)}</a></h2>'
                     f'<div class="muted">{len(rows)} {H.escape(ui["chapters"])}: {H.escape(counts or "—")}</div>'
                     f'<div class="muted">{H.escape(fam or "")}{" · " if fam else ""}{H.escape(", ".join(lic))} · '
                     f'<a href="{pname}/memory.html">{H.escape(ui["memory"])}</a></div></li>')
    en = UI["English"]
    intro = ("<p>Bible translations drafted chapter by chapter from the Hebrew and Greek, with the Berean Standard Bible as "
             "the only assisting translation. Everything here is a <strong>draft</strong> until a language team publishes it; "
             "each chapter's status is on its project page.</p>")
    body = f"<h1>{en['projects']}</h1>{intro}<ul class=cards>{''.join(cards)}</ul>"
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(page("bsb-add-books: draft translations", body, [], "", built, 0, en))
    open(os.path.join(out, "BUILT_FROM"), "w").write(built + "\n")
    open(os.path.join(out, "netlify.toml"), "w").write(NETLIFY)
    leak_test(out)
    print(f"{os.path.relpath(out, ROOT)}/: {len(cards)} projects, built from {built}")


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
    bad = re.compile(r"/Users/|/home/[a-z]|/private/tmp|\bC:\\\\|100\.86\.|sk-ant-")
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
    build(out, f"{sha} ({date})")


if __name__ == "__main__":
    main()
