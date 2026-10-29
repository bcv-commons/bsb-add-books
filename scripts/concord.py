#!/usr/bin/env python3
"""The drafting agents' learning tool for a project's language: the style corpus side by side with the
assisting translation (docs/onboarding.md). Every command prints references with both texts.

  python3 scripts/concord.py <project> eng "<regex>" [N]   verses whose assisting text (BSB) matches
  python3 scripts/concord.py <project> tgt "<regex>" [N]   verses whose target text matches (the ignored
                                                           marks are ignored: write plain letters)
  python3 scripts/concord.py <project> like "<sentence>" [N]  the verses most like an English sentence
                                                           (word overlap, rare words weigh more)
  python3 scripts/concord.py <project> lex <english word> [N]  target renderings of an English word
                                                           (lexicon_eng.tsv: count, share)
  python3 scripts/concord.py <project> hlex "<regex>" [N]  renderings of Hebrew lexemes whose id, lemma or
                                                           gloss matches (lexicon_hbo.tsv: hbo:1350, גאל, redeem)
  python3 scripts/concord.py <project> forms "<regex>" [N] target word forms matching (without the ignored marks), shown as the corpus spells them, with counts
  python3 scripts/concord.py <project> gloss "<regex>"     the edition's glossary entries (glossary.tsv)
  python3 scripts/concord.py <project> store "<regex>"     language-store entries whose id, source or value
                                                           matches, in full with their evidence
With morph entries in the store (scripts/morphs.py), a word's parts:
  python3 scripts/concord.py <project> parts <word> ...    each word as its parts, with what each affix means
  python3 scripts/concord.py <project> stem <stem> [N]     the corpus forms of a stem (write it plain), with their
                                                           parts and counts: the forms to build a new one from
  python3 scripts/concord.py <project> morph <affix> [N]   the corpus words that carry an affix (tu-, -ibw, aá-; as
                                                           the store writes it), most frequent first, and its stems
The target command is also available under the project's language code (e.g. `jam`). N defaults to 8
(40 for forms). Lexicons come from scripts/align.py.
"""
import collections, json, math, os, re, sys

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
import langtools as LT  # noqa: E402


def show(rows, n, label):
    for ref, _, _, e, t in rows[:n]:
        print(f"{ref}\n  BSB:  {e}\n  {label}: {t}\n")
    print(f"({len(rows)} verses)" if len(rows) > n else "")


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        raise SystemExit(__doc__)
    P = LT.Project(a[0])
    cmd, arg = a[1], a[2]
    n = int(a[3]) if len(a) > 3 and cmd != "parts" else (40 if cmd in ("forms", "stem", "morph") else 8)
    lang = P.p.get("language") or "target"
    if cmd == lang:
        cmd = "tgt"
    if cmd in ("lex", "hlex"):
        f = os.path.join(P.learn, "lexicon_eng.tsv" if cmd == "lex" else "lexicon_hbo.tsv")
        if not os.path.exists(f):
            raise SystemExit(f"no {os.path.relpath(f, ROOT)}: run python3 scripts/align.py {P.name}")
        rows = [l.split("\t") for l in open(f, encoding="utf-8").read().splitlines()[1:]]
        if cmd == "lex":
            hits = [r for r in rows if r[0] == arg.lower()][:n]
            print("\n".join("\t".join([P.spelled(r[1])] + r[2:]) for r in hits) or "not in the lexicon")
        else:
            hits = [r for r in rows if re.search(arg, " ".join(r[:3]), re.I)][:n * 3]
            print("\n".join("\t".join(r[:3] + [P.spelled(r[3])] + r[4:]) for r in hits) or "not in the Hebrew lexicon")
        return
    if cmd == "store":
        for fn in ("observations.json", "decisions.json"):
            f = os.path.join(P.profile, fn)
            if os.path.exists(f):
                for e in json.load(open(f, encoding="utf-8"))["entries"]:
                    if re.search(arg, " ".join(str(e.get(k, "")) for k in ("id", "source", "value", "gloss")), re.I):
                        import gloss as G
                        print(json.dumps(e, ensure_ascii=False, indent=1))
                        print("".join(f"  gloss: {G.line(g)}\n" for g in G.glosses(e)))
        return
    if cmd == "gloss":
        for row in P.glossary():
            if re.search(arg, "\t".join(row), re.I):
                print("  |  ".join(row), "\n")
        return
    rows = P.corpus()
    label = (P.p.get("language_name") or lang).split(" (")[0]
    if cmd == "eng":
        show([r for r in rows if re.search(arg, r[3], re.I)], n, label)
    elif cmd == "tgt":
        rx = re.compile(P.tok.plain(arg), re.I)
        show([r for r in rows if rx.search(P.tok.plain(r[4]))], n, label)
    elif cmd == "forms":
        # matched without the ignored marks, shown as the corpus writes them (every spelling with its count)
        rx = re.compile(P.tok.plain(arg), re.I)
        c = collections.Counter(w for r in rows for w in P.tok.rx_exact.findall(P.tok.exact(r[4])) if rx.search(P.tok.plain(w)))
        print("\n".join(f"{c[w]:6}  {w}" for w, _ in c.most_common(n)))
    elif cmd in ("parts", "stem", "morph"):
        import grammar, morphs
        S = P.segmenter()
        if not S:
            raise SystemExit(f"{P.name}: the store has no morph entries (scripts/morphs.py)")
        A = morphs.affix_entries(grammar.load(P.name))
        if cmd == "parts":
            for w in a[2:]:
                for t in P.tok.tokens(w, exact=True):
                    ms = S.split(t)
                    print(f"{t} = {morphs.parts(S, t) or t}")
                    for m in ms:
                        e = A.get((m.form, m.position)) if m.slot != "stem" else None
                        if m.slot != "stem":
                            print(f"    {m.form:8} {m.slot}{f' {m.position}' if m.position else ''}: "
                                  + (morphs.meaning(e) if e else "(not in the store)"))
            return
        words = S.vocab_exact
        if cmd == "stem":
            want = S.plain(P.tok.plain(arg))
            c = [(w, k) for w, k in words.most_common() if any(m.slot == "stem" and m.form == want for m in S.split(w))]
        else:
            fm = __import__("unicodedata").normalize("NFC", arg.lower())
            c = [(w, k) for w, k in words.most_common() if any(m.form == fm for m in S.split(w) if m.slot != "stem")]
            st = collections.Counter(next(m.form for m in S.split(w) if m.slot == "stem") for w, _ in c)
            print(f"{arg}: {sum(k for _, k in c)} tokens, {len(c)} forms, {len(st)} stems (most: "
                  + ", ".join(f"{x} {k}" for x, k in st.most_common(8)) + ")")
        print("\n".join(f"{k:6}  {w} = {morphs.parts(S, w) or w}" for w, k in c[:n]))
        print(f"({len(c)} forms)" if len(c) > n else "")
    elif cmd == "like":
        df = collections.Counter(t for r in rows for t in set(LT.eng_tokens(r[3])))
        q = set(LT.eng_tokens(arg))
        score = lambda r: sum(math.log(len(rows) / (1 + df[t])) for t in set(LT.eng_tokens(r[3])) if t in q)
        show(sorted(rows, key=score, reverse=True), n, label)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
