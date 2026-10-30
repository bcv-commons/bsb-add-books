"""Read import/<licence>/<language>/<edition>/edition.yaml and the project's project.yaml and
resolve, per book, which original text and which assisting translation apply.

Where a project lives is its output path (docs/licensing.md, *Three output paths*):

    project id                 folder                          output
    dan/dan_BSB                export/dan/dan_BSB/             export (our own work, CC0; in git)
    CC-NC/xyz/xyz_rev          export/CC-NC/xyz/xyz_rev/       export/CC-NC (derived from a CC-NC edition; in git, its licence)
    local_output/jam/jam_rev   local_output/jam/jam_rev/       local_output (derived work returned to the rights holder; never in git)

Derived work (a revision, a draft made with the edition's text of the book in view, a file in the edition's own structure)
is allowed only on the two derived paths: export/CC-NC for an open or CC-NC edition, local_output for any edition, with the
rights holder's approval recorded in edition.yaml (derived_work:) when the edition is non-free or CC-ND.

Editions are filed by licence and language, the ISO 639-3 code or an interim dialect id
(import/CC0/dan/den-frie-bibel/, import/non-free/jam/jambswn-et/), and
named by their id alone: 'based_on: den-frie-bibel' finds import/*/*/den-frie-bibel/.

Text basis -> source folders:

    nt_basis      NT original      NT assisting translation
    critical      orig/grc  (BGB)  reference/BSB
    majority      orig/grc-rp (RP) reference/MSB
    tr            orig/grc-rp (RP) reference/MSB   (closest available; see docs/sources.md)

The OT is always orig/heb + reference/BSB (the MSB's OT is the BSB).

A project inherits nt_basis from the edition it continues ('based_on'),
unless it sets its own. Command line:

    python3 scripts/project.py <project>            # show the resolved setup
    python3 scripts/project.py <project> jhn        # paths for one book
"""
import os, re, sys
import yaml
from books import BY_CODE, ROOT, order

BASIS = {
    "critical": ("orig/grc", "reference/BSB"),
    "majority": ("orig/grc-rp", "reference/MSB"),
    "tr": ("orig/grc-rp", "reference/MSB"),
}


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def edition_dir(name):
    """import/<licence>/<language>/<name>, relative to ROOT; the edition id must be unique across the folders."""
    base = os.path.join(ROOT, "import")
    hits = [os.path.join("import", lic, lang, name)
            for lic in sorted(os.listdir(base)) if not lic.startswith(("_", ".")) and os.path.isdir(os.path.join(base, lic))
            for lang in sorted(os.listdir(os.path.join(base, lic)))
            if os.path.isfile(os.path.join(base, lic, lang, name, "edition.yaml"))]
    if len(hits) != 1:
        raise SystemExit(f"edition {name!r}: " + (f"found in more than one folder: {', '.join(hits)}" if hits
                         else f"no import/<licence>/<language>/{name}/edition.yaml"))
    return hits[0]


def edition(name):
    e = load_yaml(os.path.join(ROOT, edition_dir(name), "edition.yaml"))
    e["dir"] = edition_dir(name)
    e["licence_folder"] = e["dir"].split(os.sep)[1]
    return e


def project_rel(name):
    """The project's folder relative to ROOT: local_output/<...> as given, anything else under export/."""
    return name if name.split("/")[0] == "local_output" else os.path.join("export", name)


def project_dir(name):
    return os.path.join(ROOT, project_rel(name))


def output_path(name):
    """'export' (CC0), 'export/CC-NC' or 'local_output', from where the project lives."""
    top = name.split("/")[0]
    return "local_output" if top == "local_output" else "export/CC-NC" if top == "CC-NC" else "export"


def derived_dir(name):
    """Where this project's derived work goes (deliverables made from an edition's text, such as a meaning check of the
    team's own chapters): its own folder on a derived path, else local_output/<project>/ beside the public project."""
    return project_dir(name) if output_path(name) != "export" else os.path.join(ROOT, "local_output", name)


# Open licence folders; the rest (non-free, CC-ND, CC-NC) count as non-free for quarantine and quotations.
OPEN = ("CC0", "CC-BY", "CC-BY-SA")


def approval(ed):
    """The rights holder's approval of derived work (edition.yaml derived_work:), or None when it is not recorded."""
    d = ed.get("derived_work") or {}
    return d if d.get("approved_by") and d.get("date") else None


def check_output(name, p, eds):
    """Refuse a project whose derived work would go where its editions' licences don't allow (docs/licensing.md)."""
    out = output_path(name)
    derived = [e for e in (p.get("derived_from") or []) if e]
    base = eds.get(p.get("based_on")) if p.get("based_on") else None
    if base is not None and base.get("role") == "revise" and p["based_on"] not in derived:
        derived.append(p["based_on"])
    p["derived_from"] = derived
    for e in derived:
        ed = eds.get(e) or edition(e)
        lic = ed["licence_folder"]
        if out == "export":
            if lic != "CC0":
                raise SystemExit(f"{name}: derived from {e} ({lic}): derived work can't go into export/, which is public domain "
                                 "(CC0). Only CC0 editions can be revised there; put the project under export/CC-NC/ (an open "
                                 "or CC-NC edition) or local_output/ (with the rights holder's approval).")
        elif out == "export/CC-NC":
            if lic not in OPEN + ("CC-NC",):
                raise SystemExit(f"{name}: derived from {e} ({lic}): export/CC-NC/ takes work derived from open and CC-NC "
                                 "editions only; a CC-ND or non-free edition's derived work goes to local_output/.")
        elif lic not in OPEN + ("CC-NC",) and not approval(ed):
            raise SystemExit(f"{name}: derived from {e} ({lic}): local_output/ needs the rights holder's approval in "
                             f"{ed['dir']}/edition.yaml (derived_work: approved_by, date).")
    p["output"] = out
    # what agents of a public project must not read: derived work, which is not ours (docs/licensing.md)
    if out != "local_output":
        p["do_not_open"] = list(dict.fromkeys(list(p.get("do_not_open") or []) + ["local_output/"]))


def project(name):
    p = load_yaml(os.path.join(project_dir(name), "project.yaml"))
    base = edition(p["based_on"]) if p.get("based_on") else {}
    p.setdefault("nt_basis", base.get("nt_basis", "critical"))
    if p["nt_basis"] not in BASIS:
        raise SystemExit(f"nt_basis must be one of {sorted(BASIS)}, not {p['nt_basis']!r}")
    p.setdefault("language", base.get("language"))
    p["book_order"] = p.get("book_order") or "tanakh"     # the reading order (books.ORDERS)
    order(p["book_order"])
    if not p.get("style_from"):     # missing or empty (the template has []): default to based_on
        p["style_from"] = [p["based_on"]] if p.get("based_on") else []
    p["own_quarantine"] = list(p.get("quarantine") or [])
    q = set(p["own_quarantine"])
    for e in p["style_from"]:
        q |= set(edition(e).get("quarantine") or [])
    p["quarantine"] = sorted(q)
    # export/ is public domain (CC0), like the BSB and MSB. Revising an edition makes the drafts a derivative of it:
    # in export/ only for a CC0 edition; otherwise on a derived path (check_output).
    check_output(name, p, {p["based_on"]: base} if base else {})
    return p


LICENCE_CLASS = {"CC0": "public-domain", "CC-BY": "attributable", "CC-BY-SA": "attributable", "non-free": "non-free",
                 "CC-ND": "non-free", "CC-NC": "non-free"}


def book_files(ed, code):
    """The edition's text files of one book (<code>NNN.txt or <code>.txt), as paths."""
    d = os.path.join(ROOT, ed["dir"], ed.get("text_dir", "text"))
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, f) for f in os.listdir(d) if re.fullmatch(rf"{code}(\d{{3}})?\.txt", f))


def missing_text(e):
    """None if the edition's text is here; else how to get it (edition.yaml get_text, or its fetch recipe).
    The texts are not in git (import/README.md): a fresh clone has only the editions' descriptions."""
    ed = edition(e)
    d = os.path.join(ROOT, ed["dir"], ed.get("text_dir", "text"))
    if os.path.isdir(d) and any(not f.startswith(".") for f in os.listdir(d)):
        return None
    if ed.get("get_text"):
        return ed["get_text"]
    if ed.get("fetch"):
        return f"python3 scripts/fetch_edition.py {e}"
    return f"see {ed['dir']}/edition.yaml (source)"


def missing_texts(p):
    """[(edition id, how to get it)] for the project's editions whose text is not present."""
    eds = dict.fromkeys(([p["based_on"]] if p.get("based_on") else []) + list(p.get("style_from") or []))
    return [(e, how) for e in eds if (how := missing_text(e))]


def editions_with_book(p, code):
    """Every edition of the project (based_on and style_from) that has this book: [(edition id, licence class)]."""
    out = []
    for e in dict.fromkeys(([p["based_on"]] if p.get("based_on") else []) + list(p.get("style_from") or [])):
        ed = edition(e)
        if book_files(ed, code) or os.path.isdir(os.path.join(ROOT, ed["dir"], "quarantined", code)) or code in (ed.get("books") or []):
            out.append((e, LICENCE_CLASS.get(ed["licence_folder"], "non-free")))
    return out


def has_chapter(ed, code, ch):
    """Whether the edition has chapter ch of the book: its chapter file (in text/ or quarantined/), or 'ch:' verse lines
    in a book file. None when that can't be told (no text here, as in a fresh clone)."""
    d = os.path.join(ROOT, ed["dir"], ed.get("text_dir", "text"))
    name = f"{code}{ch:03d}.txt"
    if os.path.exists(os.path.join(d, name)) or os.path.exists(os.path.join(ROOT, ed["dir"], "quarantined", code, name)):
        return True
    books = [os.path.join(d, f"{code}.txt"), os.path.join(ROOT, ed["dir"], "quarantined", code, f"{code}.txt")]
    for f in books:
        if os.path.exists(f):
            return bool(re.search(rf"^{ch}:\d", open(f, encoding="utf-8").read(), re.M))
    have = book_files(ed, code) or (os.listdir(os.path.join(ROOT, ed["dir"], "quarantined", code))
                                    if os.path.isdir(os.path.join(ROOT, ed["dir"], "quarantined", code)) else [])
    return False if have else None


def must_quarantine(p, code, chapter=None):
    """The style editions whose copy of this book a draft must not see: every non-free edition that has the
    book, and an attributable (CC BY / CC BY-SA) one when the project sets quarantine_attributable: true.
    Public-domain editions never need it. With chapter: an edition that has other chapters of the book but not this
    one needs no quarantine for it (Genesis 31-50 while the edition has 1-30); when that can't be told (no text
    here), the whole-book rule holds. On a derived path the editions the work is derived from need none (their text is
    the work's input); a held-out test there names its books in the project's own quarantine list.
    Returns [(edition id, licence class, [files still present])]."""
    out = []
    free = set(p.get("derived_from") or []) if p.get("output", "export") != "export" else set()
    for e in p["style_from"]:
        if e in free and code not in (p.get("own_quarantine") or []):
            continue
        ed = edition(e)
        cls = LICENCE_CLASS.get(ed["licence_folder"], "non-free")
        if cls == "non-free" or (cls == "attributable" and p.get("quarantine_attributable")):
            files = book_files(ed, code)
            held = os.path.isdir(os.path.join(ROOT, ed["dir"], "quarantined", code))
            if files or held or code in (ed.get("books") or []):
                if chapter is not None and has_chapter(ed, code, chapter) is False:
                    continue
                out.append((e, cls, files))
    return out


def sources(p, code):
    """(original dir, original notes suffix, assisting dir) for one book."""
    if BY_CODE[code][2] == "ot":
        return "orig/heb", None, "reference/BSB"
    orig, assist = BASIS[p["nt_basis"]]
    return orig, "_notes.txt", assist


if __name__ == "__main__":
    p = project(sys.argv[1])
    print(f"project:     {sys.argv[1]}  ({project_rel(sys.argv[1])}/)")
    print(f"output:      {p['output']}" + (f"  (derived from {', '.join(p['derived_from'])})" if p["derived_from"] else ""))
    print(f"language:    {p.get('language')}")
    print(f"based_on:    {p.get('based_on')}")
    style = [f"{e} ({edition_dir(e)})" for e in p["style_from"]]
    print(f"style_from:  {', '.join(style) or '-'}")
    print(f"nt_basis:    {p['nt_basis']}  -> NT {BASIS[p['nt_basis']][0]} + {BASIS[p['nt_basis']][1]}; Tanakh orig/heb + reference/BSB")
    print(f"quarantine:  {', '.join(p['quarantine']) or '-'}")
    for code in sys.argv[2:]:
        print(code, sources(p, code))
