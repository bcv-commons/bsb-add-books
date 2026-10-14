#!/usr/bin/env python3
"""The drafting agents' learning tool for a project's language: the style corpus side by side with the
assisting translation (docs/proposals/language-toolkit/). Every command prints references with both texts.

  python3 scripts/concord.py <project> eng "<regex>" [N]   verses whose assisting text (BSB) matches
  python3 scripts/concord.py <project> tgt "<regex>" [N]   verses whose target text matches (the ignored
                                                           marks are ignored: write plain letters)
  python3 scripts/concord.py <project> like "<sentence>" [N]  the verses most like an English sentence
                                                           (word overlap, rare words weigh more)
  python3 scripts/concord.py <project> lex <english word> [N]  target renderings of an English word
                                                           (lexicon_eng.tsv: count, share)
  python3 scripts/concord.py <project> hlex "<regex>" [N]  renderings of Hebrew lexemes whose id, lemma or
                                                           gloss matches (lexicon_hbo.tsv: hbo:1350, גאל, redeem)
  python3 scripts/concord.py <project> forms "<regex>" [N] target word forms matching, with counts
  python3 scripts/concord.py <project> gloss "<regex>"     the edition's glossary entries (glossary.tsv)
  python3 scripts/concord.py <project> store "<regex>"     language-store entries whose id, source or value
                                                           matches, in full with their evidence
The target command is also available under the project's language code (e.g. `kvg`). N defaults to 8
(40 for forms). Lexicons come from scripts/align.py.
"""
import collections, json, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
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
    n = int(a[3]) if len(a) > 3 else (40 if cmd == "forms" else 8)
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
            print("\n".join("\t".join(r[1:]) for r in hits) or "not in the lexicon")
        else:
            hits = [r for r in rows if re.search(arg, " ".join(r[:3]), re.I)][:n * 3]
            print("\n".join("\t".join(r) for r in hits) or "not in the Hebrew lexicon")
        return
    if cmd == "store":
        for fn in ("observations.json", "decisions.json"):
            f = os.path.join(P.profile, fn)
            if os.path.exists(f):
                for e in json.load(open(f, encoding="utf-8"))["entries"]:
                    if re.search(arg, " ".join(str(e.get(k, "")) for k in ("id", "source", "value")), re.I):
                        print(json.dumps(e, ensure_ascii=False, indent=1), "\n")
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
        rx = re.compile(P.tok.plain(arg), re.I)
        c = collections.Counter(w for r in rows for w in P.tok.rx.findall(P.tok.plain(r[4])) if rx.search(w))
        print("\n".join(f"{c[w]:6}  {w}" for w, _ in c.most_common(n)))
    elif cmd == "like":
        df = collections.Counter(t for r in rows for t in set(LT.eng_tokens(r[3])))
        q = set(LT.eng_tokens(arg))
        score = lambda r: sum(math.log(len(rows) / (1 + df[t])) for t in set(LT.eng_tokens(r[3])) if t in q)
        show(sorted(rows, key=score, reverse=True), n, label)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
