#!/usr/bin/env python3
"""Model text: the target language's verses as the tokens the second-draft model learns, and back. Store setting
`analysis.model_text`: "words" (the default: the text as written) or "morphs": each word as its parts, from the morph view
(scripts/morphs.py), so the model learns affixes and grammatical tone as units of their own:

    bezømbù꞉gu᷄.   ->   be+ +zø+ mbu꞉ ~PROH +gu +.
    gezǿ-tøkeák    ->   ge+ +zø+ ~H1 -tøke +ak ~H1
    ambá / amba    ->   amba ~H1 / amba

  - a prefix ends in the joiner (+), a suffix (and punctuation that touches the word) starts with it, an infix has both:
    a part with a joiner is glued to its neighbour, so words keep their boundaries;
  - grammatical tone: one token per tone morph of the store (slot tone with a tone_pattern), after the stem: ~PROH for
    tone-proh; the decoder writes its marks where the pattern says (positions from the word's end);
  - lexical tone: the part without its tone marks, then one code per mark, ~<mark><n>: the mark (H acute, L grave, F
    circumflex, R caron, M macron, MH macron-acute, ...; the code point for others) on the part's n-th tone-bearing unit
    from its end (orthography.tone: vowels for written marks).
Tone written as digits (Jyutping, numbered Pinyin) stays in the text: the tokenizer knows digits; letters or none: nothing
to separate. Only marks the store names as tone marks are coded; any other mark stays in the letters.

The decoder needs only the spec (spec_from_store(), saved in the data's meta.json as `model_text`), not the store: a model
is decoded as it was trained, whatever the store has learned since (then grammar.py retest lists the data as stale).
This file runs without the rest of the repo (train.py and draft.py use decode on a GPU machine); encoding needs the store.

    python3 scripts/nllb/model_text.py <project> check     every corpus verse encoded and decoded back; token counts
    python3 scripts/nllb/model_text.py <project> show <verse text>
    python3 scripts/nllb/model_text.py <project> encode <data dir> <out dir>
        an existing model data folder (scripts/nllb/data.py's files, or another split built the same way) with its target
        in parts: the .trg files encoded, .src and .vref copied, the spec added to meta.json. Same source, same split:
        only the target's form differs (an A/B of the form)
"""
import collections, os, sys, unicodedata

CODES = {"U+0301": "H", "U+0300": "L", "U+0302": "F", "U+030C": "R", "U+0304": "M", "U+030B": "HH", "U+030F": "LL",
         "U+1DC4": "MH", "U+1DC5": "LM", "U+1DC6": "ML", "U+1DC7": "HM", "U+1DC8": "LHL", "U+1DC9": "HLH"}
CH = lambda m: chr(int(m[2:], 16)) if m.upper().startswith("U+") else m
NFC = lambda s: unicodedata.normalize("NFC", s)


def clusters(w):
    """a word (NFD) as [base character + its combining marks and modifier letters] (as morphs.clusters)"""
    out = []
    for c in unicodedata.normalize("NFD", w):
        if out and (unicodedata.combining(c) or unicodedata.category(c) in ("Lm", "Sk")):
            out[-1] += c
        else:
            out.append(c)
    return out


def wordchar(c):
    return c.isalnum() or unicodedata.combining(c) or unicodedata.category(c) in ("Lm", "Sk")


class Codec:
    """spec: {"mode", "join", "tone", "written", "marks": [U+..], "vowels", "codes": {U+..: code},
    "tones": {token: {"form", "pattern": [[at, U+..]]}}}"""

    def __init__(self, spec):
        self.spec = spec or {"mode": "words"}
        self.on = self.spec.get("mode") == "morphs"
        if not self.on:
            return
        self.J, self.T = spec["join"], spec["tone"]
        self.coded = spec["written"] == "marks"
        self.marks = {CH(m) for m in spec["marks"]} if self.coded else set()
        self.vowels = set(spec["vowels"])
        self.code = {CH(m): c for m, c in spec["codes"].items()}
        self.mark = {c: m for m, c in self.code.items()}
        self.tones = {t: [(at, CH(m)) for at, m in v["pattern"]] for t, v in spec["tones"].items()}
        self.repairs = collections.Counter()

    def units(self, cl):
        return [i for i, c in enumerate(cl) if c[0].lower() in self.vowels]

    # --- decode -------------------------------------------------------------------------------------------------
    def decode(self, line):
        if not self.on:
            return line
        words, cur, glue = [], None, False
        for t in line.split():
            if t.startswith(self.T) and len(t) > 1:
                if cur is None:
                    self.repairs["tone code without a word"] += 1
                    continue
                cur[-1][1].append(t[len(self.T):])
                continue                                  # a code keeps its part's glue
            elif cur is not None and (glue or (t.startswith(self.J) and len(t) > 1)):
                cur.append([t, []])
            else:
                cur = [[t, []]]
                words.append(cur)
            glue = t.endswith(self.J) and len(t) > 1
        return " ".join(self.word(w) for w in words)

    def word(self, parts):
        cl, gram = [], []
        for text, codes in parts:
            t = text[len(self.J):] if text.startswith(self.J) and len(text) > 1 else text
            t = t[:-len(self.J)] if t.endswith(self.J) and len(t) > 1 else t
            pc = clusters(t)
            for c in codes:
                if c in self.tones or c.split("@")[0] in self.tones:
                    gram.append(c)
                    continue
                name, n = c.rstrip("0123456789"), c[len(c.rstrip("0123456789")):]
                u = self.units(pc)
                if name not in self.mark or not n or not 0 < int(n) <= len(u):
                    self.repairs["lexical code that doesn't fit its part"] += 1
                    continue
                k = u[-int(n)]
                pc[k] = pc[k][0] + self.mark[name] + pc[k][1:]
            cl += pc
        for g in gram:
            name, _, at = g.partition("@")
            fixed = [int(x) for x in at.split(".")] if at else []
            u = self.units(cl)
            for a, m in self.tones[name]:
                k = fixed.pop(0) if a.startswith("<") and fixed else (int(a) if not a.startswith("<") else None)
                if k is None or not 0 < -k <= len(u):
                    self.repairs["grammatical tone on a word too short for it"] += 1
                    continue
                i = u[k]
                cl[i] = cl[i][0] + m + cl[i][1:]
        return NFC("".join(cl))

    # --- encode (needs the segmenter) ----------------------------------------------------------------------------
    def encode(self, line, S):
        if not self.on:
            return line
        return " ".join(self.encode_chunk(c, S) for c in line.split())

    def encode_chunk(self, chunk, S):
        chunk = NFC(chunk)
        i = next((k for k, c in enumerate(chunk) if c.isalnum()), None)
        if i is None:
            return chunk
        j = max(k for k, c in enumerate(chunk) if wordchar(c)) + 1
        lead, core, trail = chunk[:i], chunk[i:j], chunk[j:]
        out = ([lead + self.J] if lead else []) + self.encode_word(core, S) + ([self.J + trail] if trail else [])
        return " ".join(out)

    def lex(self, pc):
        """a part's clusters without their tone marks, and the codes for them"""
        u, codes = self.units(pc), []
        for n, k in enumerate(reversed(u), 1):
            keep = pc[k][0]
            for m in pc[k][1:]:
                if m in self.marks:
                    codes.append(f"{self.T}{self.code.get(m) or f'{ord(m):04X}'}{n}")
                else:
                    keep += m
            pc[k] = keep
        return NFC("".join(pc)), list(reversed(codes))

    def encode_word(self, w, S):
        cl = clusters(w)
        ms = S.split(w) if S and w.lower() not in getattr(self, "names", ()) else []
        if not ms or len(clusters(w.lower())) != len(cl):
            t, c = self.lex(cl)
            return [t] + c
        gram = [m for m in ms if m.slot == "tone"]
        for m in gram:                                    # the grammatical marks out of the word
            for item in m.text.split():
                a, mk = item.split(":")
                cl[int(a)] = cl[int(a)].replace(CH(mk), "", 1)
        out, at = [], 0
        for m in ms:
            if m.slot == "tone":
                tok = self.T + m.form.removeprefix("tone-").upper()
                pat = self.tones.get(tok[len(self.T):], [])
                loose = [int(it.split(":")[0]) for (a, _), it in zip(pat, m.text.split()) if a.startswith("<")]
                if loose:                                 # a position the pattern leaves open: kept in the token
                    u = self.units(cl)
                    tok += "@" + ".".join(str(u.index(x) - len(u)) for x in loose)
                out.append(tok)
                continue
            n = len(clusters(m.text))
            pc, at = cl[at:at + n], at + n
            if not pc:
                continue
            t, codes = self.lex(pc)
            t = {"prefix": t + self.J, "infix": self.J + t + self.J, "suffix": self.J + t}.get(m.slot, t)
            out += [t] + codes
        return out


def spec_from_store(pname, mode=None):
    """the Codec spec for a project from its store (analysis.model_text, orthography.tone, the tone morphs)"""
    import json
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import grammar
    import morphs
    f = os.path.join(grammar.profile_dir(pname), "observations.json")
    d = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    an = d.get("analysis") or {}
    mode = mode or an.get("model_text", "words")
    if mode != "morphs":
        return {"mode": "words"}
    ts = morphs.ToneSpec(d.get("orthography") or {})
    G = grammar.Grammar(d.get("entries", []))
    tones = {e["form"].removeprefix("tone-").upper(): {"form": e["form"], "pattern": [[p["at"], p["mark"]] for p in e["tone_pattern"]]}
             for e in G.morphs if e.get("slot") == "tone" and e.get("tone_pattern")} if ts.written == "marks" else {}
    marks = sorted(f"U+{ord(m):04X}" for m in ts.marks)
    return {"mode": "morphs", "join": an.get("model_join", "+"), "tone": an.get("model_tone", "~"), "written": ts.written,
            "marks": marks, "vowels": "".join(sorted(ts.vowels)), "codes": {m: CODES.get(m, m[2:]) for m in marks},
            "tones": tones, "basis": grammar.basis(pname, None, "model_text 1")}


def codec_for(pname, mode=None, P=None):
    """(Codec, Segmenter) for encoding a project's text; refuses a joiner or tone sign that the corpus itself uses"""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import langtools as LT
    import morphs
    spec = spec_from_store(pname, mode)
    C = Codec(spec)
    if not C.on:
        return C, None
    P = P or LT.Project(pname)
    used = {c for r in P.corpus() for c in r[4]}
    for k in ("join", "tone"):
        if spec[k] in used:
            raise SystemExit(f"{pname}: the corpus uses {spec[k]!r}: set another analysis.model_{k} in the store")
    # names stay whole (Betliem is not be- + tliem): the store's name entries, and the words the corpus writes with a
    # capital nearly always (90% of at least 2), wherever they stand in the verse
    case = collections.defaultdict(lambda: [0, 0])
    for r in P.corpus():
        for w in r[4].split():
            w = w.strip("".join(c for c in w if not wordchar(c) and c != "-"))
            if w[:1].isalpha():
                case[w.lower()][w[0].isupper()] += 1
    C.names = {w for w, (lo, up) in case.items() if up + lo >= 2 and up >= 0.9 * (up + lo)}
    C.names |= {NFC(str(e.get("value", ""))).lower() for e in grammar_entries(pname) if e.get("kind") == "name"}
    return C, morphs.load(pname, P)


def grammar_entries(pname):
    import json
    import grammar
    f = os.path.join(grammar.profile_dir(pname), "observations.json")
    return json.load(open(f, encoding="utf-8")).get("entries", []) if os.path.exists(f) else []


def main(a):
    if len(a) < 2:
        raise SystemExit(__doc__)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import langtools as LT
    P = LT.Project(a[0])
    C, S = codec_for(a[0], "morphs", P)
    if a[1] == "encode" and len(a) == 4:
        import json, shutil
        src, dst = a[2], a[3]
        os.makedirs(dst, exist_ok=True)
        for f in sorted(os.listdir(src)):
            p = os.path.join(src, f)
            if f.endswith(".trg"):
                lines = open(p, encoding="utf-8").read().splitlines()
                enc = [C.encode(" ".join(t.split()), S) for t in lines]
                bad = sum(C.decode(e) != NFC(" ".join(t.split())) for t, e in zip(lines, enc))
                open(os.path.join(dst, f), "w", encoding="utf-8").write("\n".join(enc) + "\n")
                print(f"{f}: {len(lines)} lines encoded, {bad} not decoded back exactly")
                if bad:
                    sys.exit(1)
            elif f == "meta.json":
                m = json.load(open(p, encoding="utf-8"))
                m["model_text"] = C.spec
                json.dump(m, open(os.path.join(dst, f), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            elif os.path.isfile(p):
                shutil.copy(p, dst)
        print("->", dst)
        print(f"spec: tone written as {C.spec['written']}, tone marks {C.spec['marks'] or 'none'}, grammatical tone tokens "
              f"{', '.join('~' + t for t in C.spec['tones']) or 'none (no tone morph with a tone_pattern in the store)'}; "
              f"{'no morph entries: words are not split' if S is None else 'affixes from the store'}")
        return
    if a[1] == "show":
        line = " ".join(a[2:])
        e = C.encode(line, S)
        print(e)
        print(C.decode(e))
        return
    bad, n, words, toks = [], 0, 0, 0
    for r in P.corpus():
        t = " ".join(r[4].split())
        e = C.encode(t, S)
        n += 1
        words += len(t.split())
        toks += len(e.split())
        if C.decode(e) != NFC(t):
            bad.append((r[0], t, e))
    print(f"{a[0]}: {n} verses, {words} words -> {toks} model tokens ({toks / max(words, 1):.2f} a word)")
    print(f"decoded exactly: {n - len(bad)} of {n} verses")
    for ref, t, e in bad[:5]:
        d = C.decode(e).split()
        w = [(x, y) for x, y in zip(t.split(), d) if NFC(x) != y][:3]
        print(" ", ref, w)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
