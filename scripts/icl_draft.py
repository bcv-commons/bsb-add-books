#!/usr/bin/env python3
"""A second draft of a chapter, made in context: silnlp's LLM path, for review triage (never an input to the agents).

Per verse: about 100 corpus verses (BSB English -> the style corpus) chosen by silnlp's greedy coverage step, the verse's
BSB English and its open original (WLC via orig/heb.sqlite, or the BGB), in silnlp's prompt, one model call. The
original is part of the query: it removes most major errors. The drafted book is
never among the examples. The reply is read as silnlp reads it (code fence and label removed, the most target-like
line by the corpus's character trigrams), and its XML escapes are undone (no `&gt;` in the text).

The draft is shaped by the edition's wording (100 of its verses per call): it is a triage tool, local, never published.
It goes to <project>/_eval/local/second/icl/<code>NNN.txt (vN lines, Hebrew verse numbers in the OT), with the
model replies cached beside it, so a second run costs nothing. `scripts/triage.py` compares it with the project's
draft. Cost: 14-20k input tokens a verse, a chapter in 1-3 minutes; Opus rather than Sonnet.

With --format m5 (on trial) the prompt carries more of what the project knows: the examples cover the query's source
lemmas (Greek Strong's; Hebrew through the LXX equivalent, else the Hebrew lexeme) and its marked verb cells
(scripts/source_cells.py) besides its English n-grams, half the weight each; after the source, one line per verb of a
marked cell with the store's pattern (scripts/verse_analysis.py), and the store's decided renderings of the verse's terms
and names (not those whose evidence cites the drafted book: on a held-out book they would be its human text). The examples' number stays --k, so the two formats cost about the same.

The model runs through Claude Code (`claude -p`, no tools, silnlp's system prompt), so no API key is needed.

Usage: python3 scripts/icl_draft.py <project> <code> <ch>[,<ch>..] [--k 100] [--model claude-opus-5-5] [--workers 4]
                                    [--no-orig] [--out DIR] [--trg-name NAME] [--format silnlp|m5] [--show V]
Needs scikit-learn (pip install scikit-learn).
"""
import collections, hashlib, html, json, os, re, subprocess, sys, tempfile, threading
from concurrent.futures import ThreadPoolExecutor
from xml.sax.saxutils import escape as xml_escape

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
sys.path.insert(0, os.path.join(CODE, "scripts"))
import numpy as np  # noqa: E402
import langtools as LT  # noqa: E402
import vrs  # noqa: E402
from books import BY_CODE  # noqa: E402
from notes_hebrew import original_verses  # noqa: E402
from project import project as load_project, project_dir  # noqa: E402

GUIDANCE = (
    "Use the examples as evidence for {trg_lang} vocabulary, grammar, inflection, names, spelling and "
    "punctuation. Retain shared words and established borrowings when the examples support them; use "
    "natural target constructions instead of mechanically copying source wording.\n"
    "Preserve the full meaning of the source: participants, actions, negation, relationships and "
    "emphasis. Adapt an example's wording to the current sentence; similar examples may describe "
    "different people or events.")
SYSTEM = ("Translate the final {src_lang} Bible verse into {trg_lang}, following the translation conventions "
          "demonstrated by this project's parallel examples.\n" + GUIDANCE
          + " Nearby translations provide context, not additional content to translate.\n"
          "Return only the {trg_lang} translation of the final source verse on one line, without a label, "
          "verse number, explanation or alternative translations.")
SINGLE_TASK = ("only this {src_lang} verse into {trg_lang}.\n<source_to_translate>\n{source}\n</source_to_translate>\n"
               "{trg_lang}:")
FEW_SHOT = ("<translation_examples>\n{examples}\n</translation_examples>\n\nFollowing the project's examples above, "
            "translate " + SINGLE_TASK)
EXAMPLE = "{src_lang}: {source}\n{trg_lang}: {target}"
ORIGINAL = ("</source_to_translate>\n<original_{tag}>\n{text}\n</original_{tag}>\nThe English is a guide; the {name} "
            "original is what is translated: where they differ (an addition, an omission, a referent), follow the {name}.")

GRAMMAR = ("<target_grammar>\nVerbs in this verse whose form {trg_lang} marks (the pattern the project's corpus shows for "
           "the verb's person or negation; a tendency, not a rule):\n{lines}\n</target_grammar>")
FIXED = ("<fixed_renderings>\nThe project's decided renderings of the source words in this verse (Strong's number, the sense in brackets where a word has more than one: use the one that fits):\n{lines}\n"
         "</fixed_renderings>")
CONTENT = {"verb", "noun", "adj", "adv"}

lock = threading.Lock()


def source_features(code, ch, v, db, cells):
    """the lemma and marked-cell features of a source verse: g:<Greek Strong's> (Hebrew words: their LXX equivalent),
    h:<Hebrew lexeme> where there is none, c:<paradigm>=<cell>"""
    import verse_analysis as VA
    nt = BY_CODE[code][2] == "nt"
    out = set()
    q = ("select key, strong, class from tokens where book = ? and ch = ? and v = ?" if nt else
         "select key, coalesce(nullif(greekstrong, ''), 'h' || lexeme), class from tokens where book = ? and ch = ? and v = ?")
    for key, lem, cls in db["nt" if nt else "ot"].execute(q, (code.upper(), ch, v)):
        if cls in CONTENT and lem:
            lem = str(lem)
            out.add(("h:" + lem[1:]) if lem.startswith("h") else "g:" + re.sub(r"\D", "", lem).lstrip("0"))
        t = cells["nt" if nt else "ot"](code).get(key)
        for par, bundle in (t.cells if t else []):
            if par in VA.VERB_PARADIGMS and VA.marked(par, bundle):
                out.add(f"c:{par}={bundle}")
    return out


def m5_blocks(pname, code, ch, prof, bsb_words, strongs, gverses, v):
    """the grammar and fixed-renderings blocks of one verse (m5)"""
    blocks = []
    if gverses.get(v):
        lines = [re.sub(r" \((?:observed|decided|open)[^)]*\)", "", l) for l in gverses[v]]
        blocks.append(("grammar", "\n".join(lines)))
    fixed = []
    for e in prof:
        if e.get("status") != "decided" or not isinstance(e.get("value"), str):
            continue
        if re.search(rf"\b{code.upper()} \d", json.dumps(e, ensure_ascii=False).upper()):
            continue                            # learned from this book's human text: a held-out test stays clean
        if e["kind"] == "term":
            m = re.match(r"([HG])(\d+)\b", e.get("source") or "")
            if m and m[2].lstrip("0") in strongs:
                fixed.append(f"- {e['source']} = {e['value']}")
        elif e["kind"] == "name":
            n = e["id"].split(":", 1)[-1].replace("-", " ").replace("_", " ")
            if n and f" {n} " in bsb_words:
                fixed.append(f"- {n.title()} = {e['value']}")
    if fixed:
        blocks.append(("fixed", "\n".join(dict.fromkeys(fixed[:12]))))
    return blocks


def coverage_select(sim, feats, w, k, anchors=20, cand_mult=4, min_cand=100, rel_w=0.7):
    """silnlp's CoverageExampleRetriever._select (example_retrieval.py): the most similar verses as anchors, then greedily
    the verse that best covers the query's n-grams not yet covered, weighed with its similarity.
    sim: (N,) cosine; feats: rows -> bool matrix over the query's n-grams; w: the query's n-gram weights."""
    cand = list(np.argsort(-sim)[:max(cand_mult * k, min_cand)])
    if not cand:
        return []
    F = feats(cand)
    ww = w / w.sum()
    rel = sim[cand] / max(float(sim[cand].max()), 1e-12)
    chosen = list(range(min(anchors, max(1, k // 2), len(cand))))
    avail = np.ones(len(cand), bool)
    avail[chosen] = False
    counts = F[chosen].sum(axis=0).astype(float)
    while len(chosen) < min(k, len(cand)):
        gain = F @ (ww / (1.0 + counts))
        gain = gain / max(float(gain[avail].max()), 1e-12)
        util = rel_w * rel + (1 - rel_w) * gain
        util[~avail] = -np.inf
        b = int(np.argmax(util))
        chosen.append(b)
        avail[b] = False
        counts += F[b]
    return [cand[i] for i in chosen]


def ask(system, prompt, model, cache, cache_file):
    key = hashlib.sha256(json.dumps([model, system, prompt]).encode()).hexdigest()
    if key in cache:
        return cache[key]
    cmd = ["claude", "-p", "--tools", "", "--no-session-persistence", "--strict-mcp-config", "--output-format", "json",
           "--system-prompt", system, "--model", model]
    for attempt in range(4):
        with tempfile.TemporaryDirectory() as empty:
            r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=empty, timeout=900)
        try:
            d = json.loads(r.stdout)
        except Exception:
            d = {"is_error": True, "result": (r.stderr or r.stdout)[-300:]}
        if not d.get("is_error") and d.get("result", "").strip():
            u = d.get("usage", {})
            val = {"text": d["result"], "in": u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                   + u.get("cache_read_input_tokens", 0), "out": u.get("output_tokens", 0)}
            with lock:
                cache[key] = val
                with open(cache_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"key": key, **val}, ensure_ascii=False) + "\n")
            return val
        print("retry", attempt, d.get("result", "")[:200], file=sys.stderr)
    return {"text": "", "in": 0, "out": 0}


def read_reply(text, trg, resemblance):
    m = re.match(r"^\s*```[^\n]*\n(.*?)\n?\s*```\s*$", text.strip(), re.S)
    text = m.group(1) if m else text
    cand = [re.sub(rf"^\s*({re.escape(trg)}|target|translation|output|answer)\s*[:\-]\s*", "", l.strip().strip("`"),
                   flags=re.I).strip() for l in text.strip().splitlines()]
    cand = [html.unescape(c) for c in cand if c]
    return max(reversed(cand), key=resemblance) if cand else ""


def main():
    a = sys.argv[1:]
    if len(a) < 3 or a[0] in ("-h", "--help"):
        raise SystemExit(__doc__)
    pname, code, chs = a[0], a[1], [int(x) for x in a[2].split(",")]
    opt = lambda n, d: a[a.index(n) + 1] if n in a else d
    k, model, workers = int(opt("--k", "100")), opt("--model", "claude-opus-5-5"), int(opt("--workers", "4"))
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import linear_kernel
    except ImportError:
        raise SystemExit("icl_draft.py needs scikit-learn: pip install scikit-learn")
    cfg = load_project(pname)
    trg = opt("--trg-name", cfg.get("language_name", cfg.get("language", "the target language")).split(" (")[0])
    out = opt("--out", os.path.join(project_dir(pname), "_eval", "local", "second", "icl"))
    os.makedirs(out, exist_ok=True)
    P = LT.Project(pname)
    pool = [r for r in P.corpus() if r[3] and r[4] and r[1] != code]
    if not pool:
        raise SystemExit(f"{pname}: no corpus verses to draw examples from")
    src = [r[3] for r in pool]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))
    M = vec.fit_transform(src).tocsr()
    tri = set()
    for r in pool:
        tri |= {r[4][i:i + 3] for i in range(len(r[4]) - 2)}
    resemblance = lambda line: sum(line[i:i + 3] in tri for i in range(len(line) - 2)) / max(1, len(line) - 2)
    cache_file = os.path.join(out, "replies.jsonl")
    cache = {}
    if os.path.exists(cache_file):
        for l in open(cache_file, encoding="utf-8"):
            d = json.loads(l)
            cache[d["key"]] = d
    langs = dict(src_lang="English", trg_lang=trg)
    system = SYSTEM.format(**langs)
    ot = BY_CODE[code][2] != "nt"
    oname = "Hebrew" if ot else "Greek"
    m5 = opt("--format", "silnlp") == "m5"
    if m5:                                  # the pool's source features, a binary matrix beside the English n-grams
        import sqlite3, scipy.sparse as sp, source_cells as SC, verse_analysis as VA, grammar
        from verse_pack import load_profile
        db = {"ot": sqlite3.connect(os.path.join(ROOT, "orig", "heb.sqlite")),
              "nt": sqlite3.connect(os.path.join(ROOT, "orig", "grc.sqlite"))}
        ccache = {}

        def cells_of(t, c):
            if (t, c) not in ccache:
                ccache[(t, c)] = SC.cells_of(c.upper(), t)
            return ccache[(t, c)]
        cells = {t: (lambda c, t=t: cells_of(t, c)) for t in ("ot", "nt")}
        feats = [source_features(r[1], r[2][0], r[2][1], db, cells) for r in pool]
        fid = {f: i for i, f in enumerate(sorted(set().union(*feats)))}
        rows = [i for i, fs in enumerate(feats) for f in fs]
        F = sp.csr_matrix((np.ones(len(rows)), (rows, [fid[f] for fs in feats for f in fs])), shape=(len(pool), len(fid)))
        df = np.asarray((F > 0).sum(0)).ravel()
        idf = np.log((1 + len(pool)) / (1 + df)) + 1
        prof = load_profile(os.path.join(project_dir(pname), "profile"))
        G = grammar.load(pname)
    tot = collections.Counter()
    for ch in chs:
        orig = original_verses(code, ch)
        if not orig:
            raise SystemExit(f"no original text for {code} {ch}")
        jobs = []
        gverses = VA.grammar_block(pname, code, ch)[1] if m5 and G.cells else {}
        for v in sorted(orig):
            c, bv = vrs.to_bsb(code, ch, v) if ot else (ch, v)
            bsb = LT.verses_of(os.path.join(ROOT, P.assist_dir(code), f"{code}{c:03d}.txt")).get((c, bv), "")
            qv = vec.transform([bsb])
            sim = linear_kernel(qv, M).ravel()
            if m5:
                qf = [fid[f] for f in source_features(code, ch, v, db, cells) if f in fid]
                wq = idf[qf] * (qv.data.sum() / max(1e-9, idf[qf].sum())) if qf else np.zeros(0)   # half the weight
                cover = lambda cand: np.hstack([M[cand][:, qv.indices].toarray() > 0, F[cand][:, qf].toarray() > 0])
                ex = coverage_select(sim, cover, np.concatenate([qv.data, wq]), k) if qv.nnz else []
            else:
                ex = coverage_select(sim, lambda cand: (M[cand][:, qv.indices].toarray() > 0), qv.data, k) if qv.nnz else []
            ex = list(reversed(sorted(ex, key=lambda i: (sim[i], i), reverse=True)))   # most similar last
            exs = "\n\n".join(EXAMPLE.format(source=xml_escape(pool[i][3]), target=xml_escape(pool[i][4]), **langs)
                              for i in ex)
            prompt = FEW_SHOT.format(examples=exs, source=xml_escape(bsb), **langs)
            if "--no-orig" not in a:
                prompt = prompt.replace("</source_to_translate>", ORIGINAL.format(
                    tag=oname.lower(), text=xml_escape(orig[v]), name=oname), 1)
            if m5:
                strongs = {re.sub(r"\D", "", str(x)).lstrip("0") for (x,) in db["nt" if not ot else "ot"].execute(
                    f"select {'strong' if not ot else 'lexeme'} from tokens where book = ? and ch = ? and v = ?",
                    (code.upper(), ch, v)) if x}
                bw = " " + " ".join(LT.Tokeniser({}).tokens(bsb)) + " "
                extra = "\n".join((GRAMMAR if kind == "grammar" else FIXED).format(lines=xml_escape(t), **langs)
                                   for kind, t in m5_blocks(pname, code, ch, prof, bw, strongs, gverses, v))
                if extra:                       # before the closing "<language>:" line of the query
                    head, sep, tail = prompt.rpartition(f"\n{trg}:")
                    prompt = f"{head}\n{extra}{sep}{tail}"
            if "--show" in a and str(v) == opt("--show", ""):
                print(prompt[-3000:]); print(f"[{len(ex)} examples, {len(prompt)} characters]"); sys.exit(0)
            jobs.append((v, prompt))
        with ThreadPoolExecutor(workers) as tp:
            replies = list(tp.map(lambda j: ask(system, j[1], model, cache, cache_file), jobs))
        lines = [f"!!<Second draft for review triage: in-context ({k} coverage examples per verse, {model}"
                 f"{', m5 format' if m5 else ''}"
                 f"{'' if '--no-orig' in a else ', with the original'}), scripts/icl_draft.py; not for use as a draft>!!",
                 "", f"==={code} {ch}===", ""]
        for (v, _), rep in zip(jobs, replies):
            lines.append(f"v{v} {read_reply(rep['text'], trg, resemblance)}")
            tot["in"] += rep["in"]
            tot["out"] += rep["out"]
            tot["verses"] += 1
        f = os.path.join(out, f"{code}{ch:03d}.txt")
        open(f, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print(f"{code} {ch}: {len(jobs)} verses -> {os.path.relpath(f, ROOT)}", file=sys.stderr)
    print("tokens", dict(tot))


if __name__ == "__main__":
    main()
