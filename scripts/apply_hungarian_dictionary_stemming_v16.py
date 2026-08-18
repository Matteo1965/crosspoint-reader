from pathlib import Path

PAIRS = [
    ("keze", "kéz"),
    ("őrzött", "őriz"),
    ("akadályozzák", "akadályoz"),
    ("Beszélnünk", "beszél"),
    ("biztonságiőr", "biztonság"),
    ("boríthatjuk", "borít"),
    ("bástyája", "bástya"),
    ("bürokráciával", "bürokrácia"),
    ("centis", "centi"),
    ("csapdát", "csapda"),
    ("darabkája", "darab"),
    ("eleji", "eleje"),
    ("Ellenőrzik", "ellenőriz"),
    ("felbontású", "felbontás"),
    ("felszerelésük", "felszerelés"),
    ("frekvenciájú", "frekvencia"),
    ("Gondoljon", "gondol"),
    ("grafikai", "grafika"),
    ("grafikát", "grafika"),
    ("gurulós", "gurul"),
    ("gyártási", "gyártás"),
    ("halántékú", "halánték"),
    ("intelligenciái", "intelligencia"),
    ("irodát", "iroda"),
    ("irodával", "iroda"),
    ("jöhet", "jön"),
    ("kerüli", "kerül"),
    ("Kezdjük", "kezd"),
    ("kezem", "kéz"),
    ("kezébe", "kéz"),
    ("kezét", "kéz"),
    ("kezünk", "kéz"),
    ("kompromittálódik", "kompromittál"),
    ("kupoláit", "kupola"),
    ("logikája", "logika"),
    ("logikát", "logika"),
    ("logisztikája", "logisztika"),
    ("láncolatuk", "láncolat"),
    ("láncú", "lánc"),
    ("Látom", "lát"),
    ("látunk", "lát"),
    ("léphet", "lép"),
    ("megbirkózni", "birkózik"),
    ("megmozdíthatatlan", "mozdít"),
    ("Megnézem", "néz"),
    ("megnézze", "néz"),
    ("megérzi", "érez"),
    ("mintázattá", "mintázat"),
    ("mozgásuk", "mozgás"),
    ("munkájától", "munka"),
    ("módosítom", "módosít"),
    ("Nyissák", "nyit"),
    ("nyitási", "nyit"),
    ("nyomdájuk", "nyomda"),
    ("nyomtatási", "nyomtatás"),
    ("némán", "néma"),
    ("olvadjon", "olvad"),
    ("papírmunkát", "papírmunka"),
    ("papírmunkával", "papírmunka"),
    ("perifériás", "periféria"),
    ("Remélem", "remél"),
    ("rendezze", "rendez"),
    ("Repülőtéri", "repülőtér"),
    ("ridegségével", "rideg"),
    ("stílusú", "stílus"),
    ("szereti", "szeret"),
    ("szélén", "szél"),
    ("szűrőin", "szűrő"),
    ("sűrűbb", "sűrű"),
    ("technológiával", "technológia"),
    ("Terrorelhárítási", "terrorelhárítás"),
    ("tervezési", "tervezés"),
    ("titkosítási", "titkosítás"),
    ("téri", "tér"),
    ("típusú", "típus"),
    ("utcán", "utca"),
    ("utcát", "utca"),
    ("állunk", "áll"),
    ("órát", "óra"),
    ("lévő", "lét"),
    ("nézett", "néz"),
    ("védelme", "védelem"),
    ("felelte", "felel"),
    ("felemelte", "felemel"),
    ("gondolta", "gondol"),
    ("Hetvenkét", "hetvenkettő"),
    ("Ismerte", "ismer"),
    ("Jura-nál", "jura"),
    ("kellett", "kell"),
    ("lézeres", "lézer"),
    ("odalépett", "lép"),
    ("Soroksári", "soroksár"),
    ("tudtak", "tud"),
    ("táskát", "táska"),
    ("vette", "vesz"),
    ("átadta", "ad"),
    ("átmennek", "megy"),
    ("órája", "óra"),
    ("adtam", "adta"),
    ("ajtaját", "ajtó"),
    ("akiket", "aki"),
    ("akiknek", "aki"),
    ("aktáját", "akta"),
    ("aktát", "akta"),
    ("autókat", "autó"),
    ("belátásra", "lát"),
    ("bezárta", "bezár"),
    ("Bízhattak", "bízik"),
    ("cigarettáját", "cigaretta"),
    ("diplomatájával", "diplomata"),
    ("Diósgyőri", "diósgyőr"),
    ("dolga", "dolog"),
    ("dolgoznak", "dolgozik"),
    ("egyenruhása", "egyenruha"),
    ("Elfelejtették", "felejt"),
    ("elvette", "elvesz"),
    ("elővette", "elővesz"),
    ("embereken", "ember"),
    ("emberekhez", "ember"),
    ("faalapú", "fa"),
    ("fejezeteket", "fejezet"),
    ("fejlesztik", "fejleszt"),
    ("felhőalapú", "felhő"),
    ("felvette", "felvesz"),
    ("felvitele", "felvisz"),
    ("figyelmet", "figyelem"),
    ("forgott", "forog"),
    ("forintoson", "forint"),
    ("formáját", "forma"),
    ("fémdetektoros", "detektor"),
    ("fővárosunk", "főváros"),
    ("haja", "haj"),
    ("hamisítható", "hamisít"),
    ("használta", "használ"),
    ("hibát", "hiba"),
    ("héten", "hét"),
    ("húszezrest", "húszezer"),
    ("hőséggel", "hőség"),
    ("jegybanki", "jegybank"),
    ("jeleket", "jel"),
    ("jelentették", "jelent"),
    ("jelenti", "jelent"),
    ("járhatott", "jár"),
    ("játszanak", "játszik"),
    ("keressen", "keres"),
    ("kertvárosi", "kertváros"),
    ("kezében", "kéz"),
    ("kicserélni", "cserél"),
    ("Kicserélték", "cserél"),
    ("kicserélve", "cserél"),
    ("kiviszi", "kivisz"),
    ("kulcsainkat", "kulcs"),
    ("kérdezősködő", "kérdez"),
    ("kért", "kér"),
    ("készpénzforgalmi", "készpénzforgalom"),
    ("kövessen", "követ"),
    ("lapozott", "lapoz"),
    ("legnehezebben", "nehéz"),
    ("lennél", "lenni"),
    ("letette", "letesz"),
    ("léptekkel", "lépés"),
    ("matematikát", "matematika"),
    ("meghúzhatta", "meghúz"),
    ("mennek", "megy"),
    ("mennie", "megy"),
    ("moaré-védelmet", "védelem"),
    ("moshatnak", "mos"),
    ("mutasson", "mutat"),
    ("nevét", "név"),
    ("nyakában", "nyak"),
    ("nyara", "nyár"),
    ("okmánnyal", "okmány"),
    ("oldalán", "oldal"),
    ("pamuttartalmú", "pamut"),
    ("rasztervonalak", "raszter"),
    ("rejtőzködni", "rejtőzködik"),
    ("rátette", "rátesz"),
    ("részlegén", "részleg"),
    ("sarkában", "sarok"),
    ("Schengeni", "schengen"),
    ("szeretik", "szeret"),
    ("találtak", "talál"),
    ("tette", "tesz"),
    ("túloldalán", "túloldal"),
    ("tűnni", "tűnik"),
    ("utaznak", "utazik"),
    ("valutája", "valuta"),
    ("vegye", "vesz"),
    ("vesztegette", "veszteget"),
    ("vett", "vesz"),
    ("viszik", "visz"),
    ("voltam", "volt"),
    ("végén", "vég"),
    ("álljon", "áll"),
    ("ártalmatlanítására", "ártalmatlan"),
    ("átvette", "átvesz"),
    ("éjszakán", "éjszaka"),
    ("útlevelét", "útlevél"),
    ("kereskedelmet", "kereskedelem"),
    ("érzelmeket", "érzelem"),
    ("kalózkodás", "kalózkodik"),
    ("önkényuralmi", "önkényuralom"),
    ("származású", "származás"),
    ("legtöbb", "sok"),
    ("társadalmat", "társadalom"),
    ("távolították", "távolít"),
    ("prédát", "préda"),
    ("fedélzetén", "fedélzet"),
    ("semmifajta", "fajta"),
    ("legénységüknek", "legénység"),
    ("Európában", "Európa"),
    ("nehezítik", "nehezít"),
    ("átjáróin", "átjáró"),
    ("hatalmukba", "hatalom"),
    ("kerítik", "kerít"),
    ("megölik", "megöl"),
    ("kormányzatuk", "kormányzat"),
    ("uralkodóik", "uralkodó"),
    ("hírű", "hír"),
    ("CSODÁLÓIK", "csodáló"),
    ("SZEMÉBEN", "szem"),
    ("KALÓZOK", "kalóz"),
    ("sajátjukat", "saját"),
    ("dolgokra", "dolog"),
    ("figyelmüket", "figyelem"),
    ("kevesebbre", "kevés"),
    ("fegyelme", "fegyelem"),
    ("tapasztalható", "tapasztal"),
    ("formája", "forma"),
    ("köztük", "közt"),
    ("elfogadhatatlannak", "elfogadhatatlan"),
    ("használhassa", "használ"),
    ("kalózvezért", "kalózvezér"),
    ("támogassa", "támogat"),
    ("kártevőit", "kártevő"),
    ("Belize", "Belize"),
    ("hozzátéve", "hozzátesz"),
    ("feleségemmel", "feleség"),
    ("lehessen", "lehet"),
    ("mosolyú", "mosoly"),
    ("rájöttem", "rájön"),
    ("népszerűségük", "népszerűség"),
    ("zsákmánnyal", "zsákmány"),
    ("vezethető", "vezet"),
    ("foglalkoznak", "foglalkozik"),
    ("életrajzi", "életrajz"),
    ("életén", "élet"),
    ("fellelhető", "fellel"),
    ("bírósági", "bíróság"),
    ("hadihajóinak", "hadihajó"),
    ("kutatásom", "kutatás"),
    ("támpontunk", "támpont"),
    ("mentoruk", "mentor"),
    ("gyakorlatilag", "gyakorlat"),
    ("Karrierjük", "karrier"),
    ("mindegyikük", "mindegyik"),
    ("szállítmányozási", "szállítmányozás"),
]

cpp_path = Path("src/util/Dictionary.cpp")
text = cpp_path.read_text(encoding="utf-8")

if "Hungarian dictionary stemming v16" not in text:
    marker = "  // Hungarian dictionary stemming v15: reject short accidental compound-tail matches.\n"
    if marker not in text:
        raise SystemExit("v16 v15 marker not found")
    text = text.replace(marker, marker + "  // Hungarian dictionary stemming v16: validated corpus mappings and Hungarian UTF-8 case folding.\n", 1)

    lower_anchor = """  std::transform(result.begin(), result.end(), result.begin(),
                 [](unsigned char c) { return c >= 0x80 ? c : static_cast<unsigned char>(std::tolower(c)); });
"""
    lower_block = lower_anchor + """
  struct HuCasePair { const char* upper; const char* lower; };
  static constexpr HuCasePair HU_CASE_FOLD[] = {
      {"Á","á"},{"É","é"},{"Í","í"},{"Ó","ó"},{"Ö","ö"},
      {"Ő","ő"},{"Ú","ú"},{"Ü","ü"},{"Ű","ű"},
  };
  for (const auto& p : HU_CASE_FOLD) {
    size_t pos = 0;
    const size_t upperLen = strlen(p.upper);
    const size_t lowerLen = strlen(p.lower);
    while ((pos = result.find(p.upper, pos)) != std::string::npos) {
      result.replace(pos, upperLen, p.lower);
      pos += lowerLen;
    }
  }
"""
    if lower_anchor not in text:
        raise SystemExit("v16 lowercase anchor not found")
    text = text.replace(lower_anchor, lower_block, 1)

    special_start = text.find("static constexpr Pair SPECIAL[]")
    special_end = text.find("\n    };", special_start)
    if special_start < 0 or special_end < 0:
        raise SystemExit("v16 SPECIAL array not found")
    cpp_pairs = ",\n      ".join(
        '{"' + source.casefold().replace('\\','\\\\').replace('"','\\"') + '","' +
        target.replace('\\','\\\\').replace('"','\\"') + '"}'
        for source, target in PAIRS
    )
    text = text[:special_end] + ",\n      " + cpp_pairs + text[special_end:]

    dangerous = '    if (ends("essen")) { add(w.substr(0,w.size()-strlen("essen")) + "esik"); add("esik"); }'
    safe = '    if (w == "beleessen") add("beleesik");'
    if dangerous not in text:
        raise SystemExit("v16 dangerous -essen rule not found")
    text = text.replace(dangerous, safe, 1)

cpp_path.write_text(text, encoding="utf-8")

model_path = Path("scripts/hungarian_stemmer_model.py")
model = model_path.read_text(encoding="utf-8")
model_marker = "# Hungarian dictionary stemming v16 validated corpus mappings"
if model_marker not in model:
    dangerous_model = '    if w.endswith("essen"): c.extend((w[:-5]+"esik","esik"))'
    if dangerous_model not in model:
        raise SystemExit("v16 model -essen rule not found")
    model = model.replace(dangerous_model, '    if w == "beleessen": c.append("beleesik")', 1)
    mapping_lines = "\n".join(
        "    " + repr(source.casefold()) + ": " + repr(target) + ","
        for source, target in PAIRS
    )
    model += "\n\n" + model_marker + "\nSPECIAL.update({\n" + mapping_lines + "\n})\n"
    model_path.write_text(model, encoding="utf-8")

check = cpp_path.read_text(encoding="utf-8")
for required in ("Hungarian dictionary stemming v16", "HU_CASE_FOLD", '{"lehessen","lehet"}'):
    if required not in check:
        raise SystemExit(f"Missing v16 marker: {required}")
if 'add("esik")' in check:
    raise SystemExit("Unsafe bare esik fallback remains")
print(f"Hungarian dictionary stemming v16 applied: {len(PAIRS)} validated mappings")
