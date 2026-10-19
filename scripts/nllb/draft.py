#!/usr/bin/env python3
"""Draft chapters with the project's second-draft model (scripts/nllb/train.py): the second draft for review triage
(scripts/triage.py), or, on a team's request, a rough first pass of narrative and law books. Three steps; `run` needs only
this file and the model, so it can run on another machine:

  src      python3 scripts/nllb/draft.py src <project> <code> <ch>[,<ch>..] [--out DIR]
           one line per verse of the original (Hebrew numbering in the OT) with its BSB English as the source (the model
           was trained on BSB -> edition pairs): DIR/input.src + DIR/input.vref (default DIR:
           <project>/_eval/local/nllb/drafts/<code>NNN-NNN/)
  run      python3 scripts/nllb/draft.py run --data DIR [--model DIR] [--beams 2] [--device cuda|mps|cpu]
           DIR/input.pred; minutes for a chapter, on the processor too (default model: <data>/../../run/model)
  collect  python3 scripts/nllb/draft.py collect <project> DIR [--name nllb] [--out DIR2]
           <project>/_eval/local/second/<name>/<code>NNN.txt, read by scripts/triage.py; with --out the chapters go to DIR2
           as a rough pass, with DIR2/rough_check.md: the verses scripts/rough_check.py flags (a lost negation, English
           left in), to be reviewed first. A rough pass of poetry or prophecy is not worth handing over (4 major errors per
           10 verses in the study, against about 2 in narrative and law).

The vref lines are "code c:v" in the original's numbering, so a verse the BSB splits or joins is drafted once.
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
opt = lambda a, k, d=None: a[a.index(k) + 1] if k in a else d


def src(a):
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import langtools as LT
    import vrs
    from books import BY_CODE
    from notes_hebrew import original_verses
    from project import project_dir
    pname, code, chs = a[0], a[1], [int(x) for x in a[2].split(",")]
    out = opt(a, "--out") or os.path.join(project_dir(pname), "_eval", "local", "nllb", "drafts",
                                          f"{code}{chs[0]:03d}" + (f"-{chs[-1]:03d}" if len(chs) > 1 else ""))
    os.makedirs(out, exist_ok=True)
    P = LT.Project(pname)
    ot = BY_CODE[code][2] != "nt"
    s, r = [], []
    for ch in chs:
        for v in sorted(original_verses(code, ch)):
            c, bv = vrs.to_bsb(code, ch, v) if ot else (ch, v)
            bsb = LT.verses_of(os.path.join(ROOT, P.assist_dir(code), f"{code}{c:03d}.txt")).get((c, bv), "")
            s.append(" ".join(bsb.split()))
            r.append(f"{code} {ch}:{v}")
    open(os.path.join(out, "input.src"), "w", encoding="utf-8").write("\n".join(s) + "\n")
    open(os.path.join(out, "input.vref"), "w", encoding="utf-8").write("\n".join(r) + "\n")
    print(f"{len(s)} verses -> {out}")


def run(a):
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    data = opt(a, "--data")
    mdir = opt(a, "--model") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(data))), "run", "model")
    meta = json.load(open(os.path.join(mdir, "meta.json"), encoding="utf-8"))
    dev = opt(a, "--device") or ("cuda" if torch.cuda.is_available() else
                                 "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(mdir, src_lang=meta.get("src_code", "eng_Latn"))
    model = AutoModelForSeq2SeqLM.from_pretrained(mdir).to(dev).eval()
    lines = open(os.path.join(data, "input.src"), encoding="utf-8").read().splitlines()
    bos = tok.convert_tokens_to_ids(meta["trg_code"])
    preds = []
    for i in range(0, len(lines), 16):
        b = tok(lines[i:i + 16], return_tensors="pt", padding=True, truncation=True, max_length=200).to(dev)
        with torch.no_grad():
            o = model.generate(**b, forced_bos_token_id=bos, num_beams=int(opt(a, "--beams", 2)), max_new_tokens=256)
        preds += tok.batch_decode(o, skip_special_tokens=True)
    open(os.path.join(data, "input.pred"), "w", encoding="utf-8").write("\n".join(p.strip() for p in preds) + "\n")
    print(f"{len(preds)} verses drafted on {dev}")


def collect(a):
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from project import project_dir
    pname, d = a[0], a[1]
    name = opt(a, "--name", "nllb")
    refs = open(os.path.join(d, "input.vref"), encoding="utf-8").read().splitlines()
    preds = open(os.path.join(d, "input.pred"), encoding="utf-8").read().splitlines()
    assert len(refs) == len(preds), (len(refs), len(preds))
    chs = {}
    for ref, p in zip(refs, preds):
        code, cv = ref.split()
        c, v = cv.split(":")
        chs.setdefault((code, int(c)), []).append(f"v{v} {p}")
    rough = "--out" in a
    out = opt(a, "--out") or os.path.join(project_dir(pname), "_eval", "local", "second", name)
    os.makedirs(out, exist_ok=True)
    head = ("!!<Rough first pass by a fine-tuned NLLB model: meaning errors expected; check rough_check.md first>!!" if rough
            else "!!<Second draft for review triage by a fine-tuned NLLB model; not a draft>!!")
    written = []
    for (code, c), ls in chs.items():
        f = os.path.join(out, f"{code}{c:03d}.txt")
        open(f, "w", encoding="utf-8").write("\n".join([head, "", f"==={code} {c}===", ""] + ls) + "\n")
        written.append(f)
        print(os.path.relpath(f, ROOT))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "rough_check.py"), pname] + written,
                       capture_output=True, text=True, check=True).stdout
    print(r)
    if rough:
        open(os.path.join(out, "rough_check.md"), "w", encoding="utf-8").write(
            "# Rough pass: verses to check first (scripts/rough_check.py)\n\n" + r)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("src", "run", "collect"):
        raise SystemExit(__doc__)
    {"src": src, "run": run, "collect": collect}[sys.argv[1]](sys.argv[2:])
