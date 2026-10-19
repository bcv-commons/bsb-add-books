# import/CC-ND/: editions under a Creative Commons licence with ND

For editions whose licence allows sharing the text unchanged but no adaptations: CC BY-ND, CC BY-NC-ND, and the same
with SA added. An NC-ND edition belongs here, not in `CC-NC/` (ND is the stricter condition).

- **The texts are not in git**, only each edition's `edition.yaml`, README, build scripts, `.gitignore` and
  `fetch.lock.json` (as for `non-free/`; `import/README.md`).
- **Style use is as for a non-free edition:** books it has are drafted in quarantine, and quotations follow the limits
  in `docs/licensing.md`. Our independent drafts, the store, the wiki and statistics are ours and CC0.
- **Derived work** (a revision, a draft made with the edition's book in view, a file in its own structure) goes only to
  a project under `local_output/`, never to `export/`, and only with the approval of the rights holder or the translation team in the
  edition's `edition.yaml` (`derived_work: {approved_by, date, form, for, returned_to}`). It is returned to them; we never
  publish it (`docs/licensing.md`, *Three output paths*). `scripts/project.py` enforces this.
