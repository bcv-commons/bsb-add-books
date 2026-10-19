# The Danish authorised version (OT 1871, NT 1907)

Two OSIS files in `osis/`, which is git-ignored (see `.gitignore` here): only this note,
`edition.yaml` and the sync script are in git. To get or update the files:

```
python3 import/CC0/dan/dan-1871-1907/sync_from_upstream.py            # the pinned commit (below)
python3 import/CC0/dan/dan-1871-1907/sync_from_upstream.py --latest   # update to the latest commit
python3 import/CC0/dan/dan-1871-1907/sync_from_upstream.py --check    # only report
python3 import/CC0/dan/dan-1871-1907/sync_from_upstream.py --commit <sha>
```

The script copies the two files from the commit and writes the commit and their SHA-256 below.

**Source.** Den Frie Bibel keeps a corrected copy of Ulrik Sandborg-Petersen's OSIS files in
its repository [EzerIT/DFB](https://github.com/EzerIT/DFB), folder `tekst/`. It is the
maintained version: it fixes OCR errors and quotation marks of the originals in
[emg/Danish-Bible-OT-1871](https://github.com/emg/Danish-Bible-OT-1871) and
[emg/Danish-Bible-NT-1907](https://github.com/emg/Danish-Bible-NT-1907).

- Commit: `9c44026e060b9a6c29c4c25d5dafd9a9d46f7296` (2026-10-08, "Opdateret Klagesangene")
- Synced: 2026-10-13

Expected SHA-256:

```
d94a83a5ed94c6b85c7f3bbde79c84d2e97535c9cb448d6d16459051a4fbe366  DA_OT1871.OSIS.xml  (4,951,419 bytes; 39 books, 23,211 verses)
757bc41a165610e22c389fe6379b58ad6528da8e24b9195250ba7104cee1bfb1  DA_NT1907.OSIS.xml  (1,588,879 bytes; 27 books, 7,960 verses)
```

**Licence.** Public domain. The files say "This Old/New Testament is in the Public Domain",
and the repository's LICENSE says "The Danish Bible text in the tekst folder is in the public
domain." (The Hebrew/Aramaic text in the same repository is not public domain and is not used
here.)
