# 1 Mosebog 18 – noter til udkastet `gen018.txt`

Dato: 15.10.2026 · Status: **Udkast** (maskinudkast fra grundteksten, ingen eksegetisk bearbejdning eller litterært tjek endnu)

## Hvad udkastet er

- Oversat direkte fra den hebraiske tekst i `orig/heb/gen018.txt` (BHSA-klausullinjer), sammenholdt med Berean Standard Bible (`reference/BSB/gen018.txt`). BSB er kun brugt til at afgøre valg hvor hebraisken tillader mere end én gengivelse.
- Udarbejdet i karantæne: Den Frie Bibels egen 1 Mos 18 og det tidligere udkast er ikke åbnet. Stilmodel: `gen020.txt`, `gen021.txt`, `gen023.txt` med noter (der findes ingen færdige kapitler under 20 i projektet).
- Skrevet i det taggede format (`gen018.tagged`); `gen018.txt` og `gen018.align` er dannet af `scripts/full_align.py split`. Talord skrevet med cifre (50, 45, 40 …) kan ikke tagges og står uden token-nummer.
- 33 vers, versnummerering som i `orig/` (identisk med BSB).
- Tre overskrifter: v1-8 (de tre mænd), v9-15 (Sara ler), v16-33 (forbønnen for Sodoma).
- Inline-noter: `{T:}` 10 (v1, v3, v5, v10, v11, v12, v14, v19, v21, v27), `{E:}` 4 (v2, v12, v22, v25), `{H:}` 2 (v10, v14: Rom 9,9), `{N:}` 2 (`nåde` v3, `gt-mål` v6).

## Bevidste valg

| Vers | Hebraisk | Dansk | BSB | Kommentar |
|---|---|---|---|---|
| 1 | וַיֵּרָא אֵלָיו יְהוָה | HERREN viste sig for Abraham | the LORD appeared to Abraham | MT har kun »for ham«; navnet sat ind ved kapitelstart (som BSB). »viste sig for« som 26,2; 35,1. |
| 1 | בְּאֵלֹנֵי מַמְרֵא | ved Mamres ege | by the Oaks of Mamre | Stilarket og store (`term:elon`): »Mamres ege«; »terebinter« i `{T:}`. |
| 1 | כְּחֹם הַיּוֹם | på dagens hedeste tid | in the heat of the day | |
| 2 | וַיִּשָּׂא עֵינָיו וַיַּרְא וְהִנֵּה | Han så op, og se | looked up and saw | Som 33,1 (»Jakob så op, og se«). |
| 2 | וַיִּשְׁתַּחוּ אָרְצָה | bøjede sig til jorden | bowed low to the ground | Som 33,3. |
| 3 | אֲדֹנָי | Herre | My lord | MT-punkteringen (gudsbetegnelse) fulgt som i 20,4; alternativ læsning i `{T:}`. Se oversigtens punkt 5. |
| 3 | אִם־נָא מָצָאתִי חֵן בְּעֵינֶיךָ | hvis jeg har fundet nåde for dine øjne | if I have found favor in your sight | Store `formula:find_favor`; som 33,10. `{N: nåde}`. |
| 3 | אַל־נָא תַעֲבֹר מֵעַל עַבְדֶּךָ | så gå ikke din tjener forbi | do not pass your servant by | Ental, derefter flertal i v4-5. |
| 4 | יֻקַּח־נָא מְעַט־מַיִם | Lad der blive hentet lidt vand | Let a little water be brought | Passiven bevaret. |
| 5 | פַּת־לֶחֶם | en bid brød | a bit of bread | »bid brød« husord (DFB 2×). Abrahams beskedne tilbud står i kontrast til måltidet v6-8. |
| 5 | וְסַעֲדוּ לִבְּכֶם | så I kan styrke jer | refresh yourselves | `{T:}` med ordret »støtte jeres hjerte«; »styrke jer« DFB 5×. |
| 5 | כִּי־עַל־כֵּן עֲבַרְתֶּם | Det er jo derfor I er kommet forbi | This is why you have passed | Hebraisk rækkefølge bevaret (»bagefter kan I drage videre« før begrundelsen). |
| 6 | שְׁלֹשׁ סְאִים קֶמַח סֹלֶת | tre sea fint mel | three seahs of fine flour | Enheden bevaret (feature `measures`) med `{N: gt-mål}`; »fint mel« DFB 3×. |
| 6 | עֻגוֹת | fladbrød | bread | Runde brød bagt på hede sten; »fladbrød« husord (3 Mos). |
| 7 | בֶּן־בָּקָר רַךְ וָטוֹב | en spæd og god kalv | a tender and choice calf | |
| 7 | הַנַּעַר | en ung tjener | a servant | *naʕar* om en tjener, som 22,3 »unge tjenere«. |
| 8 | חֶמְאָה וְחָלָב | surmælk og mælk | curds and milk | »surmælk« som DFB (Job 29,6; 2 Mos 3,8-formlen). |
| 9 | הִנֵּה בָאֹהֶל | Derinde i teltet | There, in the tent | *hinnēh* gengivet med »Derinde«. |
| 10 | וַיֹּאמֶר | Han sagde | the LORD said | MT nævner ikke taleren; BSB indsætter »the LORD«. Udkastet følger MT; v13 navngiver HERREN. |
| 10 | שׁוֹב אָשׁוּב | Jeg kommer bestemt tilbage | I will surely return | Infinitivus absolutus som »bestemt«. |
| 10.14 | כָּעֵת חַיָּה | ved denne tid næste år | at this time next year | `{T:}` med ordret; ordlyden nær Rom 9,9 (»Ved denne tid vil jeg komme, og Sara vil have en søn«). `{H: Rom 9,9.}` ved begge vers. |
| 10 | וְהוּא אַחֲרָיו | som var bag ham | was behind him | *hûʔ* henviser til indgangen. |
| 11 | זְקֵנִים בָּאִים בַּיָּמִים | gamle og kommet langt op i årene | old and well along in years | Som 24,1 (»gammel og kommet langt op i årene«), her i flertal. |
| 11 | חָדַל לִהְיוֹת לְשָׂרָה אֹרַח כַּנָּשִׁים | Sara havde ikke længere det som kvinder har | Sarah had passed the age of childbearing | Eufemisme bevaret; ordret og forklaring i `{T:}`. |
| 12 | בְּקִרְבָּהּ לֵאמֹר | ved sig selv og tænkte | to herself, saying | *lēʔmōr* = »tænkte«, som 20,11 »Jeg tænkte«. |
| 12 | עֶדְנָה | lyst | this pleasure | `{T:}` om roden *ʕdn* (Eden). |
| 12 | וַאדֹנִי זָקֵן | min herre er gammel | my master is old | `{E:}` med 1 Pet 3,6 (DFB-ordlyd). |
| 13 | הַאַף אֻמְנָם אֵלֵד | Skulle jeg virkelig føde | Can I really bear a child | Citat i citat uden anførselstegn, som 20,5. |
| 14 | הֲיִפָּלֵא מֵיְהוָה דָּבָר | Skulle noget være umuligt for HERREN? | Is anything too difficult for the LORD? | Ordlyd som DFB Jer 32,27 (»Skulle noget være umuligt for mig?«); ordret i `{T:}`. |
| 14 | לַמּוֹעֵד | Til den fastsatte tid | At the appointed time | Som 21,2 (`gen021_notes.md` henviser hertil). |
| 15 | לֹא כִּי צָחָקְתְּ | Jo, du lo | No, but you did laugh | Dansk »Jo« dækker *lōʔ kî*. |
| 16 | וַיַּשְׁקִפוּ עַל־פְּנֵי סְדֹם | så ned over Sodoma | looked out over Sodom | |
| 16 | לְשַׁלְּחָם | for at følge dem på vej | to see them off | |
| 17-19 | וַיהוָה אָמָר | HERREN sagde | And the LORD said | Kan være indre overvejelse; »sagde« bevaret som BSB. Talen lukkes efter v19 og genåbnes i v20 (ny inkvit i MT). |
| 18 | וְנִבְרְכוּ בוֹ | i ham skal … velsignes | through him … will be blessed | Nifal, passiv som 12,3 og 22,18; ingen note her. »alle jordens folk« som 22,18; 26,4. |
| 19 | יְדַעְתִּיו | jeg har udvalgt ham | I have chosen him | `{T:}` med ordret »kendt ham«. |
| 19 | צְדָקָה וּמִשְׁפָּט | retfærdighed og ret | what is right and just | Hebraisk rækkefølge bevaret; DFB har oftest »ret og retfærdighed« (10× mod 2×) – åbent spørgsmål 3. |
| 20 | זַעֲקַת סְדֹם | Skriget over Sodoma | The outcry against Sodom | »skrig« DFB 34× (2 Mos 11,6). |
| 20 | כִּי … כִּי | sandelig … virkelig | — | Forstærkende *kî*. |
| 21 | הַכְּצַעֲקָתָהּ … עָשׂוּ כָּלָה | om de i alt har handlet efter det skrig over byen | if their actions fully justify the outcry | Suffikset (fem. sg.) forstået om byen; *kālāh* som adverbium (BSB), navneordsforståelsen i `{T:}`. |
| 22 | וְאַבְרָהָם עוֹדֶנּוּ עֹמֵד לִפְנֵי יְהוָה | men Abraham blev stående foran HERREN | but Abraham remained standing before the LORD | `{E:}` om *tiqqûn sôfᵊrîm*. |
| 23 | הַאַף תִּסְפֶּה צַדִּיק עִם־רָשָׁע | Vil du virkelig udrydde den retfærdige sammen med den uretfærdige? | Will You really sweep away the righteous with the wicked? | **Ordret som citeret i `gen020.txt` v4-noten.** *sāfāh* = »udrydde« (ikke »feje bort«, som det tidligere udkast havde; se åbent spørgsmål 2). |
| 24.26 | נָשָׂא לַמָּקוֹם | skåne stedet | spare the place | *nāśāʔ* ordret »bære/tilgive«; »skåne« DFB 10×. |
| 25 | חָלִלָה לְּךָ | Det være langt fra dig | Far be it from You | Husform (DFB Job 34,10). |
| 25 | וְהָיָה כַצַּדִּיק כָּרָשָׁע | så det går den retfærdige som den uretfærdige | so that the righteous and the wicked are treated alike | |
| 25 | הֲשֹׁפֵט כָּל־הָאָרֶץ לֹא יַעֲשֶׂה מִשְׁפָּט | Skulle hele jordens dommer ikke gøre ret? | Will not the Judge of all the earth do what is right? | `{E:}` om *mišpāṭ* (v19/v25). |
| 27.31 | הוֹאַלְתִּי | jeg har dristet mig | I have ventured | »drister« DFB 3×. |
| 27 | עָפָר וָאֵפֶר | støv og aske | dust and ashes | DFB Job 30,19; 42,6. `{T:}` om ordparret. |
| 27.30-32 | אֲדֹנָי | Herren | the Lord | Ikke-tiltale: »Herren« (store `term:adonai`). |
| 28 | הֲתַשְׁחִית | Vil du ødelægge | Will You destroy | *šiḥēt* = »ødelægge« (jf. gen019-oversigtens punkt 4). |
| 29.31-32 | בַּעֲבוּר הָאַרְבָּעִים | Af hensyn til de 40 | On account of the forty | »for de 40's skyld« undgået; v24 og v26 har »for … skyld« med navneord/pronomen. |
| 30.32 | אַל־נָא יִחַר לַאדֹנָי | Herren må ikke blive vred | May the Lord not be angry | |
| 32 | אַךְ־הַפַּעַם | kun denne ene gang endnu | once more | |
| 33 | וְאַבְרָהָם שָׁב לִמְקֹמוֹ | Abraham vendte tilbage til sit sted | Abraham returned home | Ordret »sit sted«. |
| 24-32 | tal | 50, 45, 40, 30, 20, 10; fem | fifty … ten; five | Talreglen (cifre fra 10). |

## Eksegetiske observationer

1. **v1-2.22; 19,1 HERREN og de tre mænd** – Fortællingen veksler mellem HERREN (ental) og »mændene« (flertal); først ved v22 og 19,1 skilles HERREN fra de to der går til Sodoma. Hebr 13,2 hentyder sandsynligvis til stedet. **[`{E:}` sat ved v2]**
2. **v3 *ʔădōnāy* / *ʔădōnî*** – MT punkterer som gudsbetegnelse; konsonantteksten tillader en høflig tiltale. Udkastet følger MT som 20,4. **[`{T:}` sat]**
3. **v10.14 Rom 9,9** – Paulus sammentrækker de to vers. Ordlyden ligger tæt på DFB's Rom 9,9, uden at den hebraiske »til dig« og »næste år« opgives. **[`{H:}` sat ved begge vers]**
4. **v12-15 latteren** – Fire gange *ṣāḥaq* (v12.13.15 ×2) forbereder navnet Isak (21,3.6, hvor `gen021.txt` har `{T:}` med henvisning til 18,12-15). Ingen note her for ikke at dublere. **[ingen note]**
5. **v12 *ʕædnāh*** – Samme rod som Eden; »nydelse« eller »frugtbarhed«. **[`{T:}` sat]**
6. **v12 »min herre«** – 1 Pet 3,6 bygger på netop dette ord. **[`{E:}` sat]**
7. **v17-19 Guds monolog** – Kan forstås som indre tale; v19 sammenfatter pagtens formål: »retfærdighed og ret« som vej for Abrahams hus. **[ingen note]**
8. **v21 *kālāh*** – Adverbium (»fuldt ud«) eller navneord (»udslettelse«). **[`{T:}` sat]**
9. **v22 *tiqqûn sôfᵊrîm*** – Masoretisk tradition om en ærbødig rettelse (oprindelig »HERREN blev stående foran Abraham«). **[`{E:}` sat]**
10. **v25 *mišpāṭ* og *šōfēṭ*** – Ordspil med v19; Abraham appellerer til at Guds handling må stemme med hans egen ret. **[`{E:}` sat]**
11. **v23-32 forhandlingen** – Tallene falder 50 → 45 → 40 → 30 → 20 → 10; svarformlerne varierer mellem »ødelægge« (v28.31.32) og »gøre det« (v29.30), hvilket er bevaret. **[ingen note]**
12. **v27 *ʕāfār wāʔēfær*** – Rimpar; jf. Job 30,19; 42,6. **[`{T:}` sat]**
13. **v14 *yippālēʔ*** – Samme spørgsmål i Jer 32,17.27; Luk 1,37 hentyder måske til det (kun allusion, derfor ikke `{H:}`). **[`{T:}` sat]**

## Konsistenspunkter mod Den Frie Bibel og tidligere kapitler

- **»Vil du virkelig udrydde den retfærdige sammen med den uretfærdige?«** (v23) ordret som citeret i `gen020.txt` v4 `{E:}`.
- **»gamle og kommet langt op i årene«** som 24,1; **»Han så op, og se«** som 33,1; **»bøjede sig til jorden«** som 33,3; **»fundet nåde for dine øjne«** som 33,10; **»Til den fastsatte tid«** som 21,2.
- **»Det være langt fra«** (DFB Job 34,10), **»støv og aske«** (DFB Job 30,19; 42,6), **»Skulle noget være umuligt for …?«** (DFB Jer 32,27), **»surmælk«**, **»fladbrød«**, **»fint mel«**, **»skrig«** som DFB.
- **»Mamres ege«** som stilarket og `term:elon`. Store-noten til `term:elon` nævner en anden form fra DFB's egen 1 Mos 18,1; den er ikke fulgt, da kapitlet er udarbejdet i karantæne (se åbent spørgsmål 1).
- **Herre/Herren** for *ʔădōnāy* (tiltale v3 / omtale v27.30-32), adskilt fra HERREN.
- **Sodoma, Gomorra** som stilarket.

## Nye navneformer

- Ingen nye navne. Abraham, Sara, Mamre, Sodoma, Gomorra efter stilarket.
- Ny fast gengivelse: **sea** (*sᵊʔāh*) som måleenhed med `{N: gt-mål}`.

## Åbne spørgsmål til reviewer

1. v1: »Mamres ege« (stilarket, store) eller DFB's egen form i 1 Mos 18,1, som store-noten antyder? Skal afstemmes efter karantænen.
2. v23-24 *sāfāh*: »udrydde« (som gen020-citatet) eller »feje bort« / »rive bort« (tidligere udkast, 19,15.17)? Bør ensrettes med kap. 19.
3. v19 *ṣᵊdāqāh ûmišpāṭ*: hebraisk rækkefølge »retfærdighed og ret« eller husformlen »ret og retfærdighed«?
4. v3 *ʔădōnāy*: »Herre« (MT) eller »min herre« (konsonantteksten, BSB)? (Oversigtens punkt 5.)
5. v10: »Han sagde« (MT) eller »HERREN sagde« (BSB)?
6. v6 »sea«: bevare enheden eller fordanske (»mål«)?
7. v29-32 »Af hensyn til de 40« – eller »for de 40's skyld« (tættere på v24.26)?

*Original text in these notes: Hebrew from the Westminster Leningrad Codex (public domain), via MACULA Hebrew (CC BY 4.0, Clear Bible), filled in by scripts/notes_hebrew.py.*
