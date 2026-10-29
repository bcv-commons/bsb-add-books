# 1 Mosebog – arbejdsstilark for udkastene (`export/dan/dan_BSB/gen/genNNN.txt`)

Stand: 09.10.2026. Afledt af `export/dan/dan_BSB/jos/jos_style_guide.md`.

## Grundlag

- Der oversættes **fra hebraisk** (`orig/heb/genNNN.txt`, klausul-opdelt). Eneste hjælpeoversættelse er **BSB** (`reference/BSB/genNNN.txt`), som kun bruges til at afgøre valg hvor hebraisken tillader mere end én gengivelse.
- Én dansk version pr. kapitel (`genNNN.txt`) + `genNNN_notes.md`.
- Alle generelle konventioner gælder uændret fra `export/dan/dan_BSB/jos/jos_style_guide.md`: filhoved og layout, `==…==`-overskrifter i sætningsform, `vN` inline, `>>…<<`, HERREN med versaler, ca. 100 tegn pr. linje, tal (1-9 med bogstaver, 10 og derover med cifre), måleenheder + `{N: gt-mål}`, notesystemet (`{T:}`, 2-5 `{E:}` pr. kapitel, `{H:}`, `{N:}`), translitterationsregler for navne.
- Versnummerering: hebraisk/dansk som i `orig/`.

## Notetæthed og translitteration

- Som de færdige Mosebøger i `import/CC0/dan/den-frie-bibel/text/` (2 Mos: ca. 9 {T:}, 3 {E:}, 0,3 {H:} pr. kapitel):
  - `{T:}` kun hvor ordlyden ændrer betydningen eller bærer et genkendeligt billede/ordspil, ca. 5-10 pr. kapitel;
  - `{E:}` 2-4;
  - `{H:}` kun ved direkte NT-citater af verset, ca. 0-2.
- Alt andet hører hjemme i `_notes.md`.
- Translitteration som i `import/CC0/dan/den-frie-bibel/text/`: ʔ (alef), ʕ (ajin), ᵊ (shva), aldrig ʾ/ʿ.
- Versangivelser inde i noter skrives »v. 12«, aldrig »v12« (forbeholdt versmarkører).

## Fælles valg (bindende for alle kapitler)

- *hā-ʔādām* = »mennesket«; »Adam« kun hvor MT punkterer uden artikel (2,20; 3,17.21) og fra 4,25.
- *ʔădāmāh* = »agerjorden«, *ʔæræṣ* = »jorden«.
- »Gud HERREN« for יְהוָה אֱלֹהִים.
- Skabelsesformler som i kap. 1: »Det blev aften, og det blev morgen – … dag.« / »Og sådan skete det.« / »Gud så at det var godt.«
- Åbne punkter (pronomen for »mennesket«, »levende væsen« eller »levende sjæl« i 2,7 osv.): se `gen_review_overview.md`.

## Navne og faste gengivelser, kap. 4-20 (bindende, 09.10.2026)

Husformer fra `import/CC0/dan/den-frie-bibel/text/` går forud. Hvor `import/CC0/dan/den-frie-bibel/text/` ikke har navnet, gælder translitterationsreglerne i `export/dan/dan_BSB/jos/jos_style_guide.md` (š → sh, ḥ → h, ṣ → s, afsluttende ח udelades, ʔ/ʕ inde i ord → apostrof).

| Hebraisk | Dansk | Belæg |
|---|---|---|
| קַיִן, הֶבֶל, שֵׁת, אֱנוֹשׁ | Kain, Abel, Set, Enosh | `import/CC0/dan/den-frie-bibel/text/` (Kain, Abel, Sets) |
| קֵינָן, מַהֲלַלְאֵל, יֶרֶד, חֲנוֹךְ | Kenan, Mahalalel, Jered, Enok | Enok: `import/CC0/dan/den-frie-bibel/text/heb011.txt` |
| מְתוּשֶׁלַח, לֶמֶךְ, נֹחַ | Metushela, Lamek, Noa | Noa: `import/CC0/dan/den-frie-bibel/text/` (6×) |
| שֵׁם, חָם, יֶפֶת, כְּנַעַן | Sem, Ham, Jafet, Kana'an | Kana'an: `import/CC0/dan/den-frie-bibel/text/` |
| נִמְרֹד, בָּבֶל, אַשּׁוּר, נִינְוֵה, שִׁנְעָר | Nimrod, Babel, Assur, Ninive, **Sinear** | Babel, Ninive, Sinear: `import/CC0/dan/den-frie-bibel/text/` (husform går forud for translitterationsreglen) |
| אַרְפַּכְשַׁד, שֶׁלַח, עֵבֶר, פֶּלֶג | Arpaksad, Shela, Eber, Peleg | Eber: `import/CC0/dan/den-frie-bibel/text/` |
| תֶּרַח, נָחוֹר, הָרָן (bror), חָרָן (by) | Tera, Nahor, **Haran** (bror), **Karan** (byen) | Karan: `import/CC0/dan/den-frie-bibel/text/isa037.txt` |
| אוּר כַּשְׂדִּים | Ur i Kaldæa | Kaldæa: `import/CC0/dan/den-frie-bibel/text/` |
| אַבְרָם → אַבְרָהָם (17,5), שָׂרַי → שָׂרָה (17,15) | Abram → Abraham, Saraj → Sara | Abraham, Sara: `import/CC0/dan/den-frie-bibel/text/` |
| יִצְחָק, יִשְׁמָעֵאל, הָגָר, לוֹט | Isak, Ismael, Hagar, Lot | `import/CC0/dan/den-frie-bibel/text/` |
| מַלְכִּי־צֶדֶק, שָׁלֵם, אֵל עֶלְיוֹן | Melkisedek, Salem, Gud den Højeste | `import/CC0/dan/den-frie-bibel/text/` (Hebr 7) |
| סְדֹם, עֲמֹרָה, צֹעַר | Sodoma, Gomorra, Soar | Sodoma, Gomorra: `import/CC0/dan/den-frie-bibel/text/` |
| מוֹאָב, בֶּן־עַמִּי / עַמּוֹן | Moab, Ben-Ammi / Ammon | `import/CC0/dan/den-frie-bibel/text/` |
| פַּרְעֹה, מִצְרַיִם | Farao, Egypten | `import/CC0/dan/den-frie-bibel/text/` |
| אֲבִימֶלֶךְ, גְּרָר, קָדֵשׁ | Abimelek, Gerar, Kadesh | `import/CC0/dan/den-frie-bibel/text/` |
| חֶבְרוֹן, מַמְרֵא, בֵּית־אֵל, שְׁכֶם | Hebron, Mamre, Betel, Sikem | `import/CC0/dan/den-frie-bibel/text/` |
| אֵלוֹן / אֵלֹנֵי | eg / ege (»Mores eg«, »Mamres ege«) | `import/CC0/dan/den-frie-bibel/text/jdg009.txt` v6.37 »egen«; Josva-udkast 19,33 |
| מַבּוּל, תֵּבָה | syndfloden, arken | |
| בְּרִית / כָּרַת בְּרִית / הֵקִים בְּרִית | pagt / slutte en pagt / oprette en pagt | jf. Josva-stilarket |
| מוּל / עָרְלָה | omskære / forhud | |
| אֵל שַׁדַּי | Gud den Almægtige (kontrollér husform i `import/CC0/dan/den-frie-bibel/text/`) | |
| מַלְאַךְ יְהוָה | HERRENS engel | |

- **NT-citater i disse kapitler** (`{H:}` og tekstnær gengivelse, se `import/CC0/dan/den-frie-bibel/text/`): 12,3 (Gal 3,8); 15,5 (Rom 4,18); 15,6 (Rom 4,3; Gal 3,6; Jak 2,23); 17,5 (Rom 4,17); 18,10.14 (Rom 9,9); 21-tal ikke med her.
- **Slægtsregistre (kap. 5, 11):** én fast formel gennem hele registret; tal med cifre fra 10 (»130 år«, »930 år«).

## Navne og faste gengivelser, kap. 21-50 (bindende, 09.10.2026)

Rækkefølge for navneformer: 1) husform i `import/CC0/dan/den-frie-bibel/text/`; 2) form allerede brugt i et tidligere 1 Mos-udkast (se »Nye navneformer« i `genNNN_notes.md`); 3) Josva-reglerne.

| Hebraisk | Dansk | Belæg |
|---|---|---|
| יִצְחָק, רִבְקָה, יַעֲקֹב, עֵשָׂו, אֱדוֹם, לָבָן, לֵאָה, רָחֵל | Isak, Rebekka, Jakob, Esau, Edom, Laban, Lea, Rakel | `import/CC0/dan/den-frie-bibel/text/` |
| Jakobs sønner | Ruben, Simeon, Levi, Juda, Dan, Naftali, Gad, Asher, Issakar, Zebulon, Josef, Benjamin; Dina | `import/CC0/dan/den-frie-bibel/text/` |
| בִּלְהָה, זִלְפָּה | Bilha, **Zilpa** (ז → z, som Zebulon) | regel |
| תָּמָר, פֶּרֶץ, זֶרַח, עֵר, אוֹנָן, שֵׁלָה | Tamar, Peres, Zera, Er, Onan, Shela | Peres, Zera: `import/CC0/dan/den-frie-bibel/text/` |
| אֶפְרַיִם, מְנַשֶּׁה | Efraim, Manasse | `import/CC0/dan/den-frie-bibel/text/` |
| גֹּשֶׁן, פְּנוּאֵל/פְּנִיאֵל, סֻכּוֹת, יַבֹּק, מִדְיָן | Goshen, Penuel/Peniel, Sukkot, Jabbok, Midjan | `import/CC0/dan/den-frie-bibel/text/` |
| בְּאֵר שֶׁבַע | Be'ersheba (kontrollér husform i `import/CC0/dan/den-frie-bibel/text/`/Josva-udkast) | |
| פַּדַּן אֲרָם | Paddan-Aram | regel |
| מַכְפֵּלָה, עֶפְרוֹן, חִתִּי | Makpela, Efron, hittitten | regel/Josva |
| יִשְׂרָאֵל (32,29) | Israel, med {T:} om navnet | `import/CC0/dan/den-frie-bibel/text/` |

- **Versnummerering:** `orig/` følger den hebraiske tælling. I 1 Mos 31-32 afviger BSB (BSB 31,55 = hebr. 32,1; BSB 32,1-32 = hebr. 32,2-33). Tæl altid efter `orig/`.
- **Poesi:** Jakobs velsignelse (kap. 49) og andre digte (27,27-29.39-40; 48,15-16) sættes med `//N` som i `import/CC0/dan/den-frie-bibel/text/`.
- **NT-citater i kap. 21-50** (tekstnær gengivelse + `{H:}` kun ved direkte citat): 21,10 (Gal 4,30), 21,12 (Rom 9,7; Hebr 11,18), 22,16-18 (Hebr 6,13-14; Apg 3,25), 25,23 (Rom 9,12), 47,31 (Hebr 11,21).

## Filhoved

```
!!<Modenhed: Udkast>!!
!!<Oversættelse: Maskinudkast fra grundteksten (orig/heb/genNNN.txt), sammenholdt med Berean Standard Bible>!!
!!<Eksegetisk bearbejdning: Endnu ikke sket>!!
!!<Litterært tjek: Endnu ikke sket>!!
!!<Dato for denne version: 09.10.2026>!!

===1 Mosebog, kapitel N===
```

## Genesis-gengivelser (belæg fra `import/CC0/dan/den-frie-bibel/text/`)

| Hebraisk | Dansk | Belæg / begrundelse |
|---|---|---|
| יהוה | HERREN | husstil |
| אֱלֹהִים | Gud | |
| יְהוָה אֱלֹהִים (2,4-3,23) | Gud HERREN | `import/CC0/dan/den-frie-bibel/text/isa042.txt` v5 »Gud HERREN, der var skaber af himlene«; `job042` |
| בָּרָא / עָשָׂה | skabe / gøre | skabe kun for *bārāʾ* |
| תְּהוֹם | urdybet | `import/CC0/dan/den-frie-bibel/text/psa104.txt` v6 »urdybet« |
| רָקִיעַ | hvælving(en) | `import/CC0/dan/den-frie-bibel/text/isa040.txt`-note »himmelhvælvingen i 1 Mos 1,6-8«, `job022` |
| וַיְהִי־עֶרֶב וַיְהִי־בֹקֶר | Det blev aften, og det blev morgen | fast formel, ens alle seks gange |
| וַיְהִי־כֵן | Og sådan skete det | fast formel |
| נֶפֶשׁ חַיָּה | levende væsen(er) | |
| צֶלֶם / דְּמוּת | billede / lighed | |
| זָכָר וּנְקֵבָה | som mand og kvinde | `import/CC0/dan/den-frie-bibel/text/mat019.txt` v4; `mrk010.txt` v6 |
| 2,24 | følg `import/CC0/dan/den-frie-bibel/text/mat019.txt` v5 / `mrk010.txt` v7 | NT-citat |
| 2,2-3 (hvile) | følg `import/CC0/dan/den-frie-bibel/text/heb004.txt` v4 | NT-citat |
| 2,7 (levende sjæl) | sammenhold med `import/CC0/dan/den-frie-bibel/text/1co015.txt` v45 | NT-citat |
| עֵץ הַחַיִּים | livets træ | `import/CC0/dan/den-frie-bibel/text/rev002.txt`, `rev022.txt` |
| כְּרֻבִים | keruberne | `import/CC0/dan/den-frie-bibel/text/psa099.txt`, `jer021.txt` |
| נָחָשׁ | slangen | `import/CC0/dan/den-frie-bibel/text/rev012.txt` |
| אָדָם / הָאָדָם | mennesket; egennavnet »Adam« først hvor MT er uden artikel (afgøres i noterne) | |

Disse er forslag; hvert kapitels noter dokumenterer de valg der faktisk træffes, og fælles beslutninger samles i `gen_review_overview.md`.
