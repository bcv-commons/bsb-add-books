"""Print the drafting prompt for one chapter, filled in from the project config.

Usage: python3 scripts/make_prompt.py <project> <code> <chapter> [--date DD.MM.YYYY]

Reads docs/prompts/chapter_prompt.md (everything below the first '---' line),
export/<project>/project.yaml and the import/<licence>/<language>/<edition>/edition.yaml files it
names. See docs/configuration.md for the fields.
"""
import datetime, os, re, sys
from books import BY_CODE
from project import edition, project, sources, must_quarantine, missing_texts, ROOT
import vrs

NAMES = {
    "orig/heb": ("Hebrew/Aramaic text (Hebrew verse numbering, one clause per line as `verse:indent text`)", "Hebrew"),
    "orig/grc": ("Berean Greek Bible (BGB), one verse per line as `chapter:verse text`", "Greek"),
    "orig/grc-rp": ("Robinson-Pierpont Byzantine Textform 2018, one verse per line as `chapter:verse text`", "Greek"),
    "reference/BSB": ("Berean Standard Bible (BSB)", "BSB"),
    "reference/MSB": ("Majority Standard Bible (MSB)", "MSB"),
}


def verse_count(path, nt):
    vs = set()
    for line in open(path, encoding="utf-8").read().splitlines()[1:]:
        m = re.match(r"(\d+):(\d+)", line)
        if m:
            vs.add(int(m.group(2) if nt else m.group(1)))
    return len(vs)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pname, code, chapter = args[0], args[1], int(args[2])
    date = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else datetime.date.today().strftime("%d.%m.%Y")
    p = project(pname)
    if missing := missing_texts(p):
        raise SystemExit("the agents would draft without their corpus: " + "; ".join(
            f"edition {e} is not here (get it: {how})" for e, how in missing))
    nt = BY_CODE[code][2] == "nt"
    orig_dir, notes_suffix, assist_dir = sources(p, code)
    nnn = f"{chapter:03d}"
    orig_path = f"{orig_dir}/{code}{nnn}.txt"
    if not os.path.exists(os.path.join(ROOT, orig_path)):
        sys.exit(f"no {orig_path}: OT chapters follow the Hebrew numbering (e.g. BSB Mal 4 = Hebrew Mal 3:19-24); "
                 "see python3 scripts/vrs.py <code> <chapter>")

    # OT: the BSB chapters the Hebrew verses fall in (Hebrew and BSB numbering differ in places)
    assist_chapters, shifts = ([chapter], []) if nt else vrs.chapter(code, chapter)
    assist_files = " and ".join(f"`{assist_dir}/{code}{c:03d}.txt`" for c in assist_chapters)
    numbering = ""
    if shifts:
        numbering = ("\n- **Verse numbering:** Hebrew and BSB numbering differ in this chapter: "
                     + "; ".join(shifts) + ". Number your draft as the Hebrew.")
        if assist_chapters != [chapter]:
            numbering += " Where verses belong to another BSB chapter, give the BSB numbering in a footnote."

    # a book that a non-free (or, by choice, attributable) style edition has is drafted only in quarantine
    needed = must_quarantine(p, code)
    left = [(e, f) for e, _, f in needed if f]
    if left or (needed and code not in p["quarantine"]):
        sys.exit(f"{code}: {', '.join(e for e, _, _ in needed)} has this book and isn't public domain: quarantine it "
                 f"first (python3 scripts/quarantine.py {pname} {code}); "
                 + ("still present: " + ", ".join(os.path.relpath(x, ROOT) for _, f in left for x in f[:2]) if left else
                    f"add {code} to the project's quarantine"))
    quarantined = code in p["quarantine"]
    q = ""
    if quarantined:
        q = ("**STRICT QUARANTINE:** existing translations of this book in the target language "
             "have been removed on purpose. Never read, search for, or recall from memory any "
             f"existing {p.get('language_name', p['language'])} translation of this book. "
             "No web access to Bible text in the target language.")

    style = []
    for e in p["style_from"]:
        ed = edition(e)
        d = f"{ed['dir']}/{ed.get('text_dir', 'text')}/"
        line = f"- Style and vocabulary only: {ed.get('name', e)}, `{d}`. Check word choices with Python `collections.Counter` frequency lookups over these files, and prefer its words."
        if ed.get("quote_hint"):
            line += f" {ed['quote_hint']}"
        style.append(line)
    extra_style = p.get("style_notes")
    if extra_style:
        style.append(f"- {extra_style}")

    dont = [f"`{d}`" for d in (p.get("do_not_open") or [])]
    if quarantined:
        for e in p["style_from"]:
            d = edition(e)["dir"]
            dont.append(f"`{d}/quarantined/` and any `{code}` file in `{d}/`")
            if os.path.isdir(os.path.join(ROOT, d, "source")):
                dont.append(f"`{d}/source/` (the edition's original files)")
    do_not_open = "; ".join(dont) or "-"

    # the contract: the project's and the book's style guides and review overviews that exist
    pdir = os.path.join(ROOT, "export", pname)
    have = lambda rel: os.path.exists(os.path.join(pdir, rel))
    guides = [g for g in ["style_guide.md", f"{code}/{code}_style_guide.md"] + [g.format(code=code, nnn=f"{chapter:03d}") for g in p.get("style_guides") or []] if have(g)]
    if not have(f"{code}/{code}_style_guide.md") and p.get("default_style_guide") and have(p["default_style_guide"]):
        guides.append(p["default_style_guide"])
    reviews = [r for r in ["review_overview.md", f"{code}/{code}_review_overview.md"] if have(r)]
    contract = [f"- `export/{pname}/{g}` (style guide);" for g in dict.fromkeys(guides)]
    contract += [f"- the decided items in `export/{pname}/{r}`, which are binding;" for r in reviews]
    if not contract:
        contract = ["- no style guide or review overview yet: the earlier chapters below are the contract;"]

    inl = p.get("inline_notes")
    if inl:
        kinds = "".join(f"\n  - `{{{k}: …}}`: {v};" for k, v in inl.items() if len(k) == 1)
        inline_rule = f"- **Inline notes** in the text, in the style corpus's form:{kinds}"
        if inl.get("glossary"):
            inline_rule += "\n  - `{N: …}` takes only these glossary keys: " + ", ".join(inl["glossary"]) + ";"
        if inl.get("placement"):
            inline_rule += f"\n  - {inl['placement']}."
    else:
        inline_rule = "- **Clean text:** no inline notes."

    titles = p.get("book_titles") or {}
    book_title = titles.get(code)
    if not book_title:                    # the style edition's own title for the book, if it has the book
        for e in p["style_from"]:
            ed = edition(e)
            f = os.path.join(ROOT, ed["dir"], ed.get("text_dir", "text"), f"{code}001.txt")
            if os.path.exists(f):
                m = re.search(r"^===(.*?), [^,=]+ \d+===", open(f, encoding="utf-8").read(), re.M)
                if m:
                    book_title = m[1]; titles = {**titles, code: book_title}; break
    book_title = book_title or BY_CODE[code][1]
    lang_name = p.get("language_name", p.get("language"))
    notes_lang = (p.get("notes_language") or p.get("school_language") or "English")
    if p.get("notes_structure"):
        notes_rule = f"- **Notes** in {notes_lang}, in `{code}{nnn}_notes.md`: {p['notes_structure']}"
    else:
        notes_rule = (f"- **Notes** in {notes_lang}, in `{code}{nnn}_notes.md`, with the structure of the earlier chapters:\n"
                      "  - what the draft is;\n"
                      f"  - a table *Verse · {NAMES[orig_dir][1]} · {lang_name} · {NAMES[assist_dir][1]} · Comment*;\n"
                      "  - exegetical observations;\n  - dialect/style (with corpus counts);\n  - new name forms;\n  - open questions.")
    footnotes = p.get("footnotes", True)
    fh = p.get("footnotes_header")
    fh = (" It starts with " + ", ".join(f"`{l.format(file=f'{code}{nnn}.txt', date=date)}`" for l in fh)
          + " and a blank line." if fh else "")
    footnotes_rule = (f"- **Footnotes:** {NAMES[assist_dir][1]}-style, in {lang_name}, in a separate "
                      f"`{code}{nnn}_footnotes.txt`, one per line as `vN Keyword: text`.{fh} Only when needed: name meanings, "
                      "»Or: …« alternatives, important variants, OT references." if footnotes
                      else f"- **No footnotes** (no `{code}{nnn}_footnotes.txt`).")
    layout = (f"Then `==={book_title}, {p.get('chapter_word', 'chapter')} {chapter}===`, `==headings==`, inline `vN` markers, "
              f"quotes {p.get('quotes', '„…“')}, poetry as `//1` / `//2` lines.")
    hdr = p.get("header")
    if isinstance(hdr, dict):
        hdr = hdr.get("nt" if nt else "ot")
    if hdr:
        lines = ", ".join(f"`{l.format(file=orig_path, date=date)}`" for l in hdr)
        header_rule = f"- **Header:** {lines}. {layout}"
    else:
        header_rule = f"- **Header** as in the earlier chapters, dated {date}. {layout}"
    if code not in titles and p.get("book_title_rule"):
        header_rule += f" {p['book_title_rule']}"
    sm = p.get("style_model")
    style_model_fallback = (
        "If this book has no finished chapters yet, the style model is: " + "; ".join(f"`{s}`" for s in sm)
        + ". Read them in full the same way." if sm else
        f"If this book has no finished chapters yet, use the nearest finished book in `export/{pname}/` the same way.")
    import quotes, modes
    qrule = quotes.rule_text(pname)
    mrules = modes.mode_rules(pname, p, modes.have_tools(pname))
    style_check = modes.mode(p)["style_check"]
    fields = dict(
        root=ROOT, project=pname, code=code, nnn=nnn, chapter=chapter, date=date,
        book_title=book_title, footnotes_rule=footnotes_rule, header_rule=header_rule, notes_rule=notes_rule,
        footnotes_files=" and `_footnotes.txt`" if footnotes else "", style_model_fallback=style_model_fallback,
        report_items=p.get("report_items") or ("footnotes created" if footnotes else "notes written"),
        chapter_word=p.get("chapter_word", "chapter"),
        n_verses=verse_count(os.path.join(ROOT, orig_path), nt),
        language_name=p.get("language_name", p.get("language")),
        notes_language=(p.get("notes_language") or p.get("school_language") or "English"),
        orig_language=NAMES[orig_dir][1],
        orig_path=orig_path, orig_name=NAMES[orig_dir][0],
        orig_notes_line=(f" Its variant notes are in `{orig_dir}/{code}{nnn}{notes_suffix}` (if present)." if notes_suffix else ""),
        assist_files=assist_files, numbering_block=numbering, assist_name=NAMES[assist_dir][0], assist_short=NAMES[assist_dir][1],
        style_lines="\n".join(style), do_not_open=do_not_open,
        contract_lines="\n".join(contract), inline_notes_rule=inline_rule,
        quarantine_block=q, quotes=p.get("quotes", "„…“"),
        extra_rules="\n".join(f"- {r}" for r in mrules + (p.get("rules") or []) + ([qrule] if qrule else [])),
        numbering_note=(" Count verses with Hebrew numbering." if not nt else ""),
        style_step=(f"\n- Run `python3 scripts/style.py {pname} export/{pname}/{code}/{code}{nnn}.txt --brief`: it compares your chapter "
                    "with the human translators (the human verses most like yours, and how far their own chapters stray). Work "
                    "through its flags, then its watch items: where the human models show a construction that fits the source, "
                    "use it; where a flag doesn't fit a verse, leave it. Check each word form it finds nowhere in the corpus. "
                    "Run it once more at the end." if style_check else ""),
    )
    template = open(os.path.join(ROOT, "docs", "prompts", "chapter_prompt.md"), encoding="utf-8").read()
    body = template.split("\n---\n", 1)[1]
    text = body.format(**fields)
    print(re.sub(r"\n{3,}", "\n\n", text).strip())


if __name__ == "__main__":
    main()
