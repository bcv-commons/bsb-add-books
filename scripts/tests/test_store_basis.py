#!/usr/bin/env python3
"""The store's two bases: a measured claim's `basis` (the settings fingerprint, grammar.basis) and a Grambank answer's
`answer_basis` (team, derived or labelled). Both validate side by side; an old `gb:` entry with the answer in `basis`
gets the migration message. Synthetic store, no project files. Run: python3 scripts/tests/test_store_basis.py (or pytest)."""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import grammar  # noqa: E402

BASE = dict(confidence="medium", method="corpus-derived", date="2026-10-29", status="observed")
MORPH = dict(BASE, id="m:z-", kind="morph", slot="prefix", form="z-", host="verb", value="2PL", by="agent:test",
             evidence=[{"ref": "JHN 1:1"}])
CLAIM = dict(BASE, id="claim:z-.2pl", kind="claim", value="z- marks 2PL on the verb", tests=["corpus"],
             verdict="confirmed", by="script:morphs.py", rerun=["morphs.py", "try", "m:z-"])
ANSWER = dict(BASE, id="gb:GB090", kind="feature", codes=["GB090"], value="1 (present): z-", by="script:grammar.py",
              evidence=[{"ref": "JHN 1:1"}], answer_basis="derived", rule="an affix the store codes GB090",
              basis_by_morph={"m:z-": "derived"})


def store(entries):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "text"))
    open(os.path.join(d, "text", "jhn001.txt"), "w").write("v1 Zabelo abelo.\nv2 Omitu.\n")
    f = os.path.join(d, "observations.json")
    json.dump({"iso": "xxx", "edition": "test", "partition": "observations", "entries": entries}, open(f, "w"))
    return d, f


def check(d):
    r = subprocess.run([sys.executable, os.path.join(HERE, "..", "language_profile.py"), "check", d,
                        "--text-dir", os.path.join(d, "text")], capture_output=True, text=True)
    return r.stdout + r.stderr


def measured(entries):
    """the store with the claim's basis set as a script sets it: after the write, on the store as it now is"""
    d, f = store(entries)
    data = json.load(open(f))
    for e in data["entries"]:
        if e.get("rerun"):
            e["basis"], e["basis_corpus"] = grammar.basis(d), grammar.corpus(d)
    json.dump(data, open(f, "w"))
    return d


def test_measured_claim_and_answer_validate():
    d = measured([MORPH, CLAIM, ANSWER])
    out = check(d)
    assert " 0 problems" in out, out
    assert grammar.stale(d)[0] == [], grammar.stale(d)   # the claim is current: retest has nothing to rerun


def test_claim_goes_stale_when_the_store_changes():
    d = measured([MORPH, CLAIM])
    f = os.path.join(d, "observations.json")
    data = json.load(open(f))
    data["entries"].append(dict(MORPH, id="m:-a", slot="suffix", form="-a", value="FV"))
    json.dump(data, open(f, "w"))
    assert [e["id"] for e, _ in grammar.stale(d)[0]] == ["claim:z-.2pl"]


def test_old_answer_basis_and_bad_fingerprint():
    old = {k: v for k, v in ANSWER.items() if k != "answer_basis"}
    d = measured([MORPH, dict(old, basis="derived"), dict(CLAIM, id="claim:other")])
    f = os.path.join(d, "observations.json")
    data = json.load(open(f))
    data["entries"][-1]["basis"] = "labelled"
    json.dump(data, open(f, "w"))
    out = check(d)
    assert "gb:GB090: a Grambank answer's basis is `answer_basis`" in out, out
    assert "claim:other: basis 'labelled' is not a settings fingerprint" in out, out


if __name__ == "__main__":
    test_measured_claim_and_answer_validate(); test_claim_goes_stale_when_the_store_changes()
    test_old_answer_basis_and_bad_fingerprint(); print("ok")
