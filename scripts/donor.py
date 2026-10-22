#!/usr/bin/env python3
"""The donor: the related languages of a language the model doesn't know, on two axes, for the project's `donor:` block.

  structure  the closest relatives by descent (Glottolog), whatever the model knows of them: what the language's grammar
             is likely to look like (the seeds' categories);
  known      the closest relative the model knows well enough to write: the seeds' source (scripts/seeds.py) and the
             language the second-draft model starts from (nllb_init). A property of the model, so it is measured.

The steps (`run` does them in order; `tree` and `shortlist` cost nothing):
  1. tree: from the language's glottocode up the Glottolog tree a level at a time; each level's languages that the
     levels below don't have. `structure` takes whole levels until it has at least 5 languages (--structure N).
  2. shortlist: the relatives that can be probed (a Bible in the sources scripts/fetch_edition.py fetches; DBT with a key)
     and are large (an NLLB-200 code or a Wikipedia of 1,000 articles or more), the largest of each level (NLLB first,
     then Wikipedia's size), nearest levels first; the first --probes N (default 3) are probed.
  3. probe: each candidate's write probe (scripts/probe_language.py: 16 BSB verses into the language from memory,
     chrF against an edition of it, fetched into download/donor/<iso>/; about 5k tokens a candidate).
  4. the choice: the nearest level whose candidate the model writes well (chrF by verse >= 58, as the probe's
     `known`), else the nearest it writes at all (10 above the floor of unrelated text), else none: then `known: none`
     and the seeds can only come from the relatives' typology. nllb_init: the choice's NLLB code, else the nearest
     probed candidate that has one, else the nearest relative NLLB has.
  5. write: the block in project.yaml (`donor:` replaced as a whole), the figures in _learn/donor.json; the prompts
     and answers in _eval/local/donor/ (they hold Bible verses).
The field names: known, name, known_score, candidates {iso: score}, structure [iso], structure_level, nllb_init, why.

Usage: python3 scripts/donor.py tree <iso | project>
       python3 scripts/donor.py shortlist <project> [--probes N]
       python3 scripts/donor.py run <project> [--route api|claude-code] [--model M] [--probes N] [--candidates lug,swh]
                                              [--write] [--dry-run]
Needs download/glottolog/ (python3 scripts/setup.py --only glottolog).
"""
import collections, csv, datetime, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
GL = os.path.join(ROOT, "download", "glottolog", "v5.3")
DL = os.path.join(ROOT, "download", "donor")
NLLB = os.path.join(ROOT, "scripts", "nllb", "languages.txt")
ISO_MACRO = "https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3-macrolanguages.tab"
MIN_WIKI = 1000
UA = {"User-Agent": "bsb-add-books-donor/1.0 (https://github.com/bcv-commons/bsb-add-books)"}


class Tree:
    """Glottolog: names, ISO codes, levels and each languoid's ancestors (top first)"""

    def __init__(self):
        cache = os.path.join(GL, "tree.json")
        if not os.path.exists(cache):
            if not os.path.exists(os.path.join(GL, "values.csv")):
                raise SystemExit("no Glottolog here: python3 scripts/setup.py --only glottolog")
            langs = {r["ID"]: [r["Name"], r["ISO639P3code"], r["Level"], []]
                     for r in csv.DictReader(open(os.path.join(GL, "languages.csv"), encoding="utf-8"))}
            for r in csv.DictReader(open(os.path.join(GL, "values.csv"), encoding="utf-8")):
                if r["Parameter_ID"] == "classification" and r["Language_ID"] in langs:
                    langs[r["Language_ID"]][3] = r["Value"].split("/")
            json.dump(langs, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
        self.l = json.load(open(cache, encoding="utf-8"))
        self.by_iso = {v[1]: k for k, v in self.l.items() if v[1] and v[2] == "language"}
        self.under = collections.defaultdict(list)
        for k, v in self.l.items():
            if v[2] == "language":
                for a in v[3]:
                    self.under[a].append(k)

    def name(self, g):
        return self.l[g][0] if g in self.l else g

    def iso(self, g):
        return self.l[g][1]

    def walk(self, iso):
        """[(level glottocode, distance, [language glottocodes new at this level])], nearest first"""
        g = self.by_iso.get(iso)
        if not g:
            raise SystemExit(f"Glottolog has no language with ISO code {iso!r}")
        seen, out = {g}, []
        for d, anc in enumerate(reversed(self.l[g][3]), 1):
            new = [x for x in self.under[anc] if x not in seen]
            seen |= set(new)
            out.append((anc, d, new))
        return g, out


def structure(T, levels, n=5):
    """the closest relatives by descent: whole levels until at least n with an ISO code; (isos, the last level's name)"""
    out, last = [], None
    for anc, _, new in levels:
        out += [T.iso(x) for x in new if T.iso(x)]
        last = anc
        if len(out) >= n:
            break
    return out, T.name(last) if last else None


def nllb_codes():
    return {l.split("_")[0]: l.strip() for l in open(NLLB, encoding="utf-8") if l.strip() and not l.startswith("#")}


def nllb_by_iso():
    """{iso: [NLLB codes]}: a language can have codes in several scripts (ace_Arab, ace_Latn)"""
    out = collections.defaultdict(list)
    for l in open(NLLB, encoding="utf-8"):
        if l.strip() and not l.startswith("#"):
            out[l.split("_")[0]].append(l.strip())
    return out


def pick_init(order, script):
    """(nllb_init or None, note): the first relative's NLLB code in the target `script`, else the first code at all,
    moved to the script by script_code.init_for_script. `order`: iso codes, nearest/best first. note is None when
    nothing changed; a Latin target keeps the choice it had before scripts counted."""
    import script_code as SC
    by = nllb_by_iso()
    codes = [c for i in order for c in by.get(i, [])]
    if not codes:
        return None, None
    first = next(by[i][-1] for i in order if by.get(i))     # the code nllb_codes() gives: the choice before scripts
    if script == "Latn":
        return first, None                                  # Latin targets: unchanged
    same = [c for c in codes if c.endswith("_" + script)]
    if same:
        if same[0] == first or same[0].split("_")[0] == first.split("_")[0]:
            return same[0], None
        return same[0], (f"nllb_init {same[0]}: the nearest relative in NLLB written in {script} like the target "
                         f"({first} is nearer or better known but in another script)")
    ni, why = SC.init_for_script(first, script)
    return ni, (f"nllb_init: no relative in NLLB is written in {script}; " + why) if why else None


def bible_isos():
    """the languages with a Bible text in the sources fetch_edition.py fetches (cached listings; DBT where a key is set)"""
    import io
    import fetch_edition as FE
    L = FE.LISTINGS
    out = set()
    try:
        out |= {e[0] for e in FE.getjson(FE.CATALOG, os.path.join(L, "catalog.json"), max_age=FE.DAY)["entries"]
                if e[2] in ("h", "o") or e[2] == "d" and FE.dbt_key()}
    except Exception:  # noqa: BLE001  the listings below still say what can be fetched
        pass
    out |= {t.get("language") for t in FE.getjson(f"{FE.HELLOAO}/available_translations.json", os.path.join(L, "helloao.json"),
                                                  max_age=FE.DAY)["translations"]}
    out |= {e.get("iso") for e in FE.getjson(f"{FE.OPENBIBLE}/catalog/openbible-editions.json", os.path.join(L, "openbible.json"),
                                             max_age=FE.DAY)["entries"].values() if e.get("published", True)}
    out |= {r["languageCode"] for r in csv.DictReader(io.StringIO(FE.get(f"{FE.EBIBLE}/translations.csv", os.path.join(L, "ebible.csv"),
                                                                        max_age=FE.DAY).decode("utf-8-sig")))
            if int(r["NTbooks"] or 0) >= 27}
    return out - {None, ""}


def wiki_codes(iso):
    """the Wikipedia codes a language may have: its ISO 639-1 code, its own, its macrolanguage's"""
    import fetch_edition as FE
    tab = os.path.join(ROOT, "download", "_iso639")
    part1, macro = {}, {}
    try:
        for l in FE.get("https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab",
                        os.path.join(tab, "iso-639-3.tab")).decode("utf-8").splitlines()[1:]:
            c = l.split("\t")
            if len(c) > 3 and c[3]:
                part1[c[0]] = c[3]
        for l in FE.get(ISO_MACRO, os.path.join(tab, "iso-639-3-macrolanguages.tab")).decode("utf-8").splitlines()[1:]:
            c = l.split("\t")
            if len(c) > 1:
                macro[c[1]] = c[0]
    except Exception:  # noqa: BLE001  offline: the ISO code itself
        pass
    m = macro.get(iso)
    return [x for x in (part1.get(iso), iso, part1.get(m) if m else None, m) if x]


def wiki_sizes(isos):
    """{iso: articles of its Wikipedia} (0 where it has none); one listing, one call per Wikipedia, cached"""
    import urllib.request
    import fetch_edition as FE
    f = os.path.join(DL, "wikipedia.json")
    cache = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    todo = [i for i in isos if i not in cache]
    if todo:
        try:
            raw = FE.get("https://meta.wikimedia.org/w/api.php?action=sitematrix&format=json&smtype=language"
                         "&smlangprop=code|site&smsiteprop=code", os.path.join(DL, "sitematrix.json"), max_age=30 * FE.DAY)
            sm = json.loads(raw)["sitematrix"]
            wikis = {v["code"] for k, v in sm.items() if k != "count" and isinstance(v, dict)
                     for s in v.get("site", []) if s.get("code") == "wiki" and "closed" not in s}
        except Exception:  # noqa: BLE001  offline: sizes unknown (0)
            wikis = set()
        for i in todo:
            code = next((c for c in wiki_codes(i) if c in wikis), None)
            n = 0
            if code:
                try:
                    req = urllib.request.Request(f"https://{code}.wikipedia.org/w/api.php?action=query&meta=siteinfo"
                                                 "&siprop=statistics&format=json", headers=UA)
                    n = json.load(urllib.request.urlopen(req, timeout=30))["query"]["statistics"]["articles"]
                except Exception:  # noqa: BLE001
                    n = 0
            cache[i] = {"wiki": code, "articles": n}
        os.makedirs(DL, exist_ok=True)
        json.dump(cache, open(f, "w", encoding="utf-8"), indent=1)
    return {i: cache[i] for i in isos}


def shortlist(iso, probes=3, n_structure=5, extra=()):
    """(walk, structure, structure level, [candidate]): candidate = {iso, name, level, distance, nllb, bible, wiki,
    articles, probe}"""
    T = Tree()
    g, levels = T.walk(iso)
    struct, slevel = structure(T, levels, n_structure)
    nl, bibles = nllb_codes(), bible_isos()
    rows = []
    for anc, d, new in levels:
        isos = [T.iso(x) for x in new if T.iso(x)]
        if not isos:
            continue
        sizes = wiki_sizes([i for i in isos if i in bibles or i in nl])
        for i in isos:
            w = sizes.get(i, {"wiki": None, "articles": 0})
            rows.append({"iso": i, "name": T.name(T.by_iso[i]), "level": T.name(anc), "distance": d, "nllb": nl.get(i),
                         "bible": i in bibles, "wiki": w["wiki"], "articles": w["articles"]})
        if sum(1 for r in rows if r["bible"] and (r["nllb"] or r["articles"] >= MIN_WIKI)) >= 3 * probes:
            break                                     # enough candidates: the levels above are further still
    for x in extra:                                   # a candidate asked for by name, from any level
        if x not in {r["iso"] for r in rows}:
            anc, d = next(((anc, d) for anc, d, new in levels if T.by_iso.get(x) in new), (None, 99))
            w = wiki_sizes([x])[x]
            rows.append({"iso": x, "name": T.name(T.by_iso[x]) if x in T.by_iso else x, "level": T.name(anc) if anc
                         else "outside the family", "distance": d, "nllb": nl.get(x), "bible": x in bibles,
                         "wiki": w["wiki"], "articles": w["articles"]})
    by_level = collections.OrderedDict()
    for r in rows:
        if r["bible"] and (r["nllb"] or r["articles"] >= MIN_WIKI or r["iso"] in extra):
            by_level.setdefault(r["level"], []).append(r)
    cands = [max(rs, key=lambda r: (bool(r["nllb"]), r["articles"])) for rs in by_level.values()]
    cands += [r for r in rows if r["iso"] in extra and r not in cands]
    for i, r in enumerate(cands):                     # --candidates: exactly those; else the nearest levels' first
        r["probe"] = r["iso"] in extra if extra else i < probes
    return T, g, levels, struct, slevel, cands, rows


class TextProject:
    """what probe_language.py needs of a project, for an edition's text alone (a candidate donor)"""

    def __new__(cls, text_dir, iso, name):
        import langtools as LT

        class _P(LT.Project):
            def __init__(self):
                self.name, self.p = f"donor:{iso}", {"language": iso, "language_name": name, "style_from": []}
                self.dir = os.path.dirname(text_dir)
                self.learn = self.profile = self.dir
                self.tok = LT.Tokeniser(None, [])
                self.editions, self._rows, self._spell, self._seg = [], None, None, None

            def text_dirs(self):
                return [text_dir]

            def assist_dir(self, code):
                return os.path.join("reference", "BSB")
        return _P()


def fetch_text(iso):
    """an edition of the language for its probe, in download/donor/<iso>/text/ -> (text dir, edition label)"""
    import fetch_edition as FE
    from books import BY_CODE
    from convert_usj import chapter_text, split_chapters
    d = os.path.join(DL, iso, "text")
    lab = os.path.join(DL, iso, "edition.txt")
    if os.path.isdir(d) and os.listdir(d) and os.path.exists(lab):
        return d, open(lab, encoding="utf-8").read().strip()
    found, _ = FE.candidates(iso)
    found = [c for c in found if c["source"] in ("helloao", "openbible", "ebible", "dbt") and c.get("nt") and c.get("id")]
    if not found:
        raise SystemExit(f"{iso}: no Bible text to probe against")
    c = found[0]
    title, url, statement, _, _, books = FE.fetch_source({"source": c["source"], "id": c["id"],
                                                          **({"language": iso} if c["source"] == "dbt" else {})}, False)
    os.makedirs(d, exist_ok=True)
    for book_id, btitle, items in books:
        code = (book_id or "").lower()
        if code in BY_CODE and BY_CODE[code][2] == "nt":
            for number, chapter in split_chapters(items):
                open(os.path.join(d, f"{code}{number:03d}.txt"), "w", encoding="utf-8").write(
                    chapter_text(title, f"{url} ({statement})", book_id, btitle, number, chapter))
    label = f"{c['source']}:{c['id']} ({title})"
    open(lab, "w", encoding="utf-8").write(label + "\n")
    return d, label


def probe(pname, c, route, model, out_dir):
    import probe_language as PL
    d, label = fetch_text(c["iso"])
    TP = TextProject(d, c["iso"], c["name"])
    prompt = PL.prompt_write(TP)
    open(os.path.join(out_dir, f"{c['iso']}_write_prompt.md"), "w", encoding="utf-8").write(prompt)
    text, u = PL.ask_model(prompt, route, model)
    path = os.path.join(out_dir, f"{c['iso']}_write_answer.txt")
    open(path, "w", encoding="utf-8").write(text)
    return dict(PL.score_write(TP, PL.answers(path)), edition=label, tokens=u)


def choose(cands, T, levels, iso, script="Latn"):
    """(known iso or None, its score, why, nllb_init); nllb_init in the target `script` (ISO 15924) where a relative
    has one, and why in `why`"""
    import probe_language as PL
    done = [c for c in cands if c.get("write")]
    well = [c for c in done if c["write"]["chrf_by_verse"] >= PL.KNOWN_BY_VERSE]
    some = [c for c in done if c["write"]["chrf_by_verse"] - c["write"]["floor"] >= 10]
    near = lambda cs: min(cs, key=lambda c: (c["distance"], -c["write"]["chrf_by_verse"])) if cs else None
    k = near(well) or near(some)
    best = max(done, key=lambda c: c["write"]["chrf_by_verse"]) if done else None
    tname = T.name(T.by_iso[iso])
    if k:
        how = "writes well" if k in well else "writes, with slips"
        up = f"{k['distance']} level{'s' if k['distance'] > 1 else ''} up"
        why = (f"{k['name']} ({k['level']}, {up} from {tname}) is the nearest relative that the model {how}: write "
               f"{k['write']['chrf_by_verse']} by verse (floor {k['write']['floor']})")
        if best and best is not k:
            why += (f"; {best['name']} scores higher ({best['write']['chrf_by_verse']}) but is further away "
                    f"({best['level']}): a cross-check for the seeds")
    else:
        why = (f"the model writes none of the probed relatives of {tname} "
               + (f"({', '.join(c['name'] + ' ' + str(c['write']['chrf_by_verse']) for c in done)})" if done else "(none probed)")
               + ": no seeds from memory; the structure relatives' typology only")
    order = ([k["iso"]] if k else []) + [c["iso"] for c in sorted(some, key=lambda c: c["distance"]) if c["nllb"]] \
        + [T.iso(x) for _, _, new in levels for x in new if T.iso(x)]
    ni, note = pick_init(list(dict.fromkeys(order)), script)
    if note:
        why += "; " + note
    if not ni:
        why += ("; nllb_init: no relative in NLLB-200, so English; a language of wider communication may serve better "
                "(tpi_Latn where Tok Pisin is one)")
    return (k["iso"] if k else None), (k["write"]["chrf_by_verse"] if k else None), why, ni


def write_block(pname, block):
    """the donor: block in project.yaml, replaced as a whole; the rest of the file as it is"""
    import yaml
    from project import project_dir
    f = os.path.join(project_dir(pname), "project.yaml")
    lines = open(f, encoding="utf-8").read().splitlines()
    out, skip = [], False
    for l in lines:
        if re.match(r"^donor:", l):
            skip = True
            continue
        if skip and (l.startswith((" ", "\t")) or not l.strip()):
            continue
        skip = False
        out.append(l)
    text = yaml.safe_dump({"donor": block}, allow_unicode=True, sort_keys=False, width=110).rstrip()
    at = next((i + 1 for i, l in enumerate(out) if re.match(r"^close_to:", l)), len(out))
    out[at:at] = text.splitlines()
    open(f, "w", encoding="utf-8").write("\n".join(out) + "\n")


def main(a):
    if len(a) < 2 or a[0] not in ("tree", "shortlist", "run"):
        raise SystemExit(__doc__)
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    probes = int(opt("--probes", 3))
    target = a[1]
    p = None
    if "/" in target or a[0] != "tree":
        from project import project
        p = project(target)
        iso = str(p.get("language") or "").split("-")[0].lower()
    else:
        iso = target
    if a[0] == "tree":
        T = Tree()
        g, levels = T.walk(iso)
        st, sl = structure(T, levels)
        print(f"{T.name(g)} ({iso}, {g}): " + " > ".join(T.name(x) for x in T.l[g][3]))
        for anc, d, new in levels[:8]:
            isos = [f"{T.name(x)} ({T.iso(x)})" for x in new if T.iso(x)]
            print(f"  {d}. {T.name(anc)}: {len(new)} language(s)" + (f": {', '.join(isos[:14])}" + (" …" if len(isos) > 14 else "")
                                                                       if isos else ""))
        print(f"structure: {', '.join(st)} (to {sl})")
        return
    extra = [x for x in (opt("--candidates") or "").split(",") if x]
    T, g, levels, st, sl, cands, rows = shortlist(iso, probes, extra=extra)
    print(f"{T.name(g)} ({iso}): structure {', '.join(st)} (to {sl})")
    print("candidates (a Bible to probe against, and an NLLB code or a Wikipedia of 1,000+ articles; the largest per level):")
    for c in cands:
        print(f"  {'probe' if c['probe'] else '     '} {c['name']:22} {c['iso']}  {c['level']} ({c['distance']} up)  "
              f"NLLB {c['nllb'] or '-'}  Wikipedia {c['articles']:,}")
    small = [r for r in rows if r["distance"] <= cands[0]["distance"] and r not in cands] if cands else rows
    if small:
        print("  not probed (nearer or as near, but no Bible here, or small): "
              + ", ".join(f"{r['name']} ({r['iso']}{', Bible' if r['bible'] else ''})" for r in small[:12])
              + (" …" if len(small) > 12 else "") + "  (--candidates <iso> to probe one)")
    if a[0] == "shortlist":
        return
    import probe_language as PL
    route = opt("--route") or (PL.route_available() or [None])[0]
    todo = [c for c in cands if c["probe"]]
    if not todo:
        print("\nno relative to probe (none with a Bible here and an NLLB code or a sizeable Wikipedia): known: none")
        if "--dry-run" in a:
            return
    elif "--dry-run" in a or not route:
        print(f"\n{'dry run' if route else 'no model route (ANTHROPIC_API_KEY or claude)'}: would probe "
              f"{', '.join(c['name'] for c in todo)} (write probe, about 5k tokens each)")
        return
    from project import project_dir
    pdir = project_dir(target)
    out_dir = os.path.join(pdir, "_eval", "local", "donor")
    os.makedirs(out_dir, exist_ok=True)
    tokens = collections.Counter()
    for c in todo:
        print(f"  probing {c['name']} ...", flush=True)
        try:
            c["write"] = probe(target, c, route, opt("--model"), out_dir)
        except SystemExit as e:
            print(f"    skipped: {e}")
            continue
        tokens.update(c["write"].get("tokens") or {})
        w = c["write"]
        print(f"    write {w['chrf_by_verse']} by verse (floor {w['floor']}; {w['answered']}/{w['n']} answered) against {w['edition']}")
    if todo and not any(c.get("write") for c in todo):
        raise SystemExit("no candidate could be probed: nothing chosen, nothing written")
    import langtools as LT, script_code as SC
    script, _ = SC.target_script(LT.Project(target))
    known, score, why, ni = choose(cands, T, levels, iso, script)
    block = {"known": known or "none"}
    if known:
        block["name"] = next(c["name"] for c in cands if c["iso"] == known)
        block["known_score"] = score
    block |= {"candidates": {c["iso"]: c["write"]["chrf_by_verse"] for c in cands if c.get("write")},
              "structure": st, "structure_level": sl, "nllb_init": ni or "eng_Latn", "why": why}
    print(f"\ndonor: {json.dumps(block, ensure_ascii=False)}\ntokens: {dict(tokens)}")
    rec = {"date": datetime.date.today().isoformat(), "route": route, "model": opt("--model"), "block": block,
           "candidates": cands, "tokens": dict(tokens)}
    os.makedirs(os.path.join(pdir, "_learn"), exist_ok=True)
    json.dump(rec, open(os.path.join(pdir, "_learn", "donor.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if "--write" in a:
        write_block(target, block)
        print(f"written: the donor block in {os.path.relpath(os.path.join(pdir, 'project.yaml'), ROOT)}")
    return block


if __name__ == "__main__":
    main(sys.argv[1:])
