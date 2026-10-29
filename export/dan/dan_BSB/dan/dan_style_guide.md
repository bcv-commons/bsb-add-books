# Daniels Bog – arbejdsstilark for udkastene (`export/dan/dan_BSB/dan/danNNN.txt`)

Stand: 09.10.2026. Afledt af `export/dan/dan_BSB/gen/gen_style_guide.md` og `export/dan/dan_BSB/jos/jos_style_guide.md`; alle generelle regler derfra gælder (kun BSB som hjælp, husstil fra `import/CC0/dan/den-frie-bibel/text/`, inline-noter med samme tæthed, translitteration ʔ ʕ ᵊ, »v. 12« i noter).

## Grundtekst: hebraisk OG aramæisk

- `orig/heb/danNNN.txt` indeholder grundteksten. **Dan 2,4b-7,28 er aramæisk**, resten hebraisk. Oversæt fra den aktuelle sprogform.
- Ved overgangen 2,4 (*ʔărāmît*) sættes en `{T:}`: »Herfra og til 7,28 er teksten skrevet på aramæisk.« Ved 8,1 en `{T:}` om at teksten igen er hebraisk.
- Aramæiske ord translittereres efter samme principper (ʔ ʕ ᵊ).

## Versnummerering (vigtigt)

`orig/` følger den hebraiske/danske tælling, BSB den engelske:

| `orig/` (= dansk) | BSB |
|---|---|
| 3,31-33 | 4,1-3 |
| 4,1-34 | 4,4-37 |
| 6,1 | 5,31 |
| 6,2-29 | 6,1-28 |

Tæl altid efter `orig/`. Ved sammenligning med BSB skal man forskyde tilsvarende.

## Filhoved

```
!!<Modenhed: Udkast>!!
!!<Oversættelse: Maskinudkast fra grundteksten (orig/heb/danNNN.txt), sammenholdt med Berean Standard Bible>!!
!!<Eksegetisk bearbejdning: Endnu ikke sket>!!
!!<Litterært tjek: Endnu ikke sket>!!
!!<Dato for denne version: 09.10.2026>!!

===Daniels Bog, kapitel N===
```

## Navne og faste gengivelser (bindende)

Rækkefølge: husform i `import/CC0/dan/den-frie-bibel/text/` → tidligere Daniel-udkast (»Nye navneformer«) → Josva-reglerne.

| Grundtekst | Dansk | Belæg |
|---|---|---|
| נְבוּכַדְנֶאצַּר | Nebukadnesar | `import/CC0/dan/den-frie-bibel/text/` (29×) |
| בֵּלְשַׁאצַּר (kongen) / בֵּלְטְשַׁאצַּר (Daniel) | Belshassar / Beltshassar (kontrollér husform) | regel |
| דָּרְיָוֶשׁ, כּוֹרֶשׁ | Darius, Kyros | `import/CC0/dan/den-frie-bibel/text/` |
| דָּנִיֵּאל, חֲנַנְיָה, מִישָׁאֵל, עֲזַרְיָה | Daniel, Hananja, Mishael, Azarja | `import/CC0/dan/den-frie-bibel/text/` |
| שַׁדְרַךְ, מֵישַׁךְ, עֲבֵד נְגוֹ | Shadrak, Meshak, Abed-Nego | regel |
| גַּבְרִיאֵל, מִיכָאֵל | Gabriel, Mikael | `import/CC0/dan/den-frie-bibel/text/` |
| בָּבֶל, כַּשְׂדִּים | Babylon, kaldæerne | `import/CC0/dan/den-frie-bibel/text/` |
| מָדַי, פָּרַס, יָוָן | Medien, Persien, Grækenland (Javan i {T:}) | `import/CC0/dan/den-frie-bibel/text/` |
| שׁוּשַׁן, אוּלָי | Susa, Ulaj | regel |
| עַתִּיק יוֹמִין | den Gamle af dage | |
| כְּבַר אֱנָשׁ (7,13) | en som en menneskesøn (kontrollér NT-citater i `import/CC0/dan/den-frie-bibel/text/`, fx Matt 24,30; 26,64; Åb 1,13) | |
| שִׁקּוּץ מְשֹׁמֵם (9,27; 11,31; 12,11) | ødelæggelsens vederstyggelighed (kontrollér `import/CC0/dan/den-frie-bibel/text/mat024.txt` v15 / `mrk013.txt` v14) | NT-citat |

- **Poesi:** lovsange og hymner (2,20-23; 3,33; 4,31-32; 6,27-28; 7,9-10.13-14) med `//N`.
- **NT-citater** (`{H:}` kun ved direkte citat): 7,13 (Matt 24,30; 26,64), 9,27/11,31/12,11 (Matt 24,15; Mark 13,14), 12,2 (Joh 5,29), 12,1 (Matt 24,21).
