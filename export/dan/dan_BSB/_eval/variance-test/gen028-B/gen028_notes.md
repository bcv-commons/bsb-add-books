# 1 Mosebog 28 – noter til udkastet `gen028.txt`

Dato: 15.10.2026 · Status: **Udkast** (maskinudkast fra grundteksten, ingen eksegetisk bearbejdning eller litterært tjek endnu)

## Hvad udkastet er

- Oversat direkte fra den hebraiske tekst i `orig/heb/gen028.txt` (klausul-opdelt), sammenholdt med Berean Standard Bible (`reference/BSB/gen028.txt`). BSB er kun brugt til at afgøre valg hvor hebraisken tillader mere end én gengivelse.
- Udarbejdet i karantæne: Den Frie Bibels egen 1 Mos 28 og de øvrige 1 Mos-filer i `import/CC0/dan/den-frie-bibel/` er ikke åbnet. Stilmodel: projektets kap. 26, 27, 29, 31, 35 og 48 (kap. 1-19 ligger ikke i projektmappen).
- 22 vers, versnummerering som i `orig/` (identisk med BSB). Skrevet som `gen028.tagged` (tokennumre); `.txt` og `.align` er dannet af `scripts/full_align.py split`. Utaggede indholdstokens: v. 6 *lēʔmōr* (gengivet med kolon) og v. 8 *bᵊʕênê* (»i … øjne«, opløst i »ikke brød sig om«).
- Fire overskrifter: v. 1-5 (Isak sender Jakob af sted), v. 6-9 (Esaus ægteskab), v. 10-17 (drømmen), v. 18-22 (stenstøtten og løftet).
- Inline-noter: `{T:}` 9 (v. 4, 8, 11, 12, 13, 14, 19, 21, 22), `{E:}` 3 (v. 12, 19, 22), `{H:}` 0, `{N:}` 0.
- Ingen `{H:}`: Joh 1,51 er en hentydning til v. 12, ikke et citat (nævnt i `{E:}` ved v. 12).

## Bevidste valg

| Vers | Hebraisk | Dansk | BSB | Kommentar |
|---|---|---|---|---|
| 1, 6 | לֹא־תִקַּח אִשָּׁה מִבְּנוֹת כְּנָעַן | Du må ikke tage dig en hustru blandt Kana'ans døtre | Do not take a wife from the Canaanite women | »Kana'ans døtre« som 36,2; ens begge gange. |
| 2 | קוּם לֵךְ | Bryd op og gå | Go at once | *qûm* som hjælpeverbum; jf. 27,43 »Skynd dig at flygte«. »Bryd op« som 35,1. |
| 2 | בְתוּאֵל אֲבִי אִמֶּךָ / לָבָן אֲחִי אִמֶּךָ | din morfar Betuel / din morbror Laban | your mother's father / your mother's brother | »morbror« som 29,10 (3×); »morfar« parallelt. |
| 3 | אֵל שַׁדַּי | Gud den Almægtige | God Almighty | term:H7706. |
| 3 | יְבָרֵךְ … וְיַפְרְךָ וְיַרְבֶּךָ | velsigne dig og gøre dig frugtbar og talrig | bless you and make you fruitful and multiply you | Jussiv som konjunktiv (»Gud give dig«, 27,28; 43,14). »gøre dig frugtbar og talrig« som 48,4. |
| 3 | לִקְהַל עַמִּים | en forsamling af folk | a company of peoples | Som 35,11 og 48,4; 35,11's `{T:}` henviser hertil. |
| 4 | אֶת־בִּרְכַּת אַבְרָהָם | Abrahams velsignelse | the blessing of Abraham | Jf. Gal 3,14. |
| 4 | אֶרֶץ מְגֻרֶיךָ | det land hvor du bor som fremmed | the land where you dwell as a foreigner | `{T:}` ordret, som 17,8 og 47,9 (obs. i overblikket). |
| 5 | בֶּן־בְּתוּאֵל הָאֲרַמִּי | søn af aramæeren Betuel | son of Bethuel the Aramean | »aramæeren Betuel« som 25,20. |
| 8 | רָעוֹת … בְּעֵינֵי יִצְחָק | ikke brød sig om | disapproved of | `{T:}` ordret »onde i … øjne«. |
| 9 | עַל־נָשָׁיו | ud over de hustruer han havde | in addition to the wives he already had | |
| 10 | חָרָנָה | mod Karan | for Haran | Byen = Karan. |
| 11 | וַיִּפְגַּע בַּמָּקוֹם | Han nåede til stedet | On reaching a certain place | Bestemt artikel bevaret med `{T:}`; *māqôm* som ledeord. |
| 11, 18 | מְרַאֲשֹׁתָיו | under sit hoved | under his head | Ordret »ved hans hovedende«; BSB fulgt. |
| 12 | סֻלָּם | trappe | ladder | `{T:}` med »stige«. Se obs. 2 og åbent spm. 1. |
| 12 | מַלְאֲכֵי אֱלֹהִים עֹלִים וְיֹרְדִים בּוֹ | Guds engle steg op og ned ad den | God's angels were going up and down | Verberne »stige op/ned« som Joh 1,51. |
| 13 | נִצָּב עָלָיו | stod oven over den | at the top … was standing | `{T:}`: »ved siden af ham« (BSB-fodnote). |
| 13 | אֲנִי יְהוָה אֱלֹהֵי אַבְרָהָם אָבִיךָ | Jeg er HERREN, din far Abrahams Gud | I am the LORD, the God of your father Abraham | Som 26,24 »Jeg er din far Abrahams Gud«. |
| 14 | כַּעֲפַר הָאָרֶץ | som jordens støv | like the dust of the earth | DFB 2 Mos 8,12-13; Es 40,12 »jordens støv«. |
| 14 | וּפָרַצְתָּ | du skal brede dig ud | you will spread out | |
| 14 | וְנִבְרֲכוּ בְךָ … וּבְזַרְעֶךָ | I dig og i dit afkom skal alle jordens slægter velsignes | All the families of the earth will be blessed through you and your offspring | Passiv (nifal) som 12,3; ingen refleksiv-note (modsat 22,18; 26,4, der har hitpael). »jordens slægter« som DFB Zak 14,17; `{T:}` ordret »agerjordens«. |
| 15 | וּשְׁמַרְתִּיךָ | jeg vil bevare dig | I will watch over you | Samme verbum i v. 20 »bevare mig«; ens gengivelse. |
| 15 | אֶל־הָאֲדָמָה הַזֹּאת | til dette land | to this land | *ʔădāmāh* her = landet; se åbent spm. 3. |
| 15 | דִּבַּרְתִּי לָךְ | jeg har lovet dig | I have promised you | Ordret »talt til dig«. |
| 16 | אָכֵן | Sandelig | Surely | |
| 17 | מַה־נּוֹרָא | Hvor frygtindgydende | How awesome | Samme rod som »blev bange« (*wayyîrāʔ*); se obs. 5. |
| 17 | אֵין זֶה כִּי אִם־בֵּית אֱלֹהִים | Det er intet andet end Guds hus | This is none other than the house of God | |
| 18 | מַצֵּבָה | stenstøtte | pillar | Som 31,13.45; 35,14.20. |
| 19 | וְאוּלָם לוּז שֵׁם־הָעִיר לָרִאשֹׁנָה | men tidligere hed byen Luz | though previously the city had been named Luz | »Luz« som 35,6; 48,3. |
| 20 | וַיִּדַּר יַעֲקֹב נֶדֶר | Jakob aflagde et løfte | Jacob made a vow | Som 31,13 »hvor du aflagde et løfte til mig«. |
| 20 | לֶחֶם לֶאֱכֹל וּבֶגֶד לִלְבֹּשׁ | brød at spise og klæder at tage på | food to eat and clothes to wear | *læḥæm* = »brød« (husstil); *bægæd* her »klæder« (generisk). |
| 21 | בְשָׁלוֹם | uskadt | safely | Valgt så 33,18 »nåede han uskadt« (*šālēm*) genlyder; dér henviser `{E:}` hertil. |
| 21 | וְהָיָה יְהוָה לִי לֵאלֹהִים | så skal HERREN være min Gud | then the LORD will be my God | Hovedsætning fra v. 21b som BSB; `{T:}` med alternativet. |
| 22 | יִהְיֶה בֵּית אֱלֹהִים | skal blive et Guds hus | will be God's house | |
| 22 | עַשֵּׂר אֲעַשְּׂרֶנּוּ לָךְ | vil jeg give dig tiende | I will surely give You a tenth | Figura etymologica i `{T:}`. |

## Eksegetiske observationer

1. **v. 1-5 Velsignelsen gentages bevidst** – Isak velsigner nu Jakob med vilje og som Jakob, ikke som Esau (jf. 27,33). Ordene i v. 3-4 samler løfterne fra 17,1-8 (*ʔēl šadday*, »frugtbar og talrig«, landet »hvor du bor som fremmed«) og gives videre til Jakob. **[ingen note; `{T:}` kun om *mᵊgûrîm*]**
2. **v. 12 *sullām*** – hapax. Traditionen (LXX *klimax*, Vulgata *scala*, dansk »Jakobs stige«) har »stige«; mange nyere tolker ordet ud fra *sālal* »dynge op« og babylonske tempeltårnes trapper som »trappe/rampe«, hvor engle kan gå op og ned i begge retninger samtidig. **[`{T:}` sat]**
3. **v. 12 og Babel** – »dens top nåede op til himlen« (*rōʔšô maggîaʕ haššāmāymāh*) ligner 11,4 (*rōʔšô vaššāmayim*). Kontrasten: Babel bygges nedefra, Betel åbnes ovenfra. Joh 1,51 tager billedet op om Menneskesønnen. **[`{E:}` sat ved v. 12; ingen `{H:}`, da Joh 1,51 er en hentydning]**
4. **v. 13 *ʕālāyw*** – Kan betyde »over den« (trappen, BSB) eller »ved/over ham« (Jakob, BSB-fodnote; jf. 18,2 *niṣṣāvîm ʕālāyw* »stod ved ham«). Udkastet følger BSB. **[`{T:}` sat]**
5. **v. 16-17 frygt** – *wayyîrāʔ* »han blev bange« og *nôrāʔ* »frygtindgydende« har samme rod; det danske kan ikke bevare den fælles rod uden at blive tungt. **[ingen note]**
6. **v. 17 og v. 19 *bêt ʔĕlōhîm* / *bêt-ʔēl*** – Jakobs udråb »Guds hus« forklarer navnet Betel. **[`{T:}` ved v. 19]**
7. **v. 19 Luz og Betel** – Jos 16,2 synes at skelne mellem Betel og Luz, mens 35,6; Dom 1,23 identificerer dem. **[`{E:}` sat]**
8. **v. 20-22 løftets opbygning** – Betingelsen kan slutte i v. 21a (BSB) eller omfatte »HERREN er min Gud« (v. 21b), så hovedsætningen først begynder i v. 22. Jakobs forbehold svarer punkt for punkt til løftet i v. 15 (»med dig«, »bevare dig«, »føre dig tilbage«). **[`{T:}` sat ved v. 21]**
9. **v. 22 tiende** – Forbindelse til 14,20 (Abram og Melkisedek) og til Betel som kongelig helligdom (1 Kong 12,29-33; Am 4,4). **[`{E:}` sat]**
10. **v. 6-9 Esau** – Esau forsøger at gøre sin far tilpas ved at gifte sig ind i Abrahams slægt, men vælger den udstødte linje (Ismael, 21,10-14). 36,3 kalder Ismaels datter Basemat; navneforskellen behandles i 36,3's `{T:}`. **[ingen note]**
11. **v. 15 »dette land«** – *hāʔădāmāh hazzōʔt* er her det konkrete land Jakob forlader; »agerjorden« ville lyde unaturligt. Fælles regel for *ʔădāmāh* (»agerjorden«) er derfor fraveget her og i v. 14 (med `{T:}` i v. 14). **[`{T:}` kun ved v. 14]**
12. **Hebr 11,9.13** – patriarkerne som fremmede i det lovede land (jf. v. 4); hentydning. **[ingen note]**

## Konsistenspunkter mod Den Frie Bibel og projektets kapitler

- **Gud den Almægtige** (v. 3) som 35,11; 43,14; 48,3 (term:H7706).
- **»gøre dig frugtbar og talrig … forsamling af folk«** (v. 3) som 48,4 og 35,11.
- **Luz, Betel, stenstøtte, aflægge et løfte** som 31,13; 35,6.14-15; 48,3.
- **»Jeg er … din far Abrahams Gud«** (v. 13) som 26,24.
- **»jordens støv«** (v. 14) som DFB 2 Mos 8,12-13; Es 40,12.
- **»jordens slægter«** (v. 14) som DFB Zak 14,17; 22,18 og 26,4 har »alle jordens folk« for *gôyê hāʔāræṣ*.
- **»stige op og stige ned«** som DFB Joh 1,51 (verberne).
- **»morbror«** som 29,10; »Kana'ans døtre« som 36,2; »Mahalat«, »Nebajot« som 36,3.
- **»uskadt«** (v. 21) peger frem mod 33,18.
- **Karan**, **Be'ersheba**, **Paddan-Aram** som stilarket.

## Nye navneformer

- **Mahalat** (*māḥălat*) og **Nebajot** (*nᵊvāyôt*) – allerede brugt i 25,13 og 36,3; ingen nye.
- **Luz** – som 35,6 og 48,3.
- Ingen helt nye former.

## Åbne spørgsmål til reviewer

1. v. 12 *sullām*: »trappe« (som nu, med »stige« i `{T:}`) eller den traditionelle »stige« i teksten?
2. v. 13 *ʕālāyw*: »oven over den« (BSB) eller »ved siden af ham« i teksten?
3. v. 14-15 *ʔădāmāh*: »jordens slægter« / »dette land« (naturligt dansk) eller den fælles regel »agerjorden«? Hænger sammen med 12,3.
4. v. 20-22: Skal hovedsætningen begynde i v. 21b (som nu) eller i v. 22?
5. v. 2 »morfar/morbror« (mundret, som 29,10) eller ordret »din mors far / din mors bror«?
6. v. 21 *bᵊšālôm*: »uskadt« (forbinder med 33,18) eller »i fred« (som 26,29.31)?
