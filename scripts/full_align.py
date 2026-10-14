#!/usr/bin/env python3
"""Full word alignments of a project's drafts in the bcv-commons format (lexeme-aligner's compact-alignments and
full-alignments-manual cards on Hugging Face): the one standard here, for script and agent alignments alike.

Numbers, never text:
  source   srcOrd = a CONTENT token's ordinal in _index/<BOOK>_keys.json (compact-alignments), its links in the main
           string; fnOrd = a FUNCTION token's ordinal in _index/<BOOK>_fn_keys.json, its links in the `fn` channel.
           A fused token (`a+b`, one lexeme over two MACULA nodes) is one ordinal.
  target   token positions in the draft verse's text, tokenized like compact-alignments (maximal runs of letters and
           marks; digits and punctuation separate), the verse marker and inline notes ({T: …}) left out.
  string   "ord:span ..." with spans `5`, `5-7` (contiguous), `5,9` (scattered); an unlinked ordinal is left out.

Working file, one per drafted chapter, next to the draft (export/<project>/<code>/<code>NNN.align):
    # full alignment, bcv-commons compact-alignments format (scripts/full_align.py)
    # text <sha256 of the chapter's verse texts, as hashed below>
    <verse>\t<main string>\t<fn string>\t<profile>
  profile: one character for the verse's links, from PROFILES (a = script:bridge_align, b = agent). The `text` line
  makes a stale file visible: when the draft changes, its alignment no longer matches.

The published layer, one file set per book, as on Hugging Face (`export` below):
    <iso[0]>/<iso>/<edition>+draft+bsb-add-books/<BOOK>_<hash>.json        main strings, parallel to _index/<BOOK>_lexemes.json
                                                 <BOOK>_<hash>.meta.json   channels fn, wp, fp (wx, rows, off: null)
                                                 _layer.json               attribution and the profile table
  <hash> = the last 5 hex characters of compact-alignments' book_content_hash: sha256 of "{c}:{v}:{text}" lines
  (translatable text only, ascending verses, joined by "\\n").

    python3 scripts/full_align.py check <project> [code]      the working files: stale, out of range, coverage
    python3 scripts/full_align.py export <project> [--out DIR] the layer (default build/align/)
"""
import hashlib, json, os, re, sys, unicodedata, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from books import BY_CODE  # noqa: E402

INDEX = os.path.join(ROOT, "download", "full-align", "_index")
HF_INDEX = "https://huggingface.co/datasets/bcv-commons/compact-alignments/resolve/main/_index"
UA = {"User-Agent": "bsb-add-books/1.0"}
NOTE = re.compile(r"\{[A-Z]:.*?\}", re.S)
MARK = re.compile(r"^v\d+\s+")
HEAD = "# full alignment, bcv-commons compact-alignments format (scripts/full_align.py)"
PROFILES = {"a": {"method": "script", "score": None, "prior": None, "extra": None, "attr": {"tool": "bridge_align"}},
            "b": {"method": "agent", "score": None, "prior": None, "extra": None, "attr": {}}}


def index(book, kind):
    """_index/<BOOK>_<kind>.json (lexemes, keys, fn, fn_keys), downloaded once."""
    path = os.path.join(INDEX, f"{book}_{kind}.json")
    if not os.path.exists(path):
        os.makedirs(INDEX, exist_ok=True)
        with urllib.request.urlopen(urllib.request.Request(f"{HF_INDEX}/{book}_{kind}.json", headers=UA), timeout=300) as r:
            open(path, "wb").write(r.read())
    return json.load(open(path, encoding="utf-8"))


def ordinals(book, ref):
    """{MACULA key: ('c', srcOrd) | ('f', fnOrd)} for one verse ("RUT 1:1")."""
    out = {}
    for kind, ch in (("keys", "c"), ("fn_keys", "f")):
        for o, k in enumerate(index(book, kind).get(ref, [])):
            for part in k.split("+") if k else []:
                out[part] = (ch, o)
    return out


def verse_text(raw):
    """The translatable text of a draft verse: no verse marker, no inline notes, single spaces."""
    return re.sub(r"\s+", " ", NOTE.sub(" ", MARK.sub("", raw.strip()))).strip()


def tokenize(text):
    """compact-alignments' tokenizer (usj_source.tokenize)."""
    toks, cur = [], []
    for ch in unicodedata.normalize("NFC", text):
        if unicodedata.combining(ch):
            continue
        if unicodedata.category(ch)[0] in ("L", "M"):
            cur.append(ch)
        elif cur:
            toks.append("".join(cur))
            cur = []
    if cur:
        toks.append("".join(cur))
    return toks


def text_hash(ch, verses):
    """The hash of one chapter (verses = [(v, text)]), as book_hash computes it for a book."""
    return book_hash([(ch, v, t) for v, t in verses])


def book_hash(rows):
    """rows = [(c, v, text)] of a book."""
    return hashlib.sha256("\n".join(f"{c}:{v}:{t}" for c, v, t in sorted(rows)).encode("utf-8")).hexdigest()


def span(ids):
    ids = sorted(set(ids))
    if len(ids) > 1 and ids == list(range(ids[0], ids[-1] + 1)):
        return f"{ids[0]}-{ids[-1]}"
    return ",".join(map(str, ids))


def parse(s):
    """"ord:span ..." -> {ord: [positions]}."""
    out = {}
    for e in (s or "").split():
        o, _, sp = e.partition(":")
        ids = []
        for part in sp.split(","):
            if "-" in part:
                a, b = part.split("-")
                ids += range(int(a), int(b) + 1)
            elif part.isdigit():
                ids.append(int(part))
        out[int(o)] = ids
    return out


def strings(links, ords):
    """links = {MACULA key: [target positions]} -> (main, fn, unplaced keys)."""
    c, f, miss = {}, {}, []
    for k, ids in links.items():
        if not ids:
            continue
        if k not in ords:
            miss.append(k)
            continue
        kind, o = ords[k]
        (c if kind == "c" else f).setdefault(o, []).extend(ids)
    fmt = lambda d: " ".join(f"{o}:{span(ids)}" for o, ids in sorted(d.items()))
    return fmt(c), fmt(f), miss


def write_chapter(path, ch, rows, verses):
    """rows = [(verse, main, fn, profile)]; verses = [(v, text)] the draft's."""
    with open(path, "w", encoding="utf-8") as w:
        w.write(f"{HEAD}\n# text {text_hash(ch, verses)}\n")
        for v, m, f, p in rows:
            w.write(f"{v}\t{m}\t{f}\t{p}\n")


def read_chapter(path):
    """(text hash, {verse: (main, fn, profile)})."""
    h, rows = None, {}
    for l in open(path, encoding="utf-8").read().splitlines():
        if l.startswith("# text "):
            h = l[7:].strip()
        elif l and not l.startswith("#"):
            parts = l.split("\t") + ["", "", ""]
            rows[int(parts[0])] = (parts[1], parts[2], parts[3] or "a")
    return h, rows


def draft_texts(path):
    """[(verse, text)] of a prose draft, by the same reading as bridge_align."""
    import bridge_align as BA
    return [(v, verse_text(raw)) for v, raw, _ in BA.draft_verses(path)[2]]


def chapters(pname, only=None):
    d = os.path.join(ROOT, "export", pname)
    for code in BY_CODE:
        if BY_CODE[code][2] != "ot" or (only and code != only) or not os.path.isdir(os.path.join(d, code)):
            continue
        for f in sorted(os.listdir(os.path.join(d, code))):
            m = re.fullmatch(rf"{code}(\d{{3}})\.txt", f)
            if m:
                yield code, int(m[1]), os.path.join(d, code, f), os.path.join(d, code, f"{code}{m[1]}.align")


def check(pname, only=None, quiet=False):
    """Problems (an ordinal or a position out of range) and warnings (a chapter without alignment, or stale: the
    draft changed since; rerun scripts/bridge_align.py or the agent's alignment step)."""
    problems, warns, tot = [], [], {"c": [0, 0], "f": [0, 0], "t": [0, 0]}
    for code, ch, draft, ap in chapters(pname, only):
        name = os.path.relpath(ap, ROOT)
        if not os.path.exists(ap):
            warns.append(f"{name}: missing")
            continue
        verses = draft_texts(draft)
        h, rows = read_chapter(ap)
        if h != text_hash(ch, verses):
            warns.append(f"{name}: stale (the draft changed since it was aligned)")
            continue
        book = code.upper()
        for v, t in verses:
            ref = f"{book} {ch}:{v}"
            ntok = len(tokenize(t))
            m, f, _ = rows.get(v, ("", "", "a"))
            M, F = parse(m), parse(f)
            nc, nf = len(index(book, "keys").get(ref, [])), len(index(book, "fn_keys").get(ref, []))
            for o, ids in list(M.items()) + [(-1 - o, ids) for o, ids in F.items()]:
                lim = nc if o >= 0 else nf
                oo = o if o >= 0 else -1 - o
                if oo >= lim:
                    problems.append(f"{name}: {ref}: ordinal {'c' if o >= 0 else 'f'}{oo} out of range ({lim})")
                bad = [i for i in ids if i >= ntok]
                if bad:
                    problems.append(f"{name}: {ref}: target position {bad[0]} out of range ({ntok} tokens)")
            tot["c"][0] += len(M); tot["c"][1] += nc
            tot["f"][0] += len(F); tot["f"][1] += nf
            tot["t"][0] += len({i for ids in list(M.values()) + list(F.values()) for i in ids}); tot["t"][1] += ntok
    if not quiet:
        pc = lambda k: f"{tot[k][0]}/{tot[k][1]} ({100 * tot[k][0] / max(tot[k][1], 1):.0f}%)"
        print(f"{pname}: content tokens linked {pc('c')}, function tokens {pc('f')}, draft tokens covered {pc('t')}; "
              + (f"{len(problems)} problems" if problems else "ok") + (f", {len(warns)} warnings" if warns else ""))
        for p in problems[:30] + [f"warn {w}" for w in warns[:30]]:
            print("  " + p)
    return problems


def iso_and_edition(pname):
    """compact-alignments path parts: the ISO 639-3 code (a dialect id falls back to the project's `language`), the edition."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from project import project
    lang, ed = pname.split("/")
    if not re.fullmatch(r"[a-z]{3}", lang):
        lang = str(project(pname).get("language", "")).split("-")[0]
    return lang, ed


def export(pname, out=None):
    iso, ed = iso_and_edition(pname)
    layer = f"{ed}+draft+bsb-add-books"
    d = os.path.join(out or os.path.join(ROOT, "build", "align"), iso[0], iso, layer)
    os.makedirs(d, exist_ok=True)
    by_book = {}
    for code, ch, draft, ap in chapters(pname):
        by_book.setdefault(code.upper(), []).append((ch, draft, ap))
    written = []
    for book, chs in by_book.items():
        refs = list(index(book, "lexemes").keys())
        main, fn, wp, fp = {}, {}, {}, {}
        text_rows = []
        for ch, draft, ap in chs:
            verses = draft_texts(draft)
            text_rows += [(ch, v, t) for v, t in verses]
            if not os.path.exists(ap):
                continue
            h, rows = read_chapter(ap)
            if h != text_hash(ch, verses):
                print(f"  skipped {os.path.relpath(ap, ROOT)}: stale")
                continue
            for v, (m, f, p) in rows.items():
                ref = f"{book} {ch}:{v}"
                main[ref], fn[ref] = m, f
                wp[ref] = p * len(m.split())
                fp[ref] = p * len(f.split())
        hx = book_hash(text_rows)
        for old in os.listdir(d):
            if old.startswith(book + "_") and old.endswith(".json"):
                os.remove(os.path.join(d, old))
        base = os.path.join(d, f"{book}_{hx[-5:]}")
        json.dump([main.get(r, "") for r in refs], open(base + ".json", "w", encoding="utf-8"), ensure_ascii=False)
        json.dump({"fn": [fn.get(r, "") for r in refs], "wp": [wp.get(r, "") for r in refs],
                   "fp": [fp.get(r, "") for r in refs], "wx": None, "rows": None, "off": None}, open(base + ".meta.json", "w", encoding="utf-8"), ensure_ascii=False)
        written.append(os.path.relpath(base + ".json", ROOT))
    json.dump({"version": 2, "layer": layer, "kind": "draft", "has_ids": False,
               "attribution": {"base_text": ed, "kind": "draft", "license": "CC0-1.0", "source": "bsb-add-books",
                               "versification": "org", "repo": "https://github.com/bcv-commons/bsb-add-books"},
               "profiles": PROFILES}, open(os.path.join(d, "_layer.json"), "w", encoding="utf-8"), indent=1)
    print(f"{pname}: {len(written)} books -> {os.path.relpath(d, ROOT)}/")
    return d


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("check", "export"):
        raise SystemExit(__doc__)
    if a[0] == "check":
        sys.exit(1 if check(a[1], a[2] if len(a) > 2 and not a[2].startswith("-") else None) else 0)
    export(a[1], os.path.join(ROOT, a[a.index("--out") + 1]) if "--out" in a else None)


if __name__ == "__main__":
    main()
