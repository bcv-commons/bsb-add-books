# Den Frie Bibel

The Danish text of [Den Frie Bibel](https://denfriebibel.dk) (public domain). The text (`text/`,
`sfm/`) is synced from its source by `sync_from_upstream.py` and git-ignored (`.gitignore` here);
this README, `edition.yaml` and the script are in git.

**Source.** Den Frie Bibel's own repository, [EzerIT/DFB](https://github.com/EzerIT/DFB), folder
`tekst/`, renamed from Den Frie Bibel's Danish book stems to the BSB codes (`1mos` → `gen`,
`matt` → `mat`, `sl` → `psa`, `åb` → `rev` …), content unchanged:

- Commit: `9c44026e060b9a6c29c4c25d5dafd9a9d46f7296` (2026-10-08, "Opdateret Klagesangene")
- Synced: 2026-10-13, 726 chapter files

Not copied: the OSIS files of the 1871/1907 authorised version, the Hebrew/Aramaic text in `tekst/orig/` (not public domain),
`translators.txt` (e-mail addresses; the translators are named in `edition.yaml` and in each
file's header).

**To get the text:** `python3 import/CC0/dan/den-frie-bibel/sync_from_upstream.py` fetches the commit
pinned below (and in `edition.yaml`), so a clone gets the corpus the project was built with.
**To update:** `--latest` syncs with the latest commit of EzerIT/DFB (`--check` only reports,
`--commit <sha>` takes a given commit) and writes the new commit and the book coverage into this file
and `edition.yaml`. Review with `git diff`, then commit.

**`sfm/`: the books in USFM.** Den Frie Bibel writes some books directly in USFM, in its own
`sfm/` folder next to `tekst/`; they are not in `tekst/`. The sync copies them unchanged into
`sfm/` here: one `.SFM` file per book with all its chapters (chapters not yet translated are
empty, only markers), and a `.cre` file with the credits of each finished chapter.

It also converts the chapters Den Frie Bibel publishes (its `oversigt.inc.php`) into `text/`
(`gen001.txt` …), so they sit with the rest: parsed with `usfmtc` as bcv-commons/bibles does
(`scripts/usfm_usj.py`; `pip install usfmtc`) and rendered like the other files, with the `.cre`
credits as header lines, footnotes as `{T: …}` and cross references as `{H: …}`. Den Frie Bibel's
own `\zei` markers (numbers in the running text) are left out of `text/`; they stay in `sfm/`.
Chapters with text that Den Frie Bibel doesn't publish yet (Genesis 20–25) are not converted.

<!-- sfm -->
| file | book | chapters | with text | published by Den Frie Bibel |
|---|---|---|---|---|
| `01GENDFB.SFM` | Gen | 50 | 1–25, 28 | 1–19, 28 |
| `111KIDFB.SFM` | 1 Kgs | 22 | 1–11 | 1–11 |
<!-- /sfm -->

**Licence.** "Intet dansk indhold i Den Frie Bibel er belagt med ophavsret" (denfriebibel.dk,
Ophavsret); the repository's LICENSE says the Danish text in `tekst/` is in the public domain.
The name "Den Frie Bibel" is a trademark and may not be used for modified texts.
