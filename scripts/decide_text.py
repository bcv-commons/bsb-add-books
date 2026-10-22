#!/usr/bin/env python3
"""Words or parts by measurement: the figures behind a project's `analysis.model_text` (the second-draft model's target
as whole words or as the store's parts; docs/language-store.md, scripts/nllb/model_text.py). Run as
`python3 scripts/morphs.py <project> decide [--write]`.

Figures, over the project's style corpus (langtools.Project.corpus):
  - tokens per type over the first 100,000 tokens: lexeme-aligner's measure (bcv-commons/lexeme-aligner,
    pipeline/lexeme_aligner/target_morph.py: `sample_tokens_per_type`, `should_stem`, STEM_RATIO_THRESHOLD = 13.0;
    a ratio at or below 13 turns their stemming on). The sample is capped because tokens/type grows with corpus size
    (Heaps' law); lowercased tokens, here from the project's own tokeniser and in corpus order (theirs: USJ, spine order);
  - split share: the share of tokens (and of types) the store's confirmed affixes split (morphs.parts);
  - forms per stem: distinct written forms per stem, over the stems that occur with an affix;
  - decode: every corpus type encoded as model parts and decoded back exactly (model_text.Codec, as `model_text.py check`).

The suggestion: `morphs` when the store splits enough (split share >= SPLIT_MIN of the tokens), the language is rich in
forms by lexeme-aligner's measure (ratio <= RATIO_MAX) and every type decodes back exactly; else `words`, with the reason.
The thresholds: the known and partial sample projects (Danish, Jamaican) come out words, Zinza and a second unknown
language with an affix chain morphs. They decide the model's input, not its quality: the trained comparisons so far
(Zinza, Philippians held out: chrF3 43.3 words / 43.0 morphs; the other language 45.8 / 43.5) were level or favoured
words, so `morphs` is a candidate to train and compare, not a promise.
--write records the figures and the suggestion as analysis.model_text_measured; it never changes analysis.model_text,
which a person sets after training both and comparing their scores (scripts/score.py on held-out chapters)."""
import collections
import datetime
import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RATIO_MAX = 13.0          # lexeme-aligner STEM_RATIO_THRESHOLD
SAMPLE = 100_000          # lexeme-aligner _RATIO_SAMPLE_TOKENS
SPLIT_MIN = 0.10          # share of tokens split by confirmed affixes


def figures(tokens, S=None, confirmed=None, codec=None):
    """tokens: the corpus's exact tokens in order; S: the Segmenter (None: no morph entries); confirmed:
    morphs.affix_entries; codec: a model_text Codec in morphs mode (None: no decode check)"""
    import morphs
    low = [unicodedata.normalize("NFC", t.lower()) for t in tokens]
    sample = low[:SAMPLE]
    ratio = len(sample) / len(set(sample)) if sample else None
    cnt = collections.Counter(tokens)
    split_tok = split_typ = 0
    stems = collections.defaultdict(set)
    if S is not None:
        for w, n in cnt.items():
            p = morphs.parts(S, w, confirmed)
            if p:
                split_tok += n
                split_typ += 1
                st = next((m.form for m in S.split(w) if m.slot == "stem"), None)
                if st:
                    stems[st].add(w.lower())
        for w in cnt:                              # the bare stem is a form of it too
            if w.lower() in stems:
                stems[w.lower()].add(w.lower())
    bad, model_tok = [], 0
    if codec is not None and S is not None:
        for w in cnt:
            e = codec.encode(w, S)
            model_tok += len(e.split()) * cnt[w]
            if codec.decode(e) != unicodedata.normalize("NFC", w):
                bad.append(w)
    N = len(tokens)
    return {"tokens": N, "types": len(cnt), "ratio": ratio, "sample": len(sample),
            "split_tokens": split_tok / N if N else 0.0, "split_types": split_typ / len(cnt) if cnt else 0.0,
            "forms_per_stem": sum(map(len, stems.values())) / len(stems) if stems else 1.0, "stems": len(stems),
            "decode_bad": bad if codec is not None and S is not None else None,
            "parts_per_word": model_tok / N if N and model_tok else None, "morph_entries": S is not None}


def suggest(f):
    """(model_text, reason)"""
    if not f["morph_entries"]:
        return "words", "the store has no morph entries"
    why = []
    if f["split_tokens"] < SPLIT_MIN:
        why.append(f"the store splits only {f['split_tokens']:.1%} of the tokens (< {SPLIT_MIN:.0%})")
    if f["ratio"] is None or f["ratio"] > RATIO_MAX:
        why.append(f"tokens per type {f['ratio'] or 0:.2f} > {RATIO_MAX} (lexeme-aligner: no stemming)")
    if f["decode_bad"]:
        why.append(f"{len(f['decode_bad'])} type(s) don't decode back exactly")
    if why:
        return "words", "; ".join(why)
    return "morphs", (f"the store splits {f['split_tokens']:.1%} of the tokens, tokens per type {f['ratio']:.2f} <= "
                      f"{RATIO_MAX}, every type decodes back exactly")


def run(pname, write=False):
    import langtools as LT
    import grammar
    import morphs
    from nllb import model_text as MT
    P = LT.Project(pname)
    toks = [t for r in P.corpus() for t in P.tok.tokens(r[4], exact=True)]
    G = grammar.load(pname)
    S = morphs.load(pname, P, G)
    C = None
    if S is not None:
        try:
            C, _ = MT.codec_for(pname, "morphs", P)
        except SystemExit as e:                     # the corpus uses the joiner: no clean decode
            print(f"  codec: {e}")
    f = figures(toks, S, morphs.affix_entries(G), C)
    m, why = suggest(f)
    pf = os.path.join(P.profile, "observations.json")
    d = json.load(open(pf, encoding="utf-8")) if os.path.exists(pf) else {}
    have = (d.get("analysis") or {}).get("model_text", "words")
    print(f"{pname}: {f['tokens']} tokens, {f['types']} types")
    print(f"  tokens per type (first {f['sample']} tokens; lexeme-aligner should_stem at <= {RATIO_MAX}): "
          f"{f['ratio'] or 0:.2f}")
    print(f"  split by the store's confirmed affixes: {f['split_tokens']:.1%} of tokens, {f['split_types']:.1%} of types")
    print(f"  forms per stem (stems seen with an affix): {f['forms_per_stem']:.2f} over {f['stems']} stems")
    if f["decode_bad"] is not None:
        print(f"  decoded exactly: {f['types'] - len(f['decode_bad'])} of {f['types']} types"
              + (f" (e.g. {', '.join(f['decode_bad'][:5])})" if f["decode_bad"] else "")
              + (f"; {f['parts_per_word']:.2f} model tokens a word" if f["parts_per_word"] else ""))
    print(f"  suggested model_text: {m} ({why}); the store has: {have}")
    if write:
        if not os.path.exists(pf):
            raise SystemExit(f"{pname}: no store ({pf})")
        fig = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in f.items() if k != "decode_bad"}
        fig["decode_bad"] = len(f["decode_bad"]) if f["decode_bad"] is not None else None
        d.setdefault("analysis", {})["model_text_measured"] = {
            "suggestion": m, "reason": why, "figures": fig, "by": "script:morphs.py decide",
            "date": datetime.date.today().isoformat()}
        json.dump(d, open(pf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        open(pf, "a").write("\n")
        print(f"  recorded as analysis.model_text_measured; model_text stays {have}: a suggestion to train and compare "
              f"(scripts/nllb/data.py --model-text {m}), not a switch")
    return f, m, why


def main(a):
    run(a[0], write="--write" in a)


if __name__ == "__main__":
    main(sys.argv[1:])
