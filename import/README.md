# import/: existing editions, filed by licence

Each edition is a folder `import/<licence>/<language>/<edition>/` with `edition.yaml` and the
texts in `text/` (start from `_template/`). The licence folder decides whether the
edition can be published with this repository:

| Folder | For | In git |
|---|---|---|
| `CC0/` | public domain and CC0 editions | yes, except a text that is fetched or synced (below) |
| `CC-BY/` | CC BY editions (attribution required, no further conditions) | yes, except a text that is fetched or synced |
| `CC-BY-SA/` | CC BY-SA editions (attribution, and derivatives under the same licence) | yes, except a text that is fetched or synced |
| `CC-ND/` | any CC licence with ND (BY-ND, BY-NC-ND, also with SA added): shareable unchanged, no adaptations | the text **no**; `edition.yaml` and README yes |
| `CC-NC/` | CC licences with NC and without ND (BY-NC, BY-NC-SA) | the text **no**; `edition.yaml` and README yes |
| `non-free/` | everything else: all rights reserved, unclear, other licences, permission for private use only | the text **no** (git-ignored); `edition.yaml` and README yes |

- **A text that can be fetched from a URL is never in git**, in any licence folder: only its
  `edition.yaml` (with the recipe or `get_text`), `fetch.lock.json` or the sync script's record, and
  the edition's `.gitignore` are, and every clone fetches the same pinned text. Only a text copied in by
  hand, with no source to fetch it from, is kept in git, and only in an open folder.
- **What is kept local is the text, not what we learn from it.** For every edition, non-free
  ones included, the drafts, wiki, store and statistics made from it are ours (CC0), and short
  quotations with its `credit` line may be published (`docs/licensing.md`).
- **What the folder means for derived work** (a revision, a draft made with the edition's book in view, a file in its
  own structure: `docs/licensing.md`, *Three output paths*): `CC-ND/` and `non-free/` editions only in `local_output/`,
  with the rights holder's approval recorded in `edition.yaml` (`derived_work:`); `CC-NC/` editions also in
  `export/CC-NC/`; open editions anywhere their licence allows. For quarantine and quotations, `CC-ND/` and `CC-NC/`
  editions count as non-free, as before. An NC-ND edition goes to `CC-ND/` (ND wins).
- **When in doubt, `non-free/`.** An edition moves to `CC0/`, `CC-BY/` or `CC-BY-SA/` only
  with its licence checked and recorded in `edition.yaml` (`source`, `licence`, and for
  CC BY and CC BY-SA `attribution`). Every edition that is quoted has a `credit` line, and a
  working copy newer than the published edition names the published text (`published_text`).
- **Only these licence folders for now.** An edition under any other licence, even an
  open one, goes to `non-free/` until a folder for it is agreed.
- **Language folders:** inside each licence folder, one folder per language, named by its
  ISO 639-3 code (`dan`, `deu`, `eng`). Dialects have no ISO 639-3 code of their own; how
  to name them is still open, and `ch-de-be` (Bern German) is an interim id. The precise
  language tag goes into `edition.yaml` (`language: da`, `language: gsw-BE`).
- **Edition ids are unique** across the folders: projects name an edition by its id
  alone (`based_on: <edition>`), and `scripts/project.py` finds its folder.
- **Three ways to bring an edition in** (for a new language, `python3 scripts/onboard.py` does the first for you):
  - **fetched** from a Bible source by a recipe (`fetch:` in `edition.yaml`): helloAO and
    openbible through the bcv-commons/bibles catalogue, or eBible.
    `python3 scripts/fetch_edition.py --find <iso>` lists what exists, with licences;
    `python3 scripts/fetch_edition.py <edition>` fetches it into `text/`. The recipe and
    `fetch.lock.json` (source version, a SHA-256 per file) are in git, the text isn't;
  - **synced from its own source** (e.g. one GitHub repository) by a script in the edition
    folder, `sync_from_upstream.py`: it copies the files from the commit pinned in the edition (`--latest` or `--commit`
    moves the pin), reports what changed, and writes the commit and the coverage or checksums into the
    edition's `README.md` (and `edition.yaml`). The synced files are git-ignored by the
    edition's `.gitignore`; the script, `edition.yaml` and `README.md` are in git
    (`CC0/dan/den-frie-bibel/`, `CC0/dan/dan-1871-1907/`);
  - **copied in by hand**, with a `README.md` that says where from.
- **Quarantined books** are removed from `text/` before drafting (`docs/workflow.md`).
