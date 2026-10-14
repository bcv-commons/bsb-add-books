# Ds Buech Rut – Arbeitsstilblatt für die berndeutschen Entwürfe (`export/ch-de-be/ch-de-be_BSB/rut/`)

Stand: 02.10.2026 · gilt sinngemäss auch für Jona (`export/ch-de-be/ch-de-be_BSB/jon/`)

## Grundsätze

- Übersetzt wird **direkt aus dem Hebräischen** (`orig/heb/rutNNN.txt`, klauselweise masoretischer Text).
- Einzige Hilfsübersetzung: **Berean Standard Bible** (`reference/BSB/rutNNN.txt`). Sie dient nur dazu, Entscheidungen zu kippen, wo das Hebräische mehrere Wiedergaben zulässt. SVK wird diesmal **nicht** verwendet.
- Zielsprache: **Berndeutsch**. Wortschatz und Schreibweise werden dort abgelesen; wird die geläufige Berner Form gewählt und im Notizfile vermerkt.
- **Sauberer Text:** keine Inline-Noten (`{T:}`, `{E:}`, `{H:}`, `{N:}`) im Bibeltext. Alle Übersetzungs- und exegetischen Hinweise stehen ausschliesslich in `rutNNN_notes.md` (auf **Hochdeutsch**).
- Pro Kapitel genau **eine** Fassung (`rutNNN.txt`) – kein Zwei-Spur-System wie bei Josua.

## Dateien pro Kapitel

- `rutNNN.txt` – der berndeutsche Entwurf
- `rutNNN_notes.md` – Notizen für die Durchsicht (Hochdeutsch)
- `rutNNN_footnotes.txt` – bei Bedarf: Fussnoten für Leser wie in der BSB (berndeutsch, separat vom Text, Format `vN Stichwort: Text`), z. B. Namensdeutungen
- übergreifend: `rut_style_guide.md` (dieses Blatt), `rut_review_overview.md` (offene Punkte über alle Kapitel)

## Dateikopf und Layout

```
!!<Reifegrad: Entwurf>!!
!!<Übersetzung: Maschinenentwurf aus dem Grundtext (orig/heb/rutNNN.txt), abgeglichen mit der Berean Standard Bible>!!
!!<Exegetische Bearbeitung: Noch nicht erfolgt>!!
!!<Literarische Prüfung: Noch nicht erfolgt>!!
!!<Datum dieser Version: 02.10.2026>!!

===Ds Buech Rut, Kapitel N===



v1 Fortlaufende Prosa mit Versmarkern inline … v2 … Zeilenumbruch bei ca. 100 Zeichen.
```

- Überschriften `==…==` sind redaktionell, berndeutsch.
- innere Rede `‚…‘`.
- `(1Mo 38)`.

## Feste Wiedergaben

| Hebräisch | Berndeutsch | Begründung |
|---|---|---|
| יהוה | **der HERR** (vom HERR, em HERR) | Entscheid 02.10.2026: Grossbuchstaben machen den Gottesnamen sichtbar (wie HERREN im dänischen Projekt, Luther, Zürcher). |
| אלהים | Gott | |
| שַׁדַּי | der Allmächtig | |
| חֶסֶד | Tröiji (… d Tröiji halte / erwyse) | Schlüsselwort 1,8; überall gleich halten. |
| גֹּאֵל / גאל | **Löser** / uslöse (mit Lösrächt) | deutsche Fachtradition (Luther, Zürcher »Löser«). Alternative »Erblöser«, »Verwandte mit Lösrächt« – offen |
| מֹואֲבִיָּה | d Moabitere / moabitischi Froue | |
| כַּלָּה | Schwigertochter, Pl. Schwigertöchtere | |
| חָמוֹת | Schwigermueter | |
| שְׂעֹרִים / חִטִּים | Gärschte / Weize | |
| קָצִיר | Ärn | |
| שִׁבֳּלִים | Ähri | |
| גֹּרֶן | Tenn | |
| נשׁק | es Müntschi gä | |
| בכה (mit נשׂא קול) | lut aafa briegge | |
| הִנֵּה | lue / lueget | |
| זִקְנֵי הָעִיר | (Kap. 4 – zu entscheiden: »d Eltischte« vs. »d Ratsherre vo der Stadt«) | |

## Namen

Formen aus Mt 1,3-6 übernommen, wo vorhanden:

| Hebräisch | Berndeutsch | Quelle |
|---|---|---|
| רוּת | d Rut | Mt 1,5 |
| בֹּעַז | der Boas | Mt 1,5 |
| עוֹבֵד | der Obed | Mt 1,5 |
| יִשַׁי | der Isai | Mt 1,5 |
| דָּוִד | der David | |
| פֶּרֶץ, חֶצְרוֹן, רָם, עַמִּינָדָב, נַחְשׁוֹן, שַׂלְמָה/שַׂלְמוֹן | der Perez, der Hezron, der Ram, der Amminadab, der Nachschon, der Salmon | Mt 1,3-5 |
| תָּמָר | d Tamar | Mt 1,3 |
| נָעֳמִי | d Noomi | Luther/Zürcher |
| מָרָא | Mara | |
| אֱלִימֶלֶךְ | der Elimelech | Luther/Zürcher |
| מַחְלוֹן, כִּלְיוֹן | der Machlon, der Kiljon | Luther/Zürcher |
| עָרְפָּה | d Orpa | |
| בֵּית לֶחֶם יְהוּדָה | Betlehem z Juda | |
| אֶפְרָתִים / אֶפְרָתָה | Efratiter / Efrata | |
| מוֹאָב | Moab, ds Land Moab | |
| רָחֵל, לֵאָה | d Rahel, d Lea | |
| יְהוּדָה | Juda | |

## Zahlen

zwee (m.)/zwo (f.)/zwöi (n.), drei, vier, füf, sächs, sibe, acht, nüün, zäh (attributiv auch »zäche«).

## Notizfile (`rutNNN_notes.md`), Hochdeutsch

1. Was der Entwurf ist (1-2 Zeilen)
2. Tabelle *Vers · Hebräisch · Berndeutsch · BSB · Kommentar* – wo die Wiedergabe eine bewusste Entscheidung ist
3. Exegetische Beobachtungen, nummeriert, mit Versangabe
4. Mundart-/Stilpunkte
5. Offene Fragen für die Durchsicht
