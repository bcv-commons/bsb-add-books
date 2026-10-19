# import/CC-BY/

Editions under CC BY (any version, no SA/NC/ND conditions). They are kept in git, with
their attribution.

Record in `edition.yaml`: `source`, `licence` (for example `CC BY 4.0`, with a link)
and `attribution` (the credit line the licence asks for). Keep any licence or credit
file of the edition next to `text/`.

A CC BY edition can be used as a style corpus or continued with new books. It can't be
revised into `export/`: a revision is a derivative of it and would carry its licence,
while `export/` is public domain (`scripts/project.py` refuses it).
