"""Build orig/heb/<code>NNN.txt from the shoresh scaffold API (bcv-commons/bcv-query):
MACULA Hebrew (CC BY 4.0) syntax over the UHB text (CC BY-SA 4.0), no NC data.

Same layout as the BHSA-based files (build_heb_bhsa.py): first line '<code> <chapter>',
then one line per clause segment as 'verse:indent text' (Hebrew verse numbering).

- A line is a maximal run of words that belong to the same clause in the same
  verse. Words, not tokens: a prefix (וְ, בְּ, לְ, הַ …) glued to the next token
  goes with that token's clause (MACULA sometimes puts e.g. the ל of an
  infinitive into the higher clause).
- indent = depth of the clause in the MACULA clause tree ('parent' chain).
  MACULA's tree only reaches up to the sentence; BHSA's 'tab' also encodes
  how clauses hang together across sentences, so this layout is flatter.

Raw API responses are cached in download/scaffold/<BOOK>/<chapter>.json.

Usage: python3 scripts/fetch_heb_macula.py rut            # whole book
       python3 scripts/fetch_heb_macula.py rut:1 gen:31-32  # chapters
       options: --base URL (default https://shoresh.qombi.com), --out DIR (default orig/heb)
"""
import json, os, sys, time, urllib.request
from books import BY_CODE, ROOT, heb_chapters

BASE = "https://shoresh.qombi.com"


def fetch(book, ch, base):
    cache = os.path.join(ROOT, "download", "scaffold", book, f"{ch}.json")
    if os.path.exists(cache):
        return json.load(open(cache, encoding="utf-8"))
    # the server rejects Python's default User-Agent with 403
    req = urllib.request.Request(f"{base}/scaffold/{book}/{ch}", headers={"User-Agent": "make-tanakh/1.0"})
    data = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except Exception as e:  # a cold server cache can time out or truncate
            if attempt == 2:
                raise
            print(f"  retry {book} {ch}: {e}")
            time.sleep(5)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(data, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return data


def layout(code, ch, data):
    clauses = data["clauses"]

    def depth(c):
        n = 0
        while c is not None and clauses.get(str(c), {}).get("parent") is not None:
            c = clauses[str(c)]["parent"]
            n += 1
        return n

    # tokens -> words: tokens with an empty trailer are glued to the next token
    words, cur = [], []
    for t in data["tokens"]:
        cur.append(t)
        if t.get("trailer"):
            words.append(cur)
            cur = []
    if cur:
        words.append(cur)

    lines = []
    for w in words:
        verse, clause = w[-1]["verse"], w[-1]["clause"]
        trailer = w[-1]["trailer"]
        text = "".join(t["text"] + (t["trailer"] or "") for t in w[:-1]) + w[-1]["text"]
        text += " " if trailer in (" ", "׀") else trailer
        if trailer == "׀":
            text = text.rstrip() + " ׀ "
        if lines and lines[-1][0] == verse and lines[-1][1] == clause:
            lines[-1][2] += text
        else:
            lines.append([verse, clause, text])
    out = [f"{code} {ch}"] + [f"{v}:{depth(c)} {t.strip()} " for v, c, t in lines]
    return "\n".join(out) + "\n"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else BASE
    out_dir = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(ROOT, "orig", "heb")
    args = [a for a in args if a not in (base, out_dir)]
    os.makedirs(out_dir, exist_ok=True)
    for arg in args:
        code, _, rng = arg.partition(":")
        if BY_CODE[code][2] != "ot":
            raise SystemExit(f"{code} is not an OT book")
        a, _, b = rng.partition("-")
        first = int(a) if a else 1
        last = int(b) if b else (first if a else heb_chapters(code))
        for ch in range(first, last + 1):
            data = fetch(code.upper(), ch, base)
            open(os.path.join(out_dir, f"{code}{ch:03d}.txt"), "w", encoding="utf-8").write(layout(code, ch, data))
            print(f"{code}{ch:03d}: {len(data['tokens'])} tokens, {len(data['clauses'])} clauses")


if __name__ == "__main__":
    main()
