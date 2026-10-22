#!/usr/bin/env python3
"""The agreement route of the affix audit (morphs.py audit --route agree): a verb affix that claims the class or gender
of its subject or object (a store entry's `agree`, docs/language-store.md, *Morphs*) tested inside the target itself.

The source only finds the pair: for each verb of the NT (orig/grc.sqlite) its subject (the verb's `subjref`, explicit
or not) and its object (an accusative third-person pronoun of the verb's clause, through its `referent`), and for the
OT books of the corpus (orig/heb.sqlite, the target words linked by scripts/ot_routes.ot_links) the verb's subject
(`subjref`). Both the verb and the noun must be linked to a target word, and to different ones.
The noun's class comes from the target:
- by: class (the default): the store's noun prefixes (host noun) on the noun's word, their `class` ("7"; "9/10" for a
  class pair; {"singular": "9", "plural": "10"}: the pair told apart by the source noun's number), else read from a
  `value` like CL7 / CL9/10; a lexical split by stem: {"default": "1/3", "stems": {"ti": "3"}};
- by: gender: the source noun's grammatical gender (Greek masculine / feminine / neuter; Hebrew masculine / feminine),
  for languages that mark the referent's sex or kind (a masculine and a feminine subject prefix).
A pair counts for the claim where the noun's class lies inside the claimed classes, against it where it lies outside,
and is left out where it is ambiguous (a 1/3 noun for a class-1 claim) or has no class. Then morphs.route_stats as on
every route: share with the affix and on the same stems without it, odds, the words against it, a verdict; and
`odds_all`, against every verb without it (the plain 2x2 of class and affix over all pairs)."""
import collections, os, re, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROLES = ("subject", "object")
BY = ("class", "gender")


def claim(e):
    """(role, {classes}, by) of an entry's `agree`, or None"""
    a = e.get("agree")
    if not isinstance(a, dict) or a.get("role") not in ROLES:
        return None
    c = a.get("class")
    cs = {str(x) for x in (c if isinstance(c, list) else [c])} if c not in (None, "", []) else set()
    return (a["role"], cs, a.get("by") or "class") if cs else None


CL_VALUE = re.compile(r"\bCL\s*(\d+[a-z]?(?:/\d+[a-z]?)*)", re.I)


def noun_classes(G):
    """{(form, position): class spec} of the store's live noun prefixes with a class (`class`, else a CLn value)"""
    out = {}
    for e in G.morphs:
        if e.get("host") != "noun" or e.get("slot") != "prefix" or not e.get("form"):
            continue
        c = e.get("class")
        if c is None:
            m = CL_VALUE.search(str(e.get("value") or ""))
            c = m[1] if m else None
        if c:
            out[(e["form"], int(e.get("position") or 0))] = c
    return out


def resolve(spec, number, stem=None):
    """a class spec and the source noun's number ('singular'/'plural', Hebrew 'singular'/'plural'/'dual') and the noun's
    stem -> {members}; a dict spec may name stems of their own ({"default": "1/3", "stems": {"ti": "3"}})"""
    if isinstance(spec, dict) and stem is not None and stem in (spec.get("stems") or {}):
        return set(str(spec["stems"][stem]).split("/"))
    if isinstance(spec, dict) and "default" in spec:
        return set(str(spec["default"]).split("/"))
    if isinstance(spec, dict):
        n = "plural" if (number or "").startswith(("p", "d")) else "singular" if number else None
        v = spec.get(n) if n else None
        return set(str(v).split("/")) if v else set("/".join(str(spec[x]) for x in ("singular", "plural")
                                                             if x in spec).split("/"))
    return set(str(spec).split("/"))


def label(S, classes, word, number, cache):
    """{class members} of a target noun word by its noun prefixes, or set()"""
    k = (word, number)
    if k not in cache:
        ms = S.split(word)
        got, stem = set(), next((m.form for m in ms if m.slot == "stem"), "")
        for m in ms:
            if m.slot == "prefix":
                spec = classes.get((m.form, m.position)) or (classes.get((m.form, 0)) if not m.position else None)
                if spec is None:
                    spec = next((v for (f, _), v in classes.items() if f == m.form), None)
                if spec is not None:
                    got |= resolve(spec, number, stem)
        cache[k] = got
    return cache[k]


# ---------- the pairs: (role, verb word, noun word, noun number, noun gender, ref, source) ----------

def nt_pairs(pname, S):
    import lang, morphs
    _, con = lang.connect(pname)
    con.row_factory = sqlite3.Row
    gtok = {r["key"]: r for r in con.execute("select key, book, ch, v, class, type, lemma, gcase, number, gender, "
                                              "person, mood, clause from g.tokens")}
    hw = morphs.hyphen_words(con) if getattr(S, "hyphen", False) else {}
    g2t, t2g, word = collections.defaultdict(list), collections.Counter(), {}
    for b, c, v, p, key, raw in con.execute("""select l.book, l.ch, l.v, l.pos, l.key, t.raw from nt_links l join nt_tokens t
            on t.book=l.book and t.ch=l.ch and t.v=l.v and t.pos=l.pos"""):
        if not raw:
            continue
        g2t[key].append((b, c, v, p))
        t2g[(b, c, v, p)] += 1
        word[(b, c, v, p)] = hw.get((b, c, v, p), raw)

    def tw(key):                                     # the target token linked to a Greek word, one linked only to it first
        ts = g2t.get(key)
        if not ts:
            return None
        only = [t for t in ts if t2g[t] == 1]
        return min(only or ts)
    FIN = ("indicative", "subjunctive", "imperative", "optative")
    out = []

    def add(role, vk, nk):
        g, n = gtok[vk], gtok.get(nk)
        if not n or n["class"] != "noun":
            return
        a, b = tw(vk), tw(nk)
        if a and b and a != b and word[a] != word[b]:
            out.append((role, word[a], word[b], n["number"], n["gender"], f"{g['book'].upper()} {g['ch']}:{g['v']}", "nt",
                        n["type"] == "proper"))
    subj = collections.defaultdict(list)
    ref = collections.defaultdict(list)
    for k, kind, t in con.execute("select key, kind, target from g.refs where kind in ('subjref', 'referent')"):
        (subj if kind == "subjref" else ref)[k].append(t)
    verbs_of = collections.defaultdict(list)
    for k, g in gtok.items():
        if g["class"] == "verb" and g["clause"]:
            verbs_of[g["clause"]].append(k)
    for k, g in gtok.items():
        if g["class"] == "verb" and g["person"] == "third" and g["mood"] in FIN and len(subj.get(k, ())) == 1:
            add("subject", k, subj[k][0])
        if (g["class"] == "pron" and g["lemma"] == "αὐτός" and g["gcase"] == "accusative" and len(ref.get(k, ())) == 1
                and len(verbs_of.get(g["clause"], ())) == 1):
            add("object", verbs_of[g["clause"]][0], ref[k][0])
    return out


def ot_pairs(pname, S, P=None):
    """the OT books' subjects (orig/heb.sqlite subjref), through the target words linked to the Hebrew"""
    import langtools as LT
    import ot_routes as OR
    P = P or LT.Project(pname)
    links, _ = OR.ot_links(P, getattr(S, "hyphen", False))
    if not links:
        return []
    k2w = collections.defaultdict(list)
    for B, c, v, w, key in links:
        k2w[key].append(w)
    con = sqlite3.connect(OR.HEB)
    con.row_factory = sqlite3.Row
    keys = set(k2w)
    tok = {}
    for b in sorted({l[0] for l in links}):
        for r in con.execute("select key, book, ch, v, pos, type, number, gender from tokens where book=?", (b,)):
            tok[r["key"]] = r
    out = []
    for k, t in con.execute("select key, target from refs where kind='subjref'"):
        if k not in keys or t not in keys:
            continue
        g, n = tok.get(k), tok.get(t)
        if not g or not n or g["pos"] != "verb" or n["pos"] != "noun":
            continue
        a, b = k2w[k][0], k2w[t][0]
        if a != b:
            out.append(("subject", a, b, n["number"], n["gender"], f"{g['book']} {g['ch']}:{g['v']}", "ot",
                        (n["type"] or "").startswith("proper")))
    return out


def pairs(pname, S, P=None, ot=True):
    return nt_pairs(pname, S) + (ot_pairs(pname, S, P) if ot else [])


# ---------- the route ----------

def rows_for(e, S, prs, classes, cache=None):
    """route_stats rows for one entry: (verb, parts, stem, {("agree", "yes")} where the noun's class is claimed, even,
    ref, verb word, noun word); pairs without a class or ambiguous for the claim left out -> (rows, figures)"""
    import morphs
    role, want, by = claim(e)
    cache = {} if cache is None else cache
    sc = cache.setdefault("_split", {})
    rows, fig = [], collections.Counter()
    for r, vw, nw, num, gen, ref, src, proper in prs:
        if r != role:
            continue
        fig[f"{src} pairs"] += 1
        if by == "class" and proper:                 # a name has no class prefix: left out, not counted against
            fig["names"] += 1
            continue
        if by == "gender":
            lab = {gen} if gen else set()
        else:
            lab = label(S, classes, nw, num, cache)
        if not lab:
            fig["no class"] += 1
            continue
        if lab <= want:
            fv = {("agree", "yes")}
        elif lab & want:
            fig["ambiguous"] += 1
            continue
        else:
            fv = set()
        if vw not in sc:
            ms = S.split(vw)
            sc[vw] = ({(m.form, m.position) for m in ms if m.slot != "stem"},
                      next((m.form for m in ms if m.slot == "stem"), ""))
        labs, stem = sc[vw]
        even = int(ref.rsplit(":", 1)[1]) % 2 == 0
        rows.append(("verb", labs, stem, fv, even, ref, vw, nw))
        fig["tested"] += 1
    return rows, fig


def stats(e, S, prs, classes, A=None, top=8, words=None, stem_by=None, cache=None):
    """morphs.route_stats of the agreement claim, with odds_all (against every pair without the affix) and the pairs'
    figures; an entry without `agree`, or with by: class and no noun classes in the store, is untestable"""
    import morphs
    A = A or morphs.AUDIT
    c = claim(e)
    if c is None:
        return dict(untestable="no agree claim", verdict="n.a.")
    role, want, by = c
    if by not in BY:
        return dict(untestable=f"agree by {by!r} (class or gender)", verdict="n.a.")
    if by == "class" and not classes:
        return dict(untestable="the store has no noun-class prefixes (host noun, a `class` or a CLn value)",
                    verdict="n.a.")
    rows, fig = rows_for(e, S, prs, classes, cache)
    x = morphs.route_stats(e, rows, {"agree": {"yes"}}, S, A, top, words, stem_by)
    on = [t for t in rows if morphs.comes_off(e, t[1])]
    off = [t for t in rows if not morphs.comes_off(e, t[1])]
    k, ko = sum(bool(t[3]) for t in on), sum(bool(t[3]) for t in off)
    x["odds_all"] = morphs._odds(k, len(on), ko, len(off)) if on and off and k + ko else None
    x["cells"] = (k, len(on), ko, len(off))
    x["pairs"] = dict(fig)
    x["weak"], x["claim"] = False, {f"{role} {by}": want}
    return x


def summary(G, pname=""):
    """one line: the store's agree claims and noun classes, or what is missing for the route"""
    cl = noun_classes(G)
    ag = [e for e in G.morphs if claim(e)]
    by_cls = [e for e in ag if claim(e)[2] == "class"]
    s = f"{pname}: agreement route: {len(ag)} affix(es) with an `agree` claim, {len(cl)} noun-class prefix(es)"
    if not ag:
        s += " -- no affix claims a subject/object class or gender (`agree`): nothing to test on this route"
    elif by_cls and not cl:
        s += (" -- no noun prefix has a class (`class`, or a CLn value): the class claims can't be tested; a gender "
              "claim (by: gender) can")
    return s
