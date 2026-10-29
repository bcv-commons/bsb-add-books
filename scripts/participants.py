#!/usr/bin/env python3
"""Participant resolver: who is who in a chapter, from the source structures (orig/heb.sqlite, orig/grc.sqlite).

    python3 scripts/participants.py GEN 24              # OT: orig/heb.sqlite (+ the speaker layer)
    python3 scripts/participants.py PHP 1 2             # NT: orig/grc.sqlite
    python3 scripts/participants.py GEN 1-24 --check    # the self-test only (speaker vs 1st person), no files

No project: the result is a property of the source text. The language follows the book (OT hbo, NT grc).
Every mention (a noun, a pronoun, an adjective or demonstrative with a MACULA reference, and a verb's implicit subject
via `subjref`) gets a participant id (pid) = the MACULA word key of the participant's first mention in the book. The
chapters 1..max(ch) of the book are read, so the ids and the book-level first mentions are stable whatever chapter is
asked for. Six passes, each recorded per join:

  1 names       proper nouns -> one participant per TIPNR entity (STEPBible TIPNR, CC BY 4.0: Strong's + verse
                disambiguation, e.g. Nahor@Gen.11.22 vs Nahor@Gen.11.24); without a TIPNR hit, by Strong's in the book
  2 refs        MACULA subjref / participantref / referent: the mention joins its target; a mention with several
                targets (Greek ἡμῶν = Paul + Timothy + saints) is a GROUP mention, not joined
  2b appos      MACULA Np-Appos: the two heads of an apposition join (Abraham, his master)
  3 repeat      a common noun repeated in a chapter joins the latest earlier mention of the same lemma when it is
                definite (article, suffix, Greek article) or pronoun-linked, of the same number, and the two are not
                kept apart by MACULA's references (both already linked to different participants)
  4 speaker     the speaker layer's speakers (Hebrew) / the epistle's author (Greek) are matched by name; a 1st-person
                singular mention inside the quotation with no MACULA reference joins the speaker
  5 kinship     a singular kinship noun with a possessor ("my son", "his wife") joins the possessor's TIPNR relative of
                that kind and gender when exactly one such relative is named in the chapter ("my son" in GEN 24 =
                Isaac); pass 3 never joins two named participants, nor a kinship noun with an owner to one without

Output: build/participants/<code>.participants.tsv (participants with a mention in the chapters asked) and, with
--mentions, <code>.mentions.tsv (key, pid, name). Standard library only. TIPNR is read from download/stepbible/
(`python3 scripts/setup.py --only names`, pinned commit and SHA-256); without it pass 1 falls back to Strong's per book.

Self-test (printed every run, and alone with --check): a 1st-person singular mention inside a quotation that MACULA
links to someone is compared with the speaker the speaker layer (OT) or the epistle's author (NT) names: agree / differ.
Reference figures: GEN 1-24 319 agree / 9 differ; PHP 1 36 / 0.
"""
import argparse
import collections
import glob
import os
import re
import sqlite3
import unicodedata

import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, HERE)
import books  # noqa: E402

TIPNR_DIR = os.path.join(ROOT, 'download', 'stepbible')

OSIS = dict(zip(
    'GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL '
    'AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB '
    'JAS 1PE 2PE 1JN 2JN 3JN JUD REV'.split(),
    'Gen Exo Lev Num Deu Jos Jdg Rut 1Sa 2Sa 1Ki 2Ki 1Ch 2Ch Ezr Neh Est Job Psa Pro Ecc Sng Isa Jer Lam Ezk Dan Hos Jol '
    'Amo Oba Jon Mic Nam Hab Zep Hag Zec Mal Mat Mrk Luk Jhn Act Rom 1Co 2Co Gal Eph Php Col 1Th 2Th 1Ti 2Ti Tit Phm Heb '
    'Jas 1Pe 2Pe 1Jn 2Jn 3Jn Jud Rev'.split()))
EPISTLE_AUTHOR = {'ROM': 'Paul', '1CO': 'Paul', '2CO': 'Paul', 'GAL': 'Paul', 'EPH': 'Paul', 'PHP': 'Paul', 'COL': 'Paul',
                  '1TH': 'Paul', '2TH': 'Paul', '1TI': 'Paul', '2TI': 'Paul', 'TIT': 'Paul', 'PHM': 'Paul', 'JAS': 'James',
                  '1PE': 'Peter', '2PE': 'Peter', '1JN': 'John', '2JN': 'John', '3JN': 'John', 'JUD': 'Jude'}
REF_KINDS = ('participantref', 'referent', 'subjref')
# Louw-Nida domains of persons (9 People, 10 Kinship, 11 Groups of persons, 12 supernatural beings, 87 Status)
LN_PERSON = {'009', '010', '011', '012', '087'}
# not participants: quantifiers and nouns that are prepositions or adverbs in use
NOT_MENTION = {unicodedata.normalize('NFC', x) for x in ('כֹּל', 'פָּנֶה', 'פָּנִים', 'קֶרֶב', 'תָּוֶךְ', 'πᾶς')}
GRC_DEFINITE = {unicodedata.normalize('NFC', x) for x in ('θεός', 'κύριος', 'Χριστός', 'Ἰησοῦς', 'πνεῦμα')}
HUMAN_HBO = {unicodedata.normalize('NFC', x) for x in ('אִישׁ', 'אֱנוֹשׁ', 'אָדָם', 'אִשָּׁה')}
HONORIFIC_PL = {unicodedata.normalize('NFC', x) for x in ('אֱלֹהִים', 'אָדוֹן', 'בַּעַל')}


def nfc(s):
    return unicodedata.normalize('NFC', s) if s else s


# ------------------------------------------------------------------------------------------------- TIPNR

def load_tipnr():
    """(letter, number) -> list of (uniqueName, kind, extendedStrongs letter, ESV name, set of refs 'Gen.24.1'), from
    STEPBible's TIPNR text file: a record per individual ('$========== PERSON(s)', PLACE, OTHER), its lines
    '– Named<TAB>unique name<TAB>H5152H«H5152=נָחוֹר<TAB>Nahor =ESV,NIV<TAB>Gen.11.26; Gen.11.27; ...' (also
    '– Greek', '– Spelled', ...; a form of another name as 'Amana|Abana@2Ki.5.12')."""
    f = next(iter(sorted(glob.glob(os.path.join(TIPNR_DIR, 'TIPNR-*.txt')))), None)
    idx = collections.defaultdict(list)
    if not f:
        return idx, None
    kind = None
    with open(f, encoding='utf-8-sig') as fh:
        for line in fh:
            if line.startswith('$=========='):
                k = line[11:].split('\t')[0].strip()
                kind = {'PERSON(s)': 'PERSON', 'PLACE': 'PLACE', 'OTHER': 'PERSON'}.get(k)   # EXCLUDED OTHER: none
                continue
            if not kind or not line.startswith('– '):
                continue
            c = line.rstrip('\n').split('\t')
            if len(c) < 5 or '«' not in c[2] or '@' not in c[1] or '+' in c[2]:
                continue                                  # the record's Total line, notes; a name combined of words
            m = re.match(r'([HG])0*(\d+)([A-Za-z]?)', c[2])
            if not m:
                continue
            unique = c[1].split('|')[-1].strip()
            esv = re.split(r'\s*[=;]', c[3].strip())[0].strip() or unique.split('@')[0]
            refs = {re.sub(r'[a-z]$', '', r.strip()) for r in c[4].split(';') if r.strip()}
            idx[(m.group(1), int(m.group(2)))].append((unique, kind, m.group(3).lower(), esv, refs))
    return idx, f


_RELATIONS = {}


def load_tipnr_relations():
    """uniqueName -> {'parents', 'siblings', 'partners', 'children': set of uniqueNames, 'gender': Male/Female/None},
    from the TIPNR record lines ('Isaac@Gen.17.19-Jas=H3327<TAB>description<TAB>parents 'A + B'<TAB>siblings<TAB>
    partners<TAB>children<TAB>...<TAB>Male')."""
    if _RELATIONS:
        return _RELATIONS
    f = next(iter(sorted(glob.glob(os.path.join(TIPNR_DIR, 'TIPNR-*.txt')))), None)
    if not f:
        return _RELATIONS
    with open(f, encoding='utf-8-sig') as fh:
        for line in fh:
            if line[:1] in ('$', '–', '#', ' ', '\t', '\n'):
                continue
            c = line.rstrip('\n').split('\t')
            if len(c) < 6 or not re.match(r'^[^\t=]+@[^\t=]+=[HG]\d', c[0]):
                continue
            names = lambda x: {y.strip() for y in re.split(r'[,+]', x) if '@' in y}
            _RELATIONS[c[0].split('=')[0].strip()] = {
                'parents': names(c[2]), 'siblings': names(c[3]), 'partners': names(c[4]), 'children': names(c[5]),
                'gender': next((x for x in c[6:] if x in ('Male', 'Female')), None)}
    return _RELATIONS


# possessed kinship nouns -> (TIPNR relation of the possessor, gender of the relative or None)
KINSHIP = {nfc(k): v for k, v in {
    'בֵּן': ('children', 'Male'), 'בַּת': ('children', 'Female'), 'אָב': ('parents', 'Male'), 'אֵם': ('parents', 'Female'),
    'אִשָּׁה': ('partners', 'Female'), 'אָח': ('siblings', 'Male'), 'אָחוֹת': ('siblings', 'Female'),
    'υἱός': ('children', 'Male'), 'θυγάτηρ': ('children', 'Female'), 'πατήρ': ('parents', 'Male'),
    'μήτηρ': ('parents', 'Female'), 'γυνή': ('partners', 'Female'), 'ἀνήρ': ('partners', 'Male'),
    'ἀδελφός': ('siblings', 'Male'), 'ἀδελφή': ('siblings', 'Female')}.items()}


def tipnr_entity(idx, letter, strong, book, ch, v):
    """The TIPNR entity of a proper noun: Strong's + the verse; else the only entity of that number in the chapter;
    else the only entity of that number at all."""
    m = re.match(r'0*(\d+)([a-z]?)', strong or '')
    if not m:
        return None
    cands = idx.get((letter, int(m.group(1))), [])
    if not cands:
        return None
    ref = f'{OSIS.get(book, book)}.{ch}.{v}'
    hit = [c for c in cands if ref in c[4]]
    if len({c[0] for c in hit}) > 1:
        hit = [c for c in hit if c[2] == m.group(2)] or hit
    if hit:
        return hit[0]
    pre = f'{OSIS.get(book, book)}.{ch}.'
    inch = {c[0]: c for c in cands if any(r.startswith(pre) for r in c[4])}
    if len(inch) == 1:
        return next(iter(inch.values()))
    if len({c[0] for c in cands}) == 1:
        return cands[0]
    return None


# ------------------------------------------------------------------------------------------------- union-find

class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)
            return True
        return False


# ------------------------------------------------------------------------------------------------- the resolver

class Resolver:
    """resolve(lang, book, chapters): .pid(key), .info[pid], .mentions (key -> pass), .group[key] (set of pids)."""

    def __init__(self, lang, book, chapters):
        self.lang, self.book, self.chapters = lang, book, sorted(set(chapters))
        db = os.path.join(ROOT, 'orig', 'heb.sqlite' if lang == 'hbo' else 'grc.sqlite')
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        upto = max(self.chapters)
        self.toks = {}
        for r in c.execute('select * from tokens where book=? and ch<=? order by key', (book, upto)):
            t = dict(r)
            for f in ('lemma', 'text', 'gloss'):
                t[f] = nfc(t.get(f))
            self.toks[t['key']] = t
        keys = list(self.toks)
        lo, hi = keys[0], keys[-1]
        self.refs = collections.defaultdict(lambda: collections.defaultdict(list))
        for r in c.execute('select key, kind, target from refs where key between ? and ?', (lo, hi)):
            for tg in r['target'].split():
                if tg not in self.refs[r['key']][r['kind']]:
                    self.refs[r['key']][r['kind']].append(tg)
        self.nodes = {r['id']: dict(r) for r in c.execute('select * from nodes where book=? and ch<=?', (book, upto))}
        # targets outside the loaded range (rare: another book) are loaded as plain tokens
        missing = {tg for k in self.refs for kind in REF_KINDS for tg in self.refs[k].get(kind, []) if tg not in self.toks}
        for tg in missing:
            r = c.execute('select * from tokens where key=?', (tg,)).fetchone()
            if r:
                t = dict(r)
                t['lemma'], t['gloss'] = nfc(t['lemma']), nfc(t['gloss'])
                self.toks[tg] = t
        self.quotes = []
        if lang == 'hbo':
            self.quotes = [dict(r) for r in c.execute('select * from speaker_quotations where first between ? and ?', (lo, hi))]
        self.tipnr, self.tipnr_dir = load_tipnr()
        self.uf = UF()
        self.joined_by = collections.Counter()
        self.group = {}
        self.entity = {}            # root-independent: name node -> TIPNR record
        self.speaker_pid = {}
        self.name_conflict = set()   # quotations whose speaker_name (v0.14) names someone other than their inquit
        self.speaker_check = collections.Counter()
        self._run()

    # ---- mentions
    def is_mention(self, t):
        if t['lemma'] in NOT_MENTION:
            return False
        if t['class'] in ('noun', 'pron'):
            return True
        r = self.refs.get(t['key'], {})
        if t['class'] == 'verb':
            return 'subjref' in r
        return any(k in r for k in ('participantref', 'referent'))

    def person(self, t):
        if t.get('person'):
            return t['person']
        m = re.match(r'[PFRSCDIKQX]-([123])', t.get('morph') or '') if self.lang == 'grc' else None
        return {'1': 'first', '2': 'second', '3': 'third'}[m.group(1)] if m else None

    def number(self, t):
        if t.get('number'):
            return t['number']
        m = re.match(r'[PFRSCDIKQX]-[123]?[NGDAV]?([SP])', t.get('morph') or '') if self.lang == 'grc' else None
        return {'S': 'singular', 'P': 'plural'}[m.group(1)] if m else None

    def strong(self, t):
        return t.get('lexeme') if self.lang == 'hbo' else t.get('strong')

    def is_proper(self, t):
        return t['class'] == 'noun' and t.get('type') == 'proper'

    def _join(self, a, b, why):
        if self.uf.union(a, b):
            self.joined_by[why] += 1

    def _run(self):
        T = self.toks
        targets = {tg for k in self.refs for kind in REF_KINDS for tg in self.refs[k].get(kind, [])}
        self.mention_keys = [k for k, t in T.items() if t['book'] == self.book and (self.is_mention(t) or k in targets)]
        for k in self.mention_keys:
            self.uf.find(k)
        # pass 1: names
        letter = 'H' if self.lang == 'hbo' else 'G'
        for k in self.mention_keys:
            t = T[k]
            if not self.is_proper(t):
                continue
            ent = tipnr_entity(self.tipnr, letter, self.strong(t), t['book'], t['ch'], t['v'])
            if ent:
                node = 'N:' + ent[0]
                self.entity[node] = ent
            elif self.strong(t):
                node = 'S:' + re.sub(r'[a-z]$', '', self.strong(t))
            else:
                node = 'L:' + (t['lemma'] or k)
            self._join(node, k, 'names')
        # pass 2: MACULA references
        for k in self.mention_keys:
            r = self.refs.get(k, {})
            tg = []
            for kind in REF_KINDS:
                for x in r.get(kind, []):
                    if x not in tg:
                        tg.append(x)
            if len(tg) == 1 and T.get(tg[0], {}).get('class') == 'verb' and T[k]['class'] != 'verb':
                self._join(k, 'E:' + tg[0], 'refs-event')     # "this" = the event of a clause, not its subject
            elif len(tg) == 1:
                self._join(k, tg[0], 'refs')
            elif len(tg) > 1:
                self.group[k] = tg
        # pass 2b: apposition
        self.appos_desc = set()
        kids = collections.defaultdict(list)
        for n in self.nodes.values():
            if n['parent']:
                kids[n['parent']].append(n)
        for n in self.nodes.values():
            if n['rule'] != 'Np-Appos':
                continue
            parts = [self.span(p['first'], p['last']) for p in kids[n['id']]]
            parts += [[w] for w in self.span(n['first'], n['last']) if w.get('node') == n['id']]
            parts.sort(key=lambda sp: sp[0]['key'] if sp else '')
            heads = [next((t for t in sp if t['class'] not in ('art', 'det')), None) for sp in parts[:2]]
            if len(heads) == 2 and all(heads) and all(h['class'] == 'noun' and self.is_mention(h) for h in heads):
                if self.is_proper(heads[0]) and not self.is_proper(heads[1]):
                    self.appos_desc.add(heads[1]['key'])
                if self.is_proper(heads[1]) and not self.is_proper(heads[0]):
                    self.appos_desc.add(heads[0]['key'])
                self._join(heads[0]['key'], heads[1]['key'], 'appos')
        # pass 3: repeated common nouns within a chapter
        linked = collections.Counter(self.uf.find(k) for k in self.mention_keys)
        for _round in (1, 2):        # twice: a possessor joined late can open a join of its possessed noun
            for ch in self.chapters_all():
                last = {}
                for k in self.mention_keys:
                    t = T[k]
                    if t['ch'] != ch or t['class'] != 'noun' or self.is_proper(t):
                        continue
                    L = t['lemma']
                    prev = last.get(L)
                    last[L] = k
                    if not prev or self.uf.find(prev) == self.uf.find(k):
                        continue
                    # never join two named participants (Bethuel, "the son of Milcah", and Isaac, "my son")
                    named = {self.uf.find(n) for n in self.entity}
                    if self.uf.find(prev) in named and self.uf.find(k) in named:
                        continue
                    if L not in HONORIFIC_PL and (T[prev].get('number') or '') != (t.get('number') or ''):
                        continue
                    if not (self.definite(t) or linked[self.uf.find(k)] > 1):
                        continue
                    pa, pb = self.possessor(T[prev]), self.possessor(t)
                    # a description in apposition to a name ("Milcah, wife of Nahor") belongs to the name only
                    if k in self.appos_desc:
                        continue
                    # a kinship noun is relative to its owner: "the son of Milcah" and "a son" (born to Abraham) differ
                    if L in KINSHIP and bool(pa) != bool(pb):
                        continue
                    if pa and pb and self.uf.find(pa) != self.uf.find(pb):
                        if _round == 2:
                            self.joined_by['repeat-other-owner'] += 1
                        continue
                    self._join(prev, k, 'repeat')
        # pass 4: speakers
        self._speakers()
        # pass 5: possessed kinship nouns ("my son" = Isaac), once the possessors are resolved
        self._kinship()
        self._finish()

    def _kinship(self):
        """A singular kinship noun with a possessor ("my son", "his wife") joins the possessor's relative of that kind
        (TIPNR: children, parents, partners, siblings; the relative's gender) when exactly one such relative is named
        in the same chapter. Conservative: the possessor must be a TIPNR person, the noun's participant must not
        already hold a name or a mention with another possessor."""
        rel = load_tipnr_relations()
        if not rel or not self.entity:
            return
        ent_of_root = {}
        for node, e in self.entity.items():
            ent_of_root.setdefault(self.uf.find(node), set()).add(e[0])
        node_of = {e[0]: node for node, e in self.entity.items()}
        in_ch = collections.defaultdict(set)              # chapter -> roots with a mention there
        for k in self.mention_keys:
            in_ch[self.toks[k]['ch']].add(self.uf.find(k))
        for k in self.mention_keys:
            t = self.toks[k]
            kin = KINSHIP.get(t['lemma'])
            if not kin or t['class'] != 'noun' or self.is_proper(t) or self.number(t) != 'singular':
                continue
            pk = self.possessor(t)
            if not pk:
                continue
            owners = ent_of_root.get(self.uf.find(pk), set())
            if len(owners) != 1:
                continue
            info = rel.get(next(iter(owners)))
            if not info:
                continue
            kind, gender = kin
            cands = set()
            for u in info[kind]:
                if u not in node_of or (rel.get(u, {}).get('gender') or gender) != gender:
                    continue
                r = self.uf.find(node_of[u])
                if r in in_ch[t['ch']]:
                    cands.add(r)
            if len(cands) != 1:
                continue
            target, root = next(iter(cands)), self.uf.find(k)
            if root == target or root in ent_of_root:
                continue
            # every possessed mention of the noun's participant must have the same possessor
            mates = [m for m in self.mention_keys if self.uf.find(m) == root]
            if any(self.possessor(self.toks[m]) and self.uf.find(self.possessor(self.toks[m])) != self.uf.find(pk)
                   for m in mates if self.toks[m]['class'] == 'noun'):
                continue
            self._join(target, k, 'kinship')
            ent_of_root[self.uf.find(k)] = ent_of_root.get(target, set())

    def chapters_all(self):
        return sorted({t['ch'] for t in self.toks.values() if t['book'] == self.book})

    def has_ref_in(self, root):
        return root in self._ref_roots()

    def _ref_roots(self):
        if not hasattr(self, '_rr'):
            self._rr = set()
            for k in self.mention_keys:
                if any(kind in self.refs.get(k, {}) for kind in REF_KINDS):
                    self._rr.add(self.uf.find(k))
        return self._rr

    def definite(self, t):
        T, k = self.toks, t['key']
        if not hasattr(self, '_words'):
            self._words = collections.defaultdict(list)
            for x in T.values():
                self._words[(x['book'], x['ch'], x['v'], x['word'])].append(x)
        same_word = self._words[(t['book'], t['ch'], t['v'], t['word'])] if self.lang == 'hbo' else []
        if self.lang == 'hbo':
            if any(x['class'] == 'art' for x in same_word) or any(x['class'] == 'pron' and x['key'] > k for x in same_word):
                return True
            # construct before a proper noun or a suffixed noun ("the city of Nahor")
            if t.get('state') == 'construct':
                nxt = self.next_tok(k)
                return bool(nxt and nxt['class'] == 'noun' and (self.is_proper(nxt) or self.definite(nxt)))
            return False
        if t['lemma'] in GRC_DEFINITE:
            return True
        prev = self.prev_toks(k, 3)
        return any(x['class'] == 'det' and x.get('gcase') == t.get('gcase') for x in prev)

    def span(self, lo, hi):
        import bisect
        self.next_tok(lo)
        i = bisect.bisect_left(self._order, lo)
        j = bisect.bisect_right(self._order, hi)
        return [self.toks[x] for x in self._order[i:j]]

    def possessor(self, t):
        """The key of the noun's possessor: a pronominal suffix of the same word, or the noun/pronoun after a
        construct (Hebrew); a genitive pronoun or noun right after the noun (Greek)."""
        nxt = self.next_tok(t['key'])
        if not nxt:
            return None
        if self.lang == 'hbo':
            if nxt['class'] == 'pron' and nxt['word'] == t['word'] and nxt['v'] == t['v']:
                return nxt['key']
            if t.get('state') == 'construct' and nxt['class'] in ('noun', 'pron') and self.is_mention(nxt):
                return nxt['key']
            return None
        if nxt.get('gcase') == 'genitive' and self.is_mention(nxt) and (nxt['class'] == 'pron' or
                                                                      (nxt['class'] == 'noun' and t.get('gcase') != 'genitive')):
            return nxt['key']
        return None

    def next_tok(self, k):
        if not hasattr(self, '_order'):
            self._order = sorted(x for x in self.toks if self.toks[x]['book'] == self.book)
            self._pos = {x: i for i, x in enumerate(self._order)}
        i = self._pos.get(k)
        return self.toks[self._order[i + 1]] if i is not None and i + 1 < len(self._order) else None

    def prev_toks(self, k, n):
        self.next_tok(k)
        i = self._pos.get(k, 0)
        return [self.toks[x] for x in self._order[max(0, i - n):i]]

    # ---- names and the speaker pass
    def root_name_tokens(self):
        by_root = collections.defaultdict(list)
        for k in self.mention_keys:
            by_root[self.uf.find(k)].append(k)
        return by_root

    def _speakers(self):
        by_root = self.root_name_tokens()
        names = collections.defaultdict(lambda: collections.defaultdict(set))   # ch -> lowercase name -> roots
        ent_root = {self.uf.find(n): e for n, e in self.entity.items()}
        for root, ks in by_root.items():
            for k in ks:
                t = self.toks[k]
                if root in ent_root:
                    names[t['ch']][ent_root[root][3].lower()].add(root)
                if t['class'] == 'noun':
                    if t.get('lemma'):
                        names[t['ch']][t['lemma']].add(root)   # the speaker layer's Hebrew names (v0.12 on)
                    for g in (t.get('gloss'), t.get('english')):
                        g = (g or '').lower().replace('.', ' ').replace('(the)', '').strip()
                        g = re.sub(r'^(the|of|his|her|my|your|to|from) ', '', g)
                        if g:
                            names[t['ch']][g].add(root)
        size = {r: len(ks) for r, ks in by_root.items()}

        def match(spk, ch):
            nm = names[ch]
            if not spk or spk.startswith('('):
                return None
            for cand in [spk] + re.findall(r'\(([^)]+)\)', spk) + [re.sub(r'\s*\(.*\)', '', spk)]:
                cand = cand.strip().lower()
                if cand in nm:
                    return max(nm[cand], key=lambda r: size.get(r, 0))
            m = re.match(r"(.+?)'s (?:\w+ )*(\w+)$", spk)
            if m and m.group(2).lower() in nm:
                return max(nm[m.group(2).lower()], key=lambda r: size.get(r, 0))
            return None

        if self.lang == 'hbo':
            votes, unresolved = collections.defaultdict(collections.Counter), []
            for q in self.quotes:
                if q['first'] not in self.toks:
                    continue
                ch = self.toks[q['first']]['ch']
                # the words that name the speaker (speaker_ref, v0.12 on): their participant; else the word that gives the
                # character's name (speaker_name_ref, v0.14), else the name, matched
                r = None
                for f in ('speaker_ref', 'speaker_name_ref'):
                    refs = [x for x in (q.get(f) or '').split() if x in self.toks]
                    r = max((self.uf.find(x) for x in refs), key=lambda x: size.get(x, 0)) if refs else None
                    if r in size:
                        break
                # the layer's character can contradict the inquit (GEN 24:58 Rebekah speaks, id Laban's; 1SA 17:55 Saul
                # speaks, id Abner's) or narrow a group to one (RUT 1:10, GEN 31:14): where the inquit itself has a proper
                # name other than speaker_name, or names several, its words stay in the mark
                own = [self.toks[x] for x in (q.get('speaker_ref') or '').split() if x in self.toks]
                # the head word's proper name (not a place in "the king of Sodom"); NFC: the layer and MACULA's lemmas
                # can order the marks differently (שׂ + qamats)
                names_own = {unicodedata.normalize('NFC', own[0]['lemma'])} if own and own[0].get('type') == 'proper' else set()
                # a group: several named, or a plural/dual head ("the two daughters-in-law"; not the dual in the
                # construct of "the man of the in-between", 1SA 17:4)
                group = ',' in (q['speaker'] or '') or bool(own and own[0]['class'] in ('noun', 'num')
                                                            and own[0].get('number') in ('plural', 'dual'))
                if q.get('speaker_name') and ((names_own and unicodedata.normalize('NFC', q['speaker_name']) not in names_own) or group):
                    self.name_conflict.add(q['id'])
                r = r if r in size else (match(q.get('speaker_name'), ch) or match(q['speaker'], ch)
                                         or match(q.get('alt_eng'), ch))
                if r:
                    self.speaker_pid[(self.speaker_key(q), ch)] = r
                    if q.get('speaker_id'):
                        votes[(q['speaker_id'], ch)][r] += 1
                elif q.get('speaker_id'):
                    unresolved.append((q, ch))
            # a quotation that names nobody here gets its character's participant (speaker_id, v0.14) from the chapter's other
            # quotations; the character id only fills gaps: a quotation's own words decide first (the layer gives a group
            # speaker one person's id, e.g. "Rachel and Leah" in GEN 31:14 as Rachel)
            for q, ch in unresolved:
                c = votes.get((q['speaker_id'], ch))
                if c:
                    self.speaker_pid[(self.speaker_key(q), ch)] = c.most_common(1)[0][0]
        else:
            a = EPISTLE_AUTHOR.get(self.book)
            for ch in self.chapters_all():
                r = match(a, ch)
                if r:
                    self.speaker_pid[(a, ch)] = r
        # Greek epistles: a vocative names the addressees = the participant most 2nd-person mentions in the chapter refer to
        if self.lang == 'grc' and self.book in EPISTLE_AUTHOR:
            for ch in self.chapters_all():
                ks = [k for k in self.mention_keys if self.toks[k]['ch'] == ch]
                second = collections.Counter(self.uf.find(k) for k in ks if self.person(self.toks[k]) == 'second'
                                             and self.toks[k]['class'] == 'pron' and k not in self.group)
                if not second:
                    continue
                addr = second.most_common(1)[0][0]
                for k in ks:
                    if self.toks[k].get('gcase') == 'vocative' and self.toks[k]['class'] in ('noun', 'adj'):
                        self._join(addr, k, 'addressee')
        # 1st-person singular mentions inside a quotation: check against / join to its speaker
        votes = collections.Counter()
        for k in self.mention_keys:
            t = self.toks[k]
            if self.person(t) != 'first' or self.number(t) not in ('singular', None):
                continue
            spk = self.speaker_of(k)
            r = self.speaker_pid.get((spk, t['ch']))
            if not r:
                continue
            has_ref = any(kind in self.refs.get(k, {}) for kind in REF_KINDS)
            if has_ref:
                votes[(self.uf.find(r), self.uf.find(k))] += 1
            elif self.number(t) == 'singular':
                self._join(r, k, 'speaker')
        # pass 4c: a common-noun participant that the speaker's own 1st-person references point to (twice or more) is
        # the speaker ("the girl" of 24:16 = Rebekah, "the man" of 24:21 = the servant); never two names
        named = {self.uf.find(n) for n in self.entity}
        for (rs, rk), n in votes.items():
            if rs == rk or n < 2:
                continue
            a, b = self.uf.find(rs), self.uf.find(rk)
            if a != b and not (a in named and b in named):
                self._join(a, b, 'speaker-ref')
        for k in self.mention_keys:
            t = self.toks[k]
            if self.person(t) == 'first' and self.number(t) == 'singular' and any(kind in self.refs.get(k, {}) for kind in REF_KINDS):
                r = self.speaker_pid.get((self.speaker_of(k), t['ch']))
                if r:
                    self.speaker_check['agree' if self.uf.find(k) == self.uf.find(r) else 'differ'] += 1

    def speaker_of(self, k):
        if self.lang == 'grc':
            return EPISTLE_AUTHOR.get(self.book)
        best = None
        for q in self.quotes:
            if q['first'] <= k <= q['last'] and (best is None or q['level'] > best['level']):
                best = q
        return self.speaker_key(q=best) if best else None

    @staticmethod
    def speaker_key(q):
        """a quotation's speaker key: its id where the layer names speakers by the text's own words (one lemma, אִישׁ or
        עֶבֶד, can be two people in a chapter) or by character (speaker_id, v0.14), else the English label of the older
        releases"""
        return q['id'] if q.get('speaker_ref') or q.get('speaker_id') else (q['speaker'] or q.get('alt_eng'))

    def _qids(self):
        if not hasattr(self, '_qid'):
            self._qid = {x['id']: x for x in self.quotes}
        return self._qid

    def _sids(self):
        """speaker_id (v0.14) -> its first quotation"""
        if not hasattr(self, '_sid'):
            self._sid = {}
            for x in self.quotes:
                if x.get('speaker_id'):
                    self._sid.setdefault(x['speaker_id'], x)
        return self._sid

    def is_label(self, key):
        """an English speaker label of the older releases (not a quotation id, not a character id)"""
        return key not in self._qids() and key not in self._sids()

    def speaker_label(self, key):
        q = self._qids().get(key) or self._sids().get(key)
        return (q.get('speaker_name') or q['speaker'] or q.get('alt_eng') or '') if q else (key or '')

    def _finish(self):
        by_root = self.root_name_tokens()
        self.pid_of_root, self.info = {}, {}
        for root, ks in by_root.items():
            ks = sorted(ks)
            pid = ks[0]
            self.pid_of_root[root] = pid
            nouns = [self.toks[k] for k in ks if self.toks[k]['class'] == 'noun']
            ent = next((self.entity[n] for n in self.entity if self.uf.find(n) == root), None)
            # an English speaker label (the older layer releases) names a participant; the Hebrew names of v0.12 on are the
            # participant's own nouns, which the noun naming below already uses
            spk = next((self.speaker_label(sp[0]) for sp, r in self.speaker_pid.items() if r is not None
                        and self.uf.find(r) == root and self.is_label(sp[0])
                        and not self.speaker_label(sp[0]).startswith('(')), None)
            if ent:
                name = ent[3]
            elif spk:
                name = spk.replace(' ', '_')
            elif nouns:
                prop = [n for n in nouns if self.is_proper(n)]
                pool = prop or nouns
                name = collections.Counter(self.clean(n) for n in pool).most_common(1)[0][0]
            else:
                t = self.toks[pid]
                name = self.clean(t)
            lemma = collections.Counter(n['lemma'] for n in nouns).most_common(1)[0][0] if nouns else self.toks[pid]['lemma']
            strong = collections.Counter(self.strong(n) or '' for n in nouns).most_common(1)[0][0] if nouns else ''
            self.info[pid] = {'pid': pid, 'name': name, 'lemma': lemma, 'strong': strong, 'members': ks,
                              'kind': self.kind(ent, nouns, ks), 'root': root}
        for spk, r in list(self.speaker_pid.items()):
            self.speaker_pid[spk] = self.pid_of_root[self.uf.find(r)] if self.uf.find(r) in self.pid_of_root else None
        for k, tg in self.group.items():
            self.group[k] = sorted({self.pid(x) or x for x in tg})

    def clean(self, t):
        g = (t.get('english') or t.get('gloss') or t['lemma'] or '').strip()
        g = re.sub(r'^(the|of|my|his|her|your|their|to|O)[ .]', '', g).replace('(the).', '').replace('.', '_')
        return g.replace(' ', '_') or t['lemma']

    def kind(self, ent, nouns, ks):
        if ent:
            return ent[1]
        props = [n for n in nouns if self.is_proper(n)]
        if props:
            doms = ' '.join(n.get('lexdomain') or n.get('domain') or '' for n in props)
            if self.lang == 'hbo':
                if '003001010' in doms and '003001007' not in doms:
                    return 'PLACE'
                if '003001006' in doms and '003001007' not in doms:
                    return 'GROUP'
                return 'PERSON'
            return 'PERSON' if '093001' in doms else 'PLACE'
        human = False
        for n in nouns:
            if self.lang == 'hbo':
                human |= any(d.startswith('001001002003') for d in (n.get('lexdomain') or '').split()) or n['lemma'] in HUMAN_HBO
            else:
                human |= (n.get('domain') or '')[:3] in LN_PERSON or (n.get('domain') or '').startswith('093')
        person = any(self.person(self.toks[k]) in ('first', 'second') for k in ks)
        if not nouns:
            human = True if person else any(self.toks[k]['class'] in ('verb', 'pron') for k in ks)
        plural = [n for n in nouns if n.get('number') == 'plural' and n['lemma'] not in HONORIFIC_PL]
        if nouns and len(plural) * 2 > len(nouns):
            return 'GROUP' if human else 'THING'
        return 'PERSON' if (human or person or any(n['lemma'] in HONORIFIC_PL for n in nouns)) else 'THING'

    # ---- the API
    def pid(self, key):
        """The participant id of a mention key (or a reference target); None for a non-mention."""
        if key in self.group:
            return '+'.join(self.group[key])
        if key not in self.uf.p:
            return None
        return self.pid_of_root.get(self.uf.find(key))

    def name(self, pid):
        if not pid:
            return None
        if '+' in pid:
            return '+'.join(self.name(p) or p for p in pid.split('+'))
        return self.info[pid]['name'] if pid in self.info else None

    def first_in(self, pid, ch):
        ks = [k for k in self.info.get(pid, {}).get('members', []) if self.toks[k]['ch'] == ch]
        return ks[0] if ks else None


def resolve(lang, book, chapters):
    return Resolver(lang, book.upper(), chapters)


# ------------------------------------------------------------------------------------------------- output

def write(res, out, mentions=False):
    code = res.book.lower()
    chs = set(res.chapters)
    path = os.path.join(out, f'{code}.participants.tsv')
    rows = []
    for pid, i in res.info.items():
        ks = [k for k in i['members'] if res.toks[k]['ch'] in chs]
        if not ks:
            continue
        f = res.toks[pid]
        rows.append((pid, i['name'], i['lemma'] or '', i['strong'] or '', i['kind'], len(ks),
                     f"{f['book']} {f['ch']}:{f['v']}", ' '.join(ks)))
    rows.sort()
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('pid\tname\tlemma\tstrong\tkind\tmentions\tfirst_mention\tmembers\n')
        for r in rows:
            fh.write('\t'.join(str(x) for x in r) + '\n')
    if mentions:
        with open(os.path.join(out, f'{code}.mentions.tsv'), 'w', encoding='utf-8') as fh:
            fh.write('key\tpid\tname\n')
            for k in res.mention_keys:
                if res.toks[k]['ch'] in chs:
                    p = res.pid(k)
                    fh.write(f'{k}\t{p}\t{res.name(p)}\n')
    return path, rows


def chapter_list(args):
    out = []
    for a in args:
        lo, _, hi = a.partition('-')
        out += range(int(lo), int(hi or lo) + 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('code', help='book code (GEN, php, ...)')
    ap.add_argument('ch', nargs='+', help='chapters: 24, or 1-24')
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'participants'))
    ap.add_argument('--mentions', action='store_true')
    ap.add_argument('--check', action='store_true', help='print the self-test only, write nothing')
    a = ap.parse_args()
    t = {b[0]: b[2] for b in books.BOOKS}.get(a.code.lower())
    if not t:
        raise SystemExit(f'unknown book code {a.code}')
    lang = 'hbo' if t == 'ot' else 'grc'
    chs = chapter_list(a.ch)
    if not os.path.exists(os.path.join(ROOT, 'orig', 'heb.sqlite' if lang == 'hbo' else 'grc.sqlite')):
        raise SystemExit('orig/heb.sqlite / orig/grc.sqlite missing: python3 scripts/setup.py --only src,spk')
    res = resolve(lang, a.code, chs)
    sc = res.speaker_check
    check = f"self-test (1st person in quotations vs speaker): {sc['agree']} agree / {sc['differ']} differ"
    if not res.tipnr_dir:
        check += '; no TIPNR (python3 scripts/setup.py --only names): names by Strong\'s only'
    if a.check:
        print(check)
        return
    os.makedirs(a.out, exist_ok=True)
    path, rows = write(res, a.out, a.mentions)
    n_m = sum(r[5] for r in rows)
    single = sum(1 for r in rows if r[5] == 1)
    print(f'{os.path.relpath(path, ROOT)}: {len(rows)} participants, {n_m} mentions, {single} singletons; '
          f'joins {dict(res.joined_by)}')
    print(f'speakers {dict((res.speaker_label(k[0]), v) for k, v in res.speaker_pid.items() if k[1] in chs)}')
    print(check)


if __name__ == '__main__':
    main()
