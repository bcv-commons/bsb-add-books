#!/usr/bin/env python3
"""Fine-tune NLLB on a project's verse pairs (scripts/nllb/data.py): the second-draft model for review triage, Scripture
Forge's method scaled to an 8 GB card. Needs no other repo file than model_text.py beside it, so it runs on a GPU machine
with only this folder copied there (scripts/nllb/remote.py).

Settings follow machine.py's production config (lr 2e-4 cosine, warmup 1000, effective batch 64, label smoothing 0.2, max
length 200, gradient checkpointing, at most 5000 steps, beams 2) with what an 8 GB card needs: NLLB-200-distilled-600M
instead of 1.3B, Adafactor instead of AdamW, bf16 on CUDA, batch 2 x 32 accumulation (8 and 4 ran out of memory). As
silnlp does, target characters missing from the NLLB vocabulary become tokens, and a target code NLLB lacks is added,
initialised from the data's init_lang. Early stop on the validation loss; the best model is kept.

The device: CUDA if there is one, else Apple's GPU (MPS; fp32: about 20 GB of shared memory, so a Mac with 32 GB; a 16 GB
M1 runs out of memory), else the processor (weeks: 8.8 s per batch of 2 on an i7-6700, so 4-5 minutes a step; rent a GPU instead). --device overrides.

Measured (RTX 3060 Ti, 8 GB, an NT of 7,700 verses): peak 6.6-6.9 GB, about 5 s a step, early stop at 4,000-4,500 steps,
5.5-6 hours.

Usage: python3 scripts/nllb/train.py --data DIR [--out DIR] [--model facebook/nllb-200-distilled-600M] [--steps 5000]
                                     [--batch 2] [--accum 32] [--device cuda|mps|cpu] [--smoke]
Writes <out>/model/ (model, tokenizer, meta.json), <out>/scores.json and, if the data has a test split, <out>/test.pred
(with a target in parts, model_text morphs: the words rebuilt, and the model's parts in test.pred.parts).
Needs: pip install -r scripts/nllb/requirements.txt (torch, transformers, datasets, sentencepiece, sacrebleu).
The weights of NLLB are CC BY-NC 4.0, and so is the fine-tuned model; trained on a non-free edition it is derived work too:
it stays with the project (never published) unless the edition's rights allow otherwise.
"""
import argparse, json, os, shutil, sys, time

import torch
from datasets import Dataset
from transformers import (AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq, EarlyStoppingCallback,
                          Seq2SeqTrainer, Seq2SeqTrainingArguments)


def device_of(want=None):
    if want:
        return want
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--out")
    ap.add_argument("--model", default="facebook/nllb-200-distilled-600M")
    ap.add_argument("--steps", type=int, default=5000); ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--accum", type=int, default=32); ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--trg-code"); ap.add_argument("--init-lang"); ap.add_argument("--src-code", default="eng_Latn")
    ap.add_argument("--max-len", type=int, default=200); ap.add_argument("--optim", default="adafactor")
    ap.add_argument("--max-trg-len", type=int, help="default: --max-len, or the longest target (at most 512) if longer")
    ap.add_argument("--device", choices=["cuda", "mps", "cpu"]); ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    meta = json.load(open(os.path.join(args.data, "meta.json"), encoding="utf-8"))
    trg_code, init_lang = args.trg_code or meta["trg_code"], args.init_lang or meta.get("init_lang", "eng_Latn")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from model_text import Codec, generate   # the target as the data was built (words, or morphs: decoded before scoring)
    codec = Codec(meta.get("model_text"))
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.data)), "run")
    os.makedirs(out, exist_ok=True)
    dev = device_of(args.device)
    t0 = time.time()
    read = lambda n: open(os.path.join(args.data, n), encoding="utf-8").read().splitlines()
    tr, va, te = [(read(f"{s}.src"), read(f"{s}.trg")) for s in ("train", "val", "test")]
    if args.smoke:
        tr, va, te = (tr[0][:64], tr[1][:64]), (va[0][:8], va[1][:8]), (te[0][:4], te[1][:4])

    tok = AutoTokenizer.from_pretrained(args.model, src_lang=args.src_code)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model)
    # missing target characters -> new tokens (silnlp seq2seq_config.py _find_missing_characters)
    unk = tok.unk_token_id
    chars = sorted({c for s in tr[1] + va[1] for c in s if not c.isspace()})
    missing = [c for c in chars if unk in tok(c, add_special_tokens=False).input_ids]
    new_code = trg_code not in tok.get_vocab()
    if missing:
        tok.add_tokens(missing)
    if new_code:
        tok.add_tokens([trg_code], special_tokens=True)
    model.resize_token_embeddings(len(tok))
    if new_code and init_lang in tok.get_vocab():
        with torch.no_grad():
            emb = model.get_input_embeddings().weight
            emb[tok.convert_tokens_to_ids(trg_code)] = emb[tok.convert_tokens_to_ids(init_lang)]
    tok.tgt_lang = trg_code
    print(f"device {dev}; added {len(missing)} characters: {''.join(missing)}; target code {trg_code}"
          + (f" (new, from {init_lang})" if new_code else ""), flush=True)

    # the target's limit: a target in parts (model_text morphs) is longer than the text (Kuni: 39% more pieces)
    longest = max(len(x) for x in tok(text_target=tr[1] + va[1], add_special_tokens=True)["input_ids"])
    trg_len = args.max_trg_len or min(512, max(args.max_len, longest))
    print(f"target limit {trg_len} pieces (longest {longest})", flush=True)

    def enc(src, trg):
        ds = Dataset.from_dict({"src": src, "trg": trg})

        def f(b):
            x = tok(b["src"], max_length=args.max_len, truncation=True)
            x["labels"] = tok(text_target=b["trg"], max_length=trg_len, truncation=True)["input_ids"]
            return x
        return ds.map(f, batched=True, remove_columns=["src", "trg"])

    base_collate = DataCollatorForSeq2Seq(tok)
    start_id = model.config.decoder_start_token_id

    def collate(feats):
        """Padded batch plus decoder_input_ids (labels shifted right): with label smoothing the trainer takes the labels
        out before the forward call, and transformers 5 no longer builds the decoder inputs in the collator."""
        b = base_collate(feats)
        lab = b["labels"].clone()
        lab[lab == -100] = tok.pad_token_id
        dec = lab.new_full(lab.shape, tok.pad_token_id)
        dec[:, 1:] = lab[:, :-1]
        dec[:, 0] = start_id
        b["decoder_input_ids"] = dec
        return b

    smoke = args.smoke
    targs = Seq2SeqTrainingArguments(
        output_dir=os.path.join(out, "ckpt"), max_steps=20 if smoke else args.steps,
        per_device_train_batch_size=2 if smoke else args.batch, gradient_accumulation_steps=1 if smoke else args.accum,
        # validation in the same small batches: the default of 8 runs out of an 8 GB card at the first validation (the loss
        # over the 256k-token vocabulary)
        per_device_eval_batch_size=2 if smoke else args.batch,
        learning_rate=args.lr, lr_scheduler_type="cosine", warmup_steps=2 if smoke else min(1000, args.steps // 5),
        label_smoothing_factor=0.2, optim=args.optim, bf16=dev == "cuda", gradient_checkpointing=True,
        use_cpu=dev == "cpu", eval_strategy="steps", eval_steps=10 if smoke else 500, save_strategy="steps",
        save_steps=10 if smoke else 500, save_total_limit=1, load_best_model_at_end=True, metric_for_best_model="eval_loss",
        greater_is_better=False, logging_steps=5 if smoke else 50, report_to=[], predict_with_generate=False,
        dataloader_num_workers=0 if dev == "mps" else 2, seed=111)
    trainer = Seq2SeqTrainer(model=model, args=targs, train_dataset=enc(*tr), eval_dataset=enc(*va), data_collator=collate,
                             callbacks=[EarlyStoppingCallback(early_stopping_patience=4)])
    trainer.train()
    t1 = time.time()
    # the best model (load_best_model_at_end) with the tokenizer it was trained with: a checkpoint without that tokenizer
    # (its added characters and code) drafts garbage
    mdir = os.path.join(out, "model")
    trainer.save_model(mdir)
    tok.save_pretrained(mdir)
    json.dump({**meta, "trg_code": trg_code, "init_lang": init_lang, "src_code": args.src_code, "base": args.model,
               "steps": trainer.state.global_step, "trg_len": trg_len}, open(os.path.join(mdir, "meta.json"), "w", encoding="utf-8"), indent=1)
    shutil.rmtree(os.path.join(out, "ckpt"), ignore_errors=True)

    sc: dict = {}
    if te[0]:
        model.eval()
        # drafted as draft.py drafts (looping verses again), so the score is the drafts' score
        preds, sc["looped"] = generate(model, tok, te[0], tok.convert_tokens_to_ids(trg_code), max_len=args.max_len,
                                       max_new=max(256, trg_len + 16))
        if codec.on:                    # the model's parts as written, and the words rebuilt from them (scored)
            open(os.path.join(out, "test.pred.parts"), "w", encoding="utf-8").write("\n".join(p.strip() for p in preds) + "\n")
            preds, te = [codec.decode(p) for p in preds], (te[0], [codec.decode(t) for t in te[1]])
        open(os.path.join(out, "test.pred"), "w", encoding="utf-8").write("\n".join(p.strip() for p in preds) + "\n")
        try:
            import sacrebleu
            sc = {**sc, "chrf3": sacrebleu.corpus_chrf(preds, [te[1]], char_order=6, beta=3, remove_whitespace=True).score,
                  "chrf2": sacrebleu.corpus_chrf(preds, [te[1]], char_order=6, beta=2).score,
                  "bleu": sacrebleu.corpus_bleu(preds, [te[1]]).score}
        except Exception as e:  # noqa: BLE001
            sc = {**sc, "error": str(e)}
    if codec.on:
        sc["repairs"] = dict(codec.repairs)
    sc.update(train_minutes=round((t1 - t0) / 60, 1), steps=trainer.state.global_step, device=dev,
              gpu=torch.cuda.get_device_name(0) if dev == "cuda" else dev, model=args.model,
              max_mem_gb=round(torch.cuda.max_memory_allocated() / 2 ** 30, 2) if dev == "cuda" else None)
    json.dump(sc, open(os.path.join(out, "scores.json"), "w"), indent=1)
    print(json.dumps(sc), flush=True)


if __name__ == "__main__":
    main()
