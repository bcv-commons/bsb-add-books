#!/usr/bin/env python3
"""A project's drafts as USFM, for a team's Paratext project.

Per book, one file with the chapters that are drafted:
  - the frame comes from the team's own book where the style edition has its SFM (`source/`): its `\\id` line, `\\ide`,
    `\\h`, `\\toc1-3`, `\\mt` lines and its file-name pattern, so the file imports as a book of theirs. A book they don't
    have yet gets the same frame built from the draft's title ("Iqandengaz (Genesis)": `\\h` the title, `\\toc1/2` and
    `\\mt1` the name, `\\mt2` the bracket). Without any team SFM the frame is plain (BSB book name);
  - `\\rem` lines saying what the file is: a machine draft, its status (`status.py`), the date;
  - per chapter `\\c`, headings `==X==` as `\\s1`, `\\p` after a heading and wherever the BSB starts a paragraph at that
    verse, poetry lines `//1` `//2` of the draft as `\\q1` `\\q2` (a draft without them, in a passage the BSB sets as
    poetry, gets one `\\q1` line per verse), footnotes from `<code>NNN_footnotes.txt` as `\\f + \\fr c:v \\fk … \\ft …\\f*`;
  - verse numbers: OT drafts keep the Hebrew numbering; the file takes the team's (`--numbering`, default from the
    edition's SFM: English where their Jonah has 1:17, else Hebrew). Hebrew verses that the BSB joins become one verse;
  - Unicode as the team's files have it (`--norm NFC|NFD`, default: as their SFM; a team's files may be NFD, our texts are NFC: the same
    letters, but Paratext's word list compares code points); line endings likewise (`--eol crlf|lf`, default: as their SFM);
  - the divine name marked `\\nd ...\\nd*` wherever the team's SFM marks a word so (any of their books).
The team's conventions come from the style edition's `sfm:` block in edition.yaml (scripts/sfm_profile.py: heading
marker, paragraph markers, footnote parts, \\id line, \\ide, file names, the divine name, Unicode form, line endings,
versification), each field overridable in the project's own `sfm:`; without a block they are detected from the files at
every export, as above.
Right-to-left scripts (Arabic, Hebrew, Syriac, ...; scripts/script_code.py RTL) need nothing here: USFM carries no
direction, Paratext takes it from the project's language settings, and the text keeps its logical order.
The file is checked with usfmtc (pip install usfmtc) and its verses counted against the draft.

Where it goes: a file in the team's structure is derived from their edition (docs/licensing.md), so it is written to the
project's derived path (`local_output/<project>/usfm/`, scripts/project.py derived_dir); a plain frame to build/usfm/.

Usage: python3 scripts/export_usfm.py <project> <code> [<ch>[-<ch>]] [--numbering english|hebrew] [--norm NFC|NFD] [--eol crlf|lf] [--out DIR]
"""
import datetime, glob, json, os, re, sys, unicodedata

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
from books import BOOKS, BY_CODE  # noqa: E402
from project import project, project_dir, derived_dir, edition  # noqa: E402
import vrs  # noqa: E402

KEEP = ("id", "ide", "h", "toc1", "toc2", "toc3", "mt", "mt1", "mt2", "mt3")


def book_number(code):
    i = [b[0] for b in BOOKS].index(code)    # the numbering order (books.BOOKS), never the project's reading order
    return i + 1 if BY_CODE[code][2] == "ot" else i + 2          # Paratext: OT 01-39, NT 41-67


def team_sfm(p, code):
    """(the team's SFM file for this book or None, any SFM file of theirs or None), from the style editions' source/."""
    files = []
    for e in p.get("style_from") or []:
        files += sorted(glob.glob(os.path.join(edition(e)["dir"], "source", "*.[sS][fF][mM]")))
    files = [f for f in files if "Earlier" not in os.path.basename(f)]
    mine = next((f for f in files if re.match(rf"\\id {code.upper()}\b", open(f, encoding="utf-8").readline())), None)
    return mine, (mine or (files[0] if files else None))


def team_nd(p):
    """The words the team's SFM marks as the divine name (\\nd ...\\nd*), NFC, punctuation stripped: what their files do
    (a team's newer books may mark it where their older ones don't)."""
    words = set()
    for e in p.get("style_from") or []:
        for f in glob.glob(os.path.join(edition(e)["dir"], "source", "*.[sS][fF][mM]")):
            for m in re.findall(r"\\nd (.*?)\\nd\*", open(f, encoding="utf-8").read()):
                w = unicodedata.normalize("NFC", m).strip(" ,.;:!?")
                if w:
                    words.add(w)
    return words


def sfm_profile(p):
    """the team's SFM conventions: the first style edition's `sfm:` block (scripts/sfm_profile.py), the project's
    `sfm:` fields over it; {} when neither has one"""
    out = {}
    for e in p.get("style_from") or []:
        if edition(e).get("sfm"):
            out = dict(edition(e)["sfm"])
            break
    out.update(p.get("sfm") or {})
    return out


def bsb_layout(code):
    """{(c, v): 'p' | 'q'} for verses where the BSB starts a paragraph (p, m, pmo, pi, li) or a poetry line."""
    d = json.load(open(os.path.join(ROOT, "download", "BSB", f"{code.upper()}.usj"), encoding="utf-8"))
    out, c = {}, 0
    for node in d["content"]:
        if node.get("type") == "chapter":
            c = int(node["number"])
        elif node.get("type") == "para":
            first = next((x for x in node.get("content", []) if not (isinstance(x, str) and not x.strip())), None)
            if isinstance(first, dict) and first.get("type") == "verse":
                m = node.get("marker", "")
                kind = "q" if m.startswith("q") else "p" if m in ("p", "m", "pmo", "pi", "pi1", "li", "li1", "nb") else None
                if kind:
                    out[(c, int(re.match(r"\d+", first["number"])[0]))] = kind
    return out


def parse_draft(path):
    """[('title', s) | ('s', heading) | ('v', n, [(kind, text)])], kind 'text', 'q1', 'q2'."""
    items, cur = [], None
    for raw in open(path, encoding="utf-8").read().splitlines():
        line = raw.strip()
        if not line or line.startswith("!!<"):
            continue
        m = re.match(r"^===(.*)===$", line)
        if m:
            items.append(("title", m[1].strip()))
            continue
        m = re.match(r"^==(.*)==$", line)
        if m:
            items.append(("s", m[1].strip()))
            cur = None
            continue
        q = re.match(r"^//([12])\s*(.*)$", line)
        kind, line = (f"q{q[1]}", q[2]) if q else ("text", line)
        for i, part in enumerate(re.split(r"(?:^|\s)(v\d+)\s", " " + line)):
            if re.fullmatch(r"v\d+", part):
                cur = ("v", int(part[1:]), [])
                items.append(cur)
            elif part.strip() and cur:
                cur[2].append((kind, part.strip()))
    return items


def footnotes(path):
    out = {}
    if os.path.exists(path):
        for l in open(path, encoding="utf-8").read().splitlines():
            m = re.match(r"^v(\d+)\s+(.*?):\s+(.*)$", l.strip())
            if m:
                out.setdefault(int(m[1]), []).append((m[2], m[3]))
    return out


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] in ("-h", "--help"):
        raise SystemExit(__doc__)
    pname, code = a[0], a[1]
    opt = lambda n: a[a.index(n) + 1] if n in a else None
    p = project(pname)
    pd = project_dir(pname)
    drafts = sorted(glob.glob(os.path.join(pd, code, f"{code}[0-9][0-9][0-9].txt")))
    if len(a) > 2 and not a[2].startswith("--"):
        lo, _, hi = a[2].partition("-")
        rng = range(int(lo), int(hi or lo) + 1)
        drafts = [f for f in drafts if int(os.path.basename(f)[3:6]) in rng]
    if not drafts:
        raise SystemExit(f"no drafts of {code} in {os.path.relpath(pd, ROOT)}/{code}/")
    mine, frame = team_sfm(p, code)
    prof = sfm_profile(p)
    ftxt = open(frame, encoding="utf-8").read() if frame else ""
    norm = opt("--norm") or prof.get("normalization") or (
        "NFD" if ftxt and ftxt == unicodedata.normalize("NFD", ftxt) else "NFC")
    ot = BY_CODE[code][2] == "ot"
    numbering = opt("--numbering") or prof.get("versification")
    if not numbering:
        jon = next((f for f in glob.glob(os.path.join(os.path.dirname(frame or ""), "*")) if "JON" in os.path.basename(f)), None)
        numbering = "english" if jon and re.search(r"\\c 1\b.*?\\v 17\b", open(jon, encoding="utf-8").read(), re.S) else (
            "english" if not frame else "hebrew")
    layout = bsb_layout(code)
    status = {}
    sf = os.path.join(pd, "status.yaml")
    if os.path.exists(sf):
        import yaml
        status = yaml.safe_load(open(sf, encoding="utf-8")) or {}

    # header
    head, title = [], None
    if mine:
        for l in open(mine, encoding="utf-8").read().splitlines():
            m = re.match(r"\\(\w+)\b", l)
            if m and m[1] == "c":
                break
            if m and m[1] in KEEP:
                head.append(l)
    rows = []                                   # (c, v, para, heading, [(kind, text)], [footnotes])
    for f in drafts:
        hch = int(os.path.basename(f)[3:6])
        fn = footnotes(f[:-4] + "_footnotes.txt")
        pending_h = []
        for it in parse_draft(f):
            if it[0] == "title":
                title = title or re.sub(r",\s*\w+\s*\d+\s*$", "", it[1]).strip()
            elif it[0] == "s":
                pending_h.append(it[1])
            else:
                v = it[1]
                c, bv = (vrs.to_bsb(code, hch, v) if ot and numbering == "english" else (hch, v))
                if bv == "title":
                    rows.append((c, "title", None, pending_h, it[2], []))
                else:
                    para = "s" if pending_h else layout.get((c, bv) if numbering == "english" or not ot
                                                              else vrs.to_bsb(code, hch, v))
                    rows.append((c, int(bv), para, pending_h, it[2], [(hch, v, k, t) for k, t in fn.get(v, [])]))
                pending_h = []
    if not head:
        name, _, br = (title or BY_CODE[code][1]).partition(" (")
        idl = f"\\id {code.upper()}"
        if prof.get("id_line"):
            idl = prof["id_line"].replace("{BOOK}", code.upper())
        elif frame:
            idl += re.sub(rf"^\\id \w+", "", ftxt.splitlines()[0])
        head = [idl] + (["\\ide utf-8"] if prof.get("ide", True) else []) + [f"\\h {title or name}", f"\\toc1 {name}", f"\\toc2 {name}",
                f"\\toc3 {code.capitalize()}", f"\\mt1 {name}"] + ([f"\\mt2 ({br}"] if br else [])
    chs = sorted({r[0] for r in rows})
    st = sorted({str((status.get(code) or {}).get(c, "draft")) if isinstance(status.get(code), dict) else "draft" for c in chs})
    date = datetime.date.today().isoformat()
    rem = [f"\\rem Machine draft (make-tanakh, {pname}), translated from the "
           f"{'Hebrew' if ot else 'Greek'} with the BSB as a guide; chapters {chs[0]}–{chs[-1]}; status: {', '.join(st)}; "
           f"exported {date}. Not reviewed unless the status says so."]
    if ot and numbering == "english":
        rem.append("\\rem Verse numbers as in English Bibles (the drafts keep the Hebrew numbering).")
    head = head[:2] + rem + head[2:] if head[0].startswith("\\id") and len(head) > 1 and head[1].startswith("\\ide") \
        else head[:1] + rem + head[1:]
    hmark = prof.get("heading") or "s1"
    after_q = "m" if "m" in (prof.get("paragraphs") or ["m"]) else "p"
    fk = "fk" in (prof.get("footnotes") or "fr fk ft").split()

    out, cur_c, merged, mode = list(head), None, {}, None
    for c, v, para, hs, parts, fns in rows:
        merged.setdefault((c, v), []).append((para, hs, parts, fns))
    for (c, v), group in sorted(merged.items(), key=lambda x: (x[0][0], -1 if x[0][1] == "title" else x[0][1])):
        if c != cur_c:
            out.append(f"\\c {c}")
            cur_c, mode = c, None
        para = group[0][0]
        for h in group[0][1]:
            out.append(f"\\{hmark} {h}")
            mode = None
        parts = [pt for g in group for pt in g[2]]
        fns = [x for g in group for x in g[3]]
        if v == "title":
            out.append("\\d " + " ".join(t for _, t in parts))
            continue
        note = "".join(f"\\f + \\fr {c}:{v} \\fk {k}:\\ft {t}\\f*" if fk else f"\\f + \\fr {c}:{v} \\ft {k}: {t}\\f*"
                       for _, _, k, t in fns)
        # runs of the same kind: prose stays in the open paragraph, each poetry line its own \q line
        runs = []
        for k, t in parts:
            if runs and k == "text" and runs[-1][0] == "text":
                runs[-1][1].append(t)
            else:
                runs.append((k, [t]))
        for i, (k, ts) in enumerate(runs):
            text = " ".join(ts)
            lead = f"\\v {v} " if i == 0 else ""
            end = note if i == len(runs) - 1 else ""
            if k in ("q1", "q2"):
                out.append(f"\\{k} {lead}{text}{end}")
                mode = "q"
                continue
            if i == 0 and para == "q" and len(runs) == 1:
                out.append(f"\\q1 {lead}{text}{end}")          # poetry in the BSB, no line marks in the draft
                mode = "q"
                continue
            if mode != "p" or (i == 0 and para in ("s", "p")):
                out.append("\\p" if mode != "q" or i == 0 else f"\\{after_q}")
            out.append(f"{lead}{text}{end}" if lead else text)
            mode = "p"
    nd = set(prof["divine_name"]) if "divine_name" in prof else team_nd(p)
    if nd:                                      # the divine name marked as the team's files mark it
        rx = re.compile(r"(?<![\w\\])(" + "|".join(sorted(map(re.escape, nd), key=len, reverse=True)) + r")(?!\w)")
        out = out[:len(head)] + [rx.sub(r"\\nd \1\\nd*", unicodedata.normalize("NFC", l)) for l in out[len(head):]]
    usfm = unicodedata.normalize(norm, "\n".join(out) + "\n")

    if prof.get("file_pattern") and (mine or frame):
        stem, ext = os.path.splitext(prof["file_pattern"].replace("{nn}", f"{book_number(code):02d}").replace("{BOOK}", code.upper()))
        fname = f"{stem}-draft-{chs[0]}-{chs[-1]}{ext}"
        odir = opt("--out") or os.path.join(derived_dir(pname), "usfm")
    elif mine or frame:
        base = os.path.basename(mine or frame)
        m = re.match(rf"^(.*?)-\d\d[0-9A-Z]{{3}}-(.*?)(?: [\d-]+)?\.sfm$", base, re.I)
        fname = (f"{m[1]}-{book_number(code):02d}{code.upper()}-{m[2]}-draft-{chs[0]}-{chs[-1]}.sfm" if m
                 else f"{book_number(code):02d}{code.upper()}-draft-{chs[0]}-{chs[-1]}.SFM")
        odir = opt("--out") or os.path.join(derived_dir(pname), "usfm")
    else:
        fname = f"{book_number(code):02d}{code.upper()}-draft-{chs[0]}-{chs[-1]}.SFM"
        odir = opt("--out") or os.path.join(ROOT, "build", "usfm", pname.replace("/", "_"))
    os.makedirs(odir, exist_ok=True)
    path = os.path.join(odir, fname)
    # line endings as the team's files have them (Paratext on Windows: CRLF)
    eol = opt("--eol") or prof.get("line_endings") or ("crlf" if frame and b"\r\n" in open(frame, "rb").read() else "lf")
    open(path, "w", encoding="utf-8", newline="\r\n" if eol == "crlf" else "\n").write(usfm)

    nv = sum(1 for l in usfm.splitlines() if re.search(r"\\v \d+", l))
    want = len(merged) - sum(1 for k in merged if k[1] == "title")
    try:
        import usfmtc
        usfmtc.readFile(path)
        parsed = "parses in usfmtc"
    except ImportError:
        parsed = "usfmtc not installed: not parsed"
    except Exception as e:  # noqa: BLE001
        parsed = f"usfmtc error: {str(e)[:200]}"
    print(f"{os.path.relpath(path, ROOT)}: {len(chs)} chapter(s) {chs[0]}–{chs[-1]}, {nv} verses (expected {want}), "
          f"{norm}, {eol}, {numbering} numbering, frame {'the team’s book' if mine else 'built'}, conventions "
          f"{'from the sfm: block' if prof else 'detected from their files'}; {parsed}")


if __name__ == "__main__":
    main()
