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
"0", "1", ... count from the word's start ("0" the first: be- affirmative, grave on the first and acute on the last);
a tone entry's optional `with` (a prefix form or a list) reads the pattern only on words beginning with one of them;
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
An affix's form may carry a tone mark that orthography.ignore_marks drops for finding words (aá- past beside aa-,
one tone apart; bē- beside be-, with or without positions): the parse runs on the plain letters, and the label follows
the mark as written (tone_label).
Hyphens: a store part written with one (`written`: hyphen / both) comes off a hyphen word whole; before the hyphen a chain
of such prefixes is read as fused ones would be (ge-mbo-), as a hyphen may have no grammar of its own. A protected
word is protected inside a hyphen word too (zita-te). A word entry's `parts` give its analysis by hand (nigi =
ni- + -ge written gi); an affix's `variants` the forms it takes by vowel harmony (docs/language-store.md).

    S = morphs.load(<project>)          None when the store has no morph entries
    S.split(exact_token)                [Morph(slot, form, text)]: text is the morph as written; ''.join of the texts,
                                        with the tone morph's marks put back, rebuilds the token (S.rebuild)
    S.labels(exact_token)               {"qo-", "-eav", "tone-proh", ...}: the morph forms, for matching

    python3 scripts/morphs.py <project> check      every corpus token rebuilt from its morphs; what the view finds
    python3 scripts/morphs.py <project> try [id ...] [--write]
        each affix entry measured on the NT aligned to the Greek (lang.py build): n, stems, and for the feature its
        `greek` names the lift and odds ratio (try_morphs); --write records them and a claim with its rerun recipe
    python3 scripts/morphs.py <project> try --seeds [seed id ...] [--write]
        the affix seeds (profile/seeds.json: a related language's forms, scripts/seeds.py) measured the same way, as if
        they were in the store; --write records one claim per seed (claim:seed.<name>, seed: <id>), the seeds unchanged
    python3 scripts/morphs.py <project> audit [id ...] [--route nt|ot|lxx|vamvas|agree|all]
        each affix checked on the words it splits: tokens, stems, stems also bare or with another affix of the slot, the
        feature's share with and without it on the same stems (on every host word without it when its stems never occur
        without it, and said so), its top words with their Greek, the words against it, and a verdict: confirm,
        protect-words (as kind `word` entries), restrict, retire (audit; read-only). --route: the NT aligned to the
        Greek (nt, the default), the OT books linked to the Hebrew read by the Hebrew token (ot), its LXX word (lxx) or
        its Vamvas word (vamvas), or all four (all; scripts/ot_routes.py), one row per route and a combined verdict:
        confirm, re-label, nt-only, ot-only, or the NT's own; agree (scripts/agree_route.py, in a list: nt,agree): an
        `agree` claim (subject/object class or gender) against the verb's own subject or object noun in the target.
        Ids of superseded entries are measured as if live again
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
import collections, os, re, sys, types, unicodedata
from typing import NamedTuple

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
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
        # `with`: the prefixes the pattern belongs to (be-: grave on the first, acute on the last is its affirmative);
        # the pattern is read only on a word that begins with one of them (plain letters)
        w = e.get("with") or []
        self.with_ = [x.strip("-=").lower() for x in ([w] if isinstance(w, str) else w)]

    def match(self, spec, cl, plain=None):
        """[(cluster index, mark)] the pattern takes from the word, or None; plain: the word's plain letters (for `with`)"""
        if self.with_ and not (plain and any(plain.startswith(x) for x in self.with_)):
            return None
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
                k = int(at)                       # negative: from the end; 0, 1, ...: from the start
                if (len(u) < -k if k < 0 else len(u) <= k) or mark not in spec.marks_at(cl, u[k]):
                    return None
                took.append((u[k], mark))
        return took


class Segmenter:
    def __init__(self, G, orth, vocab, classes=None):
        self.spec = ToneSpec(orth)
        self.ignore = {CH(m) for m in (orth or {}).get("ignore_marks") or []}
        # parts written with a hyphen (a morph's `written`: "fused", the default; "hyphen": only as a whole piece before
        # or after a hyphen; "both"): a word with an internal hyphen is one word with a boundary inside. A prefix written
        # so is the whole first piece (a bound person/TAM part before the stem: x-stem), a suffix the whole last piece
        # (a clitic: noun-postposition); what is between is segmented as a word. Grammatical tone is read on the whole
        # word, across the hyphen. A "hyphen" morph never comes off a fused word
        wr = lambda e: e.get("written") or "fused"
        self.hy_pre = {self.plain(e["form"].strip("-=")): e["form"] for e in G.morphs
                       if e.get("slot") == "prefix" and wr(e) in ("hyphen", "both") and e.get("form", "").strip("-=")}
        self.hy_suf = {self.plain(e["form"].strip("-=")): e["form"] for e in G.morphs
                       if e.get("slot") == "suffix" and wr(e) in ("hyphen", "both") and e.get("form", "").strip("-=")}
        self.hyphen = bool(self.hy_pre or self.hy_suf)
        if any(wr(e) == "hyphen" for e in G.morphs):
            G = types.SimpleNamespace(morphs=[e for e in G.morphs if wr(e) != "hyphen"], words=getattr(G, "words", []))
        aff = lambda slot, host=None: sorted({self.plain(e["form"].strip("-=")) for e in G.morphs if e.get("slot") == slot
                                              and e.get("form") and (host is None or e.get("host") == host)} - {""},
                                             key=len, reverse=True)
        self.pre, self.inf, self.suf = aff("prefix"), aff("infix"), aff("suffix")
        # affix chains (a Bantu verb: ni-tu-ka-mu-sohoz-a): morph entries with a `position`, prefixes counted from the
        # word's start, suffixes from the stem outward; several of them per word, each position once, in order
        self.chain = any(e.get("position") for e in G.morphs if e.get("slot") in ("prefix", "suffix"))
        # affixes told apart by tone alone (aá- past beside aa- future; bē- sequential beside be-): forms with an
        # ignored mark, matched on their plain letters, labelled by the mark as written: {(slot, position, plain):
        # {written: store form}}; an affix without a position is at 0
        self.tone_forms = collections.defaultdict(dict)
        for e in G.morphs:
            fm = unicodedata.normalize("NFC", (e.get("form") or "").lower())
            if e.get("slot") in ("prefix", "suffix") and fm.strip("-="):
                self.tone_forms[(e["slot"], int(e.get("position") or 0), self.plain(fm.strip("-=")))][fm.strip("-=")] = fm
        self.tone_forms = {k: v for k, v in self.tone_forms.items() if len(v) > 1 or any(w != k[2] for w in v)}
        # vowel harmony (-ge written -gi after i): an affix entry's `variants`, [{"written": "-gi", "after": "i"}]: the
        # written form, after a part ending in one of `after`'s letters, is this morph. A written form that is an affix of
        # its own keeps that reading; where the two clash the store settles it word by word (a word entry's `parts`)
        self.variants = collections.defaultdict(list)    # (slot, plain written) -> [(after letters, store form)]
        for e in G.morphs:
            for v in e.get("variants") or []:
                wf = self.plain(v.get("written", "").strip("-="))
                if wf and e.get("slot") in ("prefix", "suffix"):
                    self.variants[(e["slot"], wf)].append((self.plain(v.get("after") or ""), e["form"]))
        if self.chain:
            def by_pos(slot, hosts=None):
                out = collections.defaultdict(set)
                for e in G.morphs:
                    # the host filter is the chain's: an affix without a position is not part of a chain and comes
                    # off any word, as in a store without positions (a position switched on for two prefixes must not
                    # stop the store's other affixes)
                    if (e.get("slot") == slot and e.get("form", "").strip("-=")
                            and (hosts is None or not e.get("position") or (e.get("host") or "any") in hosts)):
                        out[int(e.get("position") or 1)].add(self.plain(e["form"].strip("-=")))
                return {p: sorted(v, key=len, reverse=True) for p, v in sorted(out.items())}
            self.pre_at, self.suf_at = by_pos("prefix"), by_pos("suffix")
            # (slot, position, plain form) of the affixes the store gives a position: the others are parsed at
            # position 1 and reported without one (position 0, as the store has them)
            self.positioned = {(e["slot"], int(e["position"]), self.plain(e["form"].strip("-=")))
                               for e in G.morphs if e.get("position") and e.get("slot") in ("prefix", "suffix")
                               and (e.get("form") or "").strip("-=")}
            self.chain_hosts = {e.get("host") or "any" for e in G.morphs if e.get("position")} - {"any"}
            self.at_for = {}                              # hosts -> (prefixes, suffixes) by position
            for hs in [frozenset({"any", h}) for h in self.chain_hosts] + [frozenset({"any"})]:
                self.at_for[hs] = (by_pos("prefix", hs), by_pos("suffix", hs))
        hosts = {e.get("host") for e in G.morphs if e.get("slot") in ("prefix", "suffix")}
        # words never split: free morphs (a pronoun, a conjunction) and the store's protected words (kind word: a name,
        # a word that only begins like a prefix: Danish uge 'week', not u-ge); matched on plain lowercase letters
        self.free = {self.plain(e["form"]) for e in G.morphs if e.get("slot") == "free" and e.get("form")}
        self.protected = {self.plain(e["form"]) for e in getattr(G, "words", []) if e.get("form")}
        # a word entry's `parts` (an analysis the store settles by hand: nigi = ni- + -ge written gi, by vowel
        # harmony, not ni- + -gi): [{"form": "ni-", "text": "ni"}, {"form": "-ge", "text": "gi"}]; the texts, joined, are
        # the word's plain letters; a part whose form is a stem's has no hyphen (or is "" for none)
        self.analysed = {}
        for e in getattr(G, "words", []):
            ps = e.get("parts")
            if ps and e.get("form") and "".join(self.plain(x.get("text", "")) for x in ps) == self.plain(e["form"]):
                self.analysed[self.plain(e["form"])] = [(x.get("form", ""), self.plain(x.get("text", ""))) for x in ps]
        self.free |= self.protected
        self.pairs_by_host = {h: {(p, q) for p in aff("prefix", h) for q in aff("suffix", h)} for h in hosts}
        self.tones = [ToneMorph(e) for e in G.morphs if e.get("slot") == "tone" and e.get("tone_pattern")]
        if self.spec.written in ("letters", "none"):
            self.tones = []
        self.vocab = collections.Counter()
        for w, n in (vocab.items() if isinstance(vocab, dict) else ((w, 1) for w in vocab)):
            # with hyphen parts, a piece after a hyphen (a tokeniser's "-x") is the rest of a word: evidence for its stem
            self.vocab[self.plain(w[1:] if self.hyphen and w.startswith("-") and len(w) > 1 else w)] += n
        self.forms = collections.defaultdict(collections.Counter)  # a possible stem -> {(prefix, suffix): tokens}
        self.min_stem = 2 if self.chain else 3
        for w, n in self.vocab.items():
            if w in self.protected:                       # a protected word is no evidence for a split either
                continue
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
        # and the affixes `try` found productive by their Greek feature (`productive: true`): taken off every word,
        # they still mark it (a negation suffix on verbs whose stems seldom occur in another form)
        for e in G.morphs:
            fm = self.plain(unicodedata.normalize("NFC", (e.get("form") or "").lower()).strip("-="))
            if e.get("productive") is True and fm and e.get("slot") in ("prefix", "suffix"):
                self.productive.add(fm + "-" if e["slot"] == "prefix" else "-" + fm)
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
        then the one with more of the chain's own (positioned) affixes: where a form is both a chain affix of this host and
        an affix without a position (an infinitive oku- at 2 beside a class-15 noun prefix oku-), the chain's reading wins
        on the words of its host; then the stem with most other forms. cut_ok(n): a boundary n letters from the start may
        be cut"""
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
                    own = sum(("prefix", p, a) in self.positioned for p, a in pc) + sum(
                        ("suffix", p, a) in self.positioned for p, a in sc)
                    key = (lp + ls, -len(pc) - len(sc), fit(pc, sc), own, ev)
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

    def split(self, w, tones=True):
        """[Morph] of an exact token, in the order prefix, infix, stem, tone, suffix (a word with hyphen parts: the
        hyphen prefix first, the hyphen suffixes last). tones=False: no grammatical tone is read (a word's inside)"""
        key = w if tones else ("\0", w)
        if key not in self.cache:
            r = self.split_analysed(w, tones)
            r = r or (self.split_hyphen(w, tones) if self.hyphen and "-" in w.strip("-") else None)
            self.cache[key] = r or self.split_plain(w, self.tones if tones else ())
        return self.cache[key]

    def split_analysed(self, w, tones=True):
        """a word the store analyses by hand (a word entry's `parts`): its parts cut from the written word, or None"""
        ps = self.analysed.get(self.plain(w))
        if not ps:
            return None
        cl = clusters(w.lower())
        tone = self.read_tone(cl, self.tones) if tones else None
        if tone:
            cl = list(cl)
            for i, m in tone[1]:
                cl[i] = cl[i].replace(m, "", 1)
        idx = [0]
        for c in cl:
            idx.append(idx[-1] + len(self.plain(c)))
        out, i, stem = [], 0, False
        for form, text in ps:
            if idx[i] + len(text) not in idx:
                return None                              # a part ends inside a letter's marks
            k = idx.index(idx[i] + len(text))
            t = unicodedata.normalize("NFC", "".join(cl[i:k]))
            slot = "prefix" if form.endswith("-") and not form.startswith("-") else "suffix" if form.startswith("-") and not form.endswith("-") \
                else "infix" if form.startswith("-") else "stem"
            if slot == "suffix" and not stem:
                out.append(Morph("stem", "", "")); stem = True
                if tone:
                    out.append(Morph("tone", tone[0].form, " ".join(f"{a}:U+{ord(m):04X}" for a, m in tone[1])))
            if slot == "stem":
                out.append(Morph("stem", self.plain(t), t)); stem = True
                if tone:
                    out.append(Morph("tone", tone[0].form, " ".join(f"{a}:U+{ord(m):04X}" for a, m in tone[1])))
            else:
                out.append(Morph(slot, form, t))
            i = k
        if not stem:
            out.append(Morph("stem", "", ""))
            if tone:
                out.append(Morph("tone", tone[0].form, " ".join(f"{a}:U+{ord(m):04X}" for a, m in tone[1])))
        return out if i == len(cl) else None

    def prefix_cover(self, f):
        """the store prefixes that make up the whole plain piece f before a hyphen, in order (fewest pieces), or None:
        a hyphen has no grammar of its own, so ge-mbo- before it is two prefixes, as fused"""
        forms = set(self.hy_pre) | set(self.pre)
        best = {0: []}
        for i in range(len(f)):
            if i not in best:
                continue
            for p in forms:
                if p and f.startswith(p, i) and (i + len(p) not in best or len(best[i]) + 1 < len(best[i + len(p)])):
                    best[i + len(p)] = best[i] + [p]
        return best.get(len(f))

    def read_tone(self, cl, tones):
        pl = self.plain("".join(cl))
        for t in tones:
            took = t.match(self.spec, cl, pl)
            if took:
                return t, took
        return None

    def split_hyphen(self, w, tones=True, whole=False):
        """a word with an internal hyphen and a store part written with one: [hyphen prefix] + its inside segmented +
        [tone] + [hyphen suffixes], or None (the word is segmented as any other). whole: the inside is not segmented (a
        name: Zelani-ko is the name + a clitic)"""
        cl = clusters(w.lower())
        if self.plain("".join(cl)) in self.free:
            return None
        hy = [i for i, c in enumerate(cl) if c == "-" and 0 < i < len(cl) - 1 and cl[i - 1] != "-"]
        if hy and self.plain("".join(cl[:hy[0]])) in self.free:
            return None                                  # a protected word before the hyphen (zita-te): no prefix off it
        if not hy:
            return None
        piece = lambda a, b: self.plain("".join(cl[a:b]))
        a, b, pre, post = 0, len(cl), [], []
        f = piece(0, hy[0])
        cover = None
        if f in self.hy_pre:
            a, hy = hy[0] + 1, hy[1:]
        elif f not in self.free and f and (cover := self.prefix_cover(f)) and len(cover) > 1 and cover[-1] in self.hy_pre:
            a, hy = hy[0] + 1, hy[1:]                    # a prefix chain before the hyphen, its last part one written so
        while hy and piece(hy[-1] + 1, b) in self.hy_suf:
            post.insert(0, (hy[-1], b, self.hy_suf[piece(hy[-1] + 1, b)]))
            b = hy[-1]
            hy = hy[:-1]
        if not a and not post:
            return None
        tone = self.read_tone(cl, self.tones) if tones else None
        if tone:
            cl = list(cl)
            for i, m in tone[1]:
                cl[i] = cl[i].replace(m, "", 1)
        cut = lambda x, y: unicodedata.normalize("NFC", "".join(cl[x:y]))
        if a and cover and len(cover) > 1:
            out, x = [], 0
            for p in cover:                              # each prefix's clusters: its plain letters from x
                y = x
                while y < a - 1 and len(self.plain("".join(cl[x:y]))) < len(p):
                    y += 1
                last = p == cover[-1] and y >= a - 1
                t = cut(x, a if last else y)
                out.append(Morph("prefix", self.tone_label("prefix", 0, p, t.rstrip("-")) if p not in self.hy_pre or last
                                 else self.hy_pre[p], t))
                x = y
        else:
            out = [Morph("prefix", self.tone_label("prefix", 0, f, cut(0, a).rstrip("-")) if (("prefix", 0, f) in self.tone_forms)
                         else self.hy_pre[f], cut(0, a))] if a else []
        inner = ([Morph("stem", self.plain(cut(a, b)), cut(a, b))] if whole else self.split(cut(a, b), tones=False)) if b > a else []
        k = next((n for n, m in enumerate(inner) if m.slot == "stem"), len(inner)) + 1
        out += inner[:k] + ([Morph("tone", tone[0].form, " ".join(f"{i}:U+{ord(m):04X}" for i, m in tone[1]))]
                           if tone else []) + inner[k:]
        out += [Morph("suffix", form, cut(x, y)) for x, y, form in post]
        return out

    def split_plain(self, w, tone_morphs=()):
        """split's work, uncached; tone_morphs: the grammatical tone patterns to read"""
        cl = clusters(w.lower())
        tone = None
        for t in tone_morphs:
            took = t.match(self.spec, cl, self.plain("".join(cl)))
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
        for p, q in (self.pairs if s not in self.free else ()):
            if s == p + q and at(len(p)):
                k = at(len(p))
                return [Morph("prefix", p + "-", cut(0, k)), Morph("stem", "", "")] + (
                    [Morph("tone", tone[0].form, " ".join(f"{a}:U+{ord(m):04X}" for a, m in tone[1]))] if tone else []) + [
                    Morph("suffix", "-" + q, cut(k, j))]
        blocked = s in self.free or ("-" in s.strip("-") and any(x in self.free for x in s.split("-")))
        if self.chain and not blocked and not w.startswith("-"):
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
                    out.append(Morph("prefix", self.tone_label("prefix", p, a, cut(i, k)), cut(i, k),
                                     p if ("prefix", p, a) in self.positioned else 0))
                    i = k
                if pc and self.inf:                      # an infix after the prefixes, as without a chain
                    r = s[idx[i]:len(s) - sum(len(a) for _, a in sc)]
                    for f in self.inf:
                        if r.startswith(f) and at(idx[i] + len(f)) and len(r) - len(f) >= 3:
                            k = at(idx[i] + len(f))
                            out.append(Morph("infix", "-" + f + "-", cut(i, k)))
                            i = k
                            break
                for p, a in sc:                          # from the outside in; written from the stem outward
                    k = at(idx[j] - len(a))
                    tail.insert(0, Morph("suffix", self.tone_label("suffix", p, a, cut(k, j)), cut(k, j),
                                         p if ("suffix", p, a) in self.positioned else 0))
                    j = k
        elif not blocked and not w.startswith("-"):     # a free morph (a pronoun, a conjunction) is a word
            best = None                                  # prefix and suffix chosen together: génanimák = ge-nanim-ák
            sufs = list(self.suf) + [v for (sl, v) in self.variants if sl == "suffix" and v not in self.suf]
            for p in [""] + [p for p in self.pre if s.startswith(p) and at(len(p))]:
                for q in [""] + [q for q in sufs if s.endswith(q) and at(len(s) - len(q)) and len(s) > len(p) + len(q)
                                 and (q in self.suf or self.variant_of("suffix", q, s[:len(s) - len(q)]))]:
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
                    out.append(Morph("prefix", self.tone_label("prefix", 0, p, cut(0, i)), cut(0, i)))
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
                    lab = self.tone_label("suffix", 0, q, cut(j, len(cl))) if q in self.suf else \
                        self.variant_of("suffix", q, s[:len(s) - len(q)])
                    tail = [Morph("suffix", lab, cut(j, len(cl)))]
            else:
                tail = []
        else:
            tail = []
        out.append(Morph("stem", s[idx[i]:idx[j]], cut(i, j)))
        if tone:
            out.append(Morph("tone", tone[0].form, " ".join(f"{a}:U+{ord(m):04X}" for a, m in tone[1])))
        out += tail
        return out

    def variant_of(self, slot, written, before):
        """the store form a harmony variant stands for after the plain text `before` (a suffix) / before it (a prefix), or
        None"""
        for after, form in self.variants.get((slot, written), ()):
            if before and (not after or before[-1] in after):
                return form
        return None

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


def load(pname, P=None, G=None):
    """the project's Segmenter (P: a langtools.Project, else built here; G: a grammar view in place of the store's), or
    None without morph entries"""
    import json
    import langtools as LT
    P = P or LT.Project(pname)
    G = G or grammar.load(pname)
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


METHOD = "morphs try 2"
HOSTS = {"verb": ("verb",), "noun": ("noun",), "adj": ("adj",), "pron": ("pron",)}  # any other host: every class


def hyphen_words(con):
    """{(book, ch, v, pos): the whole word} of the NT tokens (lang.py build) where the tokeniser split a word at its
    hyphens (a piece "-x" joins the token before it): tamu + -ko -> tamu-ko, for a store with hyphen parts"""
    out, cur = {}, None
    for b, c, v, p, surf, raw in con.execute("select book, ch, v, pos, surface, raw from nt_tokens order by book, ch, v, pos"):
        if (surf or "").startswith("-") and cur and cur[0] == (b, c, v):
            cur[1].append(p)
            cur[2] += "-" + (raw or "")
        else:
            if cur and len(cur[1]) > 1:
                out.update({(*cur[0], q): cur[2] for q in cur[1]})
            cur = [(b, c, v), [p], raw or ""]
    if cur and len(cur[1]) > 1:
        out.update({(*cur[0], q): cur[2] for q in cur[1]})
    return out


def affix_tokens(pname, S):
    """[(Greek class, {(affix, position)}, stem, Greek features, even verse, ref, token, Greek lemma)]: one row per
    target token form and Greek word of the NT linked to each other, the token segmented by the store's morphs"""
    import sqlite3
    import lang
    _, con = lang.connect(pname)
    con.row_factory = sqlite3.Row
    gtok = {r["key"]: r for r in con.execute("select * from g.tokens")}
    feat = lang.greek_features(con, gtok)
    rows = con.execute("""select l.book as bk, l.ch as cc, l.v as vv, l.pos as pp, t.raw, g.* from nt_links l join nt_tokens t on t.book=l.book and t.ch=l.ch
        and t.v=l.v and t.pos=l.pos join g.tokens g on g.key=l.key""").fetchall()
    hw = hyphen_words(con) if getattr(S, "hyphen", False) else {}   # a piece of a hyphen word: the whole word
    toks, seen = [], set()
    for r in rows:
        w = hw.get((r["bk"], r["cc"], r["vv"], r["pp"]), r["raw"])
        k = (w, r["key"])
        if k in seen or not r["raw"]:
            continue
        seen.add(k)
        ms = S.split(w)
        stem = next((m.form for m in ms if m.slot == "stem"), "")
        toks.append((r["class"], {(m.form, m.position) for m in ms if m.slot != "stem"}, stem, feat(r), r["vv"] % 2 == 0,
                     f"{r['bk'].upper()} {r['cc']}:{r['vv']}", w, r["lemma"]))   # w: a hyphen word whole
    return toks


def comes_off(e, labs):
    """the affix entry is among a token's parts ({(form, position)}); an entry without a position at any"""
    form, pos = e["form"], int(e.get("position") or 0)
    return (form, pos) in labs or (not pos and any(f == form for f, _ in labs))


def measure(e, toks, want, only=None):
    """an affix entry on its host words ({"all"|"even": (n, stems, lift, odds)}, the host words it comes off): want the
    Greek features ({name: {values}}) whose lift and odds are measured; only: the host words to count, by their Greek
    features (transitive clauses: {"transitive": {"yes"}})"""
    form, pos = e["form"], int(e.get("position") or 0)
    cls = HOSTS.get(e.get("host"))
    has = lambda fv, w: all(any((k, v) in fv for v in vs) for k, vs in w.items())
    out, host_on = {}, []
    for half in ("all", "even"):
        host = [t for t in toks if (cls is None or t[0] in cls) and (half == "all" or t[4]) and (not only or has(t[3], only))]
        on = [t for t in host if comes_off(e, t[1])]
        n, stems = len(on), len({t[2] for t in on})
        lift = odds = None
        if want and n and host:
            k = sum(has(t[3], want) for t in on)
            base = sum(has(t[3], want) for t in host)
            lift = round((k / n) / (base / len(host)), 2) if base else 0.0
            rest, krest = len(host) - n, base - k   # the odds of the feature where it comes off, against elsewhere
            odds = round(((k + .5) / (n - k + .5)) / ((krest + .5) / (rest - krest + .5)), 2)
        out[half] = (n, stems, lift, odds)
        if half == "all":
            host_on = on
    return out, host_on


def with_seeds(pname):
    """the store's grammar with the seeds' affixes added (scripts/seeds.py): what the segmenter would make of the corpus
    if they held. -> (G, seeds to measure, seeds the store already has [(seed, store morph)], seeds the try can't
    measure [(seed, why)], donor). A seed's form is normalised by its slot (ta-, -ibw, -ir-), a suffix's position is
    the store's where the store has the same gloss at one position (suffixes are numbered from the stem outward, and
    a store may count the extensions apart), and a seed the store already has (form, slot,
    host, position) isn't measured again: it would measure the store's morph"""
    import seeds
    d = seeds.of_project(pname) or {}
    G = grammar.load(pname)
    plain = lambda f: unicodedata.normalize("NFC", (f or "").strip("-=").lower())
    store = [m for m in G.morphs if m.get("slot") in ("prefix", "infix", "suffix")]
    at = collections.defaultdict(set)                 # a suffix's position by its gloss, where the store has one
    for m in store:
        if m.get("position") and m["slot"] == "suffix":
            at[(m["slot"], m.get("host"), m.get("value"))].add(m["position"])
    pos_by_gloss = {k: next(iter(v)) for k, v in at.items() if len(v) == 1}
    sd, same, skip = [], [], []
    for e in d.get("entries", []):
        if e.get("kind") != "morph" or e.get("slot") not in ("prefix", "infix", "suffix"):
            continue
        f = seeds.norm_form(e)
        if not f:
            skip.append((e, f"{e.get('form')!r} is not one form (a zero or an alternation: a feature)"))
            continue
        if e.get("host") not in ("verb", "noun"):
            skip.append((e, f"host {e.get('host')}: the try measures verb and noun affixes"))
            continue
        x = dict(e, form=f, status="observed")
        p = pos_by_gloss.get((e["slot"], e.get("host"), e.get("value")))
        if p and e.get("position") and p != e["position"]:
            x["position"], x["seed_position"] = p, e["position"]
        m = next((m for m in store if plain(m["form"]) == plain(f) and m["slot"] == e["slot"]
                  and m.get("host") in (e.get("host"), "any") and (not m.get("position") or not x.get("position")
                                                                    or m["position"] == x["position"])), None)
        if m:
            same.append((e, m))
            continue
        sd.append(x)
    G.morphs = G.morphs + sd
    G._by_id.update({e["id"]: e for e in sd})
    return G, sd, same, skip, d.get("donor")


def seed_result(n, stems, odds, todds, want, min_n=20, min_stems=5, min_odds=2.0):
    """(result, claim verdict) of a measured seed: confirmed; refuted (enough cases, the feature not marked); thin (too
    few to say: stays open); absent (the form never comes off); counts only (no Greek feature named)"""
    if not n:
        return "absent", "contradicted"
    if n < min_n or stems < min_stems:
        return "thin", "open"
    if not want:
        return "counts only", "open"
    if (odds or 0) >= min_odds and (todds or 0) >= min_odds:
        return "confirmed", "confirmed"
    return "refuted", "contradicted"


def write_seed_claims(pname, P, res, same, skip, donor, by="script:morphs.py try --seeds"):
    """one claim per seed (claim:seed.<name>, `seed: <seed id>`, `result`): measured, already in the store (`same_as`),
    or not measurable by the try (open); the seed stays as it is"""
    import json, datetime
    f = os.path.join(P.profile, "observations.json")
    d = json.load(open(f, encoding="utf-8"))
    today = datetime.date.today().isoformat()
    NEXT = {"confirmed": "write the morph as the corpus has it (seed: this seed), or say why not",
            "refuted": "the form doesn't mark the category here: look for the language's own form of it",
            "absent": "the form doesn't occur as an affix here: look for the language's own form of the category",
            "thin": "too few cases to say: look at them, or test the category another way",
            "counts only": "the seed names no Greek feature: look at the words it comes off",
            "in store": "the store has it already: nothing to do",
            "untestable": "test it by hand (concord.py), or as a feature"}
    rows = []
    for e, n, stems, lift, tl, odds, todds, verdict, refs, prod in res:
        g = " ".join(f"{a}={'|'.join(b) if isinstance(b, list) else b}" for a, b in sorted((e.get("greek") or {}).items()))
        result, verdict = seed_result(n, stems, odds, todds, e.get("greek"))
        fig = (f"n {n}, stems {stems}" + (f", lift {lift} (even verses {tl}), odds ratio {odds} (even verses {todds})"
                                          if lift is not None else "") + (f"; first verses {', '.join(refs)}" if refs else "")
               + (f"; measured at the store's position {e['position']} (the seed's {e['seed_position']})"
                  if e.get("seed_position") else ""))
        rows.append((e, result, verdict, fig, g, {}))
    for e, m in same:
        rows.append((e, "in store", "confirmed", f"the store has it: {m['id']} ({m['form']}, {m.get('status')})", "",
                     {"same_as": m["id"]}))
    for e, why in skip:
        rows.append((e, "untestable", "open", why, "", {}))
    for e, result, verdict, fig, g, extra in rows:
        c = {"id": f"claim:seed.{e['id'].removeprefix('seed:')}", "kind": "claim", "seed": e["id"], "result": result,
             "value": f"the {donor} affix {e['form']} ({e.get('slot')}" + (f", position {e['position']}" if e.get("position")
                                                                           else "") + ") occurs here" + (f", marking {g}" if g else ""),
             "area": "morph", "source": e["id"], "tests": ["corpus", "greek"] if g else ["corpus"], "figures": fig,
             "verdict": verdict, "next": NEXT[result], "confidence": "medium" if verdict == "confirmed" else "low",
             "method": "corpus-derived", "by": by, "date": today, "status": "observed"} | extra
        d["entries"] = [x for x in d["entries"] if x.get("id") != c["id"]] + [c]
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(f, "a").write("\n")
    print(f"written: {len(rows)} seed claim(s) into {os.path.relpath(f)}")


def try_morphs(pname, ids, P, S, write=False, by="script:morphs.py", min_n=20, min_stems=5, min_odds=2.0, G=None):
    """Each affix entry (prefix, infix, suffix; those named, else all) measured on the NT aligned to the Greek, under the
    store's whole segmentation (a chain's other affixes included): how often it comes off (n), on how many different
    stems, and, where the entry names the Greek feature it marks (`greek`: {"person+number": "fp"}, the names of
    lang.py report; a list for any of several values, {"mood": ["subjunctive", "imperative"]}), its lift (the feature's
    share among the host words it comes off, over its share among all of them) and its odds ratio (the feature's odds
    where it comes off, against the other host words: unlike the lift not capped for a common feature, the aorist), on
    every verse and on the even verses alone (a second count on half the data).
    Kept: n >= min_n, stems >= min_stems, and both odds ratios >= min_odds (without `greek`: the counts only, verdict
    open).
    Productive: a prefix or suffix with `greek` that the segmenter takes off only where the stem is attested is measured
    a second time as taken off every word that leaves a stem of 3 letters or more; where that is confirmed too and keeps
    at least half its odds ratio (on all verses and on the even ones: it marks the feature about as sharply), it is
    productive (`productive: true`, written with its figures): its words split without a stem of their own elsewhere.
    Where it isn't (a short ending that many other words share), `productive: false`.
    With write: the entry's `stats`, status observed (kept) or open (not), and one claim per entry (id claim:morph.<id>)
    with its rerun recipe and basis, so that grammar.py retest reruns it when the store changes"""
    import json, sqlite3, datetime
    import lang
    G = G or grammar.load(pname)
    cands = [e for e in G.morphs if e.get("slot") in ("prefix", "infix", "suffix") and (not ids or e.get("id") in ids)]
    if ids and len(cands) < len(set(ids)):
        raise SystemExit(f"not affix entries of the store: {', '.join(sorted(set(ids) - {e['id'] for e in cands}))}")
    toks = affix_tokens(pname, S)
    gr = lambda e: " ".join(f"{a}={'|'.join(b) if isinstance(b, list) else b}" for a, b in sorted((e.get("greek") or {}).items()))
    res = []
    for e in cands:
        form, pos = e["form"], int(e.get("position") or 0)
        want = {k: set(v) if isinstance(v, list) else {v} for k, v in (e.get("greek") or {}).items()}
        out, host_on = measure(e, toks, want)
        n, stems, lift, odds = out["all"]
        tl, todds = out["even"][2], out["even"][3]
        kept = n >= min_n and stems >= min_stems and (not want or (odds or 0) >= min_odds and (todds or 0) >= min_odds)
        verdict = ("confirmed" if kept else "contradicted") if want else ("open" if kept else "contradicted")
        refs = list(dict.fromkeys(t[5] for t in host_on))[:3]
        prod = None
        a = form.lower().strip("-=")
        key = a + "-" if e.get("slot") == "prefix" else "-" + a
        if want and e.get("slot") in ("prefix", "suffix") and (key not in S.productive or e.get("productive") is True):
            had = key in S.productive
            S.productive.add(key)
            S.cache = {}
            pout, _ = measure(e, affix_tokens(pname, S), want)
            if not had:
                S.productive.discard(key)
            S.cache = {}
            pn, ps, _, po = pout["all"]
            pto = pout["even"][3]
            prod = (pn >= min_n and ps >= min_stems and (po or 0) >= max(min_odds, 0.5 * (odds or 0))
                    and (pto or 0) >= max(min_odds, 0.5 * (todds or 0)), pn, ps, po, pto)
        res.append((e, n, stems, lift, tl, odds, todds, verdict, refs, prod))
        print(f"  {e['id']:24} {form:7} position {pos or '-'}  n {n:5}  stems {stems:4}"
              + (f"  lift {lift}, odds {odds} (even verses {todds}) for {gr(e)}" if want else "")
              + f"  -> {verdict if n else 'absent (it never comes off)'}"
              + (f"; off every word: n {prod[1]}, stems {prod[2]}, odds {prod[3]} (even verses {prod[4]}) -> "
                 + ("productive" if prod[0] else "not productive") if prod else ""))
    if not write:
        return res
    f = os.path.join(P.profile, "observations.json")
    d = json.load(open(f, encoding="utf-8"))
    today = datetime.date.today().isoformat()
    by_id = {x.get("id"): x for x in d["entries"]}
    for e, n, stems, lift, tl, odds, todds, verdict, refs, prod in res:
        x = by_id[e["id"]]
        if prod:
            x["productive"] = bool(prod[0] and verdict == "confirmed")
            x["stats"] = {**(x.get("stats") or {}), "productive_count": prod[1], "productive_hosts": prod[2],
                          **({"productive_odds": prod[3], "productive_test_odds": prod[4]} if prod[3] is not None else {})}
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
                                                   f"{todds})" if lift is not None else "")
                        + (f"; off every word: n {prod[1]}, stems {prod[2]}, odds ratio {prod[3]} (even verses {prod[4]}): "
                           + ("productive" if prod[0] and verdict == "confirmed" else "not productive") if prod else ""),
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


# ---------- the affix audit: does an affix hold on the words it splits? ----------

AUDIT = {"min_links": 10, "word_links": 3, "off_share": 0.2, "host_share": 0.3, "min_odds": 2.0,
         "protect_max": 0.1, "restrict_min": 0.4, "route_n": 20, "flat": 0.75}


def _odds(k, n, ko, no):
    return round(((k + .5) / (n - k + .5)) / ((ko + .5) / (no - ko + .5)), 2)


def route_stats(e, toks, want, S, A=AUDIT, top=8, words=None, stem_by=None, alt_keys=()):
    """an affix entry on one route's linked rows (affix_tokens' shape): its host links, the claim's share with it and
    on the same stems without it, the odds ratio (against every host link without it when its stems never occur
    without it: odds_basis "all words"), the words against it, its top words, the route's own verdict, and for
    alt_keys the value of each that its links show most (odds, n): the re-label candidates"""
    has = lambda fv, w=want: all(any((k, v) in fv for v in vs) for k, vs in w.items())
    share = lambda ts: sum(has(t[3]) for t in ts) / len(ts) if ts and want else None
    cls = HOSTS.get(e.get("host"))
    mine = [t for t in toks if comes_off(e, t[1])]
    on = [t for t in mine if cls is None or t[0] in cls]
    on_stems = {t[2] for t in on}
    host = [t for t in toks if cls is None or t[0] in cls]
    off = [t for t in host if t[2] in on_stems and not comes_off(e, t[1])]
    basis = "same stems"
    if on and not off:                               # its stems never occur without it: against every host word
        off, basis = [t for t in host if not comes_off(e, t[1])], "all words"
    links, host_links = collections.defaultdict(list), collections.defaultdict(list)
    for t in mine:
        links[S.plain(t[6])].append(t)
        if cls is None or t[0] in cls:
            host_links[S.plain(t[6])].append(t)
    words = words if words is not None else collections.Counter({w: len(ts) for w, ts in links.items()})
    against = {w: n for w, n in words.items() if want and (
        (len(host_links[w]) >= A["word_links"] and share(host_links[w]) < A["off_share"])
        or (len(links[w]) >= A["word_links"] and len(host_links[w]) < A["host_share"] * len(links[w])))}
    off_tok = sum(against.values()) / max(1, sum(words.values()))
    odds = None
    if want and on and off:
        odds = _odds(sum(has(t[3]) for t in on), len(on), sum(has(t[3]) for t in off), len(off))
    if not want:
        verdict = "no-claim"
    elif len(on) < A["min_links"]:
        verdict = "too-few"
    elif odds is not None and odds < A["min_odds"]:
        verdict = "retire"
    else:
        verdict = ("confirm" if off_tok < A["protect_max"] else "protect-words" if off_tok < A["restrict_min"]
                   else "restrict")
    holds = collections.Counter()
    for w, n in words.items():
        if w not in against and stem_by:
            holds[stem_by.get(w, w)] += n
    alt = {}
    for k in alt_keys:                               # the value of k its links show most, against the rest
        vals = collections.Counter(v for t in on for (kk, v) in t[3] if kk == k)
        best = None
        for v, kv in vals.most_common(8):
            ko = sum((k, v) in t[3] for t in off)
            o = _odds(kv, len(on), ko, len(off)) if off else None
            if o is not None and (best is None or o > best[1]):
                best = (v, o, kv / len(on))
        if best:
            alt[k] = best
    return dict(links=len(on), link_stems=len(on_stems), share_with=share(on), links_without=len(off),
                share_without=share(off), odds=odds, odds_basis=basis,
                share_rest=share([t for t in on if S.plain(t[6]) not in against]),
                top=[(w, n, len(links[w]), len(host_links[w]), share(host_links[w]),
                      collections.Counter(t[7] for t in links[w]).most_common(3)) for w, n in words.most_common(top)],
                against=sorted(against.items(), key=lambda x: -x[1]), against_share=off_tok,
                holds=[st for st, _ in holds.most_common(10)], verdict=verdict, alt=alt)


def route_state(r, A=AUDIT):
    """holds / fails / thin / flat / n.a. of one route's result: flat where the feature is on `flat` or more of the
    host links both with it and without it (3rd singular in narrative): no lift is possible, so neither holds nor fails"""
    if r is None or r.get("untestable"):
        return "n.a."
    if r["links"] < A["route_n"] or r["odds"] is None or not (r["share_with"] or r["share_without"]):
        return "thin"                                # too few links, or the feature on none of them: no evidence
    if r["odds"] >= A["min_odds"]:
        return "holds"
    return "flat" if min(r["share_with"] or 0, r["share_without"] or 0) >= A["flat"] else "fails"


def combine(rs, A=AUDIT):
    """(verdict, note) from the routes' results ({route: result}), the design's rules in order: confirm (the NT and an
    OT route hold, none fails), re-label (one route holds, another fails: it marks the holding route's category),
    nt-only (only the NT holds, an OT route fails: possibly the Greek leaking through the alignment; flagged, not
    retired), ot-only (only the OT holds: kept, noted), and else the NT's own verdict (retire, protect-words,
    restrict, too-few, no-claim). A weak route (tense from the Hebrew conjugation) counts, and is named in the note"""
    st = {k: route_state(v, A) for k, v in rs.items()}
    held = [k for k, s in st.items() if s == "holds"]
    failed = [k for k, s in st.items() if s == "fails"]
    weak = [k for k in held if rs[k].get("weak")]
    nt = rs.get("nt")
    base = nt["verdict"] if nt else None
    if not held:
        if failed:
            return "retire", "no route holds"
        return (base, "") if base == "no-claim" else (base or "too-few", "no route has enough links")
    if not failed:
        if "nt" in held and len(held) > 1:
            v = base if base in ("protect-words", "restrict") else "confirm"
            return v, (f"the NT and {', '.join(NAMES_OF[k] for k in held if k != 'nt')} hold"
                       + (" (the Hebrew on the weak reading: tense from the conjugation)" if weak else ""))
        if held == ["nt"]:
            return base, "the Tanakh routes are thin, flat or can't test the claim"
        return "ot-only", f"{', '.join(NAMES_OF[k] for k in held)} hold(s), the NT is thin: kept, noted"
    if held == ["nt"]:
        return "nt-only", (f"only the NT holds; {', '.join(NAMES_OF[k] for k in failed)} fail(s): possibly the Greek "
                           "leaking through the alignment (flagged, not retired)")
    if "nt" not in held and "nt" in failed:
        return "ot-only", (f"{', '.join(NAMES_OF[k] for k in held)} hold(s), the NT fails: kept, noted (the NT may use "
                           "another construction)")
    k = next(x for x in ("hebrew", "vamvas", "lxx", "nt") if x in failed)
    h = next(x for x in ("hebrew", "nt", "vamvas", "lxx") if x in held)
    alt = rs[h].get("alt") or {}
    best = max(alt.items(), key=lambda x: x[1][1]) if alt else None
    prop = f"; its strongest value on {NAMES_OF[h]}: {best[0]}={best[1][0]} (odds {best[1][1]})" if best else ""
    return "re-label", (f"{', '.join(NAMES_OF[x] + (' (weak)' if x in weak else '') for x in held)} hold(s), {', '.join(NAMES_OF[x] for x in failed)} "
                        f"fail(s): it marks the category of the holding route, not the claim as worded{prop}")


HYPHEN_WORD = re.compile(r"[^\W_](?:[\w\u0300-\u036f\u1dc0-\u1dff\ua789]|-(?=\w))*")
NAMES_OF = {"nt": "NT (Greek)", "hebrew": "Tanakh Hebrew", "lxx": "Tanakh LXX", "vamvas": "Tanakh Vamvas", "agree": "agreement"}


def combine_agree(rs, A=AUDIT):
    """combine() with the agreement route (scripts/agree_route.py) beside the feature routes: where it holds and no
    feature route does (a concord has no Greek feature), it confirms (or keeps its own protect-words / restrict); where
    it fails and no feature route holds, retire; else the feature routes' verdict, the agreement route named in the note"""
    ag = rs.get("agree")
    rest = {k: v for k, v in rs.items() if k != "agree"}
    if ag is None:
        return combine(rs, A)
    s = route_state(ag, A)
    base, note = combine(rest, A) if rest else (None, "")
    other = any(route_state(v, A) == "holds" for v in rest.values())
    add = lambda t: f"{note}; {t}" if note else t
    if s == "holds" and not other:
        return (ag["verdict"] if ag["verdict"] in ("protect-words", "restrict") else "confirm"), add(
            f"the agreement route holds (odds {ag['odds']}, n {ag['links']})")
    if s == "fails" and not other:
        return "retire", add(f"the agreement route fails (odds {ag['odds']}, n {ag['links']})")
    if s in ("holds", "fails", "flat"):
        return base, add(f"the agreement route {s}")
    if s == "thin" and base in (None, "no-claim"):     # a claim there is, but too few pairs to judge it
        return "too-few", add(f"the agreement route is thin (n {ag['links']})")
    return (base or ag.get("verdict") or "too-few"), note


def audit(pname, ids, P, S, G=None, top=8, A=AUDIT, routes=("nt",), route_toks=None):
    """Each affix entry (those named, else every live prefix, infix and suffix) checked on the words it splits, on
    each route (routes: nt = the NT aligned to the Greek; hebrew, lxx, vamvas = the target's OT books linked to the
    Hebrew, read by the Hebrew token, its Septuagint word, its Vamvas word: scripts/ot_routes.py):
    - its tokens and stems in the corpus; the stems also seen bare (no affix of the slot) or with another affix of the
      slot (the stem is a real stem, the affix a real choice);
    - per route, with a `greek` feature the route can test (ot_routes.route_want): the feature's share among its
      linked words of the host's class, with the affix and on the same stems without it (a stem's own meaning is no
      evidence for the affix), and the odds ratio of the two; where its stems never occur without it, against every
      host word without it, and said so (odds_basis "all words");
    - its top words, by tokens, with their linked lemmas and their own share of the feature;
    - the words against it: the feature under off_share on word_links or more host links, or host links under
      host_share of the word's links (a noun that only begins like a verb prefix);
    - the NT verdict: retire (odds ratio under min_odds), confirm (the words against it under protect_max of its
      tokens), protect-words (under restrict_min: they become kind `word` entries), restrict (it holds only on the stems
      named), no-claim (no `greek`) or too-few (under min_links host links);
    - with more than one route, the combined verdict (combine): confirm, re-label, nt-only, ot-only, or the NT's own.
    route_toks: {route: rows} in place of reading them (tests). Read-only. -> [dict] per entry; the first route's
    figures at the top level, every route's under "routes", the combined verdict under "combined" """
    import ot_routes as OR
    G = G or grammar.load(pname)
    ents = [e for e in G.morphs if e.get("slot") in ("prefix", "infix", "suffix") and e.get("form")
            and (not ids or e["id"] in ids)]
    if ids and len(ents) < len(set(ids)):
        raise SystemExit(f"not live affix entries of the store: {', '.join(sorted(set(ids) - {e['id'] for e in ents}))}")
    vocab = getattr(S, "vocab_exact", None) or S.vocab     # as written: a tone label needs the word's marks
    if getattr(S, "hyphen", False) and P is not None:      # hyphen parts: the corpus's hyphen words, whole, as well
        vocab = collections.Counter(vocab)                 # each whole, its pieces no longer counted apart
        for r in P.corpus():
            for w in HYPHEN_WORD.findall(r[4]):
                if "-" in w:
                    vocab[w] += 1
                    vocab.subtract(P.tok.tokens(w, exact=True))
        vocab = collections.Counter({w: n for w, n in vocab.items() if n > 0})
    split = {w: S.split(w) for w in vocab}
    stem_of = lambda ms: next((m.form for m in ms if m.slot == "stem"), "")
    route_toks = dict(route_toks or {})
    if "agree" in routes:                            # the agreement route: verb-noun pairs, the store's noun classes
        import agree_route as AR
        if "agree" not in route_toks:
            route_toks["agree"] = AR.pairs(pname, S, P)
        n_classes, a_cache = AR.noun_classes(G), {}
    for r in routes:
        if r == "agree":
            continue
        if r not in route_toks:
            route_toks[r] = affix_tokens(pname, S) if r == "nt" else OR.route_tokens(pname, S, r, P)
    res = []
    for e in ents:
        slot = e["slot"]
        want = {k: set(v) if isinstance(v, list) else {v} for k, v in (e.get("greek") or {}).items()}
        words, stems, stem_by = collections.Counter(), collections.Counter(), {}   # words by their plain letters
        for w, ms in split.items():
            if comes_off(e, {(m.form, m.position) for m in ms if m.slot == slot}):
                words[S.plain(w)] += vocab[w]
                stems[stem_of(ms)] += vocab[w]
                stem_by[S.plain(w)] = stem_of(ms)
        bare, other = set(), set()                       # its stems seen without it
        for w, ms in split.items():
            st = stem_of(ms)
            if st in stems and not comes_off(e, {(m.form, m.position) for m in ms if m.slot == slot}):
                (other if any(m.slot == slot for m in ms) else bare).add(st)
        per = {}
        for r in routes:
            if r == "agree":
                per[r] = AR.stats(e, S, route_toks[r], n_classes, A, top, words, stem_by, a_cache)
                continue
            w2, weak, why = OR.route_want(r, want)
            if want and w2 is None:
                per[r] = dict(untestable=why, verdict="n.a.")
                continue
            x = route_stats(e, route_toks[r], w2 or {}, S, A, top, words, stem_by, OR.ALT_KEYS.get(r, ())
                            if any(k in want for k in ("tense", "mood", "tense+mood")) else
                            ("person+number",) if want else ())
            x["weak"], x["claim"] = weak, w2
            per[r] = x
        first = per[routes[0]] if not per[routes[0]].get("untestable") else route_stats(e, [], {}, S, A, top, words,
                                                                                        stem_by)
        row = dict(entry=e, tokens=sum(words.values()), stems=len(stems), bare=len(bare), other=len(other),
                   **{k: v for k, v in first.items() if k not in ("weak", "claim", "alt")}, routes=per)
        if len(routes) > 1:
            row["combined"] = combine_agree(per, A) if "agree" in per else combine(per, A)
        res.append(row)
    return res


def revive(pname, ids):
    """(grammar view, ids revived): the named entries that are superseded in the store put back as live, to measure
    a retired affix again (audit m:-tez:verb); None and [] when every named entry is live"""
    import json
    f = os.path.join(grammar.profile_dir(pname), "observations.json")
    if not ids or not os.path.exists(f):
        return None, []
    G = grammar.load(pname)
    live = {e["id"] for e in G.morphs}
    old = [dict(e, status="superseded (revived for the audit)") for e in json.load(open(f, encoding="utf-8"))
           .get("entries", []) if e.get("id") in ids and e["id"] not in live and e.get("kind") == "morph"]
    if not old:
        return None, []
    G.morphs = G.morphs + old
    G._by_id.update({e["id"]: e for e in old})
    return G, [e["id"] for e in old]


def print_audit(res, A=AUDIT):
    pc = lambda x: "-" if x is None else f"{x:.0%}"
    for r in res:
        e = r["entry"]
        g = " ".join(f"{k}={'|'.join(v) if isinstance(v, list) else v}" for k, v in (e.get("greek") or {}).items())
        print(f"\n{e['id']}  {e['form']} ({e['slot']}, {e.get('host') or 'any'}"
              + (f", position {e['position']}" if e.get("position") else "") + f"; {g or 'no greek feature'}; "
              f"{e.get('status')})")
        print(f"  tokens {r['tokens']}, stems {r['stems']}; stems also bare {r['bare']}, with another {e['slot']} "
              f"{r['other']}")
        many = len(r["routes"]) > 1
        for name, x in r["routes"].items():
            lab = NAMES_OF[name]
            if x.get("untestable"):
                print(f"  {lab:11} can't test the claim: {x['untestable']}")
                continue
            cl = " ".join(f"{k}={'|'.join(sorted(v))}" for k, v in (x.get("claim") or {}).items())
            print(f"  {lab:11} with it {pc(x['share_with'])} / without {pc(x['share_without'])}"
                  + (" (all host words: its stems never occur without it)" if x["odds_basis"] == "all words" else "")
                  + f"   odds {x['odds']}   n {x['links']} on {x['link_stems']} stems (without: {x['links_without']})"
                  + (f"   [{cl}" + ("; weak: tense from the Hebrew conjugation" if x["weak"] else "") + "]"
                     if name != "nt" else "") + f"   -> {route_state(x, A)}")
            if name == "agree":
                k, n, ko, no = x["cells"]
                print(f"      against every verb without it: {k}/{n} vs {ko}/{no}, odds {x['odds_all']}; pairs "
                      + ", ".join(f"{a} {b}" for a, b in sorted(x["pairs"].items())))
            for k, (v, o, sh) in ((x.get("alt") or {}).items() if many else ()):
                print(f"      most marked {k}: {v} ({sh:.0%} of its links, odds {o})")
            if not many or name == "nt":
                print(f"    {'word':18} {'tokens':>6} {'links':>5} {'host':>5} {'feature':>7}  linked lemmas")
                for w, n, k, kh, sh, lem in x["top"]:
                    print(f"    {w:18} {n:6} {k:5} {kh:5} {pc(sh):>7}  " + ", ".join(f"{l} {c}" for l, c in lem))
                if x["against"]:
                    print(f"    words against it ({len(x['against'])}, {x['against_share']:.0%} of its tokens): "
                          + ", ".join(f"{w} {n}" for w, n in x["against"][:20])
                          + f"; without them {pc(x['share_rest'])} with the feature")
        first = next(iter(r["routes"].values()))
        if r["verdict"] != "n.a.":
            print(f"  verdict" + (f" ({NAMES_OF[next(iter(r['routes']))]})" if many else "") + f": {r['verdict']}" + {
                "protect-words": " (the words against it as store entries of kind word, affixes: [" + e["id"] + "])",
                "restrict": f" (it holds on the stems {', '.join(r['holds'])})",
                "retire": " (the feature is no likelier with it than without: supersede it)",
                "too-few": f" (under {A['min_links']} host links)"}.get(r["verdict"], "")
                + (" -- odds against all host words: its stems never occur without it" if
                   first.get("odds_basis") == "all words" and r["verdict"] not in ("no-claim", "too-few") else ""))
        if "combined" in r:
            v, note = r["combined"]
            print(f"  -> combined: {v}" + (f" ({note})" if note else ""))
    key = "combined" if res and "combined" in res[0] else None
    n = collections.Counter(r[key][0] if key else r["verdict"] for r in res)
    if len(res) > 1:
        print("\n" + ("combined: " if key else "") + ", ".join(f"{k} {v}" for k, v in n.most_common()))


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
    """the words that carry a verb prefix of the chain (host verb, with a position); a store without a chain: every
    word linked to the Greek verb (its affixes have no positions to pick the verb word by)"""
    A = getattr(S, "_verb_pre", None)
    if A is None:
        A = S._verb_pre = {k for k, e in affix_entries(G).items() if e.get("host") == "verb" and e.get("slot") == "prefix"
                           and e.get("position")}
    if not A:
        return list(ws)
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
    if a[1] == "decide":                          # words or parts for analysis.model_text, by measurement
        import decide_text
        return decide_text.main([a[0]] + a[2:])
    P = LT.Project(a[0])
    if a[1] == "try" and "--seeds" in a:          # the donor's affixes measured as if they were in the store
        G, sd, same, skip, donor = with_seeds(a[0])
        ids = [x for x in a[2:] if not x.startswith("--")]
        if ids:
            sd, same, skip = [e for e in sd if e["id"] in ids], [x for x in same if x[0]["id"] in ids], \
                [x for x in skip if x[0]["id"] in ids]
        if not (sd or same or skip):
            raise SystemExit(f"{a[0]}: no affix seeds (profile/seeds.json)")
        print(f"{a[0]}: {len(sd) + len(same) + len(skip)} affix seed(s) from {donor}: {len(sd)} measured with the store's "
              f"{sum(not m['id'].startswith('seed:') for m in G.morphs)} morph(s), "
              f"{len(same)} already in the store, {len(skip)} not measurable by the try")
        res = try_morphs(a[0], [e["id"] for e in sd], P, load(a[0], P, G), G=G) if sd else []
        for (e, n, stems, lift, tl, odds, todds, *_r) in res:
            r, _ = seed_result(n, stems, odds, todds, e.get("greek"))
            print(f"    {e['id']}: {r}" + (f" (measured at the store's position {e['position']}, the seed's "
                                           f"{e['seed_position']})" if e.get("seed_position") else ""))
        for e, m in same:
            print(f"  {e['id']:24} {e['form']:7} already in the store as {m['id']}")
        for e, why in skip:
            print(f"  {e['id']:24} {str(e.get('form')):7} not measured: {why}")
        if "--write" in a:
            write_seed_claims(a[0], P, res, same, skip, donor)
        return
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
    if a[1] == "audit":
        route = a[a.index("--route") + 1] if "--route" in a else "nt"
        routes = {"all": ("nt", "hebrew", "lxx", "vamvas"), "ot": ("hebrew",)}.get(route, tuple(route.split(",")))
        if set(routes) - {"nt", "hebrew", "lxx", "vamvas", "agree"}:
            raise SystemExit(f"--route: nt, ot (the Hebrew), lxx, vamvas, agree, all, or a list; got {route}")
        ids = [x for i, x in enumerate(a[2:], 2) if not x.startswith("--") and a[i - 1] != "--route"]
        G, revived = revive(a[0], ids)
        if revived:
            S = load(a[0], P, G)
            print(f"{a[0]}: measured as if live again (superseded in the store): {', '.join(revived)}")
        if "agree" in routes:
            import agree_route as AR
            print(AR.summary(G or grammar.load(a[0]), a[0]))
        if routes != ("nt",):
            import ot_routes as OR
            rep = {}
            for r in routes:
                if r not in ("nt", "agree"):
                    rep[r] = {}
                    OR.route_tokens(a[0], S, r, P, rep[r])
            for r, by in rep.items():
                if by:
                    print(f"{a[0]}: {OR.NAMES[r]} links per book: " + "; ".join(
                        f"{b} {c.get('links', 0)} ({c.get('verb links', 0)} verbs" + (
                        f", {sum(v for k, v in c.items() if k.startswith('parsed'))} of {c.get('with a word', 0)} "
                        "parsed" if r != "hebrew" else "") + (f"; skipped: {c['why']}" if c.get("skipped") else "") + ")"
                    for b, (_, c) in sorted(by.items())))
            if rep and not any(rep.values()):
                print(f"{a[0]}: no Tanakh books in the corpus linked to the Hebrew (_learn/links_hbo.tsv): the Tanakh routes are "
                      "empty")
        print_audit(audit(a[0], ids, P, S, G=G, routes=routes))
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
    if S.hyphen:                                  # with hyphen parts: the corpus's hyphen words, whole, as well
        hyw = collections.Counter(w for r in P.corpus() for w in HYPHEN_WORD.findall(r[4])
                                  if "-" in w)
        for t, n in hyw.items():
            ms = S.split(t)
            if S.rebuild(ms) != unicodedata.normalize("NFC", t.lower()):
                bad.append(t)
        hsplit = sum(n for t, n in hyw.items() if any(m.slot != "stem" for m in S.split(t)))
        print(f"{a[0]}: {len(hyw)} hyphen word types, {sum(hyw.values())} tokens; {hsplit} with a part "
              f"({hsplit / max(sum(hyw.values()), 1):.0%})")
    split = sum(n for t, n in tok.items() if len(S.split(t)) > 1)
    print(f"{a[0]}: {len(tok)} word types, {sum(tok.values())} tokens; tone written as {S.spec.written}"
          f" ({len(S.tones)} grammatical tone pattern(s)); {split} tokens ({split / sum(tok.values()):.0%}) split")
    print(f"rebuilt exactly: {len(tok) - len(bad)} of {len(tok)} types" + (f"; not: {', '.join(bad[:10])}" if bad else ""))
    for (slot, form), n in sorted(by.items(), key=lambda x: -x[1]):
        print(f"  {slot:7} {form:12} {n}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
