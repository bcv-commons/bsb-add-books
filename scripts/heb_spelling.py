"""Hebrew spelling for a modern Hebrew source or target: the NLLB data step for a project that writes or reads modern
Hebrew (scripts/nllb/data.py's source side), and the agents' corpus in the spelling they write.

  male   pointed Hebrew -> unpointed full spelling (ktiv male). The points decide where a vowel letter may go: holam
         and qubuts -> ו, hiriq in an open syllable or before a dagesh -> י (not in min and the pe-nun forms: מכל,
         הכיר), a consonantal vav or yod inside the word doubled (not next to a vowel letter; yod not after the
         prefixes), a few traditional spellings kept (משה, דוד, כהן), a few the points don't show (הייתה, עכשיו), אִתּ-
         "with" always איתי, איתה. Where the rules are uncertain (a doubled vav
         or yod, a hiriq before a dagesh, a qamats that may be qatan), every spelling is tried and the one a modern
         text uses most wins (--vocab: an unpointed modern Hebrew edition's folder); without it, the rules' choice.
         Measured on a modern NT's letters, its Gospels and Acts as the word list and its other books as the test:
         88.7% of the tokens (whose letters that text has) spelled as it spells them; where they differ, mostly piel
         forms it writes short (קבלו) and the Academy full (קיבלו), as here.
  norm   unpointed Hebrew -> the spelling of a reference text (--ref: an edition folder, e.g. one made by `male`),
         so a model meets one spelling in training and in drafting: a word the reference has stays; a word it lacks,
         whose letters differ from a reference word only in the inner ו and י (חכמה / חוכמה, עדין / עדיין), takes the
         reference's spelling when that is clearly the usual one (3 times or more, 2/3 of the words with those
         letters). A hyphen between Hebrew letters becomes a maqaf; geresh and gershayim become ' and ". For data,
         not for drafts: --report lists the changes (test: about 70% restored, 4% changed to another word).
  test   the rules on their test words; with --ref, the normaliser's test (an inner vowel letter dropped from the
         reference's own words).

Usage: python3 scripts/heb_spelling.py male <pointed edition text dir> <out dir> [--vocab DIR|counts.json]
       python3 scripts/heb_spelling.py norm --ref DIR [--ref DIR] <in file> <out file> [--report]   (any text file)
       python3 scripts/heb_spelling.py test [--ref DIR]
"""
import collections, itertools, os, random, re, sys, unicodedata

SHEVA, HATAFS, HIRIQ, TSERE, SEGOL, PATAH, QAMATS, HOLAM, HOLAM_V, QUBUTS = (
    "\u05B0", "\u05B1\u05B2\u05B3", "\u05B4", "\u05B5", "\u05B6", "\u05B7", "\u05B8", "\u05B9", "\u05BA", "\u05BB")
DAGESH = "\u05BC"
VOWELS = HATAFS + HIRIQ + TSERE + SEGOL + PATAH + QAMATS + HOLAM + HOLAM_V + QUBUTS
LETTER = re.compile(r"[\u05D0-\u05EA]")
POINT = re.compile(r"[\u0591-\u05BD\u05BF\u05C1\u05C2\u05C4\u05C5\u05C7]")   # not maqaf, paseq, sof pasuq
WORD = re.compile(r"[\u05D0-\u05EA][\u05D0-\u05EA\u0591-\u05BD\u05BF-\u05C2\u05C4-\u05C7]*")   # a maqaf ends a word
PREFIX = "ובכלמשה"
LEXICAL = {"היתה": "הייתה", "עכשו": "עכשיו"}   # the Academy's spellings the points don't show
KEEP = {"כה", "פה", "משה", "שלמה", "אהרן", "יעקב", "נח", "כהן", "כהנים", "דוד"}   # traditional spellings kept


def split(word):
    """[(letter, marks)] of a pointed word (NFD)"""
    out = []
    for ch in unicodedata.normalize("NFD", word):
        if LETTER.match(ch):
            out.append([ch, ""])
        elif out:
            out[-1][1] += ch
    return out


def vowel(m):
    return next((c for c in m if c in VOWELS or c == SHEVA), "")


def mater_vav(cells, i):
    """vav as a vowel letter: shuruk (dagesh, no vowel) or holam male (holam, the letter before has no vowel)"""
    c, m = cells[i]
    if c != "ו":
        return False
    v = vowel(m)
    return (DAGESH in m and not v) or (v in (HOLAM, HOLAM_V) and i > 0 and not vowel(cells[i - 1][1]))


def mater_yod(cells, i):
    c, m = cells[i]
    return c == "י" and not vowel(m) and DAGESH not in m and i > 0 and vowel(cells[i - 1][1]) in (HIRIQ, TSERE, SEGOL)


def voiced(cells, j):
    """letter j has a full vowel: a point other than sheva, or a shuruk / holam male after it (כּוּ)"""
    return vowel(cells[j][1]) not in ("", SHEVA) or (j + 1 < len(cells) and mater_vav(cells, j + 1))


def options(word):
    """the spellings the rules allow, as a list of alternatives per letter (the rules' choice first)"""
    cells = split(word)
    n, out = len(cells), []
    after_prefix = lambda i: all(c in PREFIX for c, _ in cells[:i]) and i <= 2
    for i, (c, m) in enumerate(cells):
        v, nxt = vowel(m), cells[i + 1] if i + 1 < n else None
        if c == "ו" and mater_vav(cells, i):
            out.append(["ו"]); continue
        if c == "ו" and 0 < i < n - 1 and (v or DAGESH in m) and not (i == 1 and cells[0][0] == "ו"):
            near = mater_vav(cells, i - 1) or mater_vav(cells, i + 1)
            alt = ["ו"] if near else ["וו", "ו"]
        elif c == "י" and 0 < i < n - 1 and (v or DAGESH in m) and v not in (SHEVA, HOLAM, HOLAM_V, QUBUTS):
            near = mater_yod(cells, i - 1) or mater_yod(cells, i + 1) or (nxt[0] == "י" and not vowel(nxt[1]))
            alt = ["י"] if near else (["י", "יי"] if after_prefix(i) or (v == HIRIQ and DAGESH not in m) else ["יי", "י"])
        else:
            alt = [c]
        if v in (HOLAM, HOLAM_V) and c != "ו" and not (nxt and nxt[0] == "ו" and mater_vav(cells, i + 1)):
            silent_alef = nxt and nxt[0] == "א" and not vowel(nxt[1])
            # before a silent alef the vav varies by word (לא, ראש, זאת / למצוא, לבוא): the word list decides
            alt = [a + "ו" for a in alt] if not silent_alef else alt + [a + "ו" for a in alt]
        elif v == QUBUTS:
            alt = [a + "ו" for a in alt]
        elif v == HATAFS[2]:                            # hataf qamats: a short o (שִׁבֳּלִים -> שיבולים), by the word list
            alt = alt + [a + "ו" for a in alt]
        elif v == HIRIQ and nxt and nxt[0] != "י" and (voiced(cells, i + 1) or (DAGESH in nxt[1] and i + 2 < n)):
            # (a dagesh after the hiriq doubles the letter, so the syllable is open even before a sheva: סִפְּרוּ -> סיפרו)
            yes, no = [a + "י" for a in alt], alt
            min_or_pn = DAGESH in nxt[1] and c in "מהנ" and after_prefix(i)
            alt = no + yes if min_or_pn else yes + no
        elif v == QAMATS and nxt and vowel(nxt[1]) == SHEVA and i + 2 < n:
            alt = alt + [a + "ו" for a in alt]          # maybe qamats qatan (חָכְמָה -> חוכמה): only the word list decides
        out.append(alt)
    return out


def lexical(w):
    """spellings the points don't show, after the prefixes (היתה -> הייתה, ועכשו -> ועכשיו). A list, not a rule: a
    letter added by the word list alone makes homographs (חטאו / חטאיו, השנים / השניים)"""
    for i in range(min(3, len(w))):
        if all(c in PREFIX for c in w[:i]) and w[i:] in LEXICAL:
            return w[:i] + LEXICAL[w[i:]]
    return w


def male(word, vocab=None):
    plain = unicodedata.normalize("NFC", POINT.sub("", unicodedata.normalize("NFD", word)))
    if plain in KEEP or not LETTER.search(plain):
        return plain
    alts = options(word)
    cells = split(word)
    for i in range(len(cells) - 1):        # אִתִּי, אִתָּהּ (with me, with her): always איתי, איתה, not the pronoun אתה
        if cells[i][0] == "א" and vowel(cells[i][1]) == HIRIQ and cells[i + 1][0] == "ת" and DAGESH in cells[i + 1][1] \
                and all(c in PREFIX for c, _ in cells[:i]):
            alts[i] = [a + "י" for a in alts[i] if not a.endswith("י")] or alts[i]
    first = "".join(a[0] for a in alts)
    if vocab:
        combos = list(itertools.islice(itertools.product(*alts), 256))
        best = max(combos, key=lambda c: vocab.get("".join(c), 0))
        if vocab.get("".join(best), 0):
            return lexical("".join(best))
    return lexical(first)


def convert(text, vocab=None):
    return WORD.sub(lambda m: male(m[0], vocab), text)


# norm
WORDS = re.compile(r"[\u05D0-\u05EA]+")


def skeleton(w):
    return w[0] + re.sub("[וי]", "", w[1:-1]) + w[-1] if len(w) > 2 else w


def load(dirs):
    words = collections.Counter()
    for d in dirs:
        words.update(vocab_of(d))
    by_key = collections.defaultdict(collections.Counter)
    for w, n in words.items():
        by_key[skeleton(w)][w] += n
    return words, by_key


class Norm:
    def __init__(self, dirs):
        self.words, self.by_key = load(dirs)
        self.changes = collections.Counter()

    def word(self, w):
        if w in self.words:
            return w
        cands = self.by_key.get(skeleton(w))
        if not cands:
            return w
        best, n = cands.most_common(1)[0]
        if n >= 3 and n >= 2 * sum(cands.values()) / 3:
            self.changes[f"{w} → {best}"] += 1
            return best
        return w

    def line(self, s):
        s = re.sub(r"(?<=[א-ת])-(?=[א-ת])", "־", s).replace("׳", "'").replace("״", '"')
        return WORDS.sub(lambda m: self.word(m[0]), s)


TESTS = {"הַכֺּל": "הכול", "חֺשֶׁךְ": "חושך", "כֻּלָּנוּ": "כולנו", "הָאֲמִתִּי": "האמיתי", "לֹא": "לא", "אוֹתוֹ": "אותו",
         "הָאֱלֹהִים": "האלוהים", "מִצְוָה": "מצווה", "עִנְיָן": "עניין", "חַיִּים": "חיים", "יִשְׂרָאֵל": "ישראל",
         "מִלִּפְנֵי": "מלפני", "תֺּקֶף": "תוקף", "מֺשֶׁה": "משה", "שָׁלוּחַ": "שלוח", "כְּבוֹדוֹ": "כבודו",
         "דִּבֵּר": "דיבר", "סִפֵּר": "סיפר", "הַוִּכּוּחַ": "הוויכוח", "רֹאשׁ": "ראש", "אִם": "אם", "בַּיִת": "בית",
         "מְיֻחָד": "מיוחד", "יְרוּשָׁלַיִם": "ירושלים", "זֹאת": "זאת", "הִכִּירוֹ": "הכירו", "מִכָּל": "מכל",
         "אִשָּׁה": "אישה", "הָיָה": "היה", "עַל־יָדָיו": "על־ידיו", "וּלְוִיִּם": "ולוויים",
         "תִּקְוָה": "תקווה", "סִפְּרוּ": "סיפרו", "אִתָּהּ": "איתה", "וְאִתּוֹ": "ואיתו", "צִוָּה": "ציווה", "בְּיַד": "ביד", "וְיֵשׁ": "ויש", "דָּוִד": "דוד", "חַיָּב": "חייב"}


def chapter_files(d):
    return sorted(f for f in os.listdir(d) if re.fullmatch(r"[0-9a-z]{3}\d{3}\.txt", f))


def vocab_of(d):
    if d.endswith(".json"):                       # word counts {word: n}, e.g. of an edition we may not keep as text
        import json
        return collections.Counter(json.load(open(d, encoding="utf-8")))
    return collections.Counter(WORDS.findall("".join(open(os.path.join(d, f), encoding="utf-8").read()
                                                     for f in chapter_files(d))))


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k: [a[i + 1] for i, x in enumerate(a) if x == k]
    args = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in ("--vocab", "--ref"))]
    cmd = args[0] if args else ""
    if cmd == "male":
        src, dst = args[1:3]
        vocab = vocab_of(opt("--vocab")[0]) if opt("--vocab") else None
        os.makedirs(dst, exist_ok=True)
        for f in chapter_files(src):
            open(os.path.join(dst, f), "w", encoding="utf-8").write(convert(open(os.path.join(src, f), encoding="utf-8").read(), vocab))
        print(f"{len(chapter_files(src))} chapters -> {dst}")
    elif cmd == "norm":
        N = Norm(opt("--ref"))
        with open(args[2], "w", encoding="utf-8") as out:
            for l in open(args[1], encoding="utf-8"):
                out.write(N.line(l))
        if "--report" in a:
            for c, n in N.changes.most_common():
                print(f"{n:5}  {c}")
    elif cmd == "test":
        bad = [(p, convert(p), w) for p, w in TESTS.items() if convert(p) != w]
        for p, got, want in bad:
            print(f"{p}: {got} (want {want})")
        print(f"male: {len(TESTS) - len(bad)}/{len(TESTS)} test words ok")
        if opt("--ref"):
            N = Norm(opt("--ref")); rng = random.Random(5)
            words = [w for w, n in N.words.items() for _ in range(n)]
            ok = wrong = kept = 0
            for w in [w for w in rng.sample(words, min(20000, len(words))) if re.search("[וי]", w[1:-1])]:
                i = rng.choice([i for i in range(1, len(w) - 1) if w[i] in "וי"])
                broken = w[:i] + w[i + 1:]
                if broken in N.words:
                    continue
                got = N.word(broken)
                ok += got == w; wrong += got not in (w, broken); kept += got == broken
            n = ok + wrong + kept
            print(f"norm: {n} words with one inner vowel letter dropped: restored {ok / n:.1%}, left {kept / n:.1%}, "
                  f"changed to another word {wrong / n:.1%}")
        sys.exit(1 if bad else 0)
    else:
        print(__doc__); sys.exit(2)
