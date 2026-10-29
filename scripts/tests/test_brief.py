#!/usr/bin/env python3
"""Regression test: the family brief (scripts/brief.py): a synthetic Glottolog lineage gives a prompt with the family's
categories; the licence rule keeps a brief on NC sources out of profile/; --check maps points to seeds and their tests.
No project files. Run: python3 scripts/tests/test_brief.py (or with pytest)."""
import os, sys, tempfile, types
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import brief as B  # noqa: E402
import seeds as S  # noqa: E402


def tree():
    # name, iso, level, ancestors (top first)
    l = {"atla1278": ["Atlantic-Congo", "", "family", []],
         "narr1281": ["Narrow Bantu", "", "family", ["atla1278"]],
         "bant1": ["Bantu", "", "family", ["atla1278", "narr1281"]],
         "ruta1": ["Rutara", "", "family", ["atla1278", "narr1281", "bant1"]],
         "xxx1": ["Testish", "xxx", "language", ["atla1278", "narr1281", "bant1", "ruta1"]],
         "yyy1": ["Neighbourish", "yyy", "language", ["atla1278", "narr1281", "bant1", "ruta1"]],
         "zzz1": ["Farish", "zzz", "language", ["atla1278", "narr1281", "bant1"]]}
    T = types.SimpleNamespace(l=l, by_iso={v[1]: k for k, v in l.items() if v[1]})
    T.name = lambda g: l[g][0] if g in l else g
    T.iso = lambda g: l[g][1]

    def walk(iso):
        g, seen, out = T.by_iso[iso], set(), []
        seen.add(g)
        for d, anc in enumerate(reversed(l[g][3]), 1):
            new = [k for k, v in l.items() if v[2] == "language" and anc in v[3] and k not in seen]
            seen |= set(new)
            out.append((anc, d, new))
        return g, out
    T.walk = walk
    return T


def test_prompt_has_family_categories():
    with tempfile.TemporaryDirectory() as d:
        text = B.prompt("t/x", T=tree(), p={"language": "xxx", "language_name": "Testish (a test)",
                                            "donor": {"known": "zzz", "name": "Farish"}}, pdir=d)
    for want in ("Testish", "xxx1", "Neighbourish (yyy)", "Farish (zzz)", "noun classes 1-18", "verb extensions",
                 "negation", "tone", "person of actor and undergoer", "orientation", "Licence rule",
                 "_eval/local/brief.md", "brief: \"<point id>\"", "glottolog.org/resource/languoid/id/xxx1"):
        assert want in text, want
    assert "Trans-New Guinea" not in text and "{" not in text.replace("{\n", "")


BRIEF = """# Testish: family brief

## Sources
| id | source | URL | licence | used for | status |
|---|---|---|---|---|---|
| S1 | Doe 2016, The Grammar Basics | https://example.org/1 | {lic} | classes | attested |

## negation
- **b.neg.prefix** [attested] expected: ti- before the subject; S1.
- **b.fut.li** [relative] expected: li- future; S1.
- **b.class.7** [family] expected: ki-; S1.
"""


def write(d, where, lic):
    f = os.path.join(d, where)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    open(f, "w", encoding="utf-8").write(BRIEF.replace("{lic}", lic))
    return f


def test_licence_rule():
    with tempfile.TemporaryDirectory() as d:
        f = write(d, "profile/brief.md", "CC BY-NC-SA 4.0")
        assert any(p.startswith("licence:") for p in B.problems(f))
        f = write(d, "_eval/local/brief.md", "CC BY-NC-SA 4.0")
        assert not B.problems(f)
    with tempfile.TemporaryDirectory() as d:
        assert not B.problems(write(d, "profile/brief.md", "CC BY 4.0"))
        assert any(p.startswith("licence:") for p in B.problems(write(d, "profile/brief.md", "unknown licence")))


def test_check_states():
    seeds = {"entries": [
        {"id": "seed:m.ti.neg.verb", "brief": "b.neg.prefix"},
        {"id": "seed:m.li.fut.verb", "brief": "b.fut.li"},
        {"id": "seed:f.ghost", "brief": "b.nowhere"}]}
    tested = {"seed:m.ti.neg.verb": [("m.ti.verb", "confirmed")],
              "seed:m.li.fut.verb": [("claim.li", "contradicted")]}
    with tempfile.TemporaryDirectory() as d:
        write(d, "_eval/local/brief.md", "CC BY-NC-SA 4.0")
        rows, probs = B.check("t/x", pdir=d, seeds_data=seeds, tested=tested)
    n, state = B.summary(rows)
    assert {pid: state(r) for pid, _, r in rows} == {"b.neg.prefix": "confirmed", "b.fut.li": "contradicted",
                                                     "b.class.7": "no test"}
    assert probs == ["seed names brief point b.nowhere, not in the brief"]


def test_seed_check_accepts_brief_method():
    e = {"id": "seed:m.ki.cl7.noun", "kind": "morph", "value": "CL7", "form": "ki-", "slot": "prefix", "host": "noun",
         "confidence": "medium", "method": "brief:hay", "by": "agent:brief", "date": "2026-10-22", "status": "seed",
         "donor_form": "ki-", "test": "a noun prefix", "brief": "b.class.7"}
    with tempfile.TemporaryDirectory() as d:
        import json
        json.dump({"entries": [e]}, open(os.path.join(d, S.FILE), "w"))
        assert S.check(d) == []
        json.dump({"entries": [dict(e, brief=None)]}, open(os.path.join(d, S.FILE), "w"))
        assert any("names its point" in p for p in S.check(d))


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
    print("ok")
