"""Copy check for a Hebrew draft of the OT (a modern Hebrew project): how much of each verse is the Hebrew original
passed through word for word. Words are compared without points and without the vowel letters ו and י inside the word
(a full spelling of the same biblical word counts as the same word); a run is a stretch of draft words that is also a
stretch of the verse's original words. Reported per verse: the longest run and the share of words in runs of 3 or
more; verses over the limits are listed for review (lists, names and genealogies are legitimately high). The
original: the WLC (MACULA Hebrew, orig/heb.sqlite), in the drafts' Hebrew numbering.
Measured: a copy of the consonantal WLC of Ruth, 97% of its words in runs; a modern Hebrew rendering, about 5-15%.

Usage: python3 scripts/heb_copy.py <project> <code> [<ch>] [--run 5] [--share 0.6]
"""
import os, re, sqlite3, sys, unicodedata
from project import ROOT, project_dir
import langtools as LT

POINTS = re.compile(r"[֑-ׇ]")
FINAL = str.maketrans("ךםןףץ", "כמנפצ")
WORD = re.compile(r"[א-ת]+")


def key(w):
    w = POINTS.sub("", unicodedata.normalize("NFD", w)).translate(FINAL)
    return w[0] + re.sub("[וי]", "", w[1:-1]) + w[-1] if len(w) > 2 else w


def words(text):
    return [key(w) for w in WORD.findall(POINTS.sub("", unicodedata.normalize("NFD", text.replace("־", " "))))]


def wlc(book):
    con = sqlite3.connect(os.path.join(ROOT, "orig", "heb.sqlite"))
    text = {}
    for c, v, t, a in con.execute("select ch, v, text, coalesce(after, '') from tokens where book = ? order by key",
                                  (book.upper(),)):
        text[(c, v)] = text.get((c, v), "") + t + a          # MACULA splits prefixes off: join a word's parts
    return {cv: words(t) for cv, t in text.items()}


def runs(draft, src):
    """(longest run, words in runs of 3 or more) of draft words that are consecutive in the source too"""
    grams = {}
    for n in range(1, len(src) + 1):
        for i in range(len(src) - n + 1):
            grams.setdefault(n, set()).add(tuple(src[i:i + n]))
    longest, covered = 0, set()
    for i in range(len(draft)):
        n = 0
        while i + n < len(draft) and tuple(draft[i:i + n + 1]) in grams.get(n + 1, ()):
            n += 1
        longest = max(longest, n)
        if n >= 3:
            covered.update(range(i, i + n))
    return longest, len(covered)


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d
    lim_run, lim_share = opt("--run", 5), opt("--share", 0.6)
    pos = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in ("--run", "--share"))]
    if len(pos) < 2:
        print(__doc__); sys.exit(2)
    name, code = pos[0], pos[1]
    d = os.path.join(project_dir(name), code)
    files = sorted(f for f in os.listdir(d) if re.fullmatch(rf"{code}\d{{3}}\.txt", f)
                   and (len(pos) < 3 or int(f[3:6]) == int(pos[2])))
    src, tot_w, tot_c, over = wlc(code), 0, 0, 0
    for f in files:
        flagged = []
        for (c, v), t in sorted(LT.verses_of(os.path.join(d, f)).items()):
            dw, sw = words(t), src.get((c, v), [])
            if not dw or not sw:
                continue
            longest, cov = runs(dw, sw)
            tot_w += len(dw); tot_c += cov
            if longest >= lim_run or cov / len(dw) > lim_share:
                flagged.append(f"{c}:{v} run {longest}, {cov / len(dw):.0%}")
        over += len(flagged)
        print(f"{f}: {len(flagged)} verses over the limits" + (": " + "; ".join(flagged) if flagged else ""))
    if tot_w:
        print(f"all: {tot_c / tot_w:.1%} of {tot_w} words in runs of 3 or more original words; {over} verses to review")
