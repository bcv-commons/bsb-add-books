# Josva 22 – reviewer-noter

## Hvad udkastene er

`jos022_svk.txt` og `jos022.txt` er maskinudkast oversat direkte fra `orig/heb/jos022.txt` (MT, klausul pr. linje).
Svenska Kärnbibeln (`svk-text/jos022.txt`) hhv. Berean Standard Bible (`reference/BSB/jos022.txt`) er kun brugt til at afgøre
valg hvor hebraisken tillader mere end én gengivelse, og til afsnitsinddeling/overskrifter. Sporforskellene fra
`export/dan/dan_BSB/jos/jos_style_guide.md` (ro/hvile, vejledning/lov) er holdt.

## Bevidste afvigelser mellem sporene

| Vers | Hebraisk | `_svk` | `_BSB` | Kommentar |
|---|---|---|---|---|
| overskrifter | – | to overskrifter (v. 1; v. 10, SVK's afsnitsskel) | to overskrifter (v. 1; v. 9, BSB's skel) | Begge sætningsform; kap. har ellers samme afsnit (v. 7, 13, 21, 30). |
| 4 | הֵנִיחַ | »skaffet jeres brødre ro« | »givet jeres brødre hvile« | Fast sporforskel (1,13.15). |
| 5 | הַמִּצְוָה וְהַתּוֹרָה | »det bud og den vejledning« | »det bud og den lov« | Fast sporforskel; ordlyden ekkoer 1,7 pr. spor (»omhyggeligt … handle efter« / »omhyggelige med at overholde«). |
| 10-11 | גְּלִילוֹת הַיַּרְדֵּן | »egnen ved Jordan« + `{T:}` (SVK »området vid Jordan«) | »Gelilot ved Jordan« + `{T:}` (BSB »Geliloth«) | *gəlîlôṯ* = »kredse/egne« (13,2 »filistrenes områder«) eller stednavn (18,17 »Gelilot« over for Adummim-passet, = Gilgal 15,7). Begge spor gør opmærksom på den anden mulighed. Reviewer vælger; kap. 18 har allerede »Gelilot« som stednavn. |
| 17-18 | וְאַתֶּם תָּשֻׁבוּ | v. 17-18 bundet sammen som ét spørgsmål (»– og så vil I i dag vende jer bort fra HERREN?«) | v. 18 som selvstændigt udbrud (»Og nu vil I vende jer bort fra HERREN!«) | Syntaksen er åben; SVK binder, BSB deler. |
| 19; 29 | מִבַּלְעֲדֵי / מִלְּבַד מִזְבַּח יְהוָה | »ved siden af HERREN vor Guds alter« | »et andet alter end HERREN vor Guds alter« (v. 19); »foruden HERREN vor Guds alter« (v. 29) | Samme sag; `_BSB` gør pointen »ét legitimt alter« tydeligere. |
| 22 | אֵל אֱלֹהִים יְהוָה (2×) | »Gud, Gud HERREN! Gud, Gud HERREN!« + `{E:}` (= `import/CC0/dan/den-frie-bibel/text/psa050.txt` v1) | »HERREN, den vældige Gud! HERREN, den vældige Gud!« + `{T:}` (BSB »The LORD, the Mighty One, is God!«) | **Anbefaling:** følg `_svk`, som er identisk med husets gengivelse af den samme formel i Sl 50,1 (»Gud, Gud HERREN har talt«, med `{T:}` om de to gudsord). |
| 28 | תַּבְנִית | »afbildning« | »kopi« | Begge med `{T: *taḇnîṯ*, model, forbillede, jf. 2 Mos 25,9.40}`. »Afbildning« er det mere husvante ord. |
| 34 | וַיִּקְרְאוּ … לַמִּזְבֵּחַ כִּי עֵד הוּא | MT-struktur: »gav alteret navn: >>Det er vidne mellem os om at HERREN er Gud.<<« + `{T:}` om det manglende navn | »kaldte alteret Vidne, … for de sagde: >>…<<« + `{T:}` (navnet indsat efter Peshitta) | Se pkt. 12. |

Alt andet er ens i de to spor.

## Eksegetiske observationer

1. **v. 1-6 – gentagelse af 1,12-18.** Josvas afsked spejler indsættelsen: »HERRENS tjener Moses«, »skaffe ro / give hvile«, »omhyggeligt … handle efter« (1,7). Inline: `{H: Jos 1,12-18}` ved v. 2 og `{H: 4 Mos 32,20-22; 5 Mos 3,18-20}` ved v. 4.
2. **v. 2 שְׁמַעְתֶּם בְקוֹלִי** – »adlydt mig«, `{T: Ordret: hørt på min røst}`. **v. 3 זֶה יָמִים רַבִּים** – »i al denne lange tid«, `{T:}`. **v. 3 שְׁמַרְתֶּם אֶת־מִשְׁמֶרֶת מִצְוַת** – »holdt det HERREN jeres Gud har pålagt jer«, `{T: Ordret: holdt vagt om HERREN jeres Guds bud}`; *mišmereṯ* er præstesprog (4 Mos 3-4).
3. **v. 4 בְּעֵבֶר הַיַּרְדֵּן** – her sagt i Shilo, altså om østsiden: »på den anden side af Jordan« (som kap. 13). Jf. overview-punkt 2 om udtrykkets perspektiv. **v. 7 מֵעֵבֶר הַיַּרְדֵּן יָמָּה** – »vest for Jordan«; **v. 11 אֶל־עֵבֶר בְּנֵי יִשְׂרָאֵל** – »på israelitternes side«.
4. **v. 5 – deuteronomistisk kæde**: elske, vandre på hans veje, holde budene, holde fast ved (*dāḇaq*), tjene af hele hjertet og hele sjælen. Gengivelsen følger `import/CC0/dan/den-frie-bibel/text/deu006.txt` v5 (»af hele dit hjerte og af hele din sjæl«) og `import/CC0/dan/den-frie-bibel/text/deu010.txt` v20 (»holde fast ved«). Inline `{H: 5 Mos 6,5; 10,12}`. Ingen `{N: Hjerte}`/`{N: Sjæl}`, da ordene er gengivet ordret (5 Mos 6,5 i `import/CC0/dan/den-frie-bibel/text/` har heller ingen).
5. **v. 8** – byttedeling med de hjemmeblevne, jf. 4 Mos 31,27 og 1 Sam 30,24-25 (kandidat til `{H:}`; ikke sat).
6. **v. 9 אֶרֶץ אֲחֻזָּתָם אֲשֶׁר נֹאחֲזוּ־בָהּ** – ordspil på *ʾāḥaz*: »det land de ejede, og som de havde taget i eje«. אֲחֻזָּה gengives gennemgående med »eje/ejer« (4 Mos 32 i `import/CC0/dan/den-frie-bibel/text/` har »ejendom«).
7. **v. 10-11 alterets placering – inline `{E:}`.** »Over for Kana'ans land … i egnen ved Jordan … på israelitternes side« placerer alteret på vestbredden, altså inde i det område de øvrige stammer har fået. Det er nøglen til reaktionen (v. 12) og til anklagen om et konkurrerende offersted (5 Mos 12,5-14). Nogle fortolkere læser dog v. 11 om østbredden; noten er formuleret forsigtigt (»peger på«).
8. **v. 12 / 16-18 / 20 עֵדָה – tre former, tre gengivelser** (jf. overview-punkt 27): עֲדַת בְּנֵי־יִשְׂרָאֵל (v. 12) → »israelitternes menighed« (som 18,1); עֲדַת יְהוָה (v. 16.17) → »HERRENS menighed«; עֲדַת יִשְׂרָאֵל (v. 18.20) → »Israels menighed« (husform i `import/CC0/dan/den-frie-bibel/text/exo012.txt`, 5×). **Bemærk** at `import/CC0/dan/den-frie-bibel/text/4mos*` gennemgående har »forsamling« for det samme ord (»israelitternes forsamling« 19×, »hele forsamlingen« 25×, »HERRENS forsamling« 4 Mos 31,16). Husets praksis er altså delt; ét valg for Josva-bogen bør træffes samlet (se åbne spørgsmål).
9. **v. 14 נָשִׂיא / רֹאשׁ בֵּית־אֲבוֹתָם / אַלְפֵי יִשְׂרָאֵל** – »ledere« (som `import/CC0/dan/den-frie-bibel/text/num001.txt` v16 »ledere af deres fædrenestammer«), »overhoved for sit fædrenehus« (»fædrenehus« 36× i `import/CC0/dan/den-frie-bibel/text/`), »Israels tusinder« (`import/CC0/dan/den-frie-bibel/text/num001.txt` v16 »overhoveder for Israels tusinder«) + `{T: Dvs. slægtsafdelingerne, jf. 4 Mos 1,16}`. Ti ledere = de ni og en halv vestlige stammer.
10. **v. 16.20.22.31 מַעַל – inline `{E:}` ved v. 16.** Substantivet »troløshed«, verbet »handle troløst« (som `import/CC0/dan/den-frie-bibel/text/num031.txt` v16 »handle troløst mod HERREN i sagen med Peor«). Kap. 7-udkastet har »forbrød sig … mod« i 7,1 med `{E:}` om *māʿal*; her er substantivet nødvendigt (»hvad er det for en troløshed«), så »troløs(hed)« er brugt konsekvent. **Reviewer:** overvej om 7,1 skal rettes til »handlede troløst med det der var lagt band på« for at matche 22,20 (som ordret citerer 7,1: מָעַל מַעַל בַּחֵרֶם).
11. **v. 17 עֲוֹן פְּעוֹר** – »synden ved Peor« + `{H: 4 Mos 25,1-9}`; `import/CC0/dan/den-frie-bibel/text/num025.txt` v18 og `num031.txt` v16 har »i sagen med Peor« for דְּבַר־פְּעוֹר. **v. 17b אֲשֶׁר לֹא־הִטַּהַרְנוּ מִמֶּנּוּ** – »som vi endnu den dag i dag ikke har renset os fra« – dvs. følgerne mærkes stadig; kandidat til `{E:}` (ikke sat, for at holde antallet nede).
12. **v. 34 – tekstkritik.** MT: וַיִּקְרְאוּ … לַמִּזְבֵּחַ כִּי עֵד הוּא בֵּינֹתֵינוּ. Selve navnet mangler; `orig/heb/jos022.txt` har ingen עֵד efter לַמִּזְבֵּחַ. Peshitta har »Vidne« (*sāhdûṯā*), og de fleste moderne oversættelser indsætter »Vidne« (DO92: »Vidne«). LXX har heller ikke noget navn. `_svk` beholder MT-strukturen og lader כִּי indlede navneindholdet (som SVK); `_BSB` indsætter »Vidne« med `{T:}`. Begge dokumenterer det. Jf. 24,27 (stenen som vidne) og 1 Mos 31,47-48 (Gal-Ed) – inline `{E:}` ved v. 27.
13. **v. 22 אֵל אֱלֹהִים יְהוָה** – inline `{E:}` (`_svk`) / `{T:}` (`_BSB`) + `{H: Sl 50,1}`. Gentagelsen fungerer som ed; »Han ved det, og Israel skal vide det« (*hûʾ yōḏēaʿ wəyiśrāʾēl hûʾ yēḏāʿ*) er svar på »hvad er det for en troløshed« i v. 16.
14. **v. 22b אַל־תּוֹשִׁיעֵנוּ** – 2. person, dvs. henvendt til HERREN midt i talen til udsendingene: »så frels os ikke i dag!« + `{T:}`. **v. 23 יְהוָה הוּא יְבַקֵּשׁ** – »så må HERREN selv kræve os til regnskab« + `{T: Ordret: søge}`.
15. **v. 24 מִדְּאָגָה מִדָּבָר** – »af bekymring for at …«; מָחָר »engang« + `{T: Ordret: i morgen}` (også v. 27.28).
16. **v. 25 אֵין־לָכֶם חֵלֶק בַּיהוָה** – »I har ingen del i HERREN«; samme frygt som 4 Mos 32 og modsat 5 Mos 12,12 (levitterne uden »del«). **v. 25b וְהִשְׁבִּיתוּ … לְבִלְתִּי יְרֹא** – »få vores børn til at holde op med at frygte HERREN«.
17. **v. 26 נַעֲשֶׂה־נָּא לָּנוּ** – »Lad os gå i gang og bygge«; ordret »lad os gøre for os«.
18. **v. 27 לַעֲבֹד אֶת־עֲבֹדַת יְהוָה לְפָנָיו** – »tjene HERREN for hans ansigt« + `{T:}`; »for HERRENS/hans ansigt« er husform (31×/2×).
19. **Offertermer**: עֹלָה »brændoffer«, מִנְחָה »afgrødeoffer« (58× i `import/CC0/dan/den-frie-bibel/text/`), זֶבַח »slagtoffer«, שְׁלָמִים »takofre« (`import/CC0/dan/den-frie-bibel/text/jdg020.txt`, `jdg021.txt`, `num006-007`, `num029`; »måltidsofre« kun `num010`, `num015`).
20. **v. 29 חָלִילָה לָּנוּ** – »Det være langt fra os« (`import/CC0/dan/den-frie-bibel/text/job027.txt`, `job034.txt`). Samme idiom kommer i 24,16.
21. **v. 30.33 וַיִּיטַב בְּעֵינֵיהֶם** – »var de tilfredse« + `{T: Ordret: det var godt i deres øjne}`; ligeledes v. 33.
22. **v. 30-31 בְּנֵי מְנַשֶּׁה** – »manassitterne« (som kap. 13/16/17-udkastene og `import/CC0/dan/den-frie-bibel/text/4mos*`); bemærk at v. 32-34 kun nævner rubenitterne og gaditterne.
23. **v. 31 אָז הִצַּלְתֶּם** – »Dermed har I reddet israelitterne fra HERRENS hånd« – ordret »da har I reddet«.
24. **v. 19 מִשְׁכַּן יְהוָה / v. 29 מִשְׁכָּנוֹ** – »HERRENS bolig« / »hans bolig« (`import/CC0/dan/den-frie-bibel/text/2mos*`: »boligen« 79×, »HERRENS bolig« 4×; ikke »tabernaklet«).

## Nye navneformer

Ingen. Alle navne (Shilo, Gilead/Gileads land, Kana'ans land, Bashan, Peor, Pinehas, Eleazar, Akan, Zera, Gelilot) er brugt før i udkastene eller i `import/CC0/dan/den-frie-bibel/text/`.
- »Pinehas, præsten Eleazars søn« = `import/CC0/dan/den-frie-bibel/text/num031.txt` v6 (num025 har »Pinehas, der var søn af Eleazar, præsten Arons søn«).
- »Peor« = `import/CC0/dan/den-frie-bibel/text/num025.txt` v18; »Ba'al-Peor« i num025 v3.5 er ikke relevant her (עֲוֹן פְּעוֹר).

## Konsistenspunkter mod `import/CC0/dan/den-frie-bibel/text/` og tidligere udkast

- 22,1-5 ↔ 1,12-18 pr. spor (ro/hvile; vejledning/lov; »omhyggeligt«).
- »Israels menighed« (`import/CC0/dan/den-frie-bibel/text/exo012.txt`), »israelitternes menighed« (18,1), »HERRENS menighed« – se pkt. 8; NB `import/CC0/dan/den-frie-bibel/text/4mos*` = »forsamling«.
- »fædrenehus«, »Israels tusinder«, »ledere«, »overhoved(er)« = `import/CC0/dan/den-frie-bibel/text/num001.txt`; »menighedens ledere« = kap. 9-udkastet (9,15.18-19).
- »det der var lagt band på«, »Akan, Zeras søn« = kap. 7-udkastet; »handle troløst« = `import/CC0/dan/den-frie-bibel/text/num031.txt` v16.
- »bronze« (ikke kobber) = kap. 6-udkastet og `import/CC0/dan/den-frie-bibel/text/2mos*`.
- »Det være langt fra os« = `import/CC0/dan/den-frie-bibel/text/job027.txt`/`job034.txt`.
- »takofre«, »afgrødeoffer«, »slagtoffer«, »brændoffer« = `import/CC0/dan/den-frie-bibel/text/jdg020.txt-021`, `4mos*`.
- »HERRENS bolig« = `import/CC0/dan/den-frie-bibel/text/2mos*`; »for hans ansigt« = `import/CC0/dan/den-frie-bibel/text/`.
- Apostrof i »Kana'ans« er lige (') som i alle udkast; `import/CC0/dan/den-frie-bibel/text/` blander ’ (29×) og ' (8×) – bør normaliseres samlet.

## Åbne spørgsmål til reviewer

1. **עֵדָה: »menighed« eller »forsamling«?** `import/CC0/dan/den-frie-bibel/text/exo012.txt` og udkastene siger »menighed«, `import/CC0/dan/den-frie-bibel/text/4mos*` siger »forsamling« (»israelitternes forsamling« 19×). Kap. 22 følger direktivet (»menighed«), men valget bør træffes for hele bogen (18,1; 22,12.16.17.18.20) og evt. hele GT-korpus.
2. **v. 22 gudsformlen** – `_svk` (= Sl 50,1) anbefales; skal `_BSB`-varianten helt væk?
3. **v. 34** – indsæt »Vidne« (som DO92, `_BSB`) eller behold MT-strukturen (`_svk`)?
4. **v. 10-11** – »Gelilot« som stednavn (som 18,17) eller appellativ »egnen ved Jordan«?
5. **7,1** – skal »forbrød sig … mod« ændres til »handlede troløst med« så 22,20's citat af 7,1 bliver ordret?
6. **v. 19b וְאֹתָנוּ אֶל־תִּמְרֹדוּ** – »gør ikke oprør mod os« (ordret; begge spor). Nogle læser »gør ikke os til oprørere«; ingen note sat – skal der?
7. Inline `{H:}` er sat ret rundhåndet i dette kapitel (7 pr. spor: 1,12-18; 4 Mos 32/5 Mos 3; 5 Mos 6,5; 4 Mos 25; Jos 7; Sl 50,1; 5 Mos 12,13-14) fordi kapitlet er en mosaik af henvisninger; kan tyndes ud.


## Harmonisering efter kap. 24

- »HERREN vor Guds« → »HERREN vores Guds« i begge spor, så det følger `import/CC0/dan/den-frie-bibel/text/`'s flertalsform (»vores Gud« 62× mod »vor Gud« 36×; »HERREN vores Gud« 16× mod 2×) og kap. 24.

*Original text in these notes: Hebrew from the Westminster Leningrad Codex (public domain), via MACULA Hebrew (CC BY 4.0, Clear Bible), filled in by scripts/notes_hebrew.py.*
