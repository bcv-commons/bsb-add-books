"""The second-draft model's source text: a source edition (default: Vamvas, modern Greek, import/CC0/ell/vamvas/) or
the project's assisting translation (`bsb`: the BSB/MSB English). The project picks it with `nllb_source` in
project.yaml; data.py, draft.py and train.py read it from here, and data.py writes it into meta.json, so a model always
drafts from the source it was trained on.

A source edition names its NLLB language code (`nllb_code` in its edition.yaml, e.g. ell_Grek) and has its text in the
original's numbering (the Hebrew verses in the OT), like every edition. Its quotation marks and dashes are made plain
(« » “ ” -> ", ‘ ’ -> ', — -> " - ", – -> -), as in the data the Greek route was tested on.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import langtools as LT  # noqa: E402
import vrs  # noqa: E402
from books import BY_CODE  # noqa: E402
from project import edition, missing_text  # noqa: E402

DEFAULT = "vamvas"
BSB = "bsb"


def plain(t):
    t = t.replace("«", '"').replace("»", '"').replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return re.sub(r"\s+", " ", t.replace("—", " - ").replace("–", "-")).strip()


class Source:
    """verse(code, c, v) -> the source text of a verse in the original's numbering ('' if the source lacks it)."""

    def __init__(self, P, name=None):
        self.P = P
        self.name = name or P.p.get("nllb_source") or DEFAULT
        self._files = {}
        if self.name == BSB:
            self.code, self.label = "eng_Latn", "the assisting translation (English)"
            return
        ed = edition(self.name)
        if not ed.get("nllb_code"):
            raise SystemExit(f"nllb_source {self.name}: its edition.yaml has no nllb_code (the NLLB language code, e.g. ell_Grek)")
        how = missing_text(self.name)
        if how:
            raise SystemExit(f"nllb_source {self.name}: its text is not here; get it with: {how}")
        self.code, self.label = ed["nllb_code"], ed.get("credit") or ed.get("name") or self.name
        self.dir = os.path.join(ROOT, ed["dir"], ed.get("text_dir", "text"))

    def verse(self, code, c, v):
        if self.name == BSB:
            bc, bv = vrs.to_bsb(code, c, v) if BY_CODE[code][2] != "nt" else (c, v)
            f = os.path.join(ROOT, self.P.assist_dir(code), f"{code}{bc:03d}.txt")
            if f not in self._files:
                self._files[f] = LT.verses_of(f) if os.path.exists(f) else {}
            return " ".join(self._files[f].get((bc, bv), "").split())
        for f in (f"{code}.txt", f"{code}{c:03d}.txt"):
            p = os.path.join(self.dir, f)
            if p not in self._files:
                self._files[p] = LT.verses_of(p) if os.path.exists(p) else {}
            if (c, v) in self._files[p]:
                return plain(self._files[p][(c, v)])
        return ""
