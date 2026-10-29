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
    <iso[0]>/<iso>/<edition>+auto+make-tanakh/<BOOK>_<hash>.json        main strings, parallel to _index/<BOOK>_lexemes.json
                                               <BOOK>_<hash>.meta.json   channels fn, wp, fp (wx, rows, off: null)
                                               _layer.json               attribution and the profile table
  <hash> = the first 8 hex characters of compact-alignments' text fingerprint v1 (text_fingerprint): per chapter the
  sha256 of the "{v}:{tokens}" lines, then the sha256 of the "{c}:{chapter digest}" lines
  (translatable text only, ascending verses, joined by "\\n").

    python3 scripts/full_align.py listing <project> <code> <ch>  numbered Hebrew and draft tokens per verse, for the agent
                                                                 that aligns (writes the script's proposal first if needed)
    python3 scripts/full_align.py prompt <project> <code> <ch>   a fresh agent's prompt to align an existing chapter
    python3 scripts/full_align.py check <project> [<code> [<ch>]] the working files: stale, out of range, coverage
    python3 scripts/full_align.py export <project> [--out DIR]   the layer (default build/align/)

The agent's step (STEP below, in every OT chapter prompt): run `listing`, correct the chapter's .align line by line
from it, mark each verse it checked with profile b, then `check`.

The tagged format (an agent's interim file, `<code>NNN.tagged`, git-ignored): the draft
in its usual layout with the Hebrew token numbers right after the letters of each word, `Synerzyt^2,3, wo^4 d^5`.
The numbers count every token of the verse in the compact-alignments index (content and function) in source order,
from 0 (`numbering`). Two more marks (lexeme-aligner's notation): `^-7` between words, a token with no target
word at its slot (at the verse's end: no particular slot), and `word^+5` / `word^+`, a word added for token 5 or for the
grammar. An unmarked word or token is not decided. In the .align they become lexeme-aligner's notation: `!ords` and
`u<ord>[@pos]` (the @ only where the slot differs from the default rule: after the last target word of the nearest
preceding linked token), and `+pos[>ord]` at the end of fn.
    python3 scripts/full_align.py tag <project> <code> <ch>     prose + .align -> <code>NNN.tagged
    python3 scripts/full_align.py split <project> <code> <ch>   <code>NNN.tagged -> prose .txt + .align (profile b),
                                                                and the content tokens left undecided per verse
"""
import collections, functools, hashlib, json, os, re, sys, unicodedata, urllib.request

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
from books import BY_CODE  # noqa: E402
from project import project_dir, project_rel  # noqa: E402

INDEX = os.path.join(ROOT, "download", "full-align", "_index")
HF_INDEX = "https://huggingface.co/datasets/bcv-commons/compact-alignments/resolve/main/_index"
UA = {"User-Agent": "make-tanakh/1.0"}
NOTE = re.compile(r"\{[A-Z]:.*?\}", re.S)
MARK = re.compile(r"^v\d+\s+")
HEAD = "# full alignment, bcv-commons compact-alignments format (scripts/full_align.py)"
PROFILES = {"a": {"method": "script", "score": None, "prior": None, "extra": None, "attr": {"tool": "bridge_align"}},
            "b": {"method": "agent", "score": None, "prior": None, "extra": None, "attr": {}}}


def _download(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                data = r.read()
            break
        except OSError:
            if attempt == 3:
                raise
    open(path + ".part", "wb").write(data)  # never leave a half-written cache file
    os.replace(path + ".part", path)


@functools.lru_cache(maxsize=None)
def source_index():
    """compact-alignments' _index/_source.json: per book the SHA-256 of each index file, and spine_index_sha256 (what a
    layer records it was built against). Re-read at most once a day."""
    import time
    path = os.path.join(INDEX, "_source.json")
    if not os.path.exists(path) or time.time() - os.path.getmtime(path) > 24 * 3600:
        try:
            _download(f"{HF_INDEX}/_source.json", path)
        except OSError:
            if not os.path.exists(path):
                return {}
    return json.load(open(path, encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def index(book, kind):
    """_index/<BOOK>_<kind>.json (lexemes, keys, fn, fn_keys), downloaded once and checked against the published
    _source.json: a cached file whose SHA-256 differs is downloaded again (the index is republished now and then, and a
    stale copy would give wrong ordinals without any error)."""
    import collections, hashlib
    path = os.path.join(INDEX, f"{book}_{kind}.json")
    want = (source_index().get("books", {}).get(book) or {}).get(f"{kind}_sha256")
    if os.path.exists(path) and want and hashlib.sha256(open(path, "rb").read()).hexdigest() != want:
        print(f"  {book}_{kind}.json: the published index changed; downloading it again", file=sys.stderr)
        os.remove(path)
    if not os.path.exists(path):
        _download(f"{HF_INDEX}/{book}_{kind}.json", path)
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


TOKENIZER_VERSION = 2   # compact-alignments' manifest.json tokenizer_version
TEXT_FP_VERSION = 1     # its text_fp_version (text_fingerprint)
MYA_KEEP = {0x1039, 0x103A}   # Myanmar virama and asat: they carry the syllable, not optional marks
MYA_CONS = [(0x1000, 0x102A), (0x103F, 0x103F), (0x1050, 0x1055), (0x105A, 0x105D), (0x1061, 0x1061), (0x1065, 0x1066),
            (0x106E, 0x1070), (0x1075, 0x1081), (0x108E, 0x108E), (0xA9E0, 0xA9E4), (0xA9E7, 0xA9EF), (0xA9FA, 0xA9FE),
            (0xAA60, 0xAA6F), (0xAA71, 0xAA76), (0xAA7A, 0xAA7A), (0xAA7E, 0xAA7F)]


def _mya(cp):
    return any(a <= cp <= b for a, b in MYA_CONS)


def _cjk(cp):
    if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0xF900 <= cp <= 0xFAFF:
        return "han"
    return "hira" if 0x3040 <= cp <= 0x309F else "kata" if 0x30A0 <= cp <= 0x30FF else None


def _unspaced(tok):
    """a run of letters in a script written without spaces, segmented as compact-alignments does: Myanmar by syllable
    (one starts at a consonant or U+1031, not after a virama, U+1031 or an asat), Han one character a token, Japanese at
    the kana/script boundaries; any other run is one token"""
    cps = [ord(c) for c in tok]
    if any(_mya(c) for c in cps):
        out, cur = [], ""
        for i, c in enumerate(cps):
            prev = cps[i - 1] if i else 0
            if (_mya(c) or c == 0x1031) and cur and prev not in (0x1039, 0x1031, 0x103A):
                out.append(cur)
                cur = ""
            cur += chr(c)
        return out + [cur] if cur else out
    if not any(_cjk(c) for c in cps):
        return [tok]
    out, cur, cls_ = [], "", None
    for ch in tok:
        cl = _cjk(ord(ch))
        if cl == "han":
            if cur:
                out.append(cur)
                cur, cls_ = "", None
            out.append(ch)
        elif cl != cls_ and cur:
            out.append(cur)
            cur, cls_ = ch, cl
        else:
            cur, cls_ = cur + ch, cl
    return out + [cur] if cur else out


def dropped(ch):
    """a character tokenizer v2 drops before it reads words: a mark with a combining class (not Myanmar's virama and
    asat) or a variation selector"""
    cp = ord(ch)
    return bool(unicodedata.combining(ch) and cp not in MYA_KEEP) or 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF


def tokenize(text):
    """compact-alignments' tokenizer v2 (tokenize.js, usj_source.tokenize): marks with a combining class dropped (not
    Myanmar's virama and asat), variation selectors dropped, then maximal runs of letters and marks; punctuation, white
    space and digits separate; scripts without spaces segmented by rule (_unspaced)."""
    toks, cur = [], []
    for ch in unicodedata.normalize("NFC", text):
        if dropped(ch):
            continue
        if unicodedata.category(ch)[0] in ("L", "M"):
            cur.append(ch)
        elif cur:
            toks += _unspaced("".join(cur))
            cur = []
    if cur:
        toks += _unspaced("".join(cur))
    return toks


def text_fingerprint(rows):
    """compact-alignments' text fingerprint v1 of a book, rows = [(c, v, text)] in the edition's own numbering (a bridged
    verse under its first number), translatable text only: (book digest, {c: chapter digest}). A verse line is
    "{v}:{tokens joined by one space}" (a verse without tokens left out); a chapter is the SHA-256 of its verse lines in
    order joined by newlines; the book the SHA-256 of the "{c}:{chapter digest}" lines. File names carry the book
    digest's first 8 hex characters: <BOOK>_<fp[:8]>.json."""
    by = collections.defaultdict(list)
    for c, v, t in sorted(rows, key=lambda r: (int(r[0]), int(r[1]))):
        toks = tokenize(t)
        if toks:
            by[int(c)].append(f"{int(v)}:{' '.join(toks)}")
    sha = lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest()
    chapters = {c: sha("\n".join(ls)) for c, ls in by.items()}
    return sha("\n".join(f"{c}:{chapters[c]}" for c in sorted(chapters))), chapters


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


def ids_of(sp):
    """"4-5,9" -> [4, 5, 9]"""
    ids = []
    for part in (sp or "").split(","):
        if "-" in part and not part.startswith("-"):
            a, b = part.split("-")
            ids += range(int(a), int(b) + 1)
        elif part.lstrip("-").isdigit():
            ids.append(int(part))
    return ids


def decisions(s):
    """The decision entries of a main or fn string (lexeme-aligner's notation): !<ords> (no target word),
    u<ord>[@<pos>] (untranslated, its slot), e<ord>[@<pos>] (rendered elsewhere), +<pos>[><ord>] (added target words, in
    fn; >ord a content token, >f<ord> a function token).
    -> {"none": [ord], "u": {ord: slot|None}, "e": {ord: slot|None}, "plus": [(pos, ("c"|"f", ord) | None)]}"""
    out = {"none": [], "u": {}, "e": {}, "plus": []}
    for e in (s or "").split():
        if e.startswith("!"):
            out["none"] += ids_of(e[1:])
        elif e[0] in "ue" and e[1:2].isdigit():
            for item in e[1:].split(","):
                o, _, slot = item.partition("@")
                out[e[0]][int(o)] = int(slot) if slot else None
        elif e.startswith("+"):
            for item in e[1:].split(","):
                pos, _, o = item.partition(">")
                owner = (("f", int(o[1:])) if o.startswith("f") else ("c", int(o))) if o else None
                out["plus"] += [(i, owner) for i in ids_of(pos)]
    return out


def parse(s):
    """"ord:span ..." -> {ord: [positions]}; the decision entries (!, u, e, +; decisions()) are left out."""
    out = {}
    for e in (s or "").split():
        if not e[:1].isdigit():
            continue
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


def chapters(pname, only=None, ch=None):
    d = project_dir(pname)
    for code in BY_CODE:
        if (only and code != only) or not os.path.isdir(os.path.join(d, code)):
            continue
        for f in sorted(os.listdir(os.path.join(d, code))):
            m = re.fullmatch(rf"{code}(\d{{3}})\.txt", f)
            if m and (ch is None or int(m[1]) == ch):
                yield code, int(m[1]), os.path.join(d, code, f), os.path.join(d, code, f"{code}{m[1]}.align")


def check(pname, only=None, quiet=False, ch=None):
    """Problems (an ordinal or a position out of range) and warnings (a chapter without alignment, or stale: the
    draft changed since; rerun scripts/bridge_align.py or the agent's alignment step)."""
    problems, warns, tot = [], [], {"c": [0, 0], "f": [0, 0], "t": [0, 0], "d": [0, 0], "v": [0, 0]}
    shared = 0  # function links whose words a content link also claims: a sign of over-linking (and with וַ -> the verb),
    # though some is right (a Danish article written as an ending renders noun and הַ alike)
    for code, ch, draft, ap in chapters(pname, only, ch):
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
        slotless = slotted = 0
        for v, t in verses:
            ref = f"{book} {ch}:{v}"
            ntok = len(tokenize(t))
            if v not in rows:
                problems.append(f"{name}: {ref}: no line for this verse")
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
            dm, df = decisions(m), decisions(f)
            slotless += len(dm["none"]) + len(df["none"])
            slotted += len(dm["u"]) + len(df["u"]) + len(dm["e"]) + len(df["e"])
            none_c = set(dm["none"]) | set(dm["u"]) | set(dm["e"])
            none_f = set(df["none"]) | set(df["u"]) | set(df["e"])
            for o, lim, kind in [(o, nc, "c") for o in none_c] + [(o, nf, "f") for o in none_f]:
                if o >= lim:
                    problems.append(f"{name}: {ref}: ordinal {kind}{o} (no target word) out of range ({lim})")
            plus = {pos for pos, _ in df["plus"] + dm["plus"]}
            if any(pos >= ntok for pos in plus):
                problems.append(f"{name}: {ref}: an added target word out of range ({ntok} tokens)")
            content = {i for ids in M.values() for i in ids}
            shared += sum(1 for ids in F.values() if ids and all(i in content for i in ids))
            tot["c"][0] += len(M); tot["c"][1] += nc
            tot["f"][0] += len(F); tot["f"][1] += nf
            covered = {i for ids in list(M.values()) + list(F.values()) for i in ids} | plus
            tot["t"][0] += len(covered); tot["t"][1] += ntok
            decided = len(set(M) | none_c) + len(set(F) | none_f)
            tot["d"][0] += decided; tot["d"][1] += nc + nf
            tot["v"][0] += decided == nc + nf and len(covered) >= ntok; tot["v"][1] += 1
        if slotless >= 5 and slotless * 3 > slotless + slotted:   # "no particular place" should be rare
            warns.append(f"{name}: {slotless} of {slotless + slotted} unrendered tokens have no slot (at the verse end); "
                         "almost every one has a place in the target")
    if not quiet:
        pc = lambda k: f"{tot[k][0]}/{tot[k][1]} ({100 * tot[k][0] / max(tot[k][1], 1):.0f}%)"
        print(f"{pname}: content tokens linked {pc('c')}, function tokens {pc('f')} ({100 * shared / max(tot['f'][0], 1):.0f}% "
              "on a content word's words: compare within a language; high where affixes render them, else over-linking), "
              f"draft tokens covered {pc('t')}; source tokens decided (linked or marked as having no word) {pc('d')}, "
              f"verses complete {pc('v')}; "
              + (f"{len(problems)} problems" if problems else "ok") + (f", {len(warns)} warnings" if warns else ""))
        for p in problems[:30] + [f"warn {w}" for w in warns[:30]]:
            print("  " + p)
    return problems


TAG = re.compile(r"\^(\d+(?:,\d+)*)")                    # word^5, word^5,6: the word renders these tokens
ADDED = re.compile(r"\^\+(\d+)?")                         # word^+5: added for token 5; word^+: added for the grammar
DROP = re.compile(r"\^-(\d+(?:,\d+)*)")                   # ^-7 between words: no word for token 7, its slot is here;
                                                           #   at the verse's end: no word, no particular slot


def strip_tags(text):
    """The tagged text without its marks: the prose draft."""
    text = re.sub(r"[ \t]+\^-\d+(?:,\d+)*", "", text)                    # a drop marker after a word or a space
    text = re.sub(r"(?m)^\^-\d+(?:,\d+)*[ \t]*", "", text)              # one at the start of a line
    return TAG.sub("", ADDED.sub("", text))
VMARK = re.compile(r"(?<![\w>.])v(\d+)(?=\s)")


def numbering(book, ref):
    """The verse-local token numbers of the tagged format: every token of the compact-alignments index (content and
    function) in source order, numbered 0, 1, 2 ... -> [(n, 'c'|'f', ordinal, [MACULA keys])]."""
    toks = []
    for kind, c in (("keys", "c"), ("fn_keys", "f")):
        for o, k in enumerate(index(book, kind).get(ref, [])):
            parts = k.split("+") if k else []
            if parts:
                toks.append((parts[0], c, o, parts))
    return [(n, c, o, parts) for n, (_, c, o, parts) in enumerate(sorted(toks))]


def word_groups(text, toks):
    """The written words of a file: runs of tokens of one verse with no whitespace between them ("man’s" = man + s,
    "daughters-in-law" = three tokens). -> {(verse, start): [(verse, start) of every token of its word, in order]}"""
    groups, cur = {}, []
    for t in toks:
        if cur and cur[-1][0] == t[0] and not re.search(r"\s", text[cur[-1][2]:t[1]]):
            cur.append(t)
        else:
            cur = [t]
        for u in cur:
            groups[(u[0], u[1])] = [(x[0], x[1]) for x in cur]
    return groups


def file_tokens(text):
    """The translatable tokens of a draft file in order, as [(verse, start, end)] in the file text: letter runs
    outside header lines, titles, headings and inline notes, the verse markers left out (as draft_verses and
    tokens_of read them). Tags (^n) and digits are separators, so a tagged file gives the same tokens."""
    out, verse, pos = [], None, 0
    flat = list(text)
    for m in NOTE.finditer(text):  # notes may wrap over lines
        flat[m.start():m.end()] = [c if c == "\n" else " " for c in text[m.start():m.end()]]
    flat = "".join(flat)
    for line in flat.splitlines(keepends=True):
        body = line.rstrip("\n")
        if body.startswith("!!<") or re.match(r"^==.*==\s*$", body):
            pos += len(line)
            continue
        blank = list(body)
        marks = {m.start(): (m.end(), int(m[1])) for m in VMARK.finditer("".join(blank) + " ")}  # a marker may end the line
        i, cur = 0, None
        while i <= len(blank):
            if i in marks and cur is None:
                end, verse = marks[i]
                i = end
                continue
            ch = blank[i] if i < len(blank) else " "
            if unicodedata.category(ch)[0] in ("L", "M"):
                cur = i if cur is None else cur
            elif cur is not None:
                if verse is not None:
                    out.append((verse, pos + cur, pos + i))
                cur = None
            i += 1
        pos += len(line)
    return out


def tag(pname, code, ch):
    """prose draft + its .align -> the tagged text (verse-local numbers after the words: ^n links, ^+n / ^+ added words,
    ^-n unrendered tokens at their slot, or at the verse's end when they have none), and the profile per verse.
    tag -> split gives the .align back; a slot equal to the default rule comes back without its @, as stored."""
    draft = os.path.join(project_dir(pname), code, f"{code}{ch:03d}.txt")
    text = open(draft, encoding="utf-8").read()
    h, rows = read_chapter(draft[:-4] + ".align")
    if h != text_hash(ch, draft_texts(draft)):
        raise SystemExit(f"{os.path.relpath(draft, ROOT)}: the .align is stale; realign first")
    book = code.upper()
    toks = file_tokens(text)
    nums, plus, drop_at, drop_end = {}, {}, {}, {}   # (verse, token index) -> [n] | "+n"/"+" | [n]; verse -> [n]
    for v, (m, f, _) in rows.items():
        numb = numbering(book, f"{book} {ch}:{v}")
        back = {(c, o): n for n, c, o, _ in numb}
        linked = {}
        for c, st in (("c", m), ("f", f)):
            for o, ids in parse(st).items():
                linked.setdefault(back[(c, o)], []).extend(ids)
                for i in ids:
                    nums.setdefault((v, i), []).append(back[(c, o)])
        for c, st in (("c", m), ("f", f)):
            d = decisions(st)
            for o in d["none"]:
                drop_end.setdefault(v, []).append(back[(c, o)])
            for kind in ("u", "e"):
                for o, slot in d[kind].items():
                    n = back[(c, o)]
                    drop_at.setdefault((v, default_slot(n, linked) if slot is None else slot), []).append(n)
            for pos, o in d["plus"]:
                plus[(v, pos)] = f"+{back[o]}" if o is not None else "+"
                if o is not None:                      # the default slot rule counts the + words that name a token
                    linked.setdefault(back[o], []).append(pos)
    out, last, k, first_of = [], 0, {}, {}
    vlast = {}
    for v, a, b in toks:
        vlast[v] = b
    pos = {}
    for v, a, b in toks:
        pos[(v, a)] = k.get(v, 0)
        k[v] = pos[(v, a)] + 1
    group = word_groups(text, toks)

    def mark(v, i):
        return ("n", tuple(sorted(set(nums[(v, i)])))) if (v, i) in nums else ("+", plus[(v, i)]) if (v, i) in plus else None

    def same_word_mark(v, a):
        """the token is not its written word's last, and every token of the word has the same mark: write it once, after
        the word (split gives it to every token of the word)"""
        g = group[(v, a)]
        if g[-1] == (v, a):
            return False
        ms = {mark(v, pos[x]) for x in g}
        return len(ms) == 1 and None not in ms and not any((v, pos[x]) in drop_at for x in g[:-1])
    k = {}
    for v, a, b in toks:
        i = k.get(v, 0)
        k[v] = i + 1
        if i == 0 and (v, -1) in drop_at:            # slot -1: right before the verse's first word
            out.append(text[last:a] + "^-" + ",".join(map(str, sorted(drop_at[(v, -1)]))) + " ")
            last = a
        out.append(text[last:b])
        if same_word_mark(v, a):
            last = b
            continue
        if (v, i) in nums:
            out.append("^" + ",".join(map(str, sorted(set(nums[(v, i)])))))
        elif (v, i) in plus:
            out.append("^" + plus[(v, i)])
        if (v, i) in drop_at:
            out.append(" ^-" + ",".join(map(str, sorted(drop_at[(v, i)]))))
        if b == vlast[v] and v in drop_end:            # no particular slot: at the verse's end
            out.append(" ^-" + ",".join(map(str, sorted(drop_end[v]))))
        last = b
    out.append(text[last:])
    return "".join(out), {v: r[2] for v, r in rows.items()}


def default_slot(n, linked):
    """lexeme-aligner's default slot of an unrendered source token n: after the last target word of the nearest preceding
    source token that shows target words (-1: the verse start). linked = {source number: [target positions]}: its links
    and the + words that name it (`+pos>ord`), all a reader of the strings sees (their compare_slots.py)."""
    before = [m for m in linked if m < n and linked[m]]
    return max(linked[max(before)]) if before else -1


def split(pname, code, ch, profile="b", write=True, tagged=None):
    """The tagged file -> the prose draft (marks removed) and the .align (profile `profile`) in lexeme-aligner's notation:
    links; !/u for source tokens with no target word (u with @slot only where it differs from the default rule); + for
    added target words (in fn; >ord: the content token they serve). Returns the report: problems (marks in the wrong
    place, unknown numbers, a token both linked and dropped), per verse the content tokens left undecided, and the rows."""
    base = os.path.join(project_dir(pname), code, f"{code}{ch:03d}")
    tagged = tagged if tagged is not None else open(base + ".tagged", encoding="utf-8").read()
    problems, untagged = [], {}
    prose = strip_tags(tagged)
    if "^" in prose:
        n = prose.index("^")
        problems.append("a ^ that is no mark (^5 or ^+5 / ^+ right after a word, ^-5 between words): "
                        f"…{prose[max(0, n - 20):n + 10]}…")
    toks = file_tokens(tagged)
    ends = {b_: (v, a_) for v, a_, b_ in toks}
    idx, k = {}, {}
    for v, a_, b_ in toks:
        idx[(v, a_)] = k.get(v, 0)
        k[v] = idx[(v, a_)] + 1
    book = code.upper()
    nums = {}

    def num(v):
        if v not in nums:
            nums[v] = {n: (c, o) for n, c, o, _ in numbering(book, f"{book} {ch}:{v}")}
        return nums[v]
    links, added, drops = {}, {}, {}           # verse -> {(c, o): [pos]} | [(pos, n|None)] | [(n, slot|None)]
    group = word_groups(tagged, toks)
    own = {ends[m.start()] for rx in (TAG, ADDED) for m in rx.finditer(tagged) if m.start() in ends}

    def word_of(v, a_):
        """the token and the tokens of its written word that carry no mark of their own"""
        return [g for g in group[(v, a_)] if g == (v, a_) or g not in own]
    for m in TAG.finditer(tagged):
        if m.start() not in ends:
            problems.append(f"tag ^{m[1]} not right after the letters of a word: …{tagged[max(0, m.start() - 20):m.end()]}…")
            continue
        v, a_ = ends[m.start()]
        for n in map(int, m[1].split(",")):
            if n not in num(v):
                problems.append(f"v{v}: ^{n} is not a token number of the verse (0-{len(num(v)) - 1})")
                continue
            for g in word_of(v, a_):
                links.setdefault(v, {}).setdefault(num(v)[n], []).append(idx[g])
    for m in ADDED.finditer(tagged):
        if m.start() not in ends:
            problems.append(f"^+{m[1] or ''} not right after the letters of a word: …{tagged[max(0, m.start() - 20):m.end()]}…")
            continue
        v, a_ = ends[m.start()]
        n = int(m[1]) if m[1] else None
        if n is not None and n not in num(v):
            problems.append(f"v{v}: ^+{n}: {n} is not a token number of the verse")
            continue
        for g in word_of(v, a_):
            added.setdefault(v, []).append((idx[g], n))
    marks = sorted((mm.start(), int(mm[1])) for mm in VMARK.finditer(tagged))
    for m in DROP.finditer(tagged):
        vm = [vv for at, vv in marks if at < m.start()]
        if not vm:
            problems.append(f"^-{m[1]} before the first verse")
            continue
        v = vm[-1]
        in_v = [t for t in toks if t[0] == v]
        before = [t for t in in_v if t[2] <= m.start()]
        after = [t for t in in_v if t[1] >= m.end()]
        slot = None if not after else (idx[(v, before[-1][1])] if before else -1)    # at the verse's end: no slot
        for n in map(int, m[1].split(",")):
            if n not in num(v):
                problems.append(f"v{v}: ^-{n}: {n} is not a token number of the verse")
                continue
            drops.setdefault(v, []).append((n, slot))
    if write and not problems:
        open(base + ".txt", "w", encoding="utf-8").write(prose)
    verses = draft_texts(base + ".txt") if write and not problems else None
    rows = []
    for v in sorted({t[0] for t in toks}):
        L, A, D = links.get(v, {}), added.get(v, []), drops.get(v, [])
        linked = {n: list(L[co]) for n, co in num(v).items() if co in L}
        for pos, n in A:
            if n is not None:
                linked.setdefault(n, []).append(pos)
        both = sorted({n for n, _ in D} & {n for n, co in num(v).items() if co in L})
        if both:
            problems.append(f"v{v}: token {', '.join(map(str, both))} both linked and dropped (^-)")
        parts = {"c": [f"{o}:{span(ids)}" for (cc, o), ids in sorted(L.items()) if cc == "c"],
                 "f": [f"{o}:{span(ids)}" for (cc, o), ids in sorted(L.items()) if cc == "f"]}
        for c in ("c", "f"):
            none = [num(v)[n][1] for n, slot in D if slot is None and num(v)[n][0] == c]
            if none:
                parts[c].append("!" + span(none))
            u = sorted((num(v)[n][1], slot, default_slot(n, linked)) for n, slot in D if slot is not None and num(v)[n][0] == c)
            if u:
                parts[c].append("u" + ",".join(f"{o}@{slot}" if slot != dflt else f"{o}" for o, slot, dflt in u))
        if A:
            owner = lambda n: "" if n is None else f">{num(v)[n][1]}" if num(v)[n][0] == "c" else f">f{num(v)[n][1]}"
            parts["f"].append("+" + ",".join(f"{pos}{owner(n)}" for pos, n in sorted(A, key=lambda x: x[0])))
        rows.append((v, " ".join(parts["c"]), " ".join(parts["f"]), profile if (L or A or D) else "a"))
        decided = {n for n, co in num(v).items() if co in L} | {n for n, _ in D}   # an added word naming n decides nothing
        miss = [n if c == "c" else f"{n}f" for n, c, o, _ in numbering(book, f"{book} {ch}:{v}") if n not in decided]
        if miss:
            untagged[v] = miss
    if write and not problems:
        write_chapter(base + ".align", ch, rows, verses)
    return problems, untagged, rows


POINTS = re.compile(r"[\u0591-\u05AF\u05BD\u05C0\u05C3-\u05C6]")  # accents and marks; vowels and dagesh stay


def listing(pname, code, ch):
    """The aligning agent's sheet: per verse the Hebrew (NT: Greek) tokens in order with their ordinals (cN content,
    fN function), lemma gloss; the draft's tokens numbered; the current .align line."""
    import bridge_align as BA, align as AL
    draft = os.path.join(project_dir(pname), code, f"{code}{ch:03d}.txt")
    ap = draft[:-4] + ".align"
    verses = BA.draft_verses(draft)[2]
    texts = [(v, verse_text(raw)) for v, raw, _ in verses]
    if not os.path.exists(ap) or read_chapter(ap)[0] != text_hash(ch, texts):
        BA.build(pname, code, ch)  # the script's proposal (profile a), on the current draft
    _, rows = read_chapter(ap)
    book = code.upper()
    sc = AL.scaffold(code, ch)["tokens"]
    by_key = {t["key"]: t for t in sc}
    lab_, lang_ = ("gr", "Greek") if BY_CODE[code][2] == "nt" else ("he", "Hebrew")
    out = [f"# {book} {ch}: alignment sheet for {os.path.relpath(ap, ROOT)} (scripts/full_align.py; numbers as in the file)",
           f"# {lab_}: {lang_} tokens in order, cN = content ordinal (main column), fN = function ordinal (fn column), with a gloss",
           "# dr: the draft's tokens, numbered; now: the file's line (main | fn | profile)"]
    for v, t in texts:
        ref = f"{book} {ch}:{v}"
        lab = {}
        for kind, c in (("keys", "c"), ("fn_keys", "f")):
            for o, k in enumerate(index(book, kind).get(ref, [])):
                parts = k.split("+") if k else []
                if parts:
                    lab[parts[0]] = (f"{c}{o}", parts)
        he = []
        for k in sorted(lab):
            name, parts = lab[k]
            word = "+".join(POINTS.sub("", by_key.get(x, {}).get("text", "")) for x in parts) or "?"  # + = one token over two words
            gl = (by_key.get(parts[0], {}).get("gloss") or "").replace(" ", "_")
            he.append(f"{name} {word} {gl}".rstrip())
        m, f, p = rows.get(v, ("", "", "a"))
        out += [f"v{v}", f" {lab_}: " + " · ".join(he), " dr: " + " ".join(f"{i} {w}" for i, w in enumerate(tokenize(t))),
                f" now: {m} | {f} | {p}"]
    return "\n".join(out)


STEP = """- **Word alignment** (last step, after the checks, when the draft text is final): run
  `python3 scripts/full_align.py listing {project} {code} {chapter}`. It writes a first alignment by script into
  `{pdir}/{code}/{code}{nnn}.align` and prints a sheet: per verse the Hebrew tokens (`cN` content, `fN`
  function words: prefixes, article, object marker, suffixes) and your draft's words, numbered. Correct the file
  line by line; each line is `verse<TAB>main<TAB>fn<TAB>profile`:
  - main: `cN` links as `N:span` (`0:3` = c0 is draft word 3; `5:7-8` contiguous; `4:2,6` scattered), ascending N;
  - fn: the same for `fN`;
  - every draft word that renders a Hebrew token goes in that token's span, function words included (»and« with
    וַ, »in« with בְּ, a pronoun with its suffix); a draft word with no Hebrew token of its own (added for
    grammar) goes into the span of the content word it belongs to; a Hebrew token with no draft word is left out;
    one draft word rendering two tokens is listed under both;
  - set the profile to `b` on every verse you have checked, changed or not.
  Keep the lines short: numbers only, no words, no comments. Then run
  `python3 scripts/full_align.py check {project} {code} {chapter}` until it says ok. Don't change the draft after
  this step (the file would no longer match it); if you must, run `listing` again and redo the changed verses."""


ALONE = """Work in {root}. The draft `{pdir}/{code}/{code}{nnn}.txt` ({language}) is final; your only task is
its word alignment to the Hebrew. Don't change the draft or any other file than the .align. The Hebrew of the
chapter is `orig/heb/{code}{nnn}.txt` if you need context; don't open other translations, `import/`, `download/`
or `scratch/`.

{step}

Report in under 60 words: verses changed from the script's proposal (about how many), anything hard to align."""


def prompt(pname, code, ch):
    """A prompt for a fresh agent that aligns an existing chapter (one whose drafting agent left no alignment)."""
    from project import project
    p = project(pname)
    alone = greek(ALONE.replace("orig/heb/", "orig/grc/")) if BY_CODE[code][2] == "nt" else ALONE
    return alone.format(root=ROOT, project=pname, pdir=project_rel(pname), code=code, nnn=f"{ch:03d}", language=p.get("language_name"),
                        step=step(pname, code, ch).replace("- **Word alignment** (last step, after the checks, when the "
                                                           "draft text is final): run", "Run").replace("your draft's", "the draft's"))


TAGGED_SOURCE_LEAN = """
- `{pdir}/_learn/packs/{code}{nnn}.pkg.md`: the **clause packages**, one block per Hebrew clause line in
  the order of `{orig}`: each token with its number (`7 וַ and · 8 יְהִי`; function words with a gloss), and under `had:` what this project wrote
  before for those words and the store's decisions. The numbers are what you tag your words with."""

TAGGED_SOURCE = """
- `{pdir}/_learn/packs/{code}{nnn}.pkg.md`: the **clause packages**, one block per Hebrew clause line in
  the order of `{orig}`: each token with its number (`7 וַ and · 8 יְהִי there_was [q.wyq.3ms]`), gloss, verb form and
  the referent of pronouns and suffixes (`ref=man(14)`); the BSB words that render the tokens (`famine^9`); and
  under `had:` what this project wrote before for those words (and the store's decisions, and for an unknown
  language the NT's words for them). Read each block as you translate its clause."""

TAGGED_WRITE = """
- **Write the draft tagged:** write it to `{pdir}/{code}/{code}{nnn}.tagged`, in the draft's usual layout,
  with the package's token numbers right after the letters of each word that renders Hebrew tokens:
  `Synerzyt^2,3, wo^4 d^5 Richter^6 im^10 Land^11 regiert^4 hei^4, isch^8 e^9 Hungersnot^9 cho^8.`
  Tag as you write each clause: a word for two tokens gets both (`^2,3`); words that render one token
  separately each get it (`wo^4 … regiert^4 hei^4`). Two more marks, both decided only now, while you write:
  - **a token your draft renders with no word** (the narrative וַ where the language has no "and", the object marker
    אֵת, a suffix the language leaves out): write `^-7` between the words where it would stand, as its own word
    (`mek^2 ^-4 di^5`). Almost every such token has a place: before the word it belongs with (an object marker before
    the object, an article before its noun, an "and" before its clause). Only a token with no place at all goes at the
    end of the verse (`ort^10. ^-7`);
  - **a word you add** with no token of its own: `^+5` after it when you add it for token 5 (a subject the Hebrew
    verb implies: `Naomi^+13`), `^+` when only the grammar needs it (`did^+`).
  Every token gets a decision: a tag on the word that renders it, or `^-`. No marks inside notes, headings, the title
  or header lines. Never write the `.txt` or the `.align` yourself: every change, also later, goes into the `.tagged`
  file."""

TAGGED_SPLIT = (", then `python3 scripts/full_align.py split {project} {code} {chapter}`: it writes the "
                "`{code}{nnn}.txt` and `{code}{nnn}.align` from the tagged file and lists the tokens you left "
                "undecided (`12f`: a function token); tag each one, or mark it `^-n` where your draft renders it with no word. "
                "After any later change to the `.tagged` file, run both again")


def tagged_fields(pname, code, ch, orig):
    nnn = f"{ch:03d}"
    f = dict(project=pname, pdir=project_rel(pname), code=code, nnn=nnn, chapter=ch, orig=orig)
    from project import project
    lean = (project(pname).get("familiarity") or "known") == "known"
    return {"package_line": (TAGGED_SOURCE_LEAN if lean else TAGGED_SOURCE).format(**f), "tagged_first": TAGGED_WRITE.format(**f),
            "tagged_split": TAGGED_SPLIT.format(**f), "draft_ext": "tagged", "align_step": ""}


def step(pname, code, ch):
    s = STEP.format(project=pname, pdir=project_rel(pname), code=code, chapter=ch, nnn=f"{ch:03d}")
    return greek(s) if BY_CODE[code][2] == "nt" else s


def greek(s):
    """An OT prompt text for an NT chapter: the Greek tokens and their examples instead of the Hebrew."""
    for a, b in (("(`cN` content, `fN`\n  function words: prefixes, article, object marker, suffixes)",
                  "(`cN` content, `fN`\n  function words: article, prepositions, conjunctions, particles, pronouns)"),
                 ("(»and« with\n    וַ, »in« with בְּ, a pronoun with its suffix)", "(»and« with\n    καί, »in« with ἐν, »the« with the article)"),
                 ("Hebrew", "Greek")):
        s = s.replace(a, b)
    return s


def iso_and_edition(pname):
    """compact-alignments path parts: the ISO 639-3 code (a dialect id falls back to the project's `language`), the edition."""
    sys.path.insert(0, os.path.join(CODE, "scripts"))
    from project import project
    lang, ed = pname.split("/")
    if not re.fullmatch(r"[a-z]{3}", lang):
        lang = str(project(pname).get("language", "")).split("-")[0]
    return lang, ed


def export(pname, out=None):
    iso, ed = iso_and_edition(pname)
    layer = f"{ed}+auto+make-tanakh"      # kind auto: made by script or agent, not hand-made gold (lexeme-aligner)
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
        hx = text_fingerprint(text_rows)[0]
        for old in os.listdir(d):
            if old.startswith(book + "_") and old.endswith(".json"):
                os.remove(os.path.join(d, old))
        base = os.path.join(d, f"{book}_{hx[:8]}")       # compact-alignments' name: the text fingerprint
        json.dump([main.get(r, "") for r in refs], open(base + ".json", "w", encoding="utf-8"), ensure_ascii=False)
        json.dump({"fn": [fn.get(r, "") for r in refs], "wp": [wp.get(r, "") for r in refs],
                   "fp": [fp.get(r, "") for r in refs], "wx": None, "rows": None, "off": None}, open(base + ".meta.json", "w", encoding="utf-8"), ensure_ascii=False)
        written.append(os.path.relpath(base + ".json", ROOT))
    src = source_index()
    json.dump({"version": 3, "lists": True, "layer": layer, "kind": "auto", "has_ids": False,   # decision lists (!, u, e, +)
               # the _index the ordinals refer to: a file built on another one points at the wrong tokens
               "spine_index_sha256": src.get("spine_index_sha256"),
               # the target positions and the file names: the tokenizer and the text fingerprint they follow
               "tokenizer_version": TOKENIZER_VERSION, "text_fp_version": TEXT_FP_VERSION,
               "attribution": {"base_text": ed, "kind": "auto", "license": "CC0-1.0", "source": "make-tanakh",
                               "versification": "org", "repo": "https://github.com/bcv-commons/make-tanakh"},
               "profiles": PROFILES}, open(os.path.join(d, "_layer.json"), "w", encoding="utf-8"), indent=1)
    print(f"{pname}: {len(written)} books -> {os.path.relpath(d, ROOT)}/")
    return d


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("check", "export", "listing", "prompt", "tag", "split"):
        raise SystemExit(__doc__)
    if a[0] == "tag":
        text, _ = tag(a[1], a[2], int(a[3]))
        out = os.path.join(project_dir(a[1]), a[2], f"{a[2]}{int(a[3]):03d}.tagged")
        open(out, "w", encoding="utf-8").write(text)
        print(f"wrote {os.path.relpath(out, ROOT)}")
        return
    if a[0] == "split":
        problems, untagged, rows = split(a[1], a[2], int(a[3]))
        for p in problems:
            print("problem: " + p)
        if not problems:
            print(f"wrote {a[2]}{int(a[3]):03d}.txt and .align; " + (
                "tokens undecided (f: a function token): " + "; ".join(f"v{v}: {' '.join(map(str, n))}" for v, n in untagged.items())
                if untagged else "every token decided"))
        sys.exit(1 if problems else 0)
    if a[0] == "prompt":
        print(prompt(a[1], a[2], int(a[3])))
        return
    if a[0] == "listing":
        print(listing(a[1], a[2], int(a[3])))
        return
    if a[0] == "check":
        sys.exit(1 if check(a[1], a[2] if len(a) > 2 else None, ch=int(a[3]) if len(a) > 3 else None) else 0)
    export(a[1], os.path.join(ROOT, a[a.index("--out") + 1]) if "--out" in a else None)


if __name__ == "__main__":
    main()
