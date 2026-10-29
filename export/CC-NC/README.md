# export/CC-NC/: work derived from non-commercial editions

Unlike the rest of `export/`, the work here is **not** CC0. Each project in `export/CC-NC/<language>/<project-id>/` is
derived from editions in `import/CC-NC/` (CC BY-NC, CC BY-NC-SA) or from open ones, and carries their licence:
**CC BY-NC 4.0**, or **CC BY-NC-SA 4.0** where an edition it is derived from is share-alike, with the editions' credit
lines in the project's `CREDITS.md`. Use it non-commercially only.

- A project here lists the editions it is derived from in `derived_from` (`project.yaml`); `scripts/project.py`
  refuses any that is CC-ND or non-free: their derived work goes to `local_output/` (`docs/licensing.md`, *Three
  output paths*).
- The website does not show these projects yet.
- The project id includes the folder: `python3 scripts/project.py CC-NC/<language>/<project-id>`.
