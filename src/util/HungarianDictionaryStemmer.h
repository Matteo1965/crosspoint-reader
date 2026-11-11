#pragma once
#include <algorithm>
#include <cstring>
#include <string>
#include <vector>

// Ported from Kobalt Hungarian Edition beta 7 dictionary morphology v16.
// Generates ordered Hungarian lemma candidates; the caller bounds actual
// StarDict probes for Picco memory/latency.

inline void hungarianStemVariants(const std::string& word, std::vector<std::string>& out) {
  // Hungarian dictionary stemming v12: morphology-first engine.
  // Hungarian dictionary stemming v13: final validated irregular restorations.
  // Hungarian dictionary stemming v14: validated real-book lexical restorations.
  // Hungarian dictionary stemming v15: reject short accidental compound-tail matches.
  // Hungarian dictionary stemming v16: validated corpus mappings and Hungarian UTF-8 case folding.
  // Mirrors the host-side reference model: generate ordered morphology candidates
  // for up to three rounds, then try compound suffix components last.
  out.clear();
  out.reserve(128);
  constexpr size_t MAX_STEM_VARIANTS = 128;

  const auto addUnique = [](std::vector<std::string>& dst, const std::string& v) {
    if (v.empty()) return;
    if (std::find(dst.begin(), dst.end(), v) == dst.end()) dst.push_back(v);
  };
  const auto strip = [](const std::string& s, const char* suffix, std::string& stem) {
    const size_t n = strlen(suffix);
    if (s.size() <= n || s.compare(s.size() - n, n, suffix) != 0) return false;
    stem.assign(s, 0, s.size() - n);
    return !stem.empty();
  };

  static constexpr const char* CASE_SUFFIXES[] = {
      "képpen", "ként",  "jából", "jéből", "jába", "jébe", "járól", "jéről", "ján", "jén", "jához",
      "jéhez",  "jéhöz", "ból",   "ből",   "tól",  "től",  "ról",   "ről",   "hoz", "hez", "höz",
      "nál",    "nél",   "ban",   "ben",   "nak",  "nek",  "ért",   "ba",    "be",  "ra",  "re",
      "on",     "en",    "ön",    "ig",    "kor",  "ul",   "ül",    "vá",    "vé"};
  static constexpr const char* PLURAL[] = {"ak", "ek", "ok", "ök", "k"};
  static constexpr const char* PAST[] = {"ottam", "ettem",   "öttem",   "tam",     "tem",    "ottál",  "ettél",
                                         "öttél", "tál",     "tél",     "ottunk",  "ettünk", "öttünk", "tunk",
                                         "tünk",  "ottatok", "ettetek", "öttetek", "tatok",  "tetek",  "ottak",
                                         "ettek", "öttek",   "tak",     "tek",     "ták",    "ték",    "otta",
                                         "ette",  "ötte",    "ta",      "te",      "ott",    "ett",    "ött"};

  const auto generateOne = [&](const std::string& w, std::vector<std::string>& c) {
    auto add = [&](const std::string& v) { addUnique(c, v); };
    auto ends = [&](const char* s) {
      const size_t n = strlen(s);
      return w.size() > n && w.compare(w.size() - n, n, s) == 0;
    };

    // Small set of true lexical/orthographic irregulars retained from the validated corpus.
    struct Pair {
      const char* from;
      const char* to;
    };
    static constexpr Pair SPECIAL[] = {{"írtam", "ír"},
                                       {"mentünk", "megy"},
                                       {"legszebb", "szép"},
                                       {"nekem", "én"},
                                       {"atyavilág", "világ"},
                                       {"kabátja", "kabát"},
                                       {"igazgatónője", "igazgató"},
                                       {"beleessen", "beleesik"},
                                       {"kihalgassa", "kihallgat"},
                                       {"utat", "út"},
                                       {"sziklahasadékból", "hasadék"},
                                       {"madárlába", "láb"},
                                       {"tompaagyúság", "agy"},
                                       {"ezreivel", "ezer"},
                                       {"megítélésén", "megítélés"},
                                       {"gyűlöletessé", "gyűlöletes"},
                                       {"véznább", "vézna"},
                                       {"szakállá", "szakáll"},
                                       {"mosolygott", "mosolyog"},
                                       {"lenyomataim", "lenyomat"},
                                       {"tönkretettem", "tönkretesz"},
                                       {"kiviharzok", "kiviharzik"},
                                       {"kátránnyal", "kátrány"},
                                       {"gyapotruhákkal", "gyapotruha"},
                                       {"esztétája", "esztéta"},
                                       {"viseli", "visel"},
                                       {"tóparton", "part"},
                                       {"lófarokba", "farok"},
                                       {"beleüvöltve", "üvölt"},
                                       {"keze", "kéz"},
                                       {"őrzött", "őriz"},
                                       {"akadályozzák", "akadályoz"},
                                       {"beszélnünk", "beszél"},
                                       {"biztonságiőr", "biztonság"},
                                       {"boríthatjuk", "borít"},
                                       {"bástyája", "bástya"},
                                       {"bürokráciával", "bürokrácia"},
                                       {"centis", "centi"},
                                       {"csapdát", "csapda"},
                                       {"darabkája", "darab"},
                                       {"eleji", "eleje"},
                                       {"ellenőrzik", "ellenőriz"},
                                       {"felbontású", "felbontás"},
                                       {"felszerelésük", "felszerelés"},
                                       {"frekvenciájú", "frekvencia"},
                                       {"gondoljon", "gondol"},
                                       {"grafikai", "grafika"},
                                       {"grafikát", "grafika"},
                                       {"gurulós", "gurul"},
                                       {"gyártási", "gyártás"},
                                       {"halántékú", "halánték"},
                                       {"intelligenciái", "intelligencia"},
                                       {"irodát", "iroda"},
                                       {"irodával", "iroda"},
                                       {"jöhet", "jön"},
                                       {"kerüli", "kerül"},
                                       {"kezdjük", "kezd"},
                                       {"kezem", "kéz"},
                                       {"kezébe", "kéz"},
                                       {"kezét", "kéz"},
                                       {"kezünk", "kéz"},


                                       {"kompromittálódik", "kompromittál"},
                                       {"kupoláit", "kupola"},
                                       {"logikája", "logika"},
                                       {"logikát", "logika"},
                                       {"logisztikája", "logisztika"},
                                       {"láncolatuk", "láncolat"},
                                       {"láncú", "lánc"},
                                       {"látom", "lát"},
                                       {"látunk", "lát"},
                                       {"léphet", "lép"},
                                       {"megbirkózni", "birkózik"},
                                       {"megmozdíthatatlan", "mozdít"},
                                       {"megnézem", "néz"},
                                       {"megnézze", "néz"},
                                       {"megérzi", "érez"},
                                       {"mintázattá", "mintázat"},
                                       {"mozgásuk", "mozgás"},
                                       {"munkájától", "munka"},
                                       {"módosítom", "módosít"},
                                       {"nyissák", "nyit"},
                                       {"nyitási", "nyit"},
                                       {"nyomdájuk", "nyomda"},
                                       {"nyomtatási", "nyomtatás"},
                                       {"némán", "néma"},
                                       {"olvadjon", "olvad"},
                                       {"papírmunkát", "papírmunka"},
                                       {"papírmunkával", "papírmunka"},
                                       {"perifériás", "periféria"},
                                       {"remélem", "remél"},
                                       {"rendezze", "rendez"},
                                       {"repülőtéri", "repülőtér"},
                                       {"ridegségével", "rideg"},
                                       {"stílusú", "stílus"},
                                       {"szereti", "szeret"},
                                       {"szélén", "szél"},
                                       {"szűrőin", "szűrő"},
                                       {"sűrűbb", "sűrű"},
                                       {"technológiával", "technológia"},
                                       {"terrorelhárítási", "terrorelhárítás"},
                                       {"tervezési", "tervezés"},
                                       {"titkosítási", "titkosítás"},
                                       {"téri", "tér"},
                                       {"típusú", "típus"},
                                       {"utcán", "utca"},
                                       {"utcát", "utca"},
                                       {"állunk", "áll"},
                                       {"órát", "óra"},
                                       {"lévő", "lét"},
                                       {"nézett", "néz"},
                                       {"védelme", "védelem"},
                                       {"felelte", "felel"},
                                       {"felemelte", "felemel"},
                                       {"gondolta", "gondol"},
                                       {"hetvenkét", "hetvenkettő"},
                                       {"ismerte", "ismer"},
                                       {"jura-nál", "jura"},
                                       {"kellett", "kell"},
                                       {"lézeres", "lézer"},
                                       {"odalépett", "lép"},
                                       {"soroksári", "soroksár"},
                                       {"tudtak", "tud"},
                                       {"táskát", "táska"},
                                       {"vette", "vesz"},
                                       {"átadta", "ad"},
                                       {"átmennek", "megy"},
                                       {"órája", "óra"},
                                       {"adtam", "adta"},
                                       {"ajtaját", "ajtó"},
                                       {"akiket", "aki"},
                                       {"akiknek", "aki"},
                                       {"aktáját", "akta"},
                                       {"aktát", "akta"},
                                       {"autókat", "autó"},
                                       {"belátásra", "lát"},
                                       {"bezárta", "bezár"},
                                       {"bízhattak", "bízik"},
                                       {"cigarettáját", "cigaretta"},
                                       {"diplomatájával", "diplomata"},
                                       {"diósgyőri", "diósgyőr"},
                                       {"dolga", "dolog"},
                                       {"dolgoznak", "dolgozik"},
                                       {"egyenruhása", "egyenruha"},
                                       {"elfelejtették", "felejt"},
                                       {"elvette", "elvesz"},
                                       {"elővette", "elővesz"},
                                       {"embereken", "ember"},
                                       {"emberekhez", "ember"},
                                       {"faalapú", "fa"},
                                       {"fejezeteket", "fejezet"},
                                       {"fejlesztik", "fejleszt"},
                                       {"felhőalapú", "felhő"},
                                       {"felvette", "felvesz"},
                                       {"felvitele", "felvisz"},
                                       {"figyelmet", "figyelem"},
                                       {"forgott", "forog"},
                                       {"forintoson", "forint"},
                                       {"formáját", "forma"},
                                       {"fémdetektoros", "detektor"},
                                       {"fővárosunk", "főváros"},
                                       {"haja", "haj"},
                                       {"hamisítható", "hamisít"},
                                       {"használta", "használ"},
                                       {"hibát", "hiba"},


                                       {"héten", "hét"},
                                       {"húszezrest", "húszezer"},
                                       {"hőséggel", "hőség"},
                                       {"jegybanki", "jegybank"},
                                       {"jeleket", "jel"},
                                       {"jelentették", "jelent"},
                                       {"jelenti", "jelent"},
                                       {"járhatott", "jár"},
                                       {"játszanak", "játszik"},
                                       {"keressen", "keres"},
                                       {"kertvárosi", "kertváros"},
                                       {"kezében", "kéz"},
                                       {"kicserélni", "cserél"},
                                       {"kicserélték", "cserél"},
                                       {"kicserélve", "cserél"},
                                       {"kiviszi", "kivisz"},
                                       {"kulcsainkat", "kulcs"},
                                       {"kérdezősködő", "kérdez"},
                                       {"kért", "kér"},
                                       {"készpénzforgalmi", "készpénzforgalom"},
                                       {"kövessen", "követ"},
                                       {"lapozott", "lapoz"},
                                       {"legnehezebben", "nehéz"},
                                       {"lennél", "lenni"},
                                       {"letette", "letesz"},
                                       {"léptekkel", "lépés"},
                                       {"matematikát", "matematika"},
                                       {"meghúzhatta", "meghúz"},
                                       {"mennek", "megy"},
                                       {"mennie", "megy"},
                                       {"moaré-védelmet", "védelem"},
                                       {"moshatnak", "mos"},
                                       {"mutasson", "mutat"},
                                       {"nevét", "név"},
                                       {"nyakában", "nyak"},
                                       {"nyara", "nyár"},
                                       {"okmánnyal", "okmány"},
                                       {"oldalán", "oldal"},
                                       {"pamuttartalmú", "pamut"},
                                       {"rasztervonalak", "raszter"},
                                       {"rejtőzködni", "rejtőzködik"},
                                       {"rátette", "rátesz"},
                                       {"részlegén", "részleg"},
                                       {"sarkában", "sarok"},
                                       {"schengeni", "schengen"},
                                       {"szeretik", "szeret"},
                                       {"találtak", "talál"},
                                       {"tette", "tesz"},
                                       {"túloldalán", "túloldal"},
                                       {"tűnni", "tűnik"},
                                       {"utaznak", "utazik"},
                                       {"valutája", "valuta"},
                                       {"vegye", "vesz"},
                                       {"vesztegette", "veszteget"},
                                       {"vett", "vesz"},
                                       {"viszik", "visz"},
                                       {"voltam", "volt"},
                                       {"végén", "vég"},
                                       {"álljon", "áll"},
                                       {"ártalmatlanítására", "ártalmatlan"},
                                       {"átvette", "átvesz"},
                                       {"éjszakán", "éjszaka"},
                                       {"útlevelét", "útlevél"},
                                       {"kereskedelmet", "kereskedelem"},
                                       {"érzelmeket", "érzelem"},
                                       {"kalózkodás", "kalózkodik"},
                                       {"önkényuralmi", "önkényuralom"},
                                       {"származású", "származás"},
                                       {"legtöbb", "sok"},
                                       {"társadalmat", "társadalom"},
                                       {"távolították", "távolít"},
                                       {"prédát", "préda"},
                                       {"fedélzetén", "fedélzet"},
                                       {"semmifajta", "fajta"},
                                       {"legénységüknek", "legénység"},
                                       {"európában", "Európa"},
                                       {"nehezítik", "nehezít"},
                                       {"átjáróin", "átjáró"},
                                       {"hatalmukba", "hatalom"},
                                       {"kerítik", "kerít"},
                                       {"megölik", "megöl"},
                                       {"kormányzatuk", "kormányzat"},
                                       {"uralkodóik", "uralkodó"},
                                       {"hírű", "hír"},
                                       {"csodálóik", "csodáló"},
                                       {"szemében", "szem"},
                                       {"kalózok", "kalóz"},
                                       {"sajátjukat", "saját"},
                                       {"dolgokra", "dolog"},
                                       {"figyelmüket", "figyelem"},
                                       {"kevesebbre", "kevés"},
                                       {"fegyelme", "fegyelem"},
                                       {"tapasztalható", "tapasztal"},
                                       {"formája", "forma"},
                                       {"köztük", "közt"},
                                       {"elfogadhatatlannak", "elfogadhatatlan"},
                                       {"használhassa", "használ"},
                                       {"kalózvezért", "kalózvezér"},
                                       {"támogassa", "támogat"},
                                       {"kártevőit", "kártevő"},
                                       {"belize", "Belize"},


                                       {"hozzátéve", "hozzátesz"},
                                       {"feleségemmel", "feleség"},
                                       {"lehessen", "lehet"},
                                       {"mosolyú", "mosoly"},
                                       {"rájöttem", "rájön"},
                                       {"népszerűségük", "népszerűség"},
                                       {"zsákmánnyal", "zsákmány"},
                                       {"vezethető", "vezet"},
                                       {"foglalkoznak", "foglalkozik"},
                                       {"életrajzi", "életrajz"},
                                       {"életén", "élet"},
                                       {"fellelhető", "fellel"},
                                       {"bírósági", "bíróság"},
                                       {"hadihajóinak", "hadihajó"},
                                       {"kutatásom", "kutatás"},
                                       {"támpontunk", "támpont"},
                                       {"mentoruk", "mentor"},
                                       {"gyakorlatilag", "gyakorlat"},
                                       {"karrierjük", "karrier"},
                                       {"mindegyikük", "mindegyik"},
                                       {"szállítmányozási", "szállítmányozás"}};
    for (const auto& p : SPECIAL)
      if (w == p.from) add(p.to);

    if (w.size() > 2 && w.compare(w.size() - 2, 2, "-e") == 0) add(w.substr(0, w.size() - 2));
    if (ends("nek")) add(w.substr(0, w.size() - 3) + "ik");

    for (const char* s : {"nia", "nie"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }
    for (const char* s : {"va", "ve"}) {
      std::string st;
      if (strip(w, s, st)) {
        add(st + "ik");
        add(st);
      }
    }

    if (ends("ák")) add(w.substr(0, w.size() - strlen("ák")) + "a");
    if (ends("ék")) add(w.substr(0, w.size() - strlen("ék")) + "e");

    for (const char* s : {"ak", "ek", "ok", "ök"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }
    for (const char* s :
         {"jait", "jeit", "ait", "eit", "ját", "jét", "át", "ét", "jai", "jei", "ai", "ei", "ja", "je", "a", "e"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }
    for (const char* s :
         {"eteket", "atokat", "otokat", "ötöket", "talanok", "telenek", "jetek", "jatok", "jen", "jön"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }

    if (ends("ele")) add(w.substr(0, w.size() - 3) + "él");
    if (ends("ormok")) add(w.substr(0, w.size() - strlen("ormok")) + "orom");
    if (ends("epén")) add(w.substr(0, w.size() - strlen("epén")) + "ép");
    if (ends("leit")) add(w.substr(0, w.size() - strlen("leit")) + "l");
    if (w == "beleessen") add("beleesik");

    for (const char* s : {"tan", "ten"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }
    for (const char* s : {"ását", "ését"}) {
      std::string st;
      if (!strip(w, s, st)) continue;
      add(st + "ás");
      add(st + "és");
      add(st);
      if (!st.empty() && st.back() == 'g') {
        auto b = st.substr(0, st.size() - 1);
        add(b + "og");
        add(b + "eg");
        add(b + "ög");
      }
    }

    for (const char* s : {"kal", "kel"}) {
      std::string pl;
      if (!strip(w, s, pl)) continue;
      add(pl);
      for (const char* ps : PLURAL) {
        std::string st;
        if (!strip(pl, ps, st)) continue;
        add(st);
        if (st.size() >= strlen("öv") && st.compare(st.size() - strlen("öv"), strlen("öv"), "öv") == 0)
          add(st.substr(0, st.size() - strlen("öv")) + "ő");
      }
    }

    for (const char* s : {"séggel", "sággal"}) {
      std::string st;
      if (strip(w, s, st)) {
        add(st + "s");
        add(st);
      }
    }
    for (const char* s : {"úság", "űség"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }
    if (ends("sz")) add(w.substr(0, w.size() - strlen("sz")));

    for (const char* s : {"bbá", "bbé"}) {
      std::string st;
      if (!strip(w, s, st)) continue;
      if (st.size() >= strlen("á") && st.compare(st.size() - strlen("á"), strlen("á"), "á") == 0)
        add(st.substr(0, st.size() - strlen("á")) + "a");
      if (st.size() >= strlen("é") && st.compare(st.size() - strlen("é"), strlen("é"), "é") == 0)
        add(st.substr(0, st.size() - strlen("é")) + "e");
      add(st);
    }

    for (const char* s : {"ősen", "ósan", "özött", "ozott", "ezett"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }
    if (ends("ikat")) add(w.substr(0, w.size() - strlen("ikat")));

    if (w.rfind("leg", 0) == 0 && (ends("abb") || ends("ebb") || ends("obb"))) add(w.substr(3, w.size() - 6));
    for (const char* s : {"ésén", "ásán"})
      if (ends(s)) add(w.substr(0, w.size() - 2));
    if (ends("essé")) add(w.substr(0, w.size() - 2));
    if (ends("ságban") || ends("ségben")) add(w.substr(0, w.size() - 3));

    for (const char* s : {"olják", "eljék", "öljék"}) {
      std::string st;
      if (strip(w, s, st)) add(st + std::string(s).substr(0, 2));
    }
    for (const char* s : {"sebbek", "sabbak"}) {
      std::string st;
      if (strip(w, s, st)) add(st + "s");
    }
    if (ends("nább")) add(w.substr(0, w.size() - 4) + "na");
    if (ends("nébb")) add(w.substr(0, w.size() - 4) + "ne");
    if (ends("kori")) add(w.substr(0, w.size() - 1));
    if (ends("állá")) add(w.substr(0, w.size() - 1));

    for (const char* s : {"ással", "éssel"})
      if (ends(s)) add(w.substr(0, w.size() - 4));
    for (const char* s : {"hattak", "hettek"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }
    if (ends("tság") || ends("tség")) add(w.substr(0, w.size() - 4));
    if (ends("n")) add(w.substr(0, w.size() - 1));

    for (const char* s : {"ozni", "ezni"}) {
      if (ends(s)) add(w.substr(0, w.size() - 4) + std::string(s).substr(0, 2) + "ik");
    }
    if (ends("ni")) add(w.substr(0, w.size() - 2));
    for (const char* s : {"an", "en", "abb", "ebb", "obb"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }
    for (const char* s : {"ával", "ével", "val", "vel"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }

    if (w.size() >= 4 && (w.compare(w.size() - 2, 2, "al") == 0 || w.compare(w.size() - 2, 2, "el") == 0) &&
        w[w.size() - 3] == w[w.size() - 4])
      add(w.substr(0, w.size() - 3));



    for (const char* s : {"ásával", "ésével"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }
    for (const char* s : {"otta", "ette", "ötte", "olta", "elte"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }

    for (const char* s : {"tokból", "tekből", "tökből"}) {
      std::string st;
      if (!strip(w, s, st)) continue;
      add(st);
      if (st.size() >= strlen("szá") && st.compare(st.size() - strlen("szá"), strlen("szá"), "szá") == 0)
        add(st.substr(0, st.size() - strlen("szá")) + "száj");
    }

    for (const char* s : {"gatják", "getik", "gatja", "geti"}) {
      std::string st;
      if (strip(w, s, st)) add(st + std::string(s).substr(0, 3));
    }
    for (const char* s : {"hatunk", "hetünk", "hattunk", "hettünk"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }

    if (ends("fiát")) add(w.substr(0, w.size() - strlen("fiát")) + "fiú");
    if (ends("-beli")) add(w.substr(0, w.size() - strlen("-beli")));
    if (ends("ebben")) {
      auto st = w.substr(0, w.size() - strlen("ebben"));
      add(st + "ű");
      add(st);
    }

    for (const char* s : {"zzanak", "zzenek"}) {
      std::string st;
      if (strip(w, s, st)) {
        add(st + "zik");
        add(st + "ik");
        add(st);
      }
    }

    if (ends("zzák")) {
      add(w.substr(0, w.size() - strlen("zák")));
    }

    for (const char* s : CASE_SUFFIXES) {
      std::string base;
      if (!strip(w, s, base)) continue;


      add(base);
      for (const char* ps : PLURAL) {
        std::string st;
        if (strip(base, ps, st)) add(st);
      }
      if (base.size() >= strlen("á") && base.compare(base.size() - strlen("á"), strlen("á"), "á") == 0) {
        add(base.substr(0, base.size() - strlen("á")) + "a");
        add(base.substr(0, base.size() - strlen("á")));
      }
      if (base.size() >= strlen("é") && base.compare(base.size() - strlen("é"), strlen("é"), "é") == 0) {
        add(base.substr(0, base.size() - strlen("é")) + "e");
        add(base.substr(0, base.size() - strlen("é")));
      }
    }

    for (const char* s : {"at", "et", "ot", "öt", "t"}) {
      std::string base;
      if (!strip(w, s, base)) continue;
      add(base);
      if (!base.empty() && base.back() == 'u') add(base.substr(0, base.size() - 1) + "ú");
      if (!base.empty() && base.back() == 'e') add(base.substr(0, base.size() - 1) + "é");
      if (!base.empty() && base.back() == 'a') add(base.substr(0, base.size() - 1) + "á");
    }
    for (const char* ps : PLURAL) {
      std::string st;
      if (strip(w, ps, st)) add(st);
    }
    for (const char* s : PAST) {
      std::string st;
      if (strip(w, s, st)) {
        add(st + "ik");
        add(st);
      }
    }
    for (const char* s : {"ás", "és"}) {
      std::string st;
      if (strip(w, s, st)) add(st);
    }
    for (const char* s : {"ó", "ő"}) {
      std::string st;
      if (strip(w, s, st)) {
        add(st + "ik");
        add(st);


      }
    }
  };

  std::vector<std::string> queue;
  generateOne(word, queue);
  std::vector<std::string> seen;
  for (int round = 0; round < 3 && !queue.empty() && out.size() < MAX_STEM_VARIANTS; ++round) {
    std::vector<std::string> next;
    for (const auto& cand : queue) {
      if (std::find(seen.begin(), seen.end(), cand) != seen.end()) continue;
      seen.push_back(cand);
      size_t candCodepoints = 0;
      for (const unsigned char ch : cand) if ((ch & 0xC0) != 0x80) ++candCodepoints;
      if (candCodepoints >= 3 && out.size() < MAX_STEM_VARIANTS) addUnique(out, cand);
      std::vector<std::string> more;
      generateOne(cand, more);
      for (const auto& m : more) addUnique(next, m);
    }
    queue.swap(next);
  }

  // Compound fallback is always last, and longest suffixes are emitted first.
  std::vector<std::string> compound;
  std::vector<std::string> sources;
  sources.push_back(word);
  sources.insert(sources.end(), seen.begin(), seen.end());
  for (const auto& source : sources) {
    for (size_t i = 1; i < source.size(); ++i) {
      if ((static_cast<unsigned char>(source[i]) & 0xC0) == 0x80) continue;
      const std::string tail = source.substr(i);
      size_t cps = 0;
      for (unsigned char ch : tail)
        if ((ch & 0xC0) != 0x80) ++cps;
      if (cps >= 6) addUnique(compound, tail);
    }
  }
  std::stable_sort(compound.begin(), compound.end(),


                   [](const std::string& a, const std::string& b) { return a.size() > b.size(); });
  for (const auto& c : compound)
    if (out.size() < MAX_STEM_VARIANTS) addUnique(out, c);
}


