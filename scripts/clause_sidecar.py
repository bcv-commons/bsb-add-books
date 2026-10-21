"""Build the clause-overlay files for one chapter draft (see docs/proposals/clause-overlay/).

Input: a draft in clause-line form ('//N vK text', '//N =' for a merged segment)
or in overlay form (prose with inline '|N' / '|=' markers before each segment),
plus the Hebrew layout orig/heb/<code>NNN.txt.

Output (printed as JSON, or written with --out DIR):
- _index/<BOOK>_clauses.json           {"RUT 1:1": [levels of the Hebrew segments], ...}
- <BOOK>_<hash>.clauses.json            ["0:0 1:1-5 2:6-11 ...", ...] parallel to the index keys

Target positions use the compact-alignments tokenizer (runs of letters and marks;
digits and punctuation are separators). The hash is the compact-alignments text
fingerprint (its first 8 hex in the name), computed over the verses of the given file only.

Usage: python3 scripts/clause_sidecar.py <draft> <orig/heb file> <BOOK> [--out DIR]
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from full_align import text_fingerprint, tokenize   # compact-alignments' tokenizer v2 and text fingerprint v1


def plain(text):
    """Translatable text only: drop inline notes {T: …} etc."""
    return re.sub(r"\{[^}]*\}", "", text)


def source_levels(path):
    """chapter, {verse: [levels]} from orig/heb."""
    lines = open(path, encoding="utf-8").read().splitlines()
    chapter = int(lines[0].split()[1])
    levels = {}
    for l in lines[1:]:
        m = re.match(r"(\d+):(\d+) ", l)
        if m:
            levels.setdefault(int(m.group(1)), []).append(int(m.group(2)))
    return chapter, levels


def draft_segments(path):
    """{verse: [segment text or '=']} from a clause-line or overlay draft."""
    body = [l for l in open(path, encoding="utf-8").read().splitlines()
            if l.strip() and not l.startswith(("!!", "=="))]
    segs, verse = {}, None
    if any(re.match(r"//\d+ ", l) for l in body) and not any("|" in l for l in body):
        for l in body:
            m = re.match(r"//\d+ (.*)$", l)
            if not m:
                continue
            t = m.group(1).strip()
            v = re.match(r"v(\d+)\s*(.*)$", t)
            if v:
                verse, t = int(v.group(1)), v.group(2).strip()
            segs.setdefault(verse, []).append(t)
        return segs
    text = " ".join(re.sub(r"^//\d+ ", "", l) for l in body)
    for part in re.split(r"(?<![\w{])(v\d+ |\|(?:\d+|=(?:\([^)]*\))?))", text):
        if not part.strip():
            continue
        if re.fullmatch(r"v\d+ ", part):
            verse = int(part[1:])
        elif part.startswith("|="):
            words = part[3:-1].strip() if part.startswith("|=(") else ""
            segs.setdefault(verse, []).append(("= " + words).strip())
        elif re.fullmatch(r"\|\d+", part):
            segs.setdefault(verse, []).append("")
        elif verse in segs and segs[verse] and not segs[verse][-1].startswith("="):
            segs[verse][-1] += part
    return segs


def is_merged(seg):
    return seg == "=" or seg.startswith("= ")


def runs(positions, first=None):
    """positions -> 'a-b,c'. The first run is where the clause's line begins: the run
    containing `first` if given, otherwise the longest run (the later one on a tie)."""
    out, start = [], None
    positions = sorted(positions)
    for i, p in enumerate(positions):
        if start is None:
            start = p
        if i + 1 == len(positions) or positions[i + 1] != p + 1:
            out.append((start, p))
            start = None
    if first is not None:
        head = [r for r in out if r[0] <= first <= r[1]]
    else:
        head = [max(out, key=lambda r: (r[1] - r[0], r[0]))] if out else []
    rest = sorted(r for r in out if r not in head)
    return ",".join(f"{a}" if a == b else f"{a}-{b}" for a, b in head + rest)


def build(draft, heb, book):
    chapter, levels = source_levels(heb)
    segs = draft_segments(draft)
    index, entries, hashed = {}, [], []
    for v in sorted(levels):
        index[f"{book} {chapter}:{v}"] = levels[v]
        draft_v = segs.get(v, [])
        if len(draft_v) != len(levels[v]):
            raise SystemExit(f"{book} {chapter}:{v}: {len(draft_v)} draft segments, {len(levels[v])} Hebrew segments")
        # token positions of every segment that has a line of its own
        owned, pos = {}, 0
        for k, s in enumerate(draft_v):
            if is_merged(s):
                continue
            words = tokenize(plain(s))
            owned[k] = [list(range(pos, pos + len(words))), [w.lower() for w in words]]
            pos += len(words)
        # a merged segment may name the words of its host line (the line before it) that render it
        merged = {}
        for k, s in enumerate(draft_v):
            if not is_merged(s):
                continue
            merged[k] = []
            host = max((h for h in owned if h < k), default=None)
            if host is None:
                continue
            hpos, hwords = owned[host]
            i = 0
            for w in tokenize(s[1:]):
                while i < len(hwords) and hwords[i] != w.lower():
                    i += 1
                if i == len(hwords):
                    raise SystemExit(f"{book} {chapter}:{v}: merged word '{w}' not found in the line above")
                merged[k].append(hpos[i])
                i += 1
            taken = set(merged[k])
            owned[host][0] = [p for p in hpos if p not in taken]
            owned[host][1] = [w for p, w in zip(hpos, hwords) if p not in taken]
            owned[host].append(hpos[0])  # the line still starts at the host's first word
        # A clause whose words were named gets its own ranges, like any other clause: whether it
        # is shown as a line of its own or merged with its neighbour is the client's decision.
        # Only a clause without any words of its own stays '=' (e.g. an untranslated כִּי).
        parts = []
        for k in range(len(draft_v)):
            if k in merged:
                parts.append(f"{k}:" + runs(merged[k]) if merged[k] else f"{k}:=")
            elif owned[k][0]:
                parts.append(f"{k}:" + runs(owned[k][0], owned[k][2] if len(owned[k]) > 2 else owned[k][0][0]))
        entries.append(" ".join(parts))
        hashed.append((chapter, v, plain(" ".join(s for s in draft_v if not is_merged(s)))))
    digest = text_fingerprint(hashed)[0]
    return index, entries, digest


def option(name):
    if name in sys.argv:
        i = sys.argv.index(name)
        value = sys.argv[i + 1]
        del sys.argv[i:i + 2]
        return value
    return None


def main():
    out, index_dir = option("--out"), option("--index-dir")
    draft, heb, book = sys.argv[1:4]
    index, entries, digest = build(draft, heb, book)
    info = os.path.join(os.path.dirname(os.path.abspath(heb)), "_source.json")
    src = json.load(open(info, encoding="utf-8")).get("source") if os.path.exists(info) else None
    if src in (None, "bhsa"):
        print(f"note: {heb} is {'a BHSA layout' if src else 'of unknown source (no _source.json): treat it as BHSA'}; "
              "the index carries its levels (CC BY-NC): keep these files private, never in export/. "
              "For published sidecars use the bcv-query layout (scripts/relayout.py).", file=sys.stderr)
    if not out:
        print(json.dumps({"index": index, "entries": entries, "sha256": digest}, ensure_ascii=False, indent=1))
        return
    index_dir = index_dir or os.path.join(out, "_index")
    os.makedirs(index_dir, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    index_path = os.path.join(index_dir, f"{book}_clauses.json")
    json.dump(index, open(index_path, "w"), separators=(",", ":"))
    sidecar = os.path.join(out, f"{book}_{digest[:8]}.clauses.json")
    json.dump(entries, open(sidecar, "w"), ensure_ascii=False, indent=0)
    print(f"{index_path}\n{sidecar}")


if __name__ == "__main__":
    main()
