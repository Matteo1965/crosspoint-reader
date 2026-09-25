# CPHUN-138 – betűköz-profilok (előkészítés)

Alap: `agent/cphun-137-search-edit-mode`. **Ez tervezési ág; firmware-build még nincs elindítva.**

## Rögzített felhasználói működés

- **Betűköz-korrekció**: KI = 0%, Gyenge = 10%, Közepes = 40%, Erős = 70%. A korábbi beállítások átállítását és a tartós mentést ellenőrizni kell; az alvásból visszatérés korábbi javítását nem szabad felülírni.
- **Optimalizációs küszöb**: KI = nincs pontszám szerinti korlátozás; Gyenge = 50 pont; Közepes = 60 pont; Erős = 70 pont. A magasabb pontszám szigorúbb feltétel. A KI **nem** kapcsolja ki a betűköz-korrekciót: minden más védelmi szempontból megengedett betűpárra érvényesíteni kell a választott korrekciót.
- A két beállítás egymástól független.
- Serif betűtípusoknál a Bitter-profil kísérleti alkalmazása; Noto Serif 16 pt saját mért profilját továbbra is preferálni kell. A tényleges glyph-advance/font-metrika az aktív betűtípusból származzon.
- A tördelés szélességmérése, pozíciószámítása és mindkét tényleges rajzolási út ugyanazon jogosultsági és védelmi logikát alkalmazza (AA/ABA, hárombetűs szavak, kerning, sorkeret).
- Az egyéni SD-fontok automatikus Serif/Sans felismerése és a Noto Sans új mérése **nem** része ennek a buildnek.

## A build indítását blokkoló forrásadatok

A CPHUN-119 forrásában lévő Bitter-lista 655 darab **legalább 60 ponttal kiválasztott** betűpárt tartalmaz, de nem tartalmazza az egyedi pontszámokat, és hiányzik az 50/70-es küszöbhöz szükséges teljes mérési tábla. A CPHUN-130 Noto Serif 16 pt listája hasonlóan 75 szűrt pár, pontszám nélkül.

Ne címkézzük át a jelenlegi 60 pontos listát 50/70 pontossá. A küszöbök megvalósítása előtt vissza kell nyerni a tényleges mérési eredményeket, vagy reprodukálni kell a mérést az eredeti eljárással. A küszöb nélküli módhoz is szükségesek a geometriai védelmi feltételek.

## Elfogadási tesztek

1. A KI korrekció nulla plusz betűközt ad, bármilyen küszöbnél.
2. A KI küszöb nem tiltja az optimalizációt, és nem kerüli meg a védett betűkombinációkat.
3. 50 → 60 → 70 pont sorrendben a jogosult párok halmaza csak szűkülhet.
4. Bitter (12/14/16/18 pt), Noto Serif (különösen 16 pt), más Serif font: ugyanaz a mérés / kirajzolás pixelpozíció.
5. Korábban mentett értékek átállítása, mentés, újraindítás és alvásból visszatérés.
