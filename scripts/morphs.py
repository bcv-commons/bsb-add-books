#!/usr/bin/env python3
"""The morph view of a project's words: each word token as prefix, stem, grammatical tone, suffix, in that order,
from the language store (scripts/grammar.py: the morph entries; docs/proposals/language-profile/, *Kinds*).

Words have three views, aligned token by token (scripts/langtools.py, Tokeniser): the plain tokens (the marks in
`orthography.ignore_marks` removed: for finding, aligning and counting, where a word's tonal variants are one form), the
exact tokens (every mark kept: for checking a form the store writes) and, here, the morphs.

Two kinds of tone (or other marks on a word's vowels) are told apart:
  - lexical: part of the word (ambá "please" is not amba "wanted"); it stays in the stem, as written;
  - grammatical: a pattern across the word that carries a meaning of its own (a prohibitive: a grave on the penult and
    U+1DC4 on the last vowel). Only a morph entry of slot `tone` with a `tone_pattern` is one; its marks are taken out
    of the word into a tone morph, the rest stay where they are.

How the language writes tone is a store setting, `orthography.tone`:
  {"written": "marks" | "digits" | "letters" | "none",
   "marks": ["U+0301", ...]   the tone marks (for "marks"; default: orthography.ignore_marks),
   "vowels": "aeiou...",      the letters that carry tone (positions in a tone_pattern count these),
   "absent": "unknown" | "neutral"}   no mark on a vowel: not written (unknown) or a tone of its own (neutral, Pinyin)
"digits": a digit at the end of each syllable (Jyutping si1, numbered Pinyin ma3); the syllable is the unit then.
"letters" (Gwoyeu Romatzyh) and "none" (characters, everyday Pinyin): no tone morph can be read from the writing.

A tone morph's `tone_pattern`: [{"at": "-2", "mark": "U+0300"}, {"at": "-1", "mark": "U+1DC4"}]: the mark on the
tone-bearing unit at that position from the end ("-1" the last, "-2" the one before), or "<-1" on any before the last;
for "digits" the mark is the digit ("3"). Every element must match.

Affixes: the store's morphs of slot prefix, infix and suffix (any host), longest first, one of each, stripped only where
what remains is attested: a word of the corpus itself, or what two affixed words leave (so a stem that merely begins
like a prefix stays whole). The view is word-class blind: it is measured, not assumed (cell_check.py, rough_check.py).

    S = morphs.load(<project>)          None when the store has no morph entries
    S.split(exact_token)                [Morph(slot, form, text)]: text is the morph as written; ''.join of the texts,
                                        with the tone morph's marks put back, rebuilds the token (S.rebuild)
    S.labels(exact_token)               {"qo-", "-eav", "tone-proh", ...}: the morph forms, for matching

    python3 scripts/morphs.py <project> check      every corpus token rebuilt from its morphs; what the view finds
    python3 scripts/morphs.py <project> show <word> ...
    python3 scripts/morphs.py <project> tone [--write [--force]]
        how the corpus writes tone, detected (detect_tone): marks, digits or none, the tone marks, the letters that carry
        them, what a missing mark means; with the figures. --write puts it into the store as orthography.tone (and
        ignore_marks if the store has none), marked as derived; a setting already there is kept unless --force. Like every
        store setting, a change makes the tests that depended on it stale (grammar.py retest)
"""
import collections, os, re, sys, unicodedata
from typing import NamedTuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import grammar  # noqa: E402

CH = lambda m: chr(int(m[2:], 16)) if m.upper().startswith("U+") else m


# combining marks that orthographies use for tone (acute, grave, circumflex, caron, macron, double acute and grave, the
# vertical line above of Pe̍h-ōe-jī, the contour marks): the candidates. Every other mark (dot below, tilde, diaeresis,
# cedilla, ogonek, ring, horn, breve) is taken as part of its letter; a store can still name it in orthography.tone.
TONE_CANDIDATES = {chr(c) for c in (0x0300, 0x0301, 0x0302, 0x030C, 0x0304, 0x030B, 0x030F, 0x030D,
                                    0x1DC4, 0x1DC5, 0x1DC6, 0x1DC7, 0x1DC8, 0x1DC9)}


def detect_tone(tokens, min_mark=0.002, min_words=0.03, min_twins=0.15, max_top=0.6, min_digits=0.3, neutral=0.35,
                conflict=0.05, min_letter=0.02):
    """(proposal, figures) from {token: count} of the corpus as written.

    The tone marks are a layer: marks that never share a letter (one tone per vowel). Marks that do share one are in
    different layers: in a two-layer orthography the other layer is the vowel quality (Vietnamese â ă ơ under the
    tones: ấ; Yoruba's dot below: ọ́). The tone layer starts from the candidates (TONE_CANDIDATES) that occur in at least
    min_mark of the tokens; while two of them share letters (in more than `conflict` of the rarer one's uses), the one
    in most such pairs goes to the other layer. Where there is another layer, a frequent mark outside the candidates
    that never shares a letter with the tone layer but does with the other layer is a tone mark too (Vietnamese hook
    above, tilde, dot below).

    Tone is written with marks when the layer has at least two marks, the marked tokens are min_words of all, and
    min_twins of the marked word types have a twin: a word with the same letters and other tone marks or none (ambá
    beside amba, Yoruba ọkọ̀ ọkọ́ ọkọ; a stress or spelling accent seldom makes one: French 12%), and no letter carries
    more than max_top of the marks (tone falls on every vowel; French accents 79% on e); with digits when
    min_digits of the tokens end a syllable in 1-9 (Jyutping si1); else none. The tone-bearing letters are those of
    which at least min_letter of the occurrences carry a tone mark (and 10 in all); a missing mark is "neutral" (a tone
    of its own: Yoruba's and Vietnamese's level tone, Pinyin's neutral) when most of those letters carry one, else
    "unknown"."""
    N = sum(tokens.values()) or 1
    fig = {"tokens": N}
    dig = sum(n for w, n in tokens.items() if re.search(r"[^\W\d_][1-9](?![0-9])", w) and not w.isdigit())
    fig["digit_syllables"] = round(dig / N, 4)
    per, uses, pair = collections.Counter(), collections.Counter(), collections.Counter()
    for w, n in tokens.items():
        ms = set()
        for cl in clusters(w.lower()):
            here = sorted({m for m in cl[1:] if unicodedata.combining(m)})
            for m in here:
                ms.add(m)
                uses[m] += n
            for x in range(len(here)):
                for y in range(x + 1, len(here)):
                    pair[(here[x], here[y])] += n
        for m in ms:
            per[m] += n
    frequent = {m for m, n in per.items() if n >= min_mark * N}
    clash = lambda a, b: pair[tuple(sorted((a, b)))] > conflict * min(uses[a], uses[b])
    layer = {m for m in frequent if m in TONE_CANDIDATES}
    other = set()
    while True:
        bad = collections.Counter({m: sum(clash(m, o) for o in layer if o != m) for m in layer})
        if not bad or max(bad.values()) == 0:
            break
        m = max(bad, key=lambda k: (bad[k], -uses[k]))
        layer.discard(m)
        other.add(m)
    if other:
        other |= {m for m in frequent - layer - other if any(clash(m, t) for t in layer)}
        layer |= {m for m in frequent - layer - other if not any(clash(m, t) for t in layer) and any(clash(m, o) for o in other)}
    U = lambda ms: sorted(f"U+{ord(m):04X}" for m in ms)
    fig["marks"] = {f"U+{ord(m):04X}": round(per[m] / N, 4) for m in sorted(frequent, key=lambda k: -per[k])}
    if other:
        fig["other_layer"] = U(other)
    strip = lambda w: unicodedata.normalize("NFC", "".join(c for c in unicodedata.normalize("NFD", w.lower()) if c not in layer))
    types = collections.Counter(unicodedata.normalize("NFC", w.lower()) for w in tokens)
    groups = collections.Counter(strip(w) for w in types)
    marked = [w for w in types if any(c in layer for c in unicodedata.normalize("NFD", w))]
    fig["marked_words"] = round(sum(n for w, n in tokens.items() if any(c in layer for c in unicodedata.normalize("NFD", w))) / N, 4)
    fig["twins"] = round(sum(groups[strip(w)] >= 2 for w in marked) / len(marked), 3) if marked else 0
    on = collections.Counter()
    for w, n in tokens.items():
        for cl in clusters(w.lower()):
            if any(m in layer for m in cl[1:]):
                on[cl[0]] += n
    fig["top_letter"] = round(max(on.values()) / sum(on.values()), 3) if on else 0
    if len(layer) >= 2 and fig["marked_words"] >= min_words and fig["twins"] >= min_twins and fig["top_letter"] <= max_top:
        occ, tone_occ = collections.Counter(), collections.Counter()
        for w, n in tokens.items():
            for cl in clusters(w.lower()):
                occ[cl[0]] += n
                tone_occ[cl[0]] += n * any(m in layer for m in cl[1:])
        vowels = sorted(c for c, k in tone_occ.items() if c.isalpha() and k >= 10 and k >= min_letter * occ[c])
        units = sum(occ[c] for c in vowels)
        fig["marked_units"] = round(sum(tone_occ[c] for c in vowels) / units, 3) if units else 0
        return ({"written": "marks", "marks": U(layer), "vowels": "".join(vowels),
                 "absent": "neutral" if fig["marked_units"] >= neutral else "unknown"}, fig)
    if fig["digit_syllables"] >= min_digits:
        return {"written": "digits", "absent": "unknown"}, fig
    fig["why_none"] = ("fewer than two frequent tone marks" if len(layer) < 2 else
                       f"marked words {fig['marked_words']:.1%} < {min_words:.0%}" if fig["marked_words"] < min_words else
                       f"twins {fig['twins']:.0%} < {min_twins:.0%}: the marks don't tell words apart"
                       if fig["twins"] < min_twins else
                       f"{fig['top_letter']:.0%} of the marks on one letter: a spelling accent, not tone")
    return {"written": "none"}, fig


class Morph(NamedTuple):
    slot: str       # prefix, infix, stem, tone, suffix
    form: str       # the store's form (qo-, -eav, tone-proh) or, for the stem, its plain text
    text: str       # as written (NFC); for a tone morph the marks it took, as "pos:mark" items


def clusters(w):
    """a word (NFD) as [base character + its combining marks and modifier letters (a length mark ꞉ belongs to its
    vowel)]"""
    out = []
    for c in unicodedata.normalize("NFD", w):
        if out and (unicodedata.combining(c) or unicodedata.category(c) in ("Lm", "Sk")):
            out[-1] += c
        else:
            out.append(c)
    return out


class ToneSpec:
    def __init__(self, orth):
        t = (orth or {}).get("tone") or {}
        self.written = t.get("written", "marks" if orth and orth.get("ignore_marks") else "none")
        self.marks = {CH(m) for m in (t.get("marks") or (orth or {}).get("ignore_marks") or [])}
        self.vowels = set(t.get("vowels") or "aeiou")
        self.absent = t.get("absent", "unknown")

    def units(self, cl):
        """the indexes of the clusters that carry tone: vowels (marks), or the digit ending each syllable (digits)"""
        if self.written == "marks":
            return [i for i, c in enumerate(cl) if c[0].lower() in self.vowels]
        if self.written == "digits":
            return [i for i, c in enumerate(cl) if c[0].isdigit()]
        return []

    def marks_at(self, cl, i):
        return {c for c in cl[i][1:] if c in self.marks} if self.written == "marks" else {cl[i][0]}


class ToneMorph:
    def __init__(self, e):
        self.form, self.value = e["form"], e.get("value")
        self.pattern = [(p["at"], CH(p["mark"])) for p in e["tone_pattern"]]

    def match(self, spec, cl):
        """[(cluster index, mark)] the pattern takes from the word, or None"""
        u = spec.units(cl)
        took = []
        for at, mark in self.pattern:
            if at.startswith("<"):
                k = int(at[1:])
                cand = [i for i in u[:k] if mark in spec.marks_at(cl, i)] if len(u) >= -k else []
                if not cand:
                    return None
                took.append((cand[-1], mark))
            else:
                k = int(at)
                if len(u) < -k or mark not in spec.marks_at(cl, u[k]):
                    return None
                took.append((u[k], mark))
        return took


class Segmenter:
    def __init__(self, G, orth, vocab):
        self.spec = ToneSpec(orth)
        self.ignore = {CH(m) for m in (orth or {}).get("ignore_marks") or []}
        aff = lambda slot, host=None: sorted({e["form"].strip("-=") for e in G.morphs if e.get("slot") == slot
                                              and e.get("form") and (host is None or e.get("host") == host)} - {""},
                                             key=len, reverse=True)
        self.pre, self.inf, self.suf = aff("prefix"), aff("infix"), aff("suffix")
        hosts = {e.get("host") for e in G.morphs if e.get("slot") in ("prefix", "suffix")}
        self.free = {self.plain(e["form"]) for e in G.morphs if e.get("slot") == "free" and e.get("form")}
        self.pairs_by_host = {h: {(p, q) for p in aff("prefix", h) for q in aff("suffix", h)} for h in hosts}
        self.tones = [ToneMorph(e) for e in G.morphs if e.get("slot") == "tone" and e.get("tone_pattern")]
        if self.spec.written in ("letters", "none"):
            self.tones = []
        self.vocab = collections.Counter()
        for w, n in (vocab.items() if isinstance(vocab, dict) else ((w, 1) for w in vocab)):
            self.vocab[self.plain(w)] += n
        self.forms = collections.defaultdict(collections.Counter)  # a possible stem -> {(prefix, suffix): tokens}
        for w, n in self.vocab.items():
            for p in [""] + [p for p in self.pre if w.startswith(p)]:
                for q in [""] + [q for q in self.suf if w.endswith(q)]:
                    if len(w) - len(p) - len(q) >= 3:
                        self.forms[w[len(p):len(w) - len(q)]][(p, q)] += n
        # a word that is a prefix and a suffix of one host and nothing else (no-qa "my (thing)": person + class), for a
        # host where most such pairs are words of the corpus (a paradigm without stems), not where one happens to be
        # (t-at): measured, not assumed
        self.pairs = set()
        for h, ps in self.pairs_by_host.items():
            if ps and sum(p + q in self.vocab for p, q in ps) >= 0.5 * len(ps):
                self.pairs |= ps
        self.min_share, self.min_productive = 0.03, 0.4
        # a productive affix: most corpus words that begin (end) with it are attested splits (two-letter qo-, ge-);
        # it is taken off any word that leaves a stem of 3 letters or more. The others (one letter: n-, t-, z-; -av)
        # only where the stem is attested
        self.productive = set()
        for side, affs in (("p", self.pre), ("s", self.suf)):
            for a in affs:
                ws = [w for w in self.vocab if (w.startswith(a) if side == "p" else w.endswith(a))
                      and len(w) - len(a) >= 3 and w not in self.free]
                ok = sum(1 for w in ws if self.attested(w[len(a):], a, "", self.vocab[w]) if side == "p")
                ok += sum(1 for w in ws if self.attested(w[:-len(a)], "", a, self.vocab[w]) if side == "s")
                if len(ws) >= 10 and ok >= self.min_productive * len(ws):
                    self.productive.add(a + "-" if side == "p" else "-" + a)
        self.cache = {}

    def plain(self, w):
        return unicodedata.normalize("NFC", "".join(c for c in unicodedata.normalize("NFD", w.lower())
                                                    if c not in self.ignore))

    def attested(self, stem, p, q, n):
        """a paradigm: an affix is taken off only where the stem also occurs with another one in its place (or none):
        ge-nanim-ák beside qo-nanim, nanim-im; a stem that is a word of its own is not enough (n-amba), nor the same
        affix on another word (n-dap beside n-dap-eáv); and the stem's other forms are not rare beside this one (a
        frequent word that merely looks affixed: n-øme, 2,343 times, beside 41: under min_share). Returns the stem's
        other forms' tokens (the evidence), 0 when not attested"""
        F = self.forms.get(stem, {})
        others = {k: v for k, v in F.items() if k != (p, q)}
        ok = (len(stem) >= 3 and (not p or any(k[0] != p for k in others)) and (not q or any(k[1] != q for k in others))
              and sum(others.values()) >= self.min_share * n)
        return sum(others.values()) if ok else 0

    def split(self, w):
        """[Morph] of an exact token, in the order prefix, infix, stem, tone, suffix"""
        if w in self.cache:
            return self.cache[w]
        cl = clusters(w.lower())
        tone = None
        for t in self.tones:
            took = t.match(self.spec, cl)
            if took:
                tone = (t, took)
                break
        if tone:                                         # the grammatical marks out of the word
            cl = list(cl)
            for i, m in tone[1]:
                cl[i] = cl[i].replace(m, "", 1)
        pl = [self.plain(c) for c in cl]                 # plain text per cluster (ignored marks off)
        s = "".join(pl)
        cut = lambda a, b: unicodedata.normalize("NFC", "".join(cl[a:b]))
        # the cluster index where the plain text reaches n characters
        idx = [0]
        for p in pl:
            idx.append(idx[-1] + len(p))
        at = lambda n: idx.index(n) if n in idx else None
        out, i, j = [], 0, len(cl)
        for p, q in self.pairs:
            if s == p + q and at(len(p)):
                k = at(len(p))
                self.cache[w] = [Morph("prefix", p + "-", cut(0, k)), Morph("stem", "", "")] + (
                    [Morph("tone", tone[0].form, " ".join(f"{a}:U+{ord(m):04X}" for a, m in tone[1]))] if tone else []) + [
                    Morph("suffix", "-" + q, cut(k, j))]
                return self.cache[w]
        if s not in self.free and not w.startswith("-"):   # a free morph (a pronoun, a conjunction) is a word
            best = None                                  # prefix and suffix chosen together: génanimák = ge-nanim-ák
            for p in [""] + [p for p in self.pre if s.startswith(p) and at(len(p))]:
                for q in [""] + [q for q in self.suf if s.endswith(q) and at(len(s) - len(q)) and len(s) > len(p) + len(q)]:
                    if not (p or q):
                        continue
                    core = s[len(p):len(s) - len(q)]
                    ev = self.attested(core, p, q, self.vocab[s]) or (
                        len(core) >= 2 and (not p or p + "-" in self.productive) and (not q or "-" + q in self.productive))
                    if ev:                               # most affixes, then the stem with the most other forms
                        key = (bool(p) + bool(q), ev)
                        if best is None or key > best[0]:
                            best = (key, p, q)
            if best:
                _, p, q = best
                if p:
                    i = at(len(p))
                    out.append(Morph("prefix", p + "-", cut(0, i)))
                    for f in self.inf:
                        r = s[idx[i]:len(s) - len(q)]
                        if r.startswith(f) and at(idx[i] + len(f)) and len(r) - len(f) >= 3:
                            k = at(idx[i] + len(f))
                            out.append(Morph("infix", "-" + f + "-", cut(i, k)))
                            i = k
                            break
                tail = []
                if q:
                    j = at(len(s) - len(q))
                    tail = [Morph("suffix", "-" + q, cut(j, len(cl)))]
            else:
                tail = []
        else:
            tail = []
        out.append(Morph("stem", s[idx[i]:idx[j]], cut(i, j)))
        if tone:
            out.append(Morph("tone", tone[0].form, " ".join(f"{a}:U+{ord(m):04X}" for a, m in tone[1])))
        out += tail
        self.cache[w] = out
        return out

    def labels(self, w):
        return {m.form for m in self.split(w) if m.slot != "stem"}

    def rebuild(self, ms):
        """the exact token from its morphs (the tone morph's marks put back on their clusters)"""
        cl = clusters("".join(m.text for m in ms if m.slot != "tone"))
        for m in ms:
            if m.slot == "tone":
                for item in m.text.split():
                    a, mk = item.split(":")
                    c = cl[int(a)]                       # after the base letter, before a modifier letter (꞉);
                    cl[int(a)] = c[0] + CH(mk) + c[1:]   # NFC below puts the marks in their canonical order
        return unicodedata.normalize("NFC", "".join(cl))


def load(pname, P=None):
    """the project's Segmenter (P: a langtools.Project, else built here), or None without morph entries"""
    import json
    import langtools as LT
    P = P or LT.Project(pname)
    G = grammar.load(pname)
    if not (G.morphs):
        return None
    orth = {}
    f = os.path.join(P.profile, "observations.json")
    if os.path.exists(f):
        orth = json.load(open(f, encoding="utf-8")).get("orthography") or {}
    vocab = collections.Counter()
    for r in P.corpus():
        vocab.update(P.tok.tokens(r[4], exact=True))
    return Segmenter(G, orth, {w: n for w, n in vocab.items() if n >= 2})


def main(a):
    if len(a) < 2:
        raise SystemExit(__doc__)
    import langtools as LT
    P = LT.Project(a[0])
    S = load(a[0], P) if a[1] != "tone" else None
    if S is None and a[1] != "tone":
        raise SystemExit(f"{a[0]}: the store has no morph entries")
    if a[1] == "tone":
        import datetime, json
        tok = collections.Counter()
        for r in P.corpus():
            tok.update(P.tok.tokens(r[4], exact=True))
        prop, fig = detect_tone(tok)
        f = os.path.join(P.profile, "observations.json")
        d = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
        have = (d.get("orthography") or {}).get("tone")
        print(f"{a[0]}: tone written as {prop['written']}" + (f", marks {' '.join(prop['marks'])} on {prop['vowels']}, a "
              f"missing mark {prop['absent']}" if prop["written"] == "marks" else ""))
        print("  figures:", json.dumps(fig, ensure_ascii=False))
        if have:
            same = {k: have.get(k) for k in prop} == prop
            print("  the store has:", json.dumps({k: v for k, v in have.items() if k != "derived"}, ensure_ascii=False),
                  "(the same)" if same else "(different)")
        if "--write" in a:
            if have and "--force" not in a:
                print("  kept the store's setting (--force replaces it)")
                return
            if not os.path.exists(f):
                raise SystemExit(f"{a[0]}: no store ({f})")
            o = d.setdefault("orthography", {})
            o["tone"] = {**prop, "derived": {"by": "script:morphs.py tone", "date": datetime.date.today().isoformat(),
                                             "figures": fig}}
            if prop["written"] == "marks" and not o.get("ignore_marks"):
                o["ignore_marks"] = prop["marks"]
            json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            open(f, "a").write("\n")
            print("  written:", os.path.relpath(f, ROOT), "(grammar.py retest lists the tests this makes stale)")
        return
    if a[1] == "show":
        for w in a[2:]:
            for t in P.tok.tokens(w, exact=True):
                print(t, " | ".join(f"{m.slot}:{m.text}" for m in S.split(t)))
        return
    if a[1] != "check":
        raise SystemExit(__doc__)
    tok, bad, by = collections.Counter(), [], collections.Counter()
    for r in P.corpus():
        for t in P.tok.tokens(r[4], exact=True):
            tok[t] += 1
    for t, n in tok.items():
        ms = S.split(t)
        if S.rebuild(ms) != unicodedata.normalize("NFC", t.lower()):
            bad.append(t)
        for m in ms:
            if m.slot != "stem":
                by[(m.slot, m.form)] += n
    split = sum(n for t, n in tok.items() if len(S.split(t)) > 1)
    print(f"{a[0]}: {len(tok)} word types, {sum(tok.values())} tokens; tone written as {S.spec.written}"
          f" ({len(S.tones)} grammatical tone pattern(s)); {split} tokens ({split / sum(tok.values()):.0%}) split")
    print(f"rebuilt exactly: {len(tok) - len(bad)} of {len(tok)} types" + (f"; not: {', '.join(bad[:10])}" if bad else ""))
    for (slot, form), n in sorted(by.items(), key=lambda x: -x[1]):
        print(f"  {slot:7} {form:12} {n}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
