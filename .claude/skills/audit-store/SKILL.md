---
name: audit-store
description: Check a language store's affixes on the words they split (morphs.py audit) and act on each verdict - keep, protect words, restrict, retire - then measure again and rebuild what depends on the store. Use when asked to audit, clean or check a project's morphs or affixes, when the morph view splits words it shouldn't, or after an agent has added many affix entries.
---

# Audit the store's affixes

The store's format: `docs/language-store.md` (*Morphs*, *Protected words*, *The morph view*). Needs the project's NT
aligned to the Greek (`python3 scripts/lang.py build <project>`); the OT routes need the OT books aligned to the Hebrew
(`align.py`, `_learn/links_hbo.tsv`) and, for the Vamvas route, `python3 scripts/setup.py --only vamvas-align`.

1. **Before:** note the figures to compare with: `python3 scripts/morphs.py <project> check` (tokens split, every type
   rebuilt) and `python3 scripts/morphs.py <project> try` (n, stems, odds ratio per affix).
2. **Audit:** `python3 scripts/morphs.py <project> audit [id ...]` (read-only; all live affixes without ids). Per affix:
   tokens and stems, the Greek feature's share with and without it on the same stems, its top words with their Greek,
   the words against it, a verdict. Where the style corpus has OT books, add `--route all`: the same claim on the OT
   linked to the Hebrew, read by the Hebrew token, its LXX word and its Vamvas word (`setup.py --only vamvas-align`),
   one row per route and a combined verdict: `re-label` (one route holds, another fails: propose the holding route's
   category to a person), `nt-only` (flag, don't retire), `ot-only` (keep, note); `flat` routes (third singular in
   narrative) say nothing either way.
3. **Decide per verdict.** Look at two or three verses of a word before acting on it
   (`python3 scripts/concord.py <project> tgt <word>`, `... parts <word>`); a figure alone is not enough.
   - `confirm`: keep it. An `open` entry becomes `observed` with `morphs.py try <id> --write`.
   - `protect-words`: each word against it that is a word of its own (a noun, a name) and not this affix becomes a
     `word` entry: `id: w:<form>`, `kind: word`, `form` as written, `value: WORD` (or `NAME`), `gloss` the Greek
     lemma it is linked to, `affixes: [<morph id>]`, `evidence` a verse where it occurs whole, `method:
     corpus-derived`, `status: observed`. A word against it that is the affix after all (a rare use, a different
     meaning of the same form) stays unprotected: say so in the morph's `note`.
   - `restrict`: it holds only on the stems the audit names. A few frequent words against it: protect them as above.
     Many: the form is too short or the host too wide. Supersede it with a narrower entry (a longer form, its own
     host) where the corpus shows one, else leave it `open` with the stems in its `note`.
   - `retire`: the feature is no likelier with it than without. Give the morph `status: superseded` and add a claim
     `claim:morph.<form>.<host>` with `supersedes: <morph id>`, `verdict: contradicted`, the audit's figures, and in
     `next` what the form might be instead. Never delete an entry.
   - `no-claim`, `too-few`: nothing to decide; a `greek` feature on a `no-claim` entry lets the next audit test it.
   - A team decision (`method: team-decision`) is never changed: report the verdict to the user instead.
4. **Check the store:** `python3 scripts/language_profile.py check export/<project>/profile --project <project>`.
5. **Measure again:** the same `check` and `try` as in step 1, then `audit` on the entries changed. Report the
   figures before and after (tokens split, types rebuilt, the changed entries' odds ratios and verdicts).
6. **Rebuild what depends on the store:** the alignment by parts (`python3 scripts/align.py <project>`, where
   `analysis.align` is `parts` or `parts+fill`), the units (`python3 scripts/build_units.py <project>`), the model
   text (`python3 scripts/nllb/model_text.py <project> check`, if the project uses it), the wiki's store blocks
   (`python3 scripts/wiki.py sync <project>`), and the verse packs of the chapters still to draft (they are built per
   chapter by `verse_pack.py`).
7. `python3 scripts/check_project.py <project>`. Don't commit; the user commits.
