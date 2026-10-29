#!/usr/bin/env python3
"""grammar.py's basis of a Grambank answer: team, derived or labelled (made-up affixes, no project files)."""
import os, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import grammar as G  # noqa: E402


def test_bases():
    d = tempfile.mkdtemp()                 # a profile dir: no language DB, so nothing can be measured
    team = {"id": "m:ko:verb", "form": "ko-", "status": "decided", "value": "NEG"}
    agent = {"id": "m:po:verb", "form": "po-", "status": "observed", "value": "NEG"}
    assert G.rule_basis(d, None, "GB107", team, {}) == ("team", None)
    assert G.rule_basis(d, None, "GB107", agent, {}) == ("labelled", None)
    assert G.rule_basis(d, None, "GB090", agent, {"m:po:verb": "po- n 40, lift 5"}) == ("derived", "po- n 40, lift 5")
    assert G.BASES.index("team") < G.BASES.index("derived") < G.BASES.index("labelled")


def test_every_store_rule_is_attributed():
    store = {r["gb_id"] for r in G.recipes() if r.get("from_store") == "yes"}
    assert store <= set(G.RULES), sorted(store - set(G.RULES))


if __name__ == "__main__":
    test_bases()
    test_every_store_rule_is_attributed()
    print("ok")
