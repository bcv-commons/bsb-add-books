# Josvabogen – oversigt for reviewer

Eksempel med ét kapitel: Jos 16. Status: **Udkast** (maskinudkast fra grundteksten; ingen eksegetisk bearbejdning
eller litterært tjek). Punkterne nedenfor er de beslutninger for hele bogen som kapitel 16 berører.

## Filer

| Kap. | Vers | Udkast | Noter | Inline-noter (E·T·H·N) |
|---|---|---|---|---|
| 16 | 10 | `jos016.txt` | `jos016_notes.md` | 4·5·2·0 |

Fælles: `jos_style_guide.md` (faste gengivelser, filhoved, notekonventioner, translitterationsregler for stednavne).
Maskinelt tjekket: hvert vers præcis én gang, balancerede `{}` og `>>…<<`, brødtekst ≤ 100-105 tegn pr. linje, ens filhoved.

## Harmoniseringer

- 16,10 følger `import/CC0/dan/den-frie-bibel/text/jdg001.txt` v29 næsten ordret (»fordrev ikke kana'anæerne som boede
  i Gezer«, »midt iblandt«).

## Åbne harmoniseringspunkter på tværs af kapitler (reviewer bør afgøre)

1. **Sluttende ח i navne** – kap. 16 dropper det (»Tappua«, »Janoa«) efter mønsteret »Zera, Jefta, Kora, Noa« i `import/CC0/dan/den-frie-bibel/text/` og stilarket. Bekræft reglen for hele bogen.
2. **Betel/Luz (16,2; 18,13)** – MT skelner (»fra Betel til Luz«), LXX identificerer; udkastet følger LXX med MT i `{T:}`. Bør harmoniseres med kap. 18.
3. **מַס־עֹבֵד** – »tvangsarbejde« (16,10; 17,13) vs »trællearbejde« (`import/CC0/dan/den-frie-bibel/text/jdg001.txt` v28.30.33.35). Ét valg.
4. **Nye navneformer** – `jos016_notes.md` har et afsnit »Nye navneformer« (Atarot-Addar, Mikmetat, Ta'anat-Shilo, Na'ara, Kana-bækken …); de bør godkendes samlet med resten af bogens.
5. **Apostrof i navne** – udkastene bruger lige `'` (»Kana'an«, »Ta'anat-Shilo«, »Na'ara«); `import/CC0/dan/den-frie-bibel/text/` blander typografisk `’` (29×) og lige `'` (8×). Én global beslutning for `export/dan/dan_BSB/` (kan rettes maskinelt).
6. **Tekstkritik nævnt i noterne, ikke i teksten** – udkastene følger MT, undtagen hvor `{T:}` siger andet (16,2: LXX).

## Anbefalet læserækkefølge for reviewer

1. `jos_style_guide.md` → 2. `jos016.txt` med `jos016_notes.md` → 3. denne fils punkter.
