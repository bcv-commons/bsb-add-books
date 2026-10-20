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
  show <project|dir> [morph|cell|claim]   the entries, one line each
  from-tsv <tsv dir> <profile dir> [--by NAME] [--date YYYY-MM-DD]
      writes the morphs.tsv, cells.tsv and claims.tsv of a working store (one row per morph, cell or claim; list
      fields ';'-separated) into <profile dir>/observations.json as entries: those of the three kinds already there
      are replaced, every other entry is kept. Check the result with scripts/language_profile.py check.
"""
import csv, datetime, json, os, re, sys

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


def line(e):
    k = e["kind"]
    if k == "morph":
        return f"{e['id']:28} {e['form']:12} {e['slot']:7} {e['host']:5} {e['value']:14} {e.get('stats', {})}"
    if k == "cell":
        return f"{e['id']:36} {e['value']:12} {e.get('stats', {})}" + (" gap" if e.get("gap") else "")
    return f"{e['id']:28} {e['verdict']:12} {e['value'][:80]}"


def main(a):
    if a[:1] == ["show"] and len(a) >= 2:
        G = load(a[1])
        for k in (a[2:3] or list(GRAMMAR)):
            for e in getattr(G, k + "s"):
                print(line(e))
    elif a[:1] == ["from-tsv"] and len(a) >= 3:
        opt = lambda k, d: a[a.index(k) + 1] if k in a else d
        from_tsv(a[1], a[2], opt("--by", "script:grammar.py"), opt("--date", datetime.date.today().isoformat()))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
