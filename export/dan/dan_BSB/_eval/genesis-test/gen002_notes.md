# 1 Mosebog 2 – noter til udkastet `1mos002.txt`

Dato: 09.10.2026 · Status: **Udkast** (maskinudkast fra grundteksten, ingen eksegetisk bearbejdning eller litterært tjek endnu)

## Hvad udkastet er

- Oversat direkte fra den hebraiske tekst i `orig/1mos002.txt` (klausul-opdelt masoretisk tekst), sammenholdt med Berean Standard Bible (`BSB/gen002.txt`), som kun er brugt til at afgøre valg hvor hebraisken tillader mere end én gengivelse. Ingen SVK.
- Husstil som `tekst/dom004.txt` og `draft/dan/jos/jos001_BSB.txt`: `!!<…>!!`-hoved, `===1 Mosebog, kapitel 2===`, fire `==…==`-overskrifter (v1-3 / v4-14 / v15-17 / v18-25), `vN` inline, `>>…<<`, ca. 100 tegn pr. linje (målt i bytes, så `awk 'length > 105'` kun rammer hovedlinje 2). 2,23 er sat med `//N`-poesilinjer.
- Inline-noter: 5 `{E:}` (v2, v4, v15, v18, v25), 20 `{T:}`, 3 `{H:}` (v2, v7, v24), 1 `{N: Sjæl}` (v7).

## Bevidste valg

| Vers | Hebraisk | Dansk | BSB | Kommentar |
|---|---|---|---|---|
| 1 | וְכָל־צְבָאָם | med hele deres hærskare | in all their vast array | *ṣāḇāʔ* »hær«; `tekst/es024.txt` (»det højes hærskare«, note til 1 Mos 2,1) og `es034.txt` (»himlens vrimmel« + `{H: 1 Mos 2,1}`). `{T:}` med ordret »hær«. |
| 2-3 | מְלַאכְתּוֹ | (al) sin gerning | (all) His work | »gerning« valgt for at ramme ordlyden i `tekst/hebr004.txt` v4 (»hvilede på den syvende dag fra alle sine gerninger«). MT's gentagelse (»som han havde gjort« 2×) er bevaret. |
| 2 | וַיִּשְׁבֹּת | hvilede | rested | Som Hebr 4,4 og `tekst/2mos020.txt` v11. |
| 3 | וַיְקַדֵּשׁ | helligede | sanctified | Som `tekst/2mos020.txt` v11 »velsignede … og helligede den«. |
| 3 | אֲשֶׁר־בָּרָא אֱלֹהִים לַעֲשׂוֹת | den som Gud havde skabt og gjort | that He had accomplished | Ordret »som Gud skabte for at gøre«; `{T:}`. *bārāʔ* = »skabe« (stilarket). |
| 4 | אֵלֶּה תוֹלְדוֹת | Dette er beretningen om | This is the account of | `tekst/4mos003.txt` v1 har »slægtshistorie« for *tôlᵊdôt*; det passer dårligt til himmel og jord. `{E:}` om formlen. |
| 4 | יְהוָה אֱלֹהִים | Gud HERREN | the LORD God | Fast formel fra stilarket (`tekst/es042.txt` v5). Bruges alle 11 gange i kapitlet. |
| 4-5 | בְּיוֹם עֲשׂוֹת … וְכֹל שִׂיחַ | Dengang Gud HERREN gjorde jord og himmel, v5 fandtes der endnu … | in the day … v5 Now no shrub … | v4b er bisætning til v5 (som i MT); versgrænsen ligger derfor midt i perioden. |
| 5 | שִׂיחַ הַשָּׂדֶה / עֵשֶׂב הַשָּׂדֶה | markens busk / markens urt | shrub of the field / plant of the field | »markens urter« som `tekst/2mos009.txt`. |
| 5-22 | אֲדָמָה / אֶרֶץ | agerjorden / jorden | the ground / the earth | Konsekvent skel: *ʔădāmāh* = »agerjord« (jf. `tekst/es045.txt` »agerjorden{H: 1 Mos 2,7}«), *ʔereṣ* = »jord«. Bevarer ordspillet med *ʔādām* i v7. |
| 6 | אֵד | et væld | springs (alt. mist) | BSB's hovedtekst vippede valget; `{T:}` med »damp/tåge«. |
| 7 | נִשְׁמַת חַיִּים | livsånde | the breath of life | `{T: Ordret: >>livs åndedræt<<.}`. »livsånde« er belagt i `tekst/ez037.txt` (dog for *rûaḥ*). |
| 7 | לְנֶפֶשׁ חַיָּה | et levende væsen | a living being | Samme gengivelse som stilarkets *nepeš ḥayyāh* i kap. 1 og som 2,19. 1 Kor 15,45 (»levende sjæl«) angivet i `{T:}` + `{H:}`; `{N: Sjæl}` tilføjet. |
| 8 | מִקֶּדֶם | ude mod øst | in the east | `{T:}` om »fra gammel tid«. |
| 9 | עֵץ הַחַיִּים / עֵץ הַדַּעַת טוֹב וָרָע | livets træ / træet til kundskab om godt og ondt | tree of life / tree of the knowledge of good and evil | »livets træ« som `tekst/åb002.txt` v7, `åb022.txt` v2.14.19. |
| 10 | רָאשִׁים | hovedløb | headwaters | `{T: Ordret: >>fire hoveder<<.}` |
| 15 | לְעָבְדָהּ וּלְשָׁמְרָהּ | til at dyrke og vogte den | to cultivate and keep it | `{E:}` om levitparallellen (4 Mos 3,7-8). |
| 16 | אָכֹל תֹּאכֵל | må du frit spise | You may eat freely | `{T:}` om infinitivus absolutus. |
| 17 | מוֹת תָּמוּת | skal du sandelig dø | you will surely die | »sandelig … dø« som `tekst/4mos026.txt` v65. `{T: Ordret: >>dø skal du dø<<.}` |
| 18, 20 | עֵזֶר כְּנֶגְדּוֹ | en hjælper der svarer til ham | a suitable helper | `{T:}` (ordret) + `{E:}` (*ʕēzer* om Gud). |
| 19-20 | חַיַּת הַשָּׂדֶה | markens vilde dyr | beast of the field | Som `tekst/2mos023.txt` v11. |
| 20 | וּלְאָדָם | til Adam | for Adam | Første sted hvor MT er uden artikel → egennavn efter stilarkets regel; BSB gør det samme. `{T:}` med »mennesket«. Ellers overalt »mennesket« for *hāʔādām*; v5 *ʔādām ʔayin* = »intet menneske«. |
| 20 | לֹא־מָצָא | fandtes der ikke | no … was found | Upersonligt, som BSB. |
| 21 | תַּרְדֵּמָה | en dyb søvn | a deep sleep | Som `tekst/job004.txt` v13, `job033.txt` v15. |
| 21-22 | צֵלָע | ribben | rib | `{T:}` med »side«. |
| 22 | וַיִּבֶן | byggede han | He made | Ordret bevaret (»byggede … en kvinde«). |
| 23 | אִשָּׁה / אִישׁ | kvinde / manden | woman / man | `{T:}` om ordspillet. Poesi med `//1`/`//2`. |
| 24 | וְדָבַק בְּאִשְׁתּוֹ … לְבָשָׂר אֶחָד | holder sig til sin hustru, og de bliver ét kød | be united to his wife … one flesh | Ordlyd som `tekst/ef005.txt` v31 / `mark010.txt` v7-8, men uden »de to«, som ikke står i MT (`{T:}`). |
| 25 | וְלֹא יִתְבֹּשָׁשׁוּ | men de skammede sig ikke | they were not ashamed | Hitpolel evt. »skammede sig ikke over for hinanden«. |

## Eksegetiske observationer

1. **v1-3 afslutter 1,1-2,3** – Overskriften er sat før v1, så den syvende dag står som selvstændigt afsnit, mens kapitelgrænsen 1/2 (middelalderlig) bevares. Kandidat: ingen inline-note nødvendig. ({E:} muligt)
2. **v2 »den syvende dag«** – Samaritanus, LXX og Peshitta har »den sjette dag«. MT er lectio difficilior. **Sat som `{E:}`** sammen med *šābat*/*šabbāt*. `{H: Hebr 4,4}` sat.
3. **v3 *bārāʔ … laʕăśôt*** – »skabte for at gøre« = sammenfattende »hele skabelsesværket«. **Sat som `{T:}`.**
4. **v4 *ʔēlleh tôlᵊdôt*** – Første af de ti *tôlᵊdôt*-formler i 1 Mos. Diskussion om v4a hører til 1,1-2,3 (kildekritisk) eller indleder 2,4b ff. (de fleste nyere). **Sat som `{E:}`.** Bemærk kiasmen »himlen og jorden« (v4a) / »jord og himmel« (v4b), bevaret i oversættelsen.
5. **v4 skift fra *ʔĕlōhîm* til *YHWH ʔĕlōhîm*** – Navneskiftet markerer at Skaberen er Israels pagtsgud. Kandidat til `{E:}` (ikke sat; overvej ved v4 hvis formlen-noten flyttes).
6. **v5-6 Uden regn og menneske** – v5 nævner to mangler (regn, menneske), som v6 og v7 udfylder. ({E:} muligt)
7. **v6 *ʔēd*** – Usikkert ord; akkadisk *edû* »flod/oversvømmelse«, sumerisk *id* »flod«; LXX *pēgē* »kilde«. **Sat som `{T:}`.**
8. **v7 *yāṣar* »forme«** – Pottemagerverbum (jf. Es 45,9 og `tekst/es045.txt` »potteskår … {H: 1 Mos 2,7}«). Ordspillet *ʔādām*/*ʔădāmāh* **sat som `{T:}`**. Kandidat til `{E:}` om pottemagerbilledet.
9. **v7 *nepeš ḥayyāh*** – Samme udtryk som om dyrene (1,20.24; 2,19); mennesket adskiller sig ved Guds indblæsning, ikke ved betegnelsen. **`{T:}` + `{H: 1 Kor 15,45}` sat**; Paulus' citat følger LXX *psychē zōsa*.
10. **v8 Eden** – Muligvis beslægtet med hebraisk *ʕēden* »fryd, overflod« (jf. Sl 36,9 *ʕădāneykā*) eller akkadisk/sumerisk *edinu* »slette«. Haven er *i* Eden (v8), floden udgår *fra* Eden (v10) – Eden er altså et større område. Kandidat til `{E:}` (ikke sat). Es 51,3 (`tekst/es051.txt`) parallelliserer »Eden« og »HERRENS have«.
11. **v9 Syntaksen** – »livets træ midt i haven og træet til kundskab …«: det er uklart om »midt i haven« også gælder det andet træ (jf. 3,3, hvor kvinden placerer kundskabstræet midt i haven). Kandidat til `{T:}`.
12. **v9 »godt og ondt«** – Merisme: kundskab om »alt« eller evnen til selv at afgøre hvad der er godt og ondt (jf. 5 Mos 1,39; 2 Sam 19,36; Hebr 5,14 i `tekst/hebr005.txt`: »skelne mellem godt og ondt«). Kandidat til `{E:}`.
13. **v10-14 Floderne** – Fire floder (fire = verdenshjørnerne?); kun Tigris og Eufrat kan identificeres sikkert. Gihon er også navnet på kilden i Jerusalem (1 Kong 1,33). Kandidat til `{E:}`.
14. **v12 *bᵊdōlaḥ* / *šōham*** – Bdellium (harpiks, jf. 4 Mos 11,7 om mannaen) og shoham-sten (note som `tekst/2mos025.txt` v7). Begge findes i tabernakel-sammenhæng → mulig helligdomsforbindelse (jf. obs. 15). **Sat som `{T:}`.**
15. **v15 *ʕābad* / *šāmar*** – Levit-parallellen (4 Mos 3,7-8; 8,26; 18,5-6). **Sat som `{E:}`**, forsigtigt formuleret. Femininsuffikset (-*āh*) går formelt på *gan* (hankøn) – evt. på *ʔădāmāh*; ikke noteret inline.
16. **v16-17 Buddet** – Første bud er en tilladelse (»af *alle* … frit«) før forbuddet. »Den dag« (*bᵊyôm*) kan betyde »når« (jf. v4). Kandidat til `{T:}`.
17. **v18 *ʕēzer kᵊnegdô*** – **Sat som `{T:}` + `{E:}`.** »Ikke godt« står i kontrast til det sjufoldige »godt« i kap. 1.
18. **v19-20 Navngivningen** – At give navn er et udtryk for herredømme (jf. 1,28). Dyrene formes også »af agerjorden« men får ikke livsånde blæst ind. ({E:} muligt)
19. **v20 *lᵊʔādām*** – Se tabel; **sat som `{T:}`**. Reviewer bør afgøre om »Adam« først skal indføres i 3,17 / 4,25 (hvor flere oversættelser gør det).
20. **v21 *tardēmāh*** – Guddommeligt fremkaldt dyb søvn (jf. 15,12; 1 Sam 26,12; Job 4,13). Kandidat til `{E:}` eller `{H:}`.
21. **v22 *wayyiben* »byggede«** – Arkitektonisk verbum, kun her om skabelse af et menneske. Kandidat til `{T: Ordret: >>byggede<<.}` hvis man vælger »formede/skabte«; udkastet bevarer »byggede«, så ingen note.
22. **v23 *zōʔt happaʕam*** – »Denne gang« (endelig!); »denne« (*zōʔt*) gentages tre gange i MT (indramning). Ordspillet *ʔîš*/*ʔiššāh* **sat som `{T:}`** (de to ord er etymologisk næppe beslægtede, men lyder ens). Ældre danske oversættelser har forsøgt »Mandinde« – bør verificeres før det evt. nævnes i en note.
23. **v24 Fortællerkommentar** – »Derfor« er fortællerens ætiologiske bemærkning, men Jesus tilskriver den Skaberen (Matt 19,4-5). **`{H:}` sat** med Matt 19,5; Mark 10,7-8; 1 Kor 6,16; Ef 5,31.
24. **v25 *ʕărûmmîm* / 3,1 *ʕārûm*** – **Sat som `{E:}`.** Verset er overgangsvers til kap. 3.

## Konsistenspunkter mod `tekst/`

- **Hebr 4,4** (`tekst/hebr004.txt`): »Gud hvilede på den syvende dag fra alle sine gerninger« → 2,2 »hvilede på den syvende dag fra al sin gerning«. Ental »gerning« følger MT's ental *mᵊlāʔkāh*.
- **1 Kor 15,45** (`tekst/1kor015.txt`): »blev til en levende sjæl« → 2,7 har »et levende væsen« (konsekvent med kap. 1 og 2,19) og NT-formen i `{T:}`. Reviewer: ønskes NT-formen i selve teksten?
- **Matt 19,5 / Mark 10,7-8 / Ef 5,31**: »forlader/skal forlade en mand sin far og mor og holde/holder sig til sin hustru, og de to bliver/skal blive ét kød« → 2,24 følger Ef 5,31/Mark 10,7 (præsens) men uden »de to« (ikke i MT). Matt 19,5 har futurum »skal« – begge belagt.
- **2 Mos 20,11** (`tekst/2mos020.txt`): »velsignede … og helligede den« → 2,3 samme verber.
- **1 Mos 2,7-henvisninger** findes i `tekst/es042.txt` (»åndedræt«), `es045.txt` (»agerjorden«), `es057.txt`, `jak004.txt` – udkastet passer med »agerjorden«; *nᵊšāmāh* er gengivet »livsånde« (Es 42,5 har »åndedræt«).
- **Es 51,3** (`tekst/es051.txt`): »Eden … HERRENS have« – »Eden« uden artikel som her.
- **Åb 2,7; 22,2.14.19**: »livets træ« – identisk.
- **Shoham-sten**: form og note som `tekst/2mos025.txt` v7 / `2mos028.txt`.
- **»markens vilde dyr«** som `tekst/2mos023.txt`; **»dyb søvn«** som `tekst/job004.txt`, `job033.txt`.
- **Pronomen for »mennesket«**: udkastet bruger »han/hans« (personligt), ikke »det/dets« (grammatisk). Undtagelse: »på dets plads« i v21 går på ribbenet. Bør afstemmes med kap. 1 og 3.

## Nye navneformer

| Hebraisk | Dansk | Begrundelse |
|---|---|---|
| עֵדֶן | Eden (Edens have) | `tekst/es051.txt` »et Eden«; `es037.txt` »Edens« (andet sted, samme form). |
| פִּישׁוֹן | Pishon | שׁ → sh (Josva-reglen: Bashan, Shilo). |
| חֲוִילָה | Havila | ח → h, sluttende ה udelades. |
| גִּיחוֹן | Gihon | ח → h. |
| כּוּשׁ | Kush | Eksisterende form i `tekst/` (`sl068.txt`, `sl087.txt`, `jer046.txt`, `nah003.txt`, `sef003.txt`); `{T:}` om identifikationen. |
| חִדֶּקֶל | Tigris | Gængs dansk form (som Eufrat), belagt i `tekst/jer050.txt`-noter; hebraisk *ḥiddeqel* i `{T:}`. Alternativ: »Hiddekel« i teksten + `{T: Dvs. Tigris.}` (jf. Dan 10,4). |
| אַשּׁוּר | Assur | Belagt i `tekst/4mos024.txt`, `es014.txt`; `{T:}` om by/land. |
| פְּרָת | Eufrat | Belagt (`tekst/jer013.txt`, `draft/dan/jos/jos001_BSB.txt`). |
| אָדָם | Adam (v20) | Egennavn første gang, se obs. 19. |

## Åbne spørgsmål til reviewer

1. 2,7: »et levende væsen« (konsekvens med kap. 1) eller »en levende sjæl« (1 Kor 15,45) i teksten?
2. 2,20: Skal »Adam« indføres her (MT uden artikel, som BSB), eller først i 3,17/4,25? Afstemmes med kap. 3.
3. 2,14: »Tigris« (gængs) eller »Hiddekel« (translitteration) i teksten?
4. 2,4: Hører v4a til det foregående eller det følgende afsnit? Udkastet lægger hele v4 i det nye afsnit.
5. 2,6: »væld« (BSB) eller »damp/tåge« (ældre danske og engelske oversættelser)?
6. 2,24: Præsens (»forlader«, som Ef 5,31) eller futurum (»skal forlade«, som Matt 19,5)?
7. Pronomen for »mennesket«: »han« eller »det«? Skal afgøres fælles for kap. 1-3 og føres ind i `1mos_review_overview.md`.
8. 2,2: Skal teksten-kritisk note (»sjette dag«) stå inline som `{E:}`, eller kun her?


## Inline-noter flyttet til noterne (09.10.2026)

Efter piloten er notetætheden tilpasset de færdige Mosebøger i `tekst/`: `{T:}` kun hvor ordlyden ændrer betydningen eller bærer et billede/ordspil, `{E:}` højst 4, `{H:}` kun ved direkte NT-citater. Følgende noter er fjernet fra teksten og bevaret her uændret:

| Vers | Efter ordet | Type | Note |
|---|---|---|---|
| 1 | hærskare | T | Ordret: >>og hele deres hær<<, dvs. alt hvad der findes i dem, jf. Es 34,4. |
| 3 | gjort | T | Ordret: >>som Gud skabte for at gøre<<. |
| 7 | livsånde | T | Ordret: >>livs åndedræt<<. |
| 10 | hovedløb | T | Ordret: >>fire hoveder<<. |
| 12 | bdellium | T | En vellugtende harpiks; andre har tænkt på perler. |
| 12 | sten | T | Der er usikkerhed om hvilken ædelsten det drejer sig om; se note til 2 Mos 25,7. |
| 13 | Kush | T | Kush betegner ellers Nubien syd for Egypten; her er identifikationen usikker. |
| 14 | Tigris | T | Hebraisk *ḥiddeqel*, jf. Dan 10,4. |
| 14 | Assur | T | Eller >>foran Assur<<. Assur kan være både byen og landet Assyrien. |
| 16 | spise | T | Ordret: >>spise skal du spise<<; den hebraiske dobbeltform understreger friheden. |
| 17 | dø | T | Ordret: >>dø skal du dø<<. |
| 25 | ikke | E | *ʕărûmmîm* >>nøgne<< klinger sammen med *ʕārûm* >>snedig<< om slangen i 3,1; ordspillet binder de to afsnit sammen. |
