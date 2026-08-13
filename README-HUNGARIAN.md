# CrossPoint Hungarian

Magyar nyelvi útmutató az Xteink X4-hez készült CrossPoint Hungarian firmware-hez.

Jelenlegi kiadás: **CrossPoint Hungarian v1.5.0 – Dictionary & Stemming Beta 1**  
Tag: `hu-v1.5.0-dict-beta.1`

> Ez egy Beta / Pre-release változat. Valós Xteink X4 készüléken tesztelt, de a magyar stemming további szóalakokkal még bővülhet.

## Főbb funkciók

- magyar automatikus EPUB-elválasztás;
- magyar StarDict szótár támogatása;
- magyar toldalékolt szóalakok stemmingje;
- javított összetett szó fallback;
- javított StarDict indexkeresés magyar címszavaknál;
- Python és C++ regressziós tesztek.

Példák:

```text
szakemberekben → szakember
szakembereken  → szakember
kabátja         → kabát
gyapotruhákkal → ruha
```

A `gyapotruhákkal → ruha` fallback szándékos: a tesztelt magyar StarDict indexben a `gyapotruha` nem szerepel önálló címszóként, a `ruha` viszont igen.

## Firmware letöltése

Release:

https://github.com/Matteo1965/crosspoint-reader/releases/tag/hu-v1.5.0-dict-beta.1

Töltsd le:

```text
CrossPoint-Hungarian-v1.5.0-dict-beta.1.zip
```

Csomagold ki, majd a benne lévő `firmware.bin` fájlt használd a telepítéshez.

## Telepítés Xteink X4-re

1. Csatlakoztasd az X4-et adatátvitelre alkalmas USB-C kábellel.
2. Nyisd meg a CrossPoint webes flashert:
   https://crosspointreader.com/#flash-tools
3. Válaszd az **X4** készüléket.
4. Válaszd a **Custom .bin** lehetőséget.
5. Tallózd be a kicsomagolt `firmware.bin` fájlt.
6. Indítsd el a firmware feltöltését.

USB-locked készülékekkel kapcsolatban lásd a projekt fő `README.md` fájlját.

## Magyar StarDict szótár

A firmware nem tartalmaz magyar szótár-adatbázist. A szótári kereséshez külön, kompatibilis StarDict szótár szükséges.

A támogatott fájlok:

```text
.idx
.dict vagy .dict.dz
.ifo
```

Az `.idx` fájlnak tömörítetlennek kell lennie; `.idx.gz` közvetlenül nem használható.

### Könyvtárstruktúra

Másold a szótárat az SD-kártya `/dictionaries/` mappájába, külön almappába. Például:

```text
/dictionaries/
└── Magyar_Ertelmezo/
    ├── magyar-ertelmezo.dict
    ├── magyar-ertelmezo.idx
    └── magyar-ertelmezo.ifo
```

A rejtett `/.dictionaries/` mappa is használható.

Egy almappában csak egy StarDict szótár legyen. Több különböző `.idx` fájlt tartalmazó mappát a CrossPoint kihagy.

## Szótár kiválasztása

Az X4-en nyisd meg:

```text
Settings → Reader → Dictionary
```

és válaszd ki a telepített magyar szótárt.

A Dictionary menüpont csak akkor jelenik meg, ha a firmware használható StarDict szótárat talál az SD-kártyán.

## `.qidx` gyorsító index

Az első kereséskor a CrossPoint megjelenítheti:

```text
Indexing dictionary…
```

Ekkor a firmware egy `.qidx` gyorsító fájlt készít az `.idx` mellé. Ez normális.

```text
magyar-ertelmezo.idx
magyar-ertelmezo.qidx
```

A `.qidx` biztonságosan törölhető; a firmware automatikusan újraépíti. Ha az `.idx` fájlt lecseréled, érdemes a régi `.qidx` fájlt is törölni.

## Szótári keresés EPUB olvasás közben

A keresést az olvasó **Look Up** funkciójával vagy a Dictionary funkcióhoz rendelt hosszú gombnyomással lehet indítani.

A firmware először pontos címszót keres. Ha nincs találat, a magyar stemming engine lehetséges alapalakokat generál, és azok közül olyan találatot választ, amely ténylegesen szerepel a telepített StarDict indexben.

Ezért a végeredmény függ a használt szótár címszóállományától is.

## Magyar automatikus elválasztás

A magyar elválasztási adatok a firmware részei, ezért külön fájlt nem kell telepíteni.

Az angol elválasztás is megmaradt. A firmware méretkorlátai miatt más beépített elválasztási szótárak eltávolításra kerülhettek ebből a magyar változatból.

## Ismert korlátozások

Ez a kiadás Beta. A magyar nyelv gazdag toldalékolása miatt előfordulhatnak még olyan szóalakok, amelyek nem a kívánt címszóra vezetnek, vagy amelyekhez a megfelelő alapszó nincs benne a telepített StarDict szótárban.

Egy hibás találatnál ezért azt is érdemes ellenőrizni, hogy a várt alapszó ténylegesen szerepel-e a `.idx` fájlban.

## Hibás szóalak jelentése

Hasznos hibajelentési forma:

```text
Keresett szó:   szakemberekben
Kapott találat: ...
Elvárt találat: szakember
Release:        hu-v1.5.0-dict-beta.1
```

Ha nincs találat:

```text
Kapott találat: None
```

Issues:

https://github.com/Matteo1965/crosspoint-reader/issues

## Fejlesztési háttér

A magyar stemming regressziós tesztekkel készül Python oldalon és a firmware tényleges C++ implementációján is.

A fejlesztés során kiderült, hogy a tesztelt magyar StarDict `.idx` raw-byte sorrendben rendezett. A korábbi ASCII case-insensitive bináris keresés ezért bizonyos címszavakat – például a `kabát` szót – kihagyhatott. A Beta 1 ezt a StarDict lookup hibát javítja.

## Szótárlicenc

A magyar StarDict szótár adatfájljai nem részei ennek a repositorynak és nem részei a GitHub Release firmware assetjének. A felhasználónak saját, jogszerűen használható kompatibilis StarDict szótárat kell telepítenie.

A szótár használatára és terjesztésére annak saját licence és forrásának feltételei vonatkoznak.
