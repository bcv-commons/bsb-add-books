#!/usr/bin/env python3
"""A project's grammar from its language store: the morph, cell and claim entries of profile/observations.json
(docs/proposals/language-profile/, *Kinds*), for the tools that segment, analyse and check (a segmenter, the verse
analysis, the draft check).

As a library:
  G = grammar.load(<project> | <profile dir>)
  G.morphs                 [entry], live ones only (superseded left out); G.cells, G.claims likewise
  G.affixes(host, slot)    the forms without their hyphens, longest first (host "verb", slot "prefix")
  G.cell(paradigm, bundle) the cell entry or None; G.paradigm(paradigm) {bundle: entry}
  G.morph(id)              one morph entry

Commands:
  status <project|dir>                    what the store holds: entries by kind and status, the Grambank features
  plan <project|dir>                      what to settle next: the Grambank features a recipe can decide that the store
                                          lacks (by relevance; those the store's own morphs answer marked `run`), open
                                          and thin cells, open claims, open morphs: the curation agent's list
  run <project|dir> [GBnnn ...] [--write] the Grambank features the store's morphs answer (docs/proposals/
                                          language-profile/grambank_recipes.tsv, from_store: yes): a morph tagged with
                                          the code, or for NEG, FUT, mood, tense and object morphs the tag; a feature
                                          entry gb:GBnnn (value 1, evidence the morphs' verses), never a 0 (no evidence
                                          is no entry). Prints them; --write puts them into observations.json (its own
                                          earlier entries replaced, an agent's or the team's left alone)
  show <project|dir> [morph|cell|claim]   the entries, one line each
  retest <project> [--run]                the tests a script ran on the store (claims with `rerun`) whose basis changed:
                                          the store learned something since (orthography.tone, a tone pattern, a morph,
                                          analysis.match) or the method did; --run reruns them (and rewrites their claims)
  from-tsv <tsv dir> <profile dir> [--by NAME] [--date YYYY-MM-DD]
      writes the morphs.tsv, cells.tsv and claims.tsv of a working store (one row per morph, cell or claim; list
      fields ';'-separated) into <profile dir>/observations.json as entries: those of the three kinds already there
      are replaced, every other entry is kept. Check the result with scripts/language_profile.py check.
"""
import collections, csv, datetime, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
GRAMMAR = ("morph", "cell", "claim")


class Grammar:
    def __init__(self, entries):
        live = [e for e in entries if e.get("status") != "superseded"]
        self.morphs = [e for e in live if e.get("kind") == "morph"]
        self.cells = [e for e in live if e.get("kind") == "cell"]
        self.claims = [e for e in live if e.get("kind") == "claim"]
        self._by_id = {e["id"]: e for e in live}

    def morph(self, mid):
        e = self._by_id.get(mid)
        return e if e and e.get("kind") == "morph" else None

    def affixes(self, host, slot):
        forms = {e["form"].strip("-=") for e in self.morphs if e.get("host") in (host, "any") and e.get("slot") == slot}
        return sorted((f for f in forms if f), key=len, reverse=True)

    def paradigm(self, name):
        return {e["bundle"]: e for e in self.cells if e.get("paradigm") == name}

    def cell(self, paradigm, bundle):
        return self.paradigm(paradigm).get(bundle)


def profile_dir(where):
    if os.path.isdir(where) and os.path.exists(os.path.join(where, "observations.json")):
        return where
    from project import project_dir
    return os.path.join(project_dir(where), "profile")


def load(where):
    f = os.path.join(profile_dir(where), "observations.json")
    return Grammar(json.load(open(f, encoding="utf-8")).get("entries", []) if os.path.exists(f) else [])


# --- from-tsv -------------------------------------------------------------------------------------------------------
REF = re.compile(r"\b([1-3A-Z][A-Z0-9]{2}) (\d{1,3}):(\d{1,3})\b")


def refs(s, n=None):
    out, seen = [], set()
    for m in REF.finditer(s or ""):
        r = f"{m[1]} {int(m[2])}:{int(m[3])}"
        if r not in seen:
            seen.add(r); out.append({"ref": r})
    if out and n:
        out[0]["n"] = n
    return out


def num(x):
    try:
        return int(x) if re.fullmatch(r"-?\d+", x) else float(x)
    except (TypeError, ValueError):
        return None


def slug(s):
    """an id the contract allows (ASCII): marks dropped, ø æ ɨ spelled out (zø- -> zoe-)"""
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))
    s = s.translate(str.maketrans({"ø": "oe", "æ": "ae", "ɨ": "ii", "ŋ": "ng", "ə": "e", "ɛ": "e", "ɔ": "o"}))
    return re.sub(r"[^a-z0-9_:.-]+", "_", s).strip("_")


def status(st):
    """the working store's statuses onto the contract's: thin -> observed (confidence low), gap -> observed + gap"""
    return st if st in ("observed", "decided", "open", "superseded") else "observed"


def confidence(lift, count):
    """from the held-out lift (or the lift) and the count: a statistic, not a judgement"""
    if lift is None or count is None:
        return "medium"
    return "high" if lift >= 5 and count >= 20 else "medium" if lift >= 2 and count >= 5 else "low"


def rows(path):
    return list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t")) if os.path.exists(path) else []


def from_tsv(src, dst, by, date):
    out = []
    for r in rows(os.path.join(src, "morphs.tsv")):
        st = {k: num(r.get(k)) for k in ("count", "hosts", "lift", "test_lift")}
        tone = not r["form"].startswith(("-", "=")) and not r["form"].endswith(("-", "=")) and " " in r["form"]
        slot = "tone" if tone else "infix" if r["form"].startswith("-") and r["form"].endswith("-") else r["slot"]
        e = {"id": slug(r["id"]), "kind": "morph", "value": r["gloss"], "slot": slot,
             "form": slug(r["id"].split(":")[1]) if tone else r["form"], "host": r["host"],
             "stats": {k: v for k, v in st.items() if v is not None}, "evidence": refs(r.get("refs"), st["count"]),
             "confidence": confidence(st["test_lift"] if st["test_lift"] is not None else st["lift"], st["count"]),
             "method": "corpus-derived", "by": r.get("by") or by, "date": r.get("date") or date,
             "status": status(r.get("status"))}
        if tone:
            e["tone"] = r["form"]
        if r.get("unimorph"):
            e["unimorph"] = r["unimorph"]
        codes = [c for c in (r.get("evidences") or "").split(";") if re.fullmatch(r"GB\d{3}", c)]
        if codes:
            e["codes"] = codes
        if r.get("note") or r.get("method"):
            e["note"] = "; ".join(x for x in (f"method {r['method']}" if r.get("method") else "", r.get("note", "")) if x)
        out.append(e)
    morph_ids = {e["id"] for e in out}
    for r in rows(os.path.join(src, "cells.tsv")):
        st = {k: num(r.get(k)) for k in ("count", "share")}
        e = {"id": slug(r["id"]), "kind": "cell", "value": r["form"], "paradigm": r["paradigm"], "bundle": r["bundle"],
             "stats": {k: v for k, v in st.items() if v is not None}, "evidence": refs(r.get("refs"), st["count"]),
             "confidence": "medium" if (st["share"] or 0) >= 0.3 and r.get("status") != "thin" else "low",
             "method": "corpus-derived", "by": by, "date": date, "status": status(r.get("status"))}
        if r.get("gap") == "1" or r.get("status") == "gap" or not e["evidence"]:
            e["gap"] = True                   # no case cited: recorded as a gap, never as a form
        ms = [slug(m) for m in (r.get("morphs") or "").split(";") if m.strip()]
        if ms:
            e["morphs"] = [m for m in ms if m in morph_ids]
        alts = re.findall(r"(\S+) x[\d.]+ \((\d+)\)", r.get("alts") or "")
        if alts:
            e["alternatives"] = [{"value": a, "n": int(n)} for a, n in alts]
        if r.get("nllb"):
            e["note"] = f"NLLB contrast: {r['nllb']}"
        out.append(e)
    for r in rows(os.path.join(src, "claims.tsv")):
        e = {"id": "claim:" + slug(r["id"]), "kind": "claim", "value": r["claim"], "area": r.get("area", ""),
             "tests": [t for t in (r.get("tests") or "").split(";") if t], "figures": r.get("figures", ""),
             "verdict": r.get("verdict") or "open", "confidence": "medium", "method": "corpus-derived", "by": by,
             "date": r.get("date") or date, "status": "observed"}
        if r.get("source"):
            e["source"] = r["source"]
        if r.get("next"):
            e["next"] = r["next"]
        out.append(e)
    f = os.path.join(dst, "observations.json")
    prof = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {"iso": "", "edition": "", "partition": "observations", "entries": []}
    kept = [e for e in prof["entries"] if e.get("kind") not in GRAMMAR]
    prof["entries"] = kept + out
    os.makedirs(dst, exist_ok=True)
    json.dump(prof, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = {k: sum(1 for e in out if e["kind"] == k) for k in GRAMMAR}
    print(f"{f}: {len(kept)} other entries kept; " + ", ".join(f"{v} {k}s" for k, v in n.items()))


# --- status, plan, run ----------------------------------------------------------------------------------------------
RECIPES = os.path.join(ROOT, "docs", "proposals", "language-profile", "grambank_recipes.tsv")
GB_DIR = os.path.join(ROOT, "download", "grambank", "v1.0.3")       # python3 scripts/setup.py --only grambank
RELEVANCE = {"high": 0, "medium": 1, "low": 2}
TAM = {"NEG", "IRR", "REAL", "OPT", "HORT", "JUSS", "FUT", "PST", "PRS", "PRF", "IPFV", "PFV", "IMP", "SBJV", "COND", "PROH"}
MOOD = {"IMP", "SBJV", "OPT", "IRR", "HORT", "JUSS", "COND", "PROH"}
CONF = {"high": 2, "medium": 1, "low": 0}


def recipes():
    return list(csv.DictReader(open(RECIPES, encoding="utf-8"), delimiter="\t"))


def questions():
    """{GBnnn: question} from Grambank's parameters.csv; {} before setup.py --only grambank"""
    f = os.path.join(GB_DIR, "parameters.csv")
    return {r["ID"]: r["Name"] for r in csv.DictReader(open(f, encoding="utf-8"))} if os.path.exists(f) else {}


def entries(where):
    f = os.path.join(profile_dir(where), "observations.json")
    return json.load(open(f, encoding="utf-8")).get("entries", []) if os.path.exists(f) else []


def gb_codes(es):
    """{GBnnn: [feature entries]} of the store's live features"""
    out = {}
    for e in es:
        if e.get("kind") == "feature" and e.get("status") != "superseded":
            for c in e.get("codes") or []:
                out.setdefault(c, []).append(e)
    return out


def answering(G, gb):
    """the store's verb morphs that answer a Grambank feature with 1 (see run)"""
    live = [m for m in G.morphs if m.get("host") in ("verb", "any") and m.get("status") in ("observed", "decided")]
    coded = [m for m in live if gb in (m.get("codes") or [])]
    if coded or gb in ("GB089", "GB090", "GB091", "GB092"):   # intransitive / transitive: only from a tagged morph
        return coded
    tags = lambda m: set(re.split(r"[.;_ ]", (m.get("value") or "").upper()))
    obj = lambda m: (m.get("value") or "").upper().startswith(("P.", "O.", "OBJ"))
    rule = {"GB079": lambda m: m.get("slot") == "prefix" and tags(m) & TAM and not obj(m),
            "GB080": lambda m: m.get("slot") == "suffix" and tags(m) & TAM and not obj(m),
            "GB084": lambda m: "FUT" in tags(m),
            "GB093": lambda m: m.get("slot") == "suffix" and obj(m),
            "GB094": lambda m: m.get("slot") in ("prefix", "infix") and obj(m),
            "GB107": lambda m: "NEG" in tags(m),
            "GB312": lambda m: bool(tags(m) & MOOD)}.get(gb)
    if gb == "GB139":                     # prohibitive pieces that differ from those of declarative negation
        proh = [m for m in live if "PROH" in tags(m)]
        neg = [m for m in live if "NEG" in tags(m) and "PROH" not in tags(m)]
        return proh + neg if proh and neg and {m["form"] for m in proh} - {m["form"] for m in neg} else []
    return [m for m in live if rule(m)] if rule else []


def derive(where, only=()):
    """the feature entries run writes: gb:GBnnn for each from_store recipe the store's morphs answer"""
    G, out = load(where), []
    for r in recipes():
        gb = r["gb_id"]
        if r.get("from_store") != "yes" or (only and gb not in only):
            continue
        ms = answering(G, gb)
        if not ms:
            continue
        ev, seen = [], set()
        for m in ms:
            for x in m.get("evidence") or []:
                if x["ref"] not in seen and len(ev) < 5:
                    seen.add(x["ref"]); ev.append({"ref": x["ref"]})
        conf = max((m.get("confidence") or "low" for m in ms), key=lambda c: CONF.get(c, 0))
        out.append({"id": f"gb:{gb}", "kind": "feature", "value": "1 (present): " + ", ".join(dict.fromkeys(m["form"] for m in ms)),
                    "codes": [gb], "evidence": ev, "confidence": conf, "method": "corpus-derived",
                    "by": "script:grammar.py", "date": datetime.date.today().isoformat(), "status": "observed",
                    "note": f"grammar.py run: answered by the store's morphs ({', '.join(m['id'] for m in ms)}); "
                            f"recipe: {r['test']}"})
    return out


def run(where, only, write):
    new = derive(where, only)
    q = questions()
    for e in new:
        gb = e["codes"][0]
        print(f"{e['id']:10} {q.get(gb, '')[:70]:70} {e['value']} ({e['confidence']})")
    if not write:
        print(f"{len(new)} features; --write puts them into the store")
        return
    f = os.path.join(profile_dir(where), "observations.json")
    prof = json.load(open(f, encoding="utf-8"))
    ids = {e["id"] for e in new}
    others = {e["id"] for e in prof["entries"] if e["id"] in ids and e.get("by") != "script:grammar.py"}
    prof["entries"] = [e for e in prof["entries"] if e["id"] not in ids or e["id"] in others] + \
        [e for e in new if e["id"] not in others]
    json.dump(prof, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{f}: {len(new) - len(others)} features written" + (f"; kept the agent's or team's {sorted(others)}" if others else ""))


def status(where):
    import collections
    es = entries(where)
    by = collections.Counter((e.get("kind"), e.get("status")) for e in es)
    for k in sorted({k for k, _ in by}):
        print(f"{k:8} " + ", ".join(f"{st} {n}" for (kk, st), n in sorted(by.items()) if kk == k))
    have, rs = gb_codes(es), recipes()
    print(f"Grambank: {len([c for c in have if c.startswith('GB')])} features in the store; recipes {len(rs)}, "
          f"of them in the store {sum(1 for r in rs if r['gb_id'] in have)}, answered by the store's morphs and not yet "
          f"written {sum(1 for r in rs if r['gb_id'] not in have and r.get('from_store') == 'yes' and answering(load(where), r['gb_id']))}"
          + ("" if questions() else " (no questions: python3 scripts/setup.py --only grambank)"))


def plan(where):
    es, G, q = entries(where), load(where), questions()
    have = gb_codes(es)
    todo = sorted((r for r in recipes() if r["gb_id"] not in have), key=lambda r: (RELEVANCE.get(r["relevance"], 3), r["gb_id"]))
    print("## Grambank features a recipe can decide, not in the store yet")
    for r in todo:
        how = "run (the store's morphs answer it)" if r.get("from_store") == "yes" and answering(G, r["gb_id"]) else \
            f"{r['method']}: {r['test']}"
        print(f"- {r['gb_id']} ({r['relevance']}) {q.get(r['gb_id'], '')}: {how}")
    cells = [c for c in G.cells if not c.get("gap") and (c.get("status") == "open" or c.get("confidence") == "low")]
    print(f"\n## Cells open or thin ({len(cells)})")
    for c in cells:
        print(f"- {c['id']}: {c.get('value')} ({c.get('status')}, {c.get('confidence')})")
    claims = [c for c in G.claims if c.get("verdict") in ("open", "new", "corpus-only")]
    print(f"\n## Claims to test ({len(claims)})")
    for c in claims:
        print(f"- {c['id']} ({c.get('verdict')}): {c['value'][:100]}" + (f"; next: {c['next']}" if c.get("next") else ""))
    ms = [m for m in G.morphs if m.get("status") == "open"]
    print(f"\n## Morphs open ({len(ms)})")
    for m in ms:
        print(f"- {m['id']}: {m.get('value')}" + (f" ({m['note'][:80]})" if m.get("note") else ""))


def line(e):
    k = e["kind"]
    if k == "morph":
        return f"{e['id']:28} {e['form']:12} {e['slot']:7} {e['host']:5} {e['value']:14} {e.get('stats', {})}"
    if k == "cell":
        return f"{e['id']:36} {e['value']:12} {e.get('stats', {})}" + (" gap" if e.get("gap") else "")
    return f"{e['id']:28} {e['verdict']:12} {e['value'][:80]}"


# --- basis and retest -------------------------------------------------------------------------------------------------
# A test a script ran on the store (a claim with `rerun`) records its `basis`: a fingerprint of what its result depends
# on. When the store learns something later (how tone is written, a tone pattern, a new morph, the view the checks use)
# or the checking method changes, the basis no longer matches and `retest` reruns the test.

def basis(where, cell=None, method=""):
    """the fingerprint of the store settings a test depends on: the orthography and analysis settings, every live morph
    (form, slot, host, tone pattern), the cell's own value and its alternatives that no test added, the checking
    method's version. The style corpus is recorded beside it (corpus()), as a profile folder alone doesn't name it"""
    import hashlib
    d = json.load(open(os.path.join(profile_dir(where), "observations.json"), encoding="utf-8"))
    G = Grammar(d.get("entries", []))
    parts = {"orthography": d.get("orthography") or {}, "analysis": d.get("analysis") or {}, "method": method,
             "morphs": sorted([e.get("form"), e.get("slot"), e.get("host"), e.get("tone_pattern")] for e in G.morphs)}
    if cell:
        ce = G.cell(*cell)
        parts["cell"] = [ce.get("value"), sorted(x.get("value") for x in ce.get("alternatives", [])
                                                 if x.get("method") != "tested")] if ce else None
    return hashlib.sha256(json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]


def corpus(where):
    """the project's style corpus (project.yaml style_from), or None for a profile folder"""
    try:
        from project import project
        return project(where).get("style_from")
    except Exception:
        return None


def stale(where):
    """[(claim entry, current basis)] of the claims a script can rerun whose basis has changed; and the number of
    script-derived entries without a recipe (their figures can't be rerun here)"""
    G = load(where)
    out, norecipe = [], 0
    for e in G.claims:
        r = e.get("rerun")
        if not r:
            norecipe += e.get("method") == "corpus-derived" and str(e.get("by", "")).startswith("script:")
            continue
        cell = tuple(r[2:4]) if r[:2] == ["cell_check.py", "try"] else None
        cur = basis(where, cell, e.get("rerun_method", ""))
        c = corpus(where)
        if e.get("basis") != cur or (c is not None and e.get("basis_corpus") != c):
            out.append((e, cur))
    return out, norecipe


def stale_data(where):
    """[(meta.json, its basis)] of the project's model data and models built in parts (model_text morphs) on store
    settings that have changed since: their tokens no longer match what the store would write"""
    import glob
    try:
        from project import project_dir
        d = os.path.join(project_dir(where), "_eval", "local", "nllb")
    except Exception:
        return []
    out, cur = [], None
    for f in sorted(glob.glob(os.path.join(d, "**", "meta.json"), recursive=True)):
        mt = json.load(open(f, encoding="utf-8")).get("model_text") or {}
        if mt.get("mode") == "morphs":
            cur = cur or basis(where, None, "model_text 1")
            if mt.get("basis") != cur:
                out.append((f, mt.get("basis")))
    return out


def retest(where, run_them):
    """list the stale tests; with --run rerun them, grouped by command (one `cell_check.py try` per cell, all its forms)"""
    import subprocess
    out, norecipe = stale(where)
    print(f"{where}: {len(out)} test(s) whose store settings changed since they ran" +
          (f"; {norecipe} script-derived claim(s) without a rerun recipe" if norecipe else ""))
    groups = collections.OrderedDict()
    for e, cur in out:
        r = e["rerun"]
        print(f"  {e['id']}: basis {e.get('basis') or 'none'} -> {cur}  ({' '.join(r)})")
        key = tuple(r[:4]) if r[:2] == ["cell_check.py", "try"] else tuple(r)
        groups.setdefault(key, []).extend(r[4:] if r[:2] == ["cell_check.py", "try"] else [])
    for f, b in stale_data(where):
        print(f"  model data {os.path.relpath(f, ROOT)}: built on basis {b}, the store is now at "
              f"{basis(where, None, 'model_text 1')}: rebuild it (scripts/nllb/data.py) before the next training")
    if not run_them:
        return
    for key, forms in groups.items():
        cmd = [sys.executable, os.path.join(ROOT, "scripts", key[0]), where, *key[1:], *dict.fromkeys(forms), "--write"]
        print("$", " ".join(cmd[1:]))
        subprocess.run(cmd, check=True)


def main(a):
    if a[:1] == ["retest"] and len(a) >= 2:
        retest(a[1], "--run" in a)
        return
    if a[:1] == ["show"] and len(a) >= 2:
        G = load(a[1])
        for k in (a[2:3] or list(GRAMMAR)):
            for e in getattr(G, k + "s"):
                print(line(e))
    elif a[:1] == ["status"] and len(a) >= 2:
        status(a[1])
    elif a[:1] == ["plan"] and len(a) >= 2:
        plan(a[1])
    elif a[:1] == ["run"] and len(a) >= 2:
        run(a[1], [x for x in a[2:] if re.fullmatch(r"GB\d{3}", x)], "--write" in a)
    elif a[:1] == ["from-tsv"] and len(a) >= 3:
        opt = lambda k, d: a[a.index(k) + 1] if k in a else d
        from_tsv(a[1], a[2], opt("--by", "script:grammar.py"), opt("--date", datetime.date.today().isoformat()))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
