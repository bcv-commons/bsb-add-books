# Ruth 3: translator's notes

## What this draft is

A machine draft of Ruth 3 in Kuni (kvg), made 14.10.2026 from the Hebrew
(`orig/heb/rut003.txt`, 18 verses, Hebrew numbering = BSB numbering) with the BSB as the only
assisting translation. The drafter knows no Kuni: every word, suffix and construction was taken
from the Kuni NT, first through the verse pack (`_learn/packs/rut003.md`, built from the store
`profile/decisions.json` / `profile/observations.json` and the lexicon), then through
`_learn/concord.py` for what the pack lacked, and from chapters 1 and 2 (`rut001.txt`,
`rut002.txt`), whose renderings are reused verbatim wherever the Hebrew repeats (Ngólam,
tugu zakhapuka, nigi ekeza ezoqám, sasae mbasønakheis, ezoqa ndakinak, Evezøza qo
bèkhakheinøqavém, khakha-mbá, nqovotaz-qa, Betliem vemiav-té genøwáv, qanaqanus, nqægo khaiya,
Moab manqei-ak sævam is not needed here). Confidence per verse: high = every piece is an attested
NT form or a direct substitution in an attested frame; medium = one or two forms built by analogy
(prefix swap for person/gender, an imperative or optative built on an attested stem); low = a
construction without a close model. Status: experiment, not reviewed; no footnotes.

## Verse table

| Verse | Hebrew (key phrase) | Kuni (key rendering) | BSB | Comment (models, confidence) |
|---|---|---|---|---|
| 1 | וַתֹּאמֶר לָהּ נָעֳמִי חֲמוֹתָהּ | Khøuwa nøme, Lut-gu zakhapuka Neomi, Lut āv gumbøe-eín nqǽgo | One day Ruth's mother-in-law Naomi said to her | "Khøuwa nøme," (one day, Luk 1:8); "Saemon-gu zimpuka" (Simon's mother-in-law, Luk 4:38) → Lut-gu zakhapuka; frame "āv gumbøe-eín nqǽgo" (ch2 v2). High. |
| 1 | בִּתִּי הֲלֹא אֲבַקֶּשׁ־לָךְ מָנוֹחַ | Ngólam. No qo-te pusup manqei vawa-qa nombogó | My daughter, should I not seek a resting place for you | "Ngólam." (Mrk 5:34); resting place = "pusup manqei" (God's rest, Heb 4:3, 4:1); seek = vawa ("Sol-qa ndøvawát" Act 11:25, "ndøvawét" Act 10:19); "I want to X" = "X-qa nombogó" (Act 25:22 "yoge-qa nombogó", 1Co 15:1 "eim-qa nøzøgó"). The rhetorical question is a statement of intent (Luk 13:16 turns a "should not" question into statements). Low (vawa-qa nombogó built; the question lost). |
| 1 | אֲשֶׁר יִיטַב־לָךְ | Yaq qo eqeieqei qóyagát | that it may be well with you | Verbatim Eph 6:3 "that it may go well with you". High. |
| 2 | הֲלֹא בֹעַז מֹדַעְתָּנוּ אֲשֶׁר … | Ndakin, nqáe! Boaz, ndego tegi sasae mbasønakheis namba, qo sasae qoqogoam, ndego nigi ekeza ezoqám | Now is not Boaz, with whose servant girls you have been working, a relative of ours? | "Ndakin" (Act 9:6), "Nqáe!" (Luk 1:20); the relative as an appositive clause after the name, "X, ndego <clause>, tege ekeza ezoqam" (Jhn 18:26); "sasae qoqogoam" (you worked, ch2 v19); "nigi ekeza ezoqám" (ch2 v20). The "is not?" becomes "Look!" + statement. Medium. |
| 2 | הִנֵּה־הוּא זֹרֶה אֶת־גֹּרֶן הַשְּׂעֹרִים הַלָּיְלָה | Nqægo lova, ndego bali evem nonqo-te, bali ndǿ-evém | tonight he is winnowing barley on the threshing floor | "nqægo lova" tonight (Luk 12:20); threshing floor = "wit evem nonqo" (Luk 3:17, Mat 3:12) → "bali evem nonqo" by analogy; "wit nanga ndǿ-evém" (he will winnow the wheat, Luk 3:17) → "bali ndǿ-evém" (the participle rendered as a future). Medium (bali evem nonqo built). |
| 3 | וְרָחַצְתְּ וָסַכְתְּ וְשַׂמְתְּ שִׂמְלֹתַיִךְ עָלַיִךְ | Yaq nakémbá, qakeza kha vø̀sungúz, neka tae et sisip mbomambaqape qakeza kha-te vø̄qouz, neka qoqa ndabua eqeieqei vø̄-uz | Therefore wash yourself, put on perfume, and wear your best clothes | "Yaq nakémbá, mòqoqáv" (Act 7:34); wash = sunguz ("zøsungúz" Act 16:33, "gèsunguzím" Act 9:37), "qakeza kha" yourself (Act 16:28); perfume = "tae et sisip mbomambaqape" (Jhn 12:3, Luk 7:46), anoint = qouz ("mo꞉qóuz" Luk 7:46, "ande oil me gembøe-qouz" Act 10:38); "ndabua eqeieqei" fine clothes (Luk 7:25), "Qoqa ndabua qozaq nonqo vø̄-uz" (put on your cloak, Act 12:8). Imperative chain vø̀-/vø̄- as Act 22:16, Act 9:34. Medium (vø̀sungúz, vø̄qouz built). |
| 3 | וְיָרַדְתְּ הַגֹּרֶן | Yaq bali evem nonqo-té qonǿvís | Go down to the threshing floor | "Manqei-té qonǿvís" (go downstairs, Act 10:20). High. |
| 3 | אַל־תִּוָּדְעִי לָאִישׁ עַד כַּלֹּתוֹ … | Geté ta ezoqam ndøgo, qo mè꞉-otevák, atema lou loge neka izam vømǿ-navøēm | do not let the man know you are there until he has finished eating and drinking | "Ezoqa mè꞉-otevák" (no one knows, 1Co 2:11: negative future of otev, notice/understand) → "the man must not notice you"; "lou loge matev neka izam matev" (eating and drinking, 1Co 10:7); "atema ... vømǿ-navøēm" (until they finish, ch2 v21). Low (the jussive passive has no model). |
| 4 | וִיהִי בְשָׁכְבוֹ וְיָדַעַתְּ אֶת־הַמָּקוֹם … | Yaq ndego sømbiam-qa tewav, ta manqei ndøgo, ma ndego tesømbiam, eqeieqei gè-ometé | When he lies down, note the place where he lies | lie down = sømbi (sleep, lie: "sømbiam nonqo" Luk 9:58, "sasa ndøsømbiam" Mat 25:5); "X-qa tewav" (goes to X), "ta manqei ndøgo, ma ..." (ch1 v7); "gè-ometé" (take note of him, 2Th 3:14) with the place as object; "eqeieqei" carefully (2Pe 1:19). Low (tesømbiam, the object of gè-ometé built). |
| 4 | וּבָאת וְגִלִּית מַרְגְּלֹתָיו וְשָׁכָבְתְּ | Yaq ndǿgo qanøqáv, teqa zenda tokhotapak-te ndabua vø̀khofoé, neka ndǿgo vø̄sømbiam | Then go in and uncover his feet, and lie down | "qanøqáv" go (Jhn 20:17); uncover = take the cloth off his feet: "Qoqa tamak vø̀khofoé" (take off your sandals, Act 7:33), "zenda tokhotapak" feet (Luk 7:44); chained imperative "neka ... vø̄løvøen" (Act 9:34) → vø̄sømbiam. Medium (vø̄sømbiam built). |
| 4 | וְהוּא יַגִּיד לָךְ אֵת … | Yaq ndego ndø̀qa-eín, qo ande āv khoqotégō | he will explain to you what you should do | Verbatim Act 9:6 ("you will be told what you must do"). High. |
| 5 | כֹּל אֲשֶׁר־תֹּאמְרִי אֶעֱשֶׂה | Manqat ate ndægo, qo toqonø-ein, no ndæ̀matønumát | I will do everything you say | "Gekha matēv ndøgo, zo ... tozo-viømemat, no ndæ̀matønumát" (whatever you ask I will do, Jhn 14:13); "Qo toqonø-ein" (you tell me, Mrk 6:23); "manqat ate qægoam" all the words (Act 10:8); "gundu-qavøiu" she replied (Jhn 4:17). High. |
| 6 | וַתֵּרֶד הַגֹּרֶן וַתַּעַשׂ כְּכֹל … | bali evem nonqo-té gunøvís. Yaq ndugu matev ate ndægo ndømatanám, av tugu zakhapuka manqa gumbøe-løvua | she went down to the threshing floor and did everything her mother-in-law had instructed | "tenøvís" (he went down, Act 10:21), "ginøvis" (they went down) → gunøvís; "ndømatanám" did (Mat 1:20); "av ... geqambe-matanam" (as he did for you, Mrk 5:19); "manqa gezø-løvua" ordered (Heb 11:28) → gumbøe-løvua (she ordered her). Medium (gunøvís, gumbøe-løvua built). |
| 7 | וַיֹּאכַל בֹּעַז וַיֵּשְׁתְּ וַיִּיטַב לִבּוֹ | Boaz lou loge neka izam qamømbøe-navøem, yaq ndego khanakhanakh ndøndáp | After Boaz had finished eating and drinking and was in good spirits | "Yesu manqa manqate qamømbøe-navøem, yaq ..." (when Jesus had finished speaking, Luk 5:4); "lou loge ... neka izam" (1Co 10:7); "khanakhanakh ndøndáp" (she was overjoyed, Act 12:14; "my heart is glad" Act 2:26). High. |
| 7 | וַיָּבֹא לִשְׁכַּב בִּקְצֵה הָעֲרֵמָה | ndego bali nqeitam-qa vaev-té genøwáv, ndǿgo genø-sømbiám | he went to lie down at the end of the heap of grain | heap: no NT word; "bali nqeitam" (stored/piled barley) from nqeit (store: "lou nqeitam nonqo khoev" barn, Luk 3:17; "ginqeitømem" filled baskets, Jhn 6:13); "vaev-té genø-ámb" (placed at the end, 1Co 4:9); "ginø-sømbiám" (they lay sleeping, Mat 26:43) → genø-sømbiám. Low (bali nqeitam built). |
| 7 | וַתָּבֹא בַלָּט וַתְּגַל מַרְגְּלֹתָיו וַתִּשְׁכָּב | Lut khonoam-te ndowáv, teqa zenda tokhotapak-te ndabua vø̄khofoe, ndǿgo sasa ndøsømbiam | Ruth went in secretly, uncovered his feet, and lay down | "khonoam-te" in secret (Act 16:37, Eph 5:12); "ndowáv" came (Luk 7:16); "ekeza ndabua vø̄khofoe" (threw off their cloaks, Act 22:23); "venanqei sasa ndøsømbiam" (fell asleep, Mat 25:5). High. |
| 8 | וַיְהִי בַּחֲצִי הַלַּיְלָה וַיֶּחֱרַד … | Yaq qamø-umba ndøgo, Boaz gesuzam. Kha wageap-ús. Yaq ndego gendoqambun | At midnight, Boaz was startled, turned over | "Yaq qamø-umba ndøgo," (at midnight, Mat 25:6); "gesuzam" woke up (Act 16:27); "Kha wageap-ús." trembling (Luk 8:47, Act 16:29); "gendoqambun" turned (Jhn 1:38, 21:20). "Startled" = woke up + trembling. Medium. |
| 8 | וְהִנֵּה אִשָּׁה שֹׁכֶבֶת מַרְגְּלֹתָיו | Yaq nqáe! Sævam kopo, teqa zenda tokhotapak-te gusømbimám | there lying at his feet was a woman! | "Yaq nqáe! ... Sævam kopo mø̀ndøgoám" (Luk 13:11); "gesømbimám" (he lay bedridden, Act 9:33) with gu- for a woman. Medium (gusømbimám built). |
| 9 | וַיֹּאמֶר מִי־אָתְּ | Yaq ndego gumbobevap, “Gê, qo gekha ezoqâm?” | “Who are you?” he asked | "Pita gumbobevap" (asked her, Act 5:8); "Gê, qo gekha ezoqâm?" verbatim Jhn 1:19. High. |
| 9 | אָנֹכִי רוּת אֲמָתֶךָ | No Lút. No qogu sasae sævam | I am your servant Ruth | "No Yesú." (Act 9:5); "no qogu sasae sævam" (ch2 v13, Gal 4:22). High. |
| 9 | וּפָרַשְׂתָּ כְנָפֶךָ עַל־אֲמָתְךָ | Ambá qoqa ndabua-te qonø-gutavɨ́n | Spread the corner of your garment over me | request frame "Ambá ibøkha qonø-etoamɨ́n" (please give me water, Jhn 4:7) on gutav (cover: "vø̄gutav" light covered him, Act 9:3; "begutáv" cover her head, 1Co 11:6); the BSB's "garment" (ndabua), not the footnote's "wing" (taf, ch2 v12). Low (qonø-gutavɨ́n built). |
| 9 | כִּי גֹאֵל אָתָּה | Zapa ndǿgo, qo nigi ekeza ezoqám, ni nqovotaz-qa nqoqote꞉go | for you are a kinsman-redeemer | ch2 v20 "nigi ekeza ezoqa nøme, ndigu ni nqovotaz-qa ndi꞉gú" turned to 2sg with "av qo nqoqote꞉go" (as you are, Rev 19:10). Low (no term, see ch2). |
| 10 | בְּרוּכָה אַתְּ לַיהוָה בִּתִּי | Ngólam. Evezøza qo bèkhakheinøqavém | May the LORD bless you, my daughter | ch2 v4 verbatim (built there from Jhn 12:13 + Mrk 5:34); "gumbo-ein" (Luk 2:34). Medium. |
| 10 | הֵיטַבְתְּ חַסְדֵּךְ הָאַחֲרוֹן מִן־הָרִאשׁוֹן | Qoqa tanakh matev ndakin, qoqa tanakh matev bugukhokhof, mø̀ndøløvú | You have shown more kindness now than before | comparison "A, B mø̀ndøløvú" (ch1 v13, 1Jn 3:20); "tanakh matev" chesed (ch1 v8); "bugukhokhof" before (Act 15:14). Medium. |
| 10 | לְבִלְתִּי־לֶכֶת אַחֲרֵי הַבַּחוּרִים אִם־דַּל וְאִם־עָשִׁיר | qo ezoqa ndakinak-qa zita-te okhoeáv, oskiá ndøgo, gigiap-av ezoqam o gigiap eve ezoqam | you have not run after the younger men, whether rich or poor | "okhoeav" did not go (2Co 1:23 "Kolin taon-te okhoeav qagoam"); "ezoqa ndakinak" young men (ch2); "X-qa zita-te" after; "oskiá ndøgo, ezoqa kandakanda o ezoqa khasøkhasis" (whether great or small, Mrk 12:14); poor "gigiap-av ezoqam" (Luk 14:21), rich "gigiap eve ezoqam" (Luk 14:12, ch2 v1). High. |
| 11 | וְעַתָּה בִּתִּי אַל־תִּירְאִי | Ngólam. Ndakin qo møe ndø̀go᷄ | And now do not be afraid, my daughter | "Qo møe ndø̀go᷄" (Luk 1:13, store formula); "Ndakin mòqo-itán" (Act 9:6). High. |
| 11 | כֹּל אֲשֶׁר־תֹּאמְרִי אֶעֱשֶׂה־לָּךְ | Gekha matēv ndøgo, qo toqonø-ein, no nøtaqá-matanám | I will do for you whatever you request | "Gekha matēv ndøgo, ... no ndæ̀matønumát" (Jhn 14:13) with "nøtaqá-matanám" (I will do for you, Heb 6:14) and "qo toqonø-ein" (Mrk 6:23). High. |
| 11 | כִּי יוֹדֵעַ כָּל־שַׁעַר עַמִּי … | nogi vemiav-ak ezoqa ewaqape mø̀ndæzøtéz, qo sævam eqeieqeí. Qoqa matev eqeieqeí | all my fellow townspeople know that you are a woman of noble character | "vemiav-ak ezoqa ewaqape" (the whole town, Mrk 1:33) with nogi; "ndigu mø̀ndæzøtéz, noqa manqat unimanqatín" (they know that my word is true, 2Co 4:2); worthy = "ezoqa eqeieqeí" (1Co 15:9); "qoqa matev eqeieqei" (good character, 1Co 15:33). Medium (sævam eqeieqeí for אֵשֶׁת חַיִל). |
| 12 | וְעַתָּה כִּי אָמְנָם כִּי … | Unimanqatín. No qoge ekeza ezoqám, qo nqovotaz-qa nqate꞉go | Yes, it is true that I am a kinsman-redeemer | "Unimanqatín." (truly, 1Co 1:16); "av no nqate꞉go" (as I am, 1Co 7:7); qoge = your (a man, Jhn 20:17 "noge"). Low (as v9). |
| 12 | וְגַם יֵשׁ גֹּאֵל קָרוֹב מִמֶּנִּי | Geté ezoqa nøme ndêgó, até ndegó-a, qoge ekeza ezoqám. Ndego qo-te avønín. Ndego no mø̀ndøløvú, taqa yaq-te | but there is a redeemer nearer than I | "Geté ezoqa nøme ndêgó, ndego ..." (there is another who, Jhn 5:32); "Até ndegó-a" (he too, Luk 20:30); "avønín" near (1Jn 2:18); "A, B mø̀ndøløvú" exceeds (1Jn 3:20; "Ndego no ùnime꞉-løvúmb" he far surpasses me, Act 13:25); "taqa yaq-te" in that respect. Low ("nearer" paraphrased). |
| 13 | לִינִי הַלַּיְלָה | Nqægo lova, nqanek qanøqóm | Stay here tonight | "nqanek" here (Act 8:36, 9:17); "qanøqóm" sit/stay (Act 2:34). Medium (lodge rendered as stay). |
| 13 | וְהָיָה בַבֹּקֶר אִם־יִגְאָלֵךְ טוֹב יִגְאָל | Yaq qanaqanus, ndego qo nqovotaz-qa poev tømbogoat, ndøgo qanimáv. Yaq ndego betaqá-nqovotáz | in the morning, if he wants to redeem you, good. Let him redeem you | "unimanqatin poev tømbogoat te-te" (if He wants Him, Mat 27:43); "ndøgo qanimáv" (that is good, ch2 v22, Gal 4:18); optative betaqa- (betaqagó, betaqa-fàkha᷄n Mat 16:22; ch2 betaqá-etoám) on nqovotaz. Medium (betaqá-nqovotáz built). |
| 13 | וְאִם־לֹא יַחְפֹּץ לְגָאֳלֵךְ וּגְאַלְתִּיךְ … | Geté ndego qo nqovotaz-qa poeveav tøgoat, yaq no Evezøza-te, āv qaté-unimanqatín nqǽgo: No ekezan søtaqá-nqovotáz | But if he does not want to redeem you, as surely as the LORD lives, I will | "tøkeeav tøgoat" (if he does not help, 1Co 10:27) with poeveáv (does not want, 1Co 7:28); oath frame "Mbumbukiam-te, āv qati-unimanqatiním nqǽgo:" (we swore to God, Act 23:14), 1sg "āv qaté-unimanqatín nqǽgo" (Mat 10:32); "ekezan" myself (Mat 27:43); "Søtaqá-etoám" (I will give you, Mrk 6:23) → søtaqá-nqovotáz. Low (the oath idiom "as the LORD lives" has no model; søtaqá-nqovotáz built). |
| 13 | שִׁכְבִי עַד־הַבֹּקֶר | Yaq ndakin nqanek vø̀sømbiám, atema qanaqanús | Now lie here until morning | imperative built as vø̀khofoé (Act 7:33) on sømbiam; "atema khagús" (until evening, ch2 v17) → atema qanaqanús (the NT's "until daybreak" is "atema꞉ vøndōpave", Act 20:11). Medium. |
| 14 | וַתִּשְׁכַּב מַרְגְּלוֹתָיו עַד־הַבֹּקֶר | ndugu teqa zenda tokhotapak-te gusømbimám, atema qanaqanús | she lay down at his feet until morning | as v8 and v13. Medium. |
| 14 | וַתָּקָם בְּטֶרֶם יַכִּיר אִישׁ אֶת־רֵעֵהוּ | Geté qanaqanus lovølova-ús, ndugu até gundigu. Ezoqa nøme matavapøteáv, av nqægo, ngunuk Lūt | she got up before anyone else could recognize her | "Qanaqanus lovølova-ús" (early in the morning while dark, Jhn 8:2, Mat 20:1); "até gundigu" she got up (ch1 v6, Luk 7:38); "ndigu paev ezoqam matavapøteáv, av nqægo, ngenek Yesū" (they did not recognize that it was Jesus, Jhn 21:4). "Before anyone could recognize" = "while still dark; no one recognized her". Medium. |
| 14 | וַיֹּאמֶר אַל־יִוָּדַע כִּי־בָאָה הָאִשָּׁה הַגֹּרֶן | Boaz āv gene-eín nqǽgo, “Ezoqa mè꞉-otevák, av nqægo, sævam kopo bali evem nonqo-te ndowāv.” | Boaz said, “Do not let it be known that a woman came to the threshing floor.” | "Ezoqa mè꞉-otevák" (no one knows, 1Co 2:11) + "av nqægo" content with the macron (store indirect_speech). Low (as v3). |
| 15 | הָבִי הַמִּטְפַּחַת אֲשֶׁר־עָלַיִךְ וְאֶחֳזִי־בָהּ | Qoqa ndabua qozaq nonqo qotøndó-ndáp, neka qoté-ovøyām | Bring the shawl you are wearing and hold it out | shawl/cloak = "ndabua qozaq nonqo" (Act 12:8; "qozaq nonqo ndabua ... qotøndó-ndáp" bring the cloak, 2Ti 4:13); "Pingim qoté-ovøyām" (stretch out your hand, Luk 6:10). "which is on you" dropped (qoqa = your). Medium (ovøyam of a cloth built). |
| 15 | וַתֹּאחֶז בָּהּ וַיָּמָד שֵׁשׁ־שְׂעֹרִים … | Yaq ndugu sège-matanám. Yaq ndego bali yakhav siks, ta ndabua-te ndøqóuz, tuqa nqanqa-té vø̄ve | When she did so, he poured in six measures of barley and placed it on her | "Yaq Pita sège-matanám" (Peter did so, Act 12:8); "ndis-te ibøkha ndøqóuz" (poured water into the basin, Jhn 13:5); measures = yakhav (ch2 v17; "ezoqa siks" Act 11:12); "nqanqa-té gunǿvé" (puts it on his shoulders, Luk 15:5), "vø̄ve" placed (Act 2:33). Medium (yakhav as seah; "on her" = on her shoulders). |
| 15 | וַיָּבֹא הָעִיר | Yaq ndego Betliem vemiav-té genøwáv | Then he went into the city | ch2 v18 (she) / ch1 v1 (he); the BSB's "he". High. |
| 16 | וַתָּבוֹא אֶל־חֲמוֹתָהּ וַתֹּאמֶר מִי־אַתְּ בִּתִּי | Lut tugu zakhapuka-té gunøqaván. Yaq Neomi gumbobevap, “Ngólam. Gê, áv khané꞉go, qo-te?” | When Ruth returned to her mother-in-law, Naomi asked her, “How did it go, my daughter?” | "tugu namba qawan-té gunøqaván" (she went back to her sister, Jhn 11:28); "gumbobevap" (Act 5:8); "Gê, áv khané꞉go, ..." (how is it that, Act 2:8) → "how is it with you?", the BSB's reading of "who are you?". Medium (the question built). |
| 16 | וַתַּגֶּד־לָהּ אֵת כָּל־אֲשֶׁר עָשָׂה־לָהּ הָאִישׁ | Lut tugu zakhapuka, emanqat ate qægoam vømbō-vøndaz, av Boaz gumbøe-matanam | Ruth told her all that Boaz had done for her | "tuqa emanqat ate qægoam, vømbō-vøndaz" (told him the whole truth, Mrk 5:33); "av Mbumbukiam Evezøza geqambe-matanam" (what the Lord has done for you, Mrk 5:19) → gumbøe-matanam (he for her). Medium. |
| 17 | שֵׁשׁ־הַשְּׂעֹרִים הָאֵלֶּה נָתַן לִי | Nqanek bali yakhav siks, ndego genø-etoam | He gave me these six measures of barley | "nqanek" this (Luk 1:20); "genø-etoam" he gave me (2Co 13:10, 14x). High (yakhav as v15). |
| 17 | כִּי אָמַר אַל־תָּבוֹאִי רֵיקָם אֶל־חֲמוֹתֵךְ | ndego āv genømbe-eín nqǽgo, ‘Qo qogu zakhapuka-te, khakha-mbá nango ndø-òkho᷄.’ | for he said, ‘Do not go back to your mother-in-law empty-handed.’ | "āv genømbe-eín nqǽgo" (he said to me, ch2 v21); "khakha-mbá" empty-handed (Luk 1:53, ch1 v21); prohibitive "ndø-òkho᷄" (do not go, 1Ti 5:21, attested as such) with nango (back). High. |
| 18 | שְׁבִי בִתִּי עַד אֲשֶׁר … | Ngólam. Qanøqóm, atema nqanek matev vømǿfakhān. Yaq manqat toqomǿ-ewág, gekha matēv ndøgo, tøfakhan | Wait, my daughter, until you find out how things go | שְׁבִי "sit" = "qanøqóm" (Act 2:34); "atema Evezøza vømǿfakhān" (until the Lord comes, 1Co 4:5) with matev; "manqat ndǿgo toqomǿ-ewág, gekha matēv ndøgo, ..." (you will be told what, Act 22:10); "Nqanek matev tøfakhan" (when this happens, 1Co 15:54). Medium. |
| 18 | כִּי לֹא יִשְׁקֹט הָאִישׁ … | ta ezoqam ndøgo, pusa gétayák, atema nqanek manqat nqægo khaiya vømǿ-navøēm | he will not rest unless he has resolved the matter today | "pusa ndø̀tá" rests (Heb 4:10); "yaq-fia gétayák" (will not hold judgment, Mat 23:16, Rom 8:1) gives the 3sg negative future of the same stem ta; "atema ... vømǿ-navøēm" (ch2 v21); "nqægo khaiya" today (Act 19:40). Low (pusa gétayák built; "unless" rendered as "until"). |

## Exegetical observations

- v1 מָנוֹחַ "resting place" (a home with a husband) is "pusup manqei", the NT's "place of rest"
  (Heb 4:1-11); chapter 1 v9 had "pusup" + "zivis-qá khoev-te" for מְנוּחָה. The rhetorical
  "should I not seek" is a statement of intent; the NT turns such questions into statements
  (Luk 13:16) or asks them with the negated verb ("Gê, no Yesu ometeâv?", 1Co 9:1), and I found
  no deontic 1sg form to negate.
- v2 הֲלֹא "is not Boaz ...?" = "Nqáe!" + statement, the NT's attention marker (ch2 v8 "Listen").
  Threshing floor: the NT's "wit evem nonqo" (wheat-winnowing place, Luk 3:17) with bali;
  "winnow" = evem (Luk 3:17 "ndǿ-evém"); the Hebrew participle "is winnowing tonight" is a
  future ("will winnow tonight").
- v3 The three preparations are three chained imperatives (Act 22:16 pattern). "Perfume" is the
  NT's "tae et sisip mbomambaqape" (Jhn 12:3 nard); "anoint/put on" = qouz, which also means
  "pour" (Jhn 13:5) and is reused in v15. "Do not let the man know you are there" has no
  jussive-passive model; "ta ezoqam ndøgo, qo mè꞉-otevák" says "the man must not notice you"
  with the negative future of otev (1Co 2:11); the same form carries v14 "do not let it be
  known".
- v4, 7, 8, 13, 14 "lie down" (שׁכב) is the sleep stem sømbi, the NT's word for lying on a mat
  (Act 9:33) and sleeping (Mat 25:5); the gender/number forms gusømbimám, genø-sømbiám and the
  imperatives are built. "Uncover his feet" is made concrete as "take the cloth off his feet"
  (khofoe, the verb of Act 7:33 "take off your sandals" and Act 22:23 "threw off their cloaks").
- v7 "the heap of grain" (עֲרֵמָה) has no NT word: "bali nqeitam" (stored/piled barley) from the
  store-stem nqeit (barn, Luk 3:17). "Was in good spirits" = "khanakhanakh ndøndáp" (became glad).
- v8 "startled" (חרד, trembled) = "woke up" (gesuzam, Act 16:27) + "Kha wageap-ús." (trembling,
  Luk 8:47); "turned over" (נלפת) = "gendoqambun", the NT's "turned (to look)".
- v9 "spread your wing/garment over me": the BSB's main text (garment) is followed with the NT's
  "cover" (gutav) in a polite request (Ambá ... -ɨn); a reviewer may prefer the wing image
  ("qoqa taf mokho-te"), which would echo Boaz's blessing in 2:12.
- v9, 12, 13 גֹּאֵל keeps chapter 2's description (a relative who is there to redeem us,
  nqovotaz-qa) in predicate form: "qo nigi ekeza ezoqám, ni nqovotaz-qa nqoqote꞉go" (you are
  our relative, to redeem us); "redeem you" uses the 2sg-object optative/future built on
  nqovotaz (betaqá-, søtaqá-).
- v10 "more kindness now than before" uses the comparison frame of 1:13 (A, B mø̀ndøløvú);
  "run after the young men" is "went after" (okhoeav, did not go); "whether rich or poor" uses
  the NT's "oskiá ndøgo, A o B" (Mrk 12:14) with the NT's own words for rich and poor.
- v11 אֵשֶׁת חַיִל "woman of noble character": "sævam eqeieqeí" (a worthy woman, after
  "ezoqa eqeieqeí" 1Co 15:9) plus "Qoqa matev eqeieqeí" (your character is good, 1Co 15:33);
  "all the gate of my people" = "all the people of my village" (Mrk 1:33). "They know that" is
  the 2Co 4:2 frame.
- v12 "a redeemer nearer than I": "near" (avønín) is spatial/temporal in the NT; closeness of
  kin is expressed as "he is near to you; he exceeds me in that" (the Act 13:25 "he surpasses
  me" idea with 1Jn 3:20's mø̀ndøløvú).
- v13 "as surely as the LORD lives": no NT counterpart; the swearing frame "I swear to God
  thus:" (Act 23:12-14, Mat 10:32) carries the oath but not "lives". "Stay/lodge here tonight"
  and "wait" (v18 שְׁבִי) are both "qanøqóm" (sit, stay).
- v14 "before anyone could recognize another" = "early, while it was still dark, she got up;
  no one recognized that it was Ruth", with the NT's "did not recognize that it was Jesus"
  (Jhn 21:4).
- v15 The shawl (מִטְפַּחַת) is the NT's "ndabua qozaq nonqo" (wrap-cloth, cloak); "hold it out"
  = "stretch it out" (Luk 6:10's hand); "six measures" = "bali yakhav siks" with the basket/
  measure unit of 2:17 (the real amount, about 40 l, is not conveyed); "placed it on her" =
  "put it on her shoulders" (Luk 15:5). "He went into the city": the BSB's masculine reading
  (the Hebrew ketiv) is kept.
- v16 מִי־אַתְּ "who are you?" is read with the BSB as "how did it go?" ("Gê, áv khané꞉go, qo-te?").
- v18 "he will not rest unless he has resolved the matter today" = "he will not rest until he
  has finished this matter today" (pusa gétayák, built from "yaq-fia gétayák" will not hold
  judgment, Mat 23:16); "how things go" = "what happens" (tøfakhan).

## Dialect and style (corpus counts, Kuni NT)

- Divine name as chapters 1-2: Evezøza for YHWH (vv. 10, 13); no Elohim in this chapter.
- Speech frames as before: "āv gumbøe-eín nqǽgo" (v1), "gumbo-ein" (vv. 10, 15, 18),
  "gundu-qavøiu" (vv. 5, 9), "gumbobevap" (asked her, vv. 9, 16; Act 5:8), "āv gene-eín nqǽgo"
  (v14), "āv guni-eín nqǽgo" (v17), "āv genømbe-eín nqǽgo" (he said to me, v17); orders as
  "manqa ... -løvua" (heading, v6; 19 verses with manqa + løvua).
- Household and body: ndabua 233 (cloth, garment), ndabua qozaq nonqo / qozaq nonqo ndabua 15
  (cloak), tae et sisip (mbomambaqape) 11 verses (perfume), qouz 40 (pour, anoint), sunguz 23
  (wash), zenda tokhotapak 57 (feet), nqanqa-te 2 (shoulders), yakhav 15 (basket, measure),
  bali (barley), wit evem nonqo 2 (threshing floor), evem 6 (winnow), nqeit 57 (store, put in).
- Night and sleep: lova 49 (night), nqægo lova 7 verses (tonight), umba 46 (midnight forms),
  lovølova 34 (dark, night), qanaqanus 25 (morning), sømbi 33 (sleep, lie), suzam 23 (wake),
  khonoam 45 (secret).
- People and kin: ekeza ezoqam 35 verses (relative), sasae sævam 5 verses (maidservant),
  sasae mbasønakheis (servant girls, ch2), ezoqa ndakinak 15 verses (young men), gigiap-av
  ezoqam 42 verses (the poor), gigiap eve ezoqam 5 verses (the rich), vemiav-ak ezoqa ewaqape
  (the whole town), nqovotaz 33 (redeem, set free), eqeieqei 609 (good, worthy).
- Mind and speech: poev 298 / poeveav 57 (want / not want), vawa 27 (seek), zøtez 238 (know),
  matøvem / matavapøteav 104 (recognize / not recognize), unimanqatin 1440 (true, believe,
  swear), khanakhanakh 275 (joy), kha wageap 4 verses (trembling), gendoqambun 10 (turned),
  avønin 165 (near), matanam 339 (do).
- Imperatives attested as such: qonǿvís, qanøqáv, vø̀khofoé, vø̄-uz, qanøqóm, qotøndó-ndáp,
  qoté-ovøyām, ndø-òkho᷄ (prohibitive), møe ndø̀go᷄ (prohibitive); built on the vø̀-/vø̄- chain:
  vø̀sungúz, vø̄qouz, vø̄sømbiam, vø̀sømbiám.
- Headings: no tone marks, verb-final, actors named (as chapters 1-2).
- Forms built by analogy (not attested as such): vawa-qa nombogó, bali evem nonqo, bali
  ndǿ-evém, vø̀sungúz, vø̄qouz, mè꞉-otevák with a named subject, sømbiam-qa tewav, tesømbiam,
  vø̄sømbiam, vø̀sømbiám, gusømbimám, genø-sømbiám, gunøvís, gumbøe-løvua, gumbøe-matanam, bali
  nqeitam, qonø-gutavɨ́n, nqoqote꞉go / nqate꞉go in the redeemer predicate, bèkhakheinøqavém (ch2),
  betaqá-nqovotáz, søtaqá-nqovotáz, atema qanaqanús, "Gê, áv khané꞉go, qo-te?", "Ndego no
  mø̀ndøløvú, taqa yaq-te", pusa gétayák, bali yakhav siks, tuqa nqanqa-té vø̄ve, sævam eqeieqeí,
  nogi vemiav-ak ezoqa ewaqape, qoté-ovøyām of a cloth, gè-ometé of a place.

## New name forms

None. Lut, Boaz, Neomi, Betliem as in chapters 1-2; "Lut-gu zakhapuka" (Ruth's mother-in-law)
follows "Saemon-gu zimpuka" (Luk 4:38).

## Open questions

1. v1 "should I not seek a resting place for you?": rendered as a statement of intent
   ("No qo-te pusup manqei vawa-qa nombogó", built after "yoge-qa nombogó", Act 25:22). Is there
   a natural rhetorical form for "ought I not …?", and is "pusup manqei" usable for a home?
2. Threshing floor "bali evem nonqo", winnow "evem", heap "bali nqeitam": the first two follow
   Luk 3:17's "wit evem nonqo", the heap is built; a speaker should supply the real farming
   words (see also chapter 2's gleaning and sheaves).
3. "Lie down" as the sleep verb sømbi, with the built forms gusømbimám, genø-sømbiám and the
   imperatives vø̄sømbiam / vø̀sømbiám; "uncover his feet" as "take the cloth off his feet".
4. v3, 14 "do not let the man know / do not let it be known": "X mè꞉-otevák" (X will/must not
   notice) rests on 1Co 2:11; the mood (jussive) and the grave on mè꞉ need checking.
5. v9 "spread your garment over me" as the request "Ambá qoqa ndabua-te qonø-gutavɨ́n"; the
   wing reading (taf) is the alternative. The kinsman-redeemer still has no term; v9, 12, 13
   use the chapter 2 description in predicate form and the built 2sg-object forms
   betaqá-nqovotáz / søtaqá-nqovotáz.
6. v12 "a redeemer nearer than I" paraphrased ("he is near to you; he exceeds me in that"): is
   there a kinship word for "closer relative"?
7. v13 "as surely as the LORD lives": the NT swearing frame "no Evezøza-te, āv qaté-unimanqatín
   nqǽgo:" drops "lives"; a Kuni oath idiom may exist.
8. v15 "six measures" = "bali yakhav siks": the unit is the basket of 2:17; the amount is
   unknown to the reader. "Placed it on her" = "put it on her shoulders" (nqanqa, Luk 15:5).
9. v16 "How did it go?" as "Gê, áv khané꞉go, qo-te?" (how is it with you): built from Act 2:8;
   tone and idiom unverified. The Hebrew "who are you?" could also be kept as in v9.
10. v18 "he will not rest" = "pusa gétayák", from "yaq-fia gétayák" (will not hold judgment);
    the stem ta is the same, the collocation is not attested. "Unless he has resolved the matter
    today" is rendered "until he has finished this matter today".
11. "Until morning" = "atema qanaqanús" (after "atema khagús"); the NT's own "until daybreak"
    is "atema꞉ vøndōpave" (Act 20:11), whose spelling (꞉ after atema) I did not copy.
