# Josvabogen – arbejdsstilark for udkastene (`export/dan/dan_BSB/jos/josNNN_*.txt`)

Formålet er at holde alle kapitler ensartede med hinanden **og** med de allerede oversatte kapitler under `import/CC0/dan/den-frie-bibel/text/`.
Konventionerne er aflæst af `import/CC0/dan/den-frie-bibel/text/` (især `jdg001-021`, `2mos*`, `4mos*`, `rut001-004`).

## Filer pr. kapitel

- `export/dan/dan_BSB/jos/josNNN.txt` – oversat fra `orig/heb/josNNN.txt`, sammenholdt med `reference/BSB/josNNN.txt`
- `export/dan/dan_BSB/jos/josNNN_notes.md` – reviewer-noter (afvigelsestabel, eksegetiske observationer, åbne spørgsmål)

Hjælpeteksten (BSB) bruges kun til at afgøre valg hvor hebraisken tillader mere end én gengivelse – der oversættes **fra hebraisk**, ikke fra den.

## Filhoved og layout

```
!!<Modenhed: Udkast>!!
!!<Oversættelse: Maskinudkast fra grundteksten (orig/heb/josNNN.txt), sammenholdt med Svenska Kärnbibeln>!!   ← eller: Berean Standard Bible
!!<Eksegetisk bearbejdning: Endnu ikke sket>!!
!!<Litterært tjek: Endnu ikke sket>!!
!!<Dato for denne version: 17.08.2026>!!

===Josvabogen, kapitel N===


==Overskrift i sætningsform==

v1 Løbende prosa med versmarkører inline … v2 … linjer ombrydes ved ca. 100 tegn (som jdg001.txt).

==Næste afsnit==
```

- Overskrifter (`==…==`) er redaktionelle indholdsresuméer, gerne i sætningsform (»Juda indtager Hebron og Debir«).
- Prosa: sammenhængende afsnit, tom linje mellem afsnit. Poesi (Jos 10,12-13) sættes med `//N`-linjer som i Salmerne/Ruth.
- Citater: `>>…<<`. Indlejret citat i citat: også `>>…<<` (husstil) eller kolon uden ekstra tegn ved korte indre citater.
- Inkvit kan sættes midt i replikken: `>>Det skal Juda,<< svarede HERREN. >>Se, …<<`

## Faste gengivelser

| Hebraisk | Dansk |
|---|---|
| יהוה | HERREN (HERRENS) |
| אלהים | Gud |
| בני ישראל | israelitterne |
| יהושע בן־נון | Josva, Nuns søn |
| משה עבד יהוה | HERRENS tjener Moses |
| ארון ברית יהוה | HERRENS pagts ark |
| ארון הברית / ארון | pagtens ark / arken |
| הכהנים הלוים | levitpræsterne |
| חרם (verbum) | lægge band på |
| חרם (nomen) | det der er lagt band på / bandet |
| שופר / שופרות היובלים | vædderhorn |
| ים־סוף | Sivhavet |
| הים הגדול | Det Store Hav |
| ים המלח | Salthavet |
| הערבה | Araba(-sletten) |
| הנגב | Negev / sydlandet (begge belagt; brug »sydlandet« i geografiske opremsninger som Dom 1) |
| השפלה | lavlandet |
| ההר | bjerglandet |
| כנעני, אמרי, חתי, חוי, פרזי, יבוסי, גרגשי | kana'anæerne, amoritterne, hittitterne, hivvitterne, perizzitterne, jebusitterne, girgashitterne (små bogstaver, dobbelt-t) |
| שטים | Shittim |
| העי | Aj |
| עכן / עמק עכור | Akan / Akors dal |
| גלגל, גבעון, יריחו, רחב, מקדה, לכיש, עגלון, לבנה, חברון, דבר, עזקה, ירמות, כפירה, בארות, קרית יערים, בית־און, בית־אל, בית־חורון, אילון, אדני־צדק, גזר, קדש, עזה, גשן | Gilgal, Gibeon, Jeriko, Rahab, Makkeda, Lakish, Eglon, Libna, Hebron, Debir, Azeka, Jarmut, Kefira, Be'erot, Kirjat-Jearim, Bet-Aven, Betel, Bet-Horon, Ajjalon, Adoni-Sedek, Gezer, Kadesh, Gaza, Goshen |
| ירדן | Jordan (uden »floden« medmindre nødvendigt) |
| מלאך / שר־צבא יהוה | HERRENS hærs fører (5,14) |
| חזק ואמץ | stærk og modig |
| תורה | lov / lovbog (jf. 8,31-34) |
| שטרים | ledere |
| הניח | give hvile |

## Stednavne og folkenavne (kap. 11-21 er navnetunge)

Translitterationsregler aflæst af `import/CC0/dan/den-frie-bibel/text/` (følg dem for navne der ikke står i tabellen ovenfor):

| Hebraisk | Dansk | Eksempler fra `import/CC0/dan/den-frie-bibel/text/` |
|---|---|---|
| שׁ | sh | Bashan, Ashdod, Bet-Shemesh, Shilo, Shittim, Kadesh, Ashtarot |
| שׂ / ס | s | Sikem, Sukkot, Sisera |
| צ | s | Sidon, Adoni-Sedek, Mispa (22×; ikke »Mizpa«), Sins ørken |
| ז | z | Azeka, Zins ørken, Gezer, Zera |
| ח | h | Hasor (4×; ikke »Hazor«), Hebron, Hermon, Heshbon |
| כ / ק | k | Kaleb, Kirjat-Jearim, Kadesh, Ekron, Karmel |
| ע / א inde i ord | ' (apostrof) | Se'ir, Ba'al, Be'erot, Jizre'el, Ta'anak, kana'anæerne |
| Sammensatte navne | bindestreg, begge led med stort | Kirjat-Arba, Kirjat-Sefer, Bet-Horon, Ba'al-Gad, En-Dor, Abel-Shittim, Kadesh-Barnea |
| Sluttende ח | udelades | Zera, Jefta, Kora, Noa → Tappua, Janoa, Sokó→Soko |
| בְּנֵי / בְּנוֹת som stednavn | »… og dens småbyer« for וּבְנֹתֶיהָ; »Anaks efterkommere« for בְּנֵי עֲנָק | »Anaks efterkommere« (3×) |
| Folkenavne | små bogstaver, -itter/-æere | filistrene, sidonierne, anakitterne, geshuritterne, ma'akatitterne, avvitterne, refaitterne, kenizzitten |
| מִדְבַּר צִן / סִין | Zins ørken / Sins ørken | (begge belagt) |
| הַר חֶרְמוֹן, הַר הֶחָלָק | Hermonbjerget, Halakbjerget (eller »Hermon«, »det nøgne bjerg«{T:}) | »Hermon« (5×) |
| בִּקְעַת הַלְּבָנוֹן | Libanondalen | |
| מֵי מֵרוֹם | Meroms vand | |
| יָם כִּנְרוֹת / כִּנֶּרֶת | Kinneretsøen / Kinneret | »Kinneret« (1×), »Genesaret« kun i NT |
| יָם הָעֲרָבָה יָם הַמֶּלַח | Arabahavet, Salthavet | (jf. kap. 3) |
| הַנֶּגֶב | sydlandet (i geografiske opremsninger), Negev (som egennavn) | |
| כָּלֵב בֶּן־יְפֻנֶּה הַקְּנִזִּי | Kaleb, kenizzitten Jefunnes søn | (1×, følg den) |
| בִּלְעָם בֶּן־בְּעוֹר | Bileam, Beors søn | (4×) |

- Kongelisten i kap. 12 og bylisterne i kap. 13, 15, 16 sættes som løbende prosa med `vN`-markører (ikke som tabel), som `import/CC0/dan/den-frie-bibel/text/num033.txt` gør med lejrlisten. Hvert navn behold sin form fra første forekomst i bogen; noter nye navneformer i `josNNN_notes.md` under et punkt »Nye navneformer« så de kan godkendes samlet.
- Danske gængse former (Jerusalem, Hebron, Betlehem, Jordan, Libanon, Egypten, Gilead, Efraim, Manasse, Juda, Ruben, Gad, Zebulon, Issakar, Asher, Naftali, Dan, Benjamin, Simeon, Levi) bruges uændret.

## Tal og mål

- 1-9 skrives med bogstaver (»tre dage«, »syv præster«, »syv gange«), 10 og derover med cifre (»12 mænd«, »30.000«, »2.000 alen«).
- Måleenheder gengives med hebraisk enhed + glossenote: »2.000 alen{N: gt-mål}«, »200 sekel{N: gt-mål}«. Noten sættes ved første forekomst i kapitlet.

## Noter

| Tag | Brug | Format |
|---|---|---|
| `{T: …}` | Oversættelsesnote: ordret gengivelse, alternativ, »dvs.« | `{T: Ordret: >>…<<.}` · `{T: Eller >>…<<.}` · `{T: Dvs. Middelhavet.}` |
| `{E: …}` | Eksegetisk note – **2-5 pr. kapitel**, forsigtige formuleringer (forslag, ikke afgørelser). Hebraisk translittereret i `*…*` | `{E: Verbet *hāgāh* betegner en halvhøj recitation, jf. Sl 1,2.}` |
| `{H: …}` | Krydshenvisning (NT-citater, klare indre henvisninger) | `{H: Hebr 13,5}` · `{H: 5 Mos 31,6-8}` |
| `{N: …}` | Kun eksisterende glosseopslag: `gt-mål`, `nåde`, `Sjæl`, `Ansigt`, `Hjerte`, `Hærskarers` | `{N: gt-mål}` |

Noten sættes umiddelbart efter det ord/tegn den vedrører, uden mellemrum: `fod,{T: …}` – som i `import/CC0/dan/den-frie-bibel/text/`.
Den fulde eksegetiske gennemgang lægges i `josNNN_notes.md`; inline-noterne skal være få.

## Notes-filen (`josNNN_notes.md`)

Skabelon (de ældre `jos0NN_notes.md` sammenligner også med et `_svk`-spor, som ikke findes her):

1. Hvad udkastene er (1-2 linjer)
2. Tabel: *Vers · Hebraisk · Dansk · BSB · Kommentar*
3. Eksegetiske observationer, nummereret, med versnummer og markering af om de er kandidater til `{E:}` / `{T:}` / `{H:}`
4. Konsistenspunkter mod `import/CC0/dan/den-frie-bibel/text/`
5. Åbne spørgsmål til reviewer
