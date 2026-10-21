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
"""
import collections, os, sys, unicodedata
from typing import NamedTuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import grammar  # noqa: E402

CH = lambda m: chr(int(m[2:], 16)) if m.upper().startswith("U+") else m


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
    S = load(a[0], P)
    if S is None:
        raise SystemExit(f"{a[0]}: the store has no morph entries")
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
