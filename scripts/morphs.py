#!/usr/bin/env python3
"""The morph view of a project's words: each word token as prefix, stem, grammatical tone, suffix, in that order,
from the language store (scripts/grammar.py: the morph entries; docs/language-store.md, *Kinds*).

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
Affix chains: where the store's affixes have a `position` (prefixes counted from the word's start, suffixes from the
stem outward), several of each are taken off, each position once and in order (ni-tu-ka-mu-sohoz-a). The evidence is
then by letters: each affix comes off only where another form of the stem lacks the letters from it to the stem
(tu-ka-batiz-ibw-a, as every form of tiz has ba before it). Of the parses, the one that takes off most letters in the
fewest pieces (ba-, not b-a-). Chains are host-aware where the NT is aligned to the Greek (lang.py build): a host's
affixes (verb) come off only words linked to that Greek class in at least half their tokens, and off other words only
where they leave the stem of such a word, so nouns keep their class prefixes (abaantu) unless the store lists them.
A chain affix's form may carry a tone mark that orthography.ignore_marks drops for finding words (aá- past beside aa-,
one tone apart): the parse runs on the plain letters, and the label follows the mark as written (tone_label).

    S = morphs.load(<project>)          None when the store has no morph entries
    S.split(exact_token)                [Morph(slot, form, text)]: text is the morph as written; ''.join of the texts,
                                        with the tone morph's marks put back, rebuilds the token (S.rebuild)
    S.labels(exact_token)               {"qo-", "-eav", "tone-proh", ...}: the morph forms, for matching

    python3 scripts/morphs.py <project> check      every corpus token rebuilt from its morphs; what the view finds
    python3 scripts/morphs.py <project> try [id ...] [--write]
        each affix entry measured on the NT aligned to the Greek (lang.py build): n, stems, and for the feature its
        `greek` names the lift and odds ratio (try_morphs); --write records them and a claim with its rerun recipe
    python3 scripts/morphs.py <project> show <word> ...
    python3 scripts/morphs.py <project> rates      the features the confirmed affixes mark, and how often the human NT
        marks them on the Greek verbs that have them: those marked on 60% or more are checked in the loop
    python3 scripts/morphs.py <project> review <code> <ch>   that check on an OT draft (chapter_check.py runs it): the
        verbs whose draft words lack the part for a feature of the Hebrew verb (person and number, negation, object,
        mood; wayyiqtol as a past)
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
                conflict=0.05, min_letter=0.02, min_double=0.01):
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
    more than max_top of the marks (tone falls on every vowel; French accents 79% on e). An orthography that marks one
    tone only (the high tone with an acute, as many Bantu languages do: Zinza Múungu) has a layer of one mark: it is tone
    when that mark stands twice in a word in at least min_double of the marked words (a stress accent stands once at most:
    Spanish, Italian, modern Greek), on min_words of all; the unmarked vowels then have the other tone (absent neutral).
    With digits when
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
    if marked:
        dbl = sum(n for w, n in tokens.items() if sum(c in layer for c in unicodedata.normalize("NFD", w)) >= 2)
        fig["double"] = round(dbl / max(1, fig["marked_words"] * N), 3)
    single = (len(layer) == 1 and fig["marked_words"] >= min_words and fig.get("double", 0) >= min_double
              and fig["top_letter"] <= max_top)
    if single or (len(layer) >= 2 and fig["marked_words"] >= min_words and fig["twins"] >= min_twins
                  and fig["top_letter"] <= max_top):
        occ, tone_occ = collections.Counter(), collections.Counter()
        for w, n in tokens.items():
            for cl in clusters(w.lower()):
                occ[cl[0]] += n
                tone_occ[cl[0]] += n * any(m in layer for m in cl[1:])
        vowels = sorted(c for c, k in tone_occ.items() if c.isalpha() and k >= 10 and k >= min_letter * occ[c])
        units = sum(occ[c] for c in vowels)
        fig["marked_units"] = round(sum(tone_occ[c] for c in vowels) / units, 3) if units else 0
        return ({"written": "marks", "marks": U(layer), "vowels": "".join(vowels),
                 "absent": "neutral" if single or fig["marked_units"] >= neutral else "unknown"}, fig)
    if fig["digit_syllables"] >= min_digits:
        return {"written": "digits", "absent": "unknown"}, fig
    fig["why_none"] = ("no frequent tone mark" if not layer else
                       f"one mark, never twice in a word ({fig.get('double', 0):.1%}): a stress accent" if len(layer) == 1 else
                       f"marked words {fig['marked_words']:.1%} < {min_words:.0%}" if fig["marked_words"] < min_words else
                       f"twins {fig['twins']:.0%} < {min_twins:.0%}: the marks don't tell words apart"
                       if fig["twins"] < min_twins else
                       f"{fig['top_letter']:.0%} of the marks on one letter: a spelling accent, not tone")
    return {"written": "none"}, fig


class Morph(NamedTuple):
    slot: str       # prefix, infix, stem, tone, suffix
    form: str       # the store's form (qo-, -eav, tone-proh) or, for the stem, its plain text
    text: str       # as written (NFC); for a tone morph the marks it took, as "pos:mark" items
    position: int = 0   # an affix of a chain: its position (the store's `position`), else 0


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
    def __init__(self, G, orth, vocab, classes=None):
        self.spec = ToneSpec(orth)
        self.ignore = {CH(m) for m in (orth or {}).get("ignore_marks") or []}
        aff = lambda slot, host=None: sorted({e["form"].strip("-=") for e in G.morphs if e.get("slot") == slot
                                              and e.get("form") and (host is None or e.get("host") == host)} - {""},
                                             key=len, reverse=True)
        self.pre, self.inf, self.suf = aff("prefix"), aff("infix"), aff("suffix")
        # affix chains (a Bantu verb: ni-tu-ka-mu-sohoz-a): morph entries with a `position`, prefixes counted from the
        # word's start, suffixes from the stem outward; several of them per word, each position once, in order
        self.chain = any(e.get("position") for e in G.morphs if e.get("slot") in ("prefix", "suffix"))
        if self.chain:
            def by_pos(slot, hosts=None):
                out = collections.defaultdict(set)
                for e in G.morphs:
                    if (e.get("slot") == slot and e.get("form", "").strip("-=")
                            and (hosts is None or (e.get("host") or "any") in hosts)):
                        out[int(e.get("position") or 1)].add(self.plain(e["form"].strip("-=")))
                return {p: sorted(v, key=len, reverse=True) for p, v in sorted(out.items())}
            # affixes told apart by tone alone (aá- past beside aa- future): forms with an ignored mark, matched on
            # their plain letters, labelled by the mark as written: {(slot, position, plain): {written: store form}}
            self.tone_forms = collections.defaultdict(dict)
            for e in G.morphs:
                fm = unicodedata.normalize("NFC", (e.get("form") or "").lower())
                if e.get("position") and e.get("slot") in ("prefix", "suffix") and fm.strip("-="):
                    self.tone_forms[(e["slot"], int(e["position"]), self.plain(fm.strip("-=")))][fm.strip("-=")] = fm
            self.tone_forms = {k: v for k, v in self.tone_forms.items() if len(v) > 1 or any(w != k[2] for w in v)}
            self.pre_at, self.suf_at = by_pos("prefix"), by_pos("suffix")
            self.chain_hosts = {e.get("host") or "any" for e in G.morphs if e.get("position")} - {"any"}
            self.at_for = {}                              # hosts -> (prefixes, suffixes) by position
            for hs in [frozenset({"any", h}) for h in self.chain_hosts] + [frozenset({"any"})]:
                self.at_for[hs] = (by_pos("prefix", hs), by_pos("suffix", hs))
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
        self.min_stem = 2 if self.chain else 3
        for w, n in self.vocab.items():
            if self.chain:                                # (prefix chain, suffix chain) as tuples of forms
                for pc, lp in self.chains(w, "p"):
                    for sc, ls in self.chains(w, "s"):
                        if len(w) - lp - ls >= self.min_stem:
                            self.forms[w[lp:len(w) - ls]][(pc, sc)] += n
                continue
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
                if self.chain:                            # the affix alone, at any of its positions
                    at_ = self.pre_at if side == "p" else self.suf_at
                    ones, none = [((p, a),) for p, fs in at_.items() if a in fs], ()
                else:
                    ones, none = [a], ""
                ok = sum(1 for w in ws if any(self.attested(w[len(a):], o, none, self.vocab[w]) for o in ones) if side == "p")
                ok += sum(1 for w in ws if any(self.attested(w[:-len(a)], none, o, self.vocab[w]) for o in ones) if side == "s")
                if len(ws) >= 10 and ok >= self.min_productive * len(ws):
                    self.productive.add(a + "-" if side == "p" else "-" + a)
        # host-aware chains: a word's classes from the NT aligned to the Greek (classes: {word: Counter(Greek class:
        # tokens linked to one, and "" all its linked tokens)}): each class linked in at least half its tokens (2 or
        # more), so a verb that also renders its subject's article (bakagaamba: οἱ ... εἶπον) is still a verb. A chain's
        # affixes of a host (verb) come off only that class's words, and off a word the NT doesn't link where what they
        # leave is the stem of such a word (stems_of)
        self.word_class, self.stems_of = {}, {}
        if self.chain and classes:
            acc = collections.defaultdict(collections.Counter)
            for w, c in classes.items():
                acc[self.plain(w)].update(c)
            for w, c in acc.items():
                if c[""] >= 2:
                    self.word_class[w] = frozenset(k for k, n in c.items() if k and n >= 0.5 * c[""])
        self.cache = {}

    def tone_label(self, slot, pos, plain, text):
        """the store form of a chain affix: where the store tells its forms apart by tone (aá- beside aa-), the one
        written so (marks as in the text), the unmarked one where the text has no mark, else the form as written"""
        v = self.tone_forms.get((slot, pos, plain))
        dash = (lambda x: x + "-") if slot == "prefix" else (lambda x: "-" + x)
        if not v:
            return dash(plain)
        t = unicodedata.normalize("NFC", text.lower())
        if t in v:
            return v[t]
        return v.get(plain) or dash(plain) if t == plain else dash(t)

    def hosts_of(self, s):
        """the hosts whose chain affixes may come off the plain word s (None: all, no word classes known)"""
        if not self.word_class:
            return None
        k = self.word_class.get(s)
        if k:                                            # no class in half its tokens: as a word the NT doesn't link
            hs = k & self.chain_hosts
            return frozenset({"any", min(hs)}) if hs else frozenset({"any"})   # one host's chain (verb before noun)
        for h in sorted(self.chain_hosts):
            if h not in self.stems_of:
                self.stems_of[h] = {r[0] for w, c in self.word_class.items() if h in c
                                    for r in [self.chain_parse(w, frozenset({"any", h}))] if r}
            r = self.chain_parse(s, frozenset({"any", h}))
            if r and r[0] in self.stems_of[h]:
                return frozenset({"any", h})
        return frozenset({"any"})

    def chain_parse(self, s, hosts=None, cut_ok=lambda n: True, fit=lambda pc, sc: 0):
        """(stem, prefix chain, suffix chain) of the plain word s, or None: of the chains that leave an attested stem
        (or are all productive), the one that takes off most letters in the fewest pieces (ba-, not b-a-), then the one
        whose affixes are written as the store writes them (fit: b-aá-, not ba-á-, where aá- is a form and á- is not),
        then the stem with most other forms. cut_ok(n): a boundary n letters from the start may be cut"""
        at = self.at_for.get(hosts) if hosts is not None else None
        best = None
        for pc, lp in self.chains(s, "p", cut_ok, at):
            for sc, ls in self.chains(s, "s", lambda n: cut_ok(len(s) - n), at):
                if not (pc or sc) or len(s) - lp - ls < self.min_stem:
                    continue
                core = s[lp:len(s) - ls]
                ev = self.attested(core, pc, sc, self.vocab[s]) or (
                    len(core) >= 2 and all(a + "-" in self.productive for _, a in pc)
                    and all("-" + a in self.productive for _, a in sc))
                if ev:
                    key = (lp + ls, -len(pc) - len(sc), fit(pc, sc), ev)
                    if best is None or key > best[0]:
                        best = (key, core, pc, sc)
        return best[1:] if best else None

    def plain(self, w):
        return unicodedata.normalize("NFC", "".join(c for c in unicodedata.normalize("NFD", w.lower())
                                                    if c not in self.ignore))

    def chains(self, s, side, ok=lambda n: True, at_=None):
        """[(chain of (position, form), length)] of every affix chain that fits the start (side p) or the end (side s) of the plain
        string s, the empty one included; positions rise from the word's start (prefixes) or from the stem outward
        (suffixes: the outermost is taken first, so from the end they fall). ok(n): a boundary n letters from that edge
        may be cut (a cluster boundary)"""
        at = (at_[0] if side == "p" else at_[1]) if at_ else (self.pre_at if side == "p" else self.suf_at)
        out = []

        def walk(i, last, ch):
            out.append((tuple(ch), i))
            for p in (sorted(at) if side == "p" else sorted(at, reverse=True)):
                if (side == "p" and p <= last) or (side == "s" and p >= last):
                    continue
                for f in at[p]:
                    hit = s.startswith(f, i) if side == "p" else s[:len(s) - i].endswith(f)
                    if hit and len(s) - i - len(f) >= self.min_stem and ok(i + len(f)):
                        walk(i + len(f), p, ch + [(p, f)])
        walk(0, 0 if side == "p" else 10 ** 6, [])
        return out

    def attested(self, stem, p, q, n):
        """a paradigm: an affix is taken off only where the stem also occurs with another one in its place (or none):
        ge-nanim-ák beside qo-nanim, nanim-im; a stem that is a word of its own is not enough (n-amba), nor the same
        affix on another word (n-dap beside n-dap-eáv); and the stem's other forms are not rare beside this one (a
        frequent word that merely looks affixed: n-øme, 2,343 times, beside 41: under min_share). Returns the stem's
        other forms' tokens (the evidence), 0 when not attested. For a chain, each of its affixes: tu-ka-batiz-ibw-a,
        not tu-ka-ba-tiz-, as every form of tiz has ba- before it"""
        F = self.forms.get(stem, {})
        others = {k: v for k, v in F.items() if k != (p, q)}
        if self.chain:                                   # p, q chains: each affix missing or replaced in another form
            # by letters, not parses: an affix comes off where another form of the stem lacks the letters from it to the
            # stem (any parse: ku-b-a-tiz has the letters of ba- before tiz, so ba- stays in batiz)
            pre = lambda ch: "".join(f for _, f in ch)                 # prefixes from the word's start
            suf = lambda ch: "".join(f for _, f in reversed(ch))       # suffixes from the stem outward
            ok = (len(stem) >= self.min_stem
                  and all(any(not pre(k[0]).endswith(pre(p[i:])) for k in others) for i in range(len(p)))
                  and all(any(not suf(k[1]).startswith(suf(q[i:])) for k in others) for i in range(len(q)))
                  and sum(others.values()) >= self.min_share * n)
        else:
            ok = (len(stem) >= self.min_stem and (not p or any(k[0] != p for k in others))
                  and (not q or any(k[1] != q for k in others)) and sum(others.values()) >= self.min_share * n)
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
        if self.chain and s not in self.free and not w.startswith("-"):
            def fit(pc, sc):                             # +1 an affix written with a store form's mark, -1 one written
                score, a, b = 0, 0, len(cl)              # with a mark no store form of it has
                for slot, ch_ in (("prefix", pc), ("suffix", sc)):
                    for p, f in ch_:
                        if slot == "prefix":
                            k = at(idx[a] + len(f)); t = cut(a, k); a = k
                        else:
                            k = at(idx[b] - len(f)); t = cut(k, b); b = k
                        t = unicodedata.normalize("NFC", t.lower())
                        if t != f:
                            score += 1 if t in self.tone_forms.get((slot, p, f), {}) else -1
                return score
            best = self.chain_parse(s, self.hosts_of(s), lambda n: at(n) is not None, fit)
            tail = []
            if best:
                _, pc, sc = best
                for p, a in pc:
                    k = at(idx[i] + len(a))
                    out.append(Morph("prefix", self.tone_label("prefix", p, a, cut(i, k)), cut(i, k), p))
                    i = k
                for p, a in sc:                          # from the outside in; written from the stem outward
                    k = at(idx[j] - len(a))
                    tail.insert(0, Morph("suffix", self.tone_label("suffix", p, a, cut(k, j)), cut(k, j), p))
                    j = k
        elif s not in self.free and not w.startswith("-"):   # a free morph (a pronoun, a conjunction) is a word
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
    S = Segmenter(G, orth, {w: n for w, n in vocab.items() if n >= 2}, word_classes(pname, P))
    S.vocab_exact = vocab                         # every corpus token as written, for stem_forms
    return S


def word_classes(pname, P):
    """{exact token: Counter(Greek word class: its tokens linked to one; "": its linked tokens)} of the NT aligned to the
    Greek (lang.py build), for host-aware chains; None without it"""
    import sqlite3
    import lang
    if not os.path.exists(lang.db_path(P)):
        return None
    _, con = lang.connect(pname)
    tok = collections.defaultdict(set)
    for b, c, v, p, raw, cls in con.execute("""select l.book, l.ch, l.v, l.pos, t.raw, g.class from nt_links l join nt_tokens t
            on t.book=l.book and t.ch=l.ch and t.v=l.v and t.pos=l.pos join g.tokens g on g.key=l.key"""):
        if raw and cls:
            tok[(b, c, v, p, raw)].add(cls)
    out = collections.defaultdict(collections.Counter)
    for k, cs in tok.items():
        out[k[4]].update(cs | {""})
    return out


METHOD = "morphs try 1"
HOSTS = {"verb": ("verb",), "noun": ("noun",), "adj": ("adj",), "pron": ("pron",)}  # any other host: every class


def try_morphs(pname, ids, P, S, write=False, by="script:morphs.py", min_n=20, min_stems=5, min_odds=2.0):
    """Each affix entry (prefix, infix, suffix; those named, else all) measured on the NT aligned to the Greek, under the
    store's whole segmentation (a chain's other affixes included): how often it comes off (n), on how many different
    stems, and, where the entry names the Greek feature it marks (`greek`: {"person+number": "fp"}, the names of
    lang.py report; a list for any of several values, {"mood": ["subjunctive", "imperative"]}), its lift (the feature's
    share among the host words it comes off, over its share among all of them) and its odds ratio (the feature's odds
    where it comes off, against the other host words: unlike the lift not capped for a common feature, the aorist), on
    every verse and on the even verses alone (a second count on half the data).
    Kept: n >= min_n, stems >= min_stems, and both odds ratios >= min_odds (without `greek`: the counts only, verdict
    open).
    With write: the entry's `stats`, status observed (kept) or open (not), and one claim per entry (id claim:morph.<id>)
    with its rerun recipe and basis, so that grammar.py retest reruns it when the store changes"""
    import json, sqlite3, datetime
    import lang
    G = grammar.load(pname)
    cands = [e for e in G.morphs if e.get("slot") in ("prefix", "infix", "suffix") and (not ids or e.get("id") in ids)]
    if ids and len(cands) < len(set(ids)):
        raise SystemExit(f"not affix entries of the store: {', '.join(sorted(set(ids) - {e['id'] for e in cands}))}")
    _, con = lang.connect(pname)
    con.row_factory = sqlite3.Row
    gtok = {r["key"]: r for r in con.execute("select * from g.tokens")}
    feat = lang.greek_features(con, gtok)
    rows = con.execute("""select l.book as bk, l.ch as cc, l.v as vv, t.raw, g.* from nt_links l join nt_tokens t on t.book=l.book and t.ch=l.ch
        and t.v=l.v and t.pos=l.pos join g.tokens g on g.key=l.key""").fetchall()
    toks, seen = [], set()
    for r in rows:                                   # one row per target token (its first link)
        k = (r["raw"], r["key"])
        if k in seen or not r["raw"]:
            continue
        seen.add(k)
        ms = S.split(r["raw"])
        stem = next((m.form for m in ms if m.slot == "stem"), "")
        toks.append((r["class"], {(m.form, m.position) for m in ms if m.slot != "stem"}, stem, feat(r), r["vv"] % 2 == 0,
                     f"{r['bk'].upper()} {r['cc']}:{r['vv']}"))
    gr = lambda e: " ".join(f"{a}={'|'.join(b) if isinstance(b, list) else b}" for a, b in sorted((e.get("greek") or {}).items()))
    res = []
    for e in cands:
        form, pos = e["form"], int(e.get("position") or 0)
        cls = HOSTS.get(e.get("host"))
        want = {k: set(v) if isinstance(v, list) else {v} for k, v in (e.get("greek") or {}).items()}
        has = lambda fv: all(any((k, v) in fv for v in vs) for k, vs in want.items())
        out = {}
        for half in ("all", "even"):
            host = [t for t in toks if (cls is None or t[0] in cls) and (half == "all" or t[4])]
            on = [t for t in host if (form, pos) in t[1] or (not pos and any(f == form for f, _ in t[1]))]
            n, stems = len(on), len({t[2] for t in on})
            lift = odds = None
            if want and n and host:
                k = sum(has(t[3]) for t in on)
                base = sum(has(t[3]) for t in host)
                lift = round((k / n) / (base / len(host)), 2) if base else 0.0
                rest, krest = len(host) - n, base - k   # the odds of the feature where it comes off, against elsewhere
                odds = round(((k + .5) / (n - k + .5)) / ((krest + .5) / (rest - krest + .5)), 2)
            out[half] = (n, stems, lift, odds)
            if half == "all":
                host_on = on
        n, stems, lift, odds = out["all"]
        tl, todds = out["even"][2], out["even"][3]
        kept = n >= min_n and stems >= min_stems and (not want or (odds or 0) >= min_odds and (todds or 0) >= min_odds)
        verdict = ("confirmed" if kept else "contradicted") if want else ("open" if kept else "contradicted")
        refs = list(dict.fromkeys(t[5] for t in host_on))[:3]
        res.append((e, n, stems, lift, tl, odds, todds, verdict, refs))
        print(f"  {e['id']:24} {form:7} position {pos or '-'}  n {n:5}  stems {stems:4}"
              + (f"  lift {lift}, odds {odds} (even verses {todds}) for {gr(e)}" if want else "")
              + f"  -> {verdict}")
    if not write:
        return res
    f = os.path.join(P.profile, "observations.json")
    d = json.load(open(f, encoding="utf-8"))
    today = datetime.date.today().isoformat()
    by_id = {x.get("id"): x for x in d["entries"]}
    for e, n, stems, lift, tl, odds, todds, verdict, refs in res:
        x = by_id[e["id"]]
        if not x.get("evidence") and refs:          # a proposal without evidence gets the first verses it comes off in
            x["evidence"] = [{"ref": refs[0], "n": n}] + [{"ref": r} for r in refs[1:]]
        x["stats"] = {**(x.get("stats") or {}), "count": n, "hosts": stems,
                      **({"lift": lift, "test_lift": tl, "odds": odds, "test_odds": todds} if lift is not None else {})}
        if x.get("status") in ("open", "observed"):  # a decided entry stays decided: the figures go beside it
            x["status"] = "observed" if verdict == "confirmed" else "open"
        want = gr(e)
        c = {"id": f"claim:morph.{e['id'].removeprefix('m:')}", "kind": "claim",
             "value": f"{e['form']} ({e.get('slot')}" + (f", position {e['position']}" if e.get("position") else "")
                      + f", {e.get('host') or 'any'}) is an affix" + (f" marking {want}" if want else ""),
             "area": "morph", "source": e.get("by") or "", "tests": ["corpus"],
             "figures": f"n {n}, stems {stems}" + (f", lift {lift} (even verses {tl}), odds ratio {odds} (even verses "
                                                   f"{todds})" if lift is not None else ""),
             "verdict": verdict, "next": {"confirmed": "the morph stays (observed)", "open": "counts only: name its "
                                          "Greek feature (`greek`) to test it",
                                          "contradicted": "the morph stays open: revise or supersede it"}[verdict],
             "confidence": "medium" if verdict == "confirmed" else "low", "method": "corpus-derived", "by": by,
             "date": today, "status": "observed", "rerun": ["morphs.py", "try", e["id"]], "rerun_method": METHOD}
        if c["id"] in by_id:
            d["entries"] = [c if y.get("id") == c["id"] else y for y in d["entries"]]
        else:
            d["entries"].append(c)
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(f, "a").write("\n")
    b = grammar.basis(pname, None, METHOD)       # after the write: the store as the test leaves it
    claims = {f"claim:morph.{e['id'].removeprefix('m:')}" for e, *_ in res}
    for y in d["entries"]:
        if y.get("id") in claims:
            y["basis"], y["basis_corpus"] = b, grammar.corpus(pname)
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(f, "a").write("\n")
    print(f"written: {len(res)} morph(s) and their claims into {os.path.relpath(f)}")
    return res


# ---------- the morph view for the drafting agents: a word's parts, a stem's forms, and the loop's check ----------

def parts(S, w, confirmed=None):
    """an exact token as its parts written with hyphens (y-aá-mu-gaamb-il-a; a grammatical tone after a +:
    zøveqas+tone-proh), or None for a word of one part. confirmed (affix_entries): None as well where an affix is not
    confirmed (open, or not in the store), so a guess (a name cut by an open suffix) isn't shown as a split"""
    ms = S.split(w)
    if len(ms) < 2:
        return None
    if confirmed is not None and any(m.slot != "stem" and not is_confirmed(confirmed.get((m.form, m.position)))
                                     for m in ms):
        return None
    t = [m.text for m in ms if m.slot != "tone" and m.text]
    return "-".join(t) + "".join(f"+{m.form}" for m in ms if m.slot == "tone")


def is_confirmed(e, min_n=20, min_stems=5):
    """an affix entry the corpus bears out: observed or decided, or, without a Greek feature to test, open with try's
    counts passing (n and stems: a final vowel)"""
    if not e:
        return False
    st = e.get("stats") or {}
    return e.get("status") in ("observed", "decided") or (
        e.get("status") == "open" and not e.get("greek") and (st.get("count") or 0) >= min_n and (st.get("hosts") or 0) >= min_stems)


def meaning(e):
    """an affix entry's meaning in a few words: its value (2.SG), the Greek feature it marks, open if not confirmed"""
    g = " ".join(f"{a}={'|'.join(b) if isinstance(b, list) else b}" for a, b in sorted((e.get("greek") or {}).items()))
    return (e.get("value") or "") + (f" ({g})" if g else "") + (" [open]" if e.get("status") == "open" else "")


def affix_entries(G):
    """{(store form, position): entry} of the store's live affixes (prefix, infix, suffix, tone)"""
    out = {}
    for e in G.morphs:
        if e.get("slot") in ("prefix", "infix", "suffix", "tone") and e.get("form") and e.get("status") not in ("rejected",):
            out[(unicodedata.normalize("NFC", e["form"].lower()), int(e.get("position") or 0))] = e
    return out


def affix_table(G):
    """the store's affixes for a verse pack or a prompt: one line per slot and position, each with its meaning"""
    by = collections.defaultdict(list)
    for (fm, pos), e in affix_entries(G).items():
        by[(e["slot"], e.get("host") or "any", pos)].append(f"{fm} {meaning(e)}".strip())
    order = {"prefix": 0, "infix": 1, "tone": 2, "suffix": 3}
    return [f"- {slot}{f' {pos}' if pos else ''} ({host}): " + "; ".join(sorted(v))
            for (slot, host, pos), v in sorted(by.items(), key=lambda x: (order[x[0][0]], x[0][1], x[0][2]))]


def stem_forms(S):
    """{plain stem: Counter(exact stem text)} of the corpus words (a word of one part is its own stem)"""
    if getattr(S, "_stems", None) is None:
        st = collections.defaultdict(collections.Counter)
        for w, n in S.vocab_exact.items():
            for m in S.split(w):
                if m.slot == "stem" and m.form:
                    st[m.form][m.text] += n
        S._stems = st
    return S._stems


def built(S, w):
    """a form the corpus lacks, as the store's parts build it: (parts, note) where its stem is the stem of a corpus word
    and at least one affix comes off (note: the stem written with other marks than the corpus writes it, else ""),
    or None"""
    ms = S.split(w)
    stem = next((m for m in ms if m.slot == "stem"), None)
    if len(ms) < 2 or not stem or not stem.form:
        return None
    c = stem_forms(S).get(stem.form)
    if not c:
        return None
    note = "" if stem.text in c else f"the stem {stem.text}: the corpus writes {', '.join(x for x, _ in c.most_common(2))}"
    return parts(S, w), note


# the loop's check: a verb of the original whose draft word lacks the part the store says marks its feature, where the
# human translation marks it in most such verbs (measured on the NT aligned to the Greek). Features in the names of
# lang.greek_features; a Hebrew verb is given the same names (hebrew_features): its person and number, a negation in
# its clause, its clause's object pronoun, and for the forms that say it, mood (imperative; jussive and cohortative as
# subjunctive; infinitive; participle) and tense (wayyiqtol as an aorist indicative). qatal, yiqtol, weqatal and the
# stems (niphal as a passive) are left out: their Greek counterparts vary too much. Only words that carry a verb prefix
# of the chain count (a verb rendered by a noun or a pronoun says nothing about its parts), and an imperative, an
# infinitive or a participle is not expected to carry a subject.
DIMS = {"person+number": "subject", "person+number+mood": "subject", "negated": "negation", "object": "object",
        "tense": "tense", "tense+mood": "tense", "mood": "mood"}
HEB_NEG = {"לֹא", "לָא", "אַל", "בַּל", "בְּלִי", "אַיִן", "בִּלְתִּי"}
HEB_MOOD = {"imperative": "imperative", "jussive": "subjunctive", "cohortative": "subjunctive",
            "infinitive construct": "infinitive", "infinitive absolute": "infinitive",
            "participle active": "participle", "participle passive": "participle"}


def marking(G, min_odds=2.0):
    """{(store form, position): (dimension, label, want)} of the store's affixes that mark a Greek feature and are
    confirmed: decided, or observed with odds ratios >= min_odds (morphs.py try)"""
    out = {}
    for k, e in affix_entries(G).items():
        g = e.get("greek") or {}
        dim = next((DIMS[a] for a in g if a in DIMS), None)
        st = e.get("stats") or {}
        if not dim or not (e.get("status") == "decided" or e.get("status") == "observed"
                           and (st.get("odds") or 0) >= min_odds and (st.get("test_odds") or 0) >= min_odds):
            continue
        want = {a: set(b) if isinstance(b, list) else {b} for a, b in g.items()}
        label = " ".join(f"{a}={'|'.join(sorted(b))}" for a, b in sorted(want.items()))
        out[k] = (dim, label, want)
    return out


def _has(want, fv):
    return all(any((a, v) in fv for v in vs) for a, vs in want.items())


NO_SUBJECT = {("mood", "imperative"), ("mood", "infinitive"), ("mood", "participle")}


def expected(M, fv):
    """{(dimension, label): {(form, position)}}: the confirmed affixes a verb with the features fv would carry"""
    out = collections.defaultdict(set)
    for (fm, pos), (dim, label, want) in M.items():
        if dim == "subject" and fv & NO_SUBJECT:
            continue
        if _has(want, fv):
            out[(dim, label)].add((fm, pos))
    return out


def carried(S, M, dim, fv, words):
    """does one of the words (exact tokens) carry an affix of the dimension that fits the features fv"""
    for w in words:
        for m in S.split(w):
            x = M.get((m.form, m.position))
            if x and x[0] == dim and _has(x[2], fv):
                return True
    return False


def verb_words(S, G, ws):
    """the words that carry a verb prefix of the chain (host verb, with a position)"""
    A = getattr(S, "_verb_pre", None)
    if A is None:
        A = S._verb_pre = {k for k, e in affix_entries(G).items() if e.get("host") == "verb" and e.get("slot") == "prefix"
                           and e.get("position")}
    return [w for w in ws if any((m.form, m.position) in A for m in S.split(w))]


def human_rates(pname, P, S, M):
    """{(dimension, label): [verbs, carried, forms]} on the NT aligned to the Greek (lang.py build): of the Greek verbs
    with the feature linked to a word with a verb prefix, how many have one that carries one of its affixes"""
    import sqlite3
    import lang
    _, con = lang.connect(pname)
    con.row_factory = sqlite3.Row
    gtok = {r["key"]: r for r in con.execute("select * from g.tokens")}
    feat = lang.greek_features(con, gtok)
    words = collections.defaultdict(list)
    for key, raw in con.execute("select l.key, t.raw from nt_links l join nt_tokens t on t.book=l.book and t.ch=l.ch "
                                "and t.v=l.v and t.pos=l.pos"):
        if raw:
            words[key].append(raw)
    out = collections.defaultdict(lambda: [0, 0, set()])
    G = grammar.load(pname)
    for key, ws in words.items():
        g = gtok.get(key)
        if not g or g["class"] != "verb":
            continue
        ws = verb_words(S, G, ws)
        if not ws:
            continue
        fv = feat(g)
        for (dim, label), forms in expected(M, fv).items():
            r = out[(dim, label)]
            r[0] += 1
            r[1] += carried(S, M, dim, fv, ws)
            r[2] |= forms
    return dict(out)


def checked(rates, min_n=20, min_rate=0.6):
    return {k: r for k, r in rates.items() if r[0] >= min_n and r[1] >= min_rate * r[0]}


def hebrew_features(code, ch):
    """{Hebrew key: (token row, {(feature, value)})} of a chapter's verbs (orig/heb.sqlite), in the names of
    lang.greek_features (see DIMS above for what is mapped)"""
    import sqlite3
    con = sqlite3.connect(os.path.join(ROOT, "orig", "heb.sqlite"))
    con.row_factory = sqlite3.Row
    rows = con.execute("select * from tokens where book=? and ch=?", (code.upper(), ch)).fetchall()
    neg = {r["clause"] for r in rows if r["lemma"] in HEB_NEG and r["clause"]}
    obj = {}
    for r in rows:
        if r["role"] == "o" and r["pos"] in ("suffix", "pronoun") and r["person"] and r["clause"]:
            obj.setdefault(r["clause"], f"{'123'[['first', 'second', 'third'].index(r['person'])]}{(r['number'] or 's')[:1]}")
    out = {}
    for r in rows:
        if r["pos"] != "verb":
            continue
        fv = set()
        num = {"dual": "plural"}.get(r["number"], r["number"])
        mood = HEB_MOOD.get(r["type"])
        if r["type"] == "wayyiqtol":
            mood = "indicative"
            fv |= {("tense", "aorist"), ("tense+mood", "aorist.indicative")}
        if mood:
            fv.add(("mood", mood))
        if num:
            fv.add(("number", num))
        if r["person"] in ("first", "second", "third") and num:
            fv |= {("person", r["person"]), ("person+number", f"{r['person'][:1]}{num[:1]}")}
            if mood in ("subjunctive", "imperative"):
                fv.add(("person+number+mood", f"{r['person'][:1]}{num[:1]}.{mood}"))
        if r["clause"] in neg:
            fv.add(("negated", "yes"))
        if r["clause"] in obj:
            fv.add(("object", obj[r["clause"]]))
        out[r["key"]] = (r, fv)
    return out


def draft_words(pname, code, ch):
    """{verse: {Hebrew key: [exact tokens of the draft words tagged with it]}} of an OT chapter: its .tagged working
    copy, else the tagging rebuilt from the .txt and .align (full_align.tag)"""
    import full_align as F
    from project import project_dir
    P = __import__("langtools").Project(pname)
    tg = os.path.join(project_dir(pname), code, f"{code}{ch:03d}.tagged")
    text = open(tg, encoding="utf-8").read() if os.path.exists(tg) else F.tag(pname, code, ch)[0]
    text = F.ADDED.sub("", text)
    bits = re.split(r"(?<![\w>.])v(\d+)(?=\s)", text)
    out = {}
    for i in range(1, len(bits) - 1, 2):
        v, body = int(bits[i]), bits[i + 1]
        num = {n: keys for n, _, _, keys in F.numbering(code.upper(), f"{code.upper()} {ch}:{v}")}
        words = collections.defaultdict(list)
        for w, ns in re.findall(r"(\S+?)\^(\d+(?:,\d+)*)", body):
            for n in ns.split(","):
                for k in num.get(int(n), []):
                    words[k] += P.tok.tokens(w, exact=True)
        out[v] = dict(words)
    return out


def chain_review(pname, code, ch, P=None, S=None, cap=12):
    """REVIEW lines for chapter_check.py: the verbs of an OT chapter whose draft words lack the part the store says
    marks a feature the Hebrew verb has (checked: features the human NT marks on 60% of such verbs or more, 20 or more;
    only words with a verb prefix);
    [] without chain affixes that mark a Greek feature, or without the NT aligned to the Greek"""
    import langtools as LT
    import lang
    P = P or LT.Project(pname)
    if not os.path.exists(lang.db_path(P)):
        return []
    S = S or load(pname, P)
    if not S or not S.chain:
        return []
    G = grammar.load(pname)
    M = marking(G)
    if not M:
        return []
    ok = checked(human_rates(pname, P, S, M))
    if not ok:
        return []
    heb = hebrew_features(code, ch)
    plain = lambda x: S.plain(x.strip("-="))
    out, by = [], collections.Counter()
    for v, words in sorted(draft_words(pname, code, ch).items()):
        for key, ws in words.items():
            if key not in heb:
                continue
            r, fv = heb[key]
            ws = verb_words(S, G, ws)
            if not ws:
                continue
            for (dim, label), forms in expected(M, fv).items():
                if (dim, label) not in ok or carried(S, M, dim, fv, ws):
                    continue
                by[(dim, label)] += 1
                if by[(dim, label)] > cap:
                    continue
                n, k, _ = ok[(dim, label)]
                have = [m for w in ws for m in S.split(w) if m.slot != "stem"]
                near = [m.form for m in have if any(m.position == p and plain(m.form) == plain(f) and m.form != f
                                                    for f, p in forms)]
                out.append(f"word parts {ch}:{v} {' '.join(ws)} ({r['text']} {r['gloss'] or ''}, {r['morph']}): {dim} "
                           f"{label}: none of {', '.join(sorted(f for f, _ in forms))}" + (f" (written {', '.join(near)}: other marks)" if near else "")
                           + f"; the human NT marks it on {k / n:.0%} of {n} such verbs")
    for (dim, label), n in by.items():
        if n > cap:
            out.append(f"word parts: {n - cap} more verbs without {dim} {label}")
    return out


def main(a):
    if len(a) < 2:
        raise SystemExit(__doc__)
    import langtools as LT
    P = LT.Project(a[0])
    S = load(a[0], P) if a[1] != "tone" else None
    if S is None and a[1] != "tone":
        raise SystemExit(f"{a[0]}: the store has no morph entries")
    if a[1] == "try":
        ids = [x for x in a[2:] if not x.startswith("--")]
        try_morphs(a[0], ids, P, S, write="--write" in a)
        return
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
    if a[1] == "rates":
        M = marking(grammar.load(a[0]))
        rates, ok = human_rates(a[0], P, S, M), None
        ok = checked(rates)
        print(f"{a[0]}: the confirmed affixes that mark a Greek feature, on the NT's verbs with it (checked in the loop: "
              "marked on 60% or more of 20 or more)")
        for (dim, label), (n, k, forms) in sorted(rates.items()):
            print(f"  {dim:9} {label:34} {', '.join(sorted(f for f, _ in forms)):18} {k:5}/{n:<5} {k / n:4.0%}"
                  + ("  checked" if (dim, label) in ok else ""))
        return
    if a[1] == "review":
        for l in chain_review(a[0], a[2], int(a[3]), P, S):
            print(l)
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
