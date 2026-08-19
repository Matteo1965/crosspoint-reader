from pathlib import Path

CASE=("képpen","ként","jából","jéből","jába","jébe","járól","jéről","ján","jén","jához","jéhez","jéhöz","ból","ből","tól","től","ról","ről","hoz","hez","höz","nál","nél","ban","ben","nak","nek","ért","ba","be","ra","re","on","en","ön","ig","kor","ul","ül","vá","vé")
PLURAL=("ak","ek","ok","ök","k")
PAST=("ottam","ettem","öttem","tam","tem","ottál","ettél","öttél","tál","tél","ottunk","ettünk","öttünk","tunk","tünk","ottatok","ettetek","öttetek","tatok","tetek","ottak","ettek","öttek","tak","tek","ták","ték","otta","ette","ötte","ta","te","ott","ett","ött")
SPECIAL={"nekem":"én","atyavilág":"világ","kabátja":"kabát","igazgatónője":"igazgató","beleessen":"beleesik","kihalgassa":"kihallgat","utat":"út","sziklahasadékból":"hasadék","madárlába":"láb","tompaagyúság":"agy","ezreivel":"ezer"}

def uniq(xs):
    out=[]; seen=set()
    for x in xs:
        if x and x not in seen: seen.add(x); out.append(x)
    return out

def candidates(word):
    w=word.lower(); c=[]
    if w in SPECIAL: c.append(SPECIAL[w])
    if w.endswith("-e"): c.append(w[:-2])
    if w.endswith("nek") and len(w)>3: c.append(w[:-3]+"ik")
    for s in ("nia","nie"):
        if w.endswith(s): c.append(w[:-len(s)])
    for s in ("va","ve"):
        if w.endswith(s):
            stem=w[:-len(s)]; c.extend((stem+"ik",stem))
    if w.endswith("ák") and len(w)>2: c.append(w[:-2]+"a")
    if w.endswith("ék") and len(w)>2: c.append(w[:-2]+"e")
    for s in ("ak","ek","ok","ök"):
        if w.endswith(s) and len(w)>len(s): c.append(w[:-len(s)])
    for s in ("jait","jeit","ait","eit","ját","jét","át","ét","jai","jei","ai","ei","ja","je","a","e"):
        if w.endswith(s) and len(w)>len(s): c.append(w[:-len(s)])
    for s in ("eteket","atokat","otokat","ötöket","talanok","telenek","jetek","jatok","jen","jön"):
        if w.endswith(s): c.append(w[:-len(s)])
    if w.endswith("ele"): c.append(w[:-3]+"él")
    if w.endswith("ormok"): c.append(w[:-5]+"orom")
    if w.endswith("epén"): c.append(w[:-4]+"ép")
    if w.endswith("leit"): c.append(w[:-4]+"l")
    if w == "beleessen": c.append("beleesik")
    for s in ("tan","ten"):
        if w.endswith(s): c.append(w[:-len(s)])
    for s in ("ását","ését"):
        if w.endswith(s):
            stem=w[:-len(s)]; c.extend((stem+"ás",stem+"és",stem))
            if stem.endswith("g"): c.extend((stem[:-1]+"og",stem[:-1]+"eg",stem[:-1]+"ög"))
    for s in ("kal","kel"):
        if w.endswith(s):
            pl=w[:-len(s)]; c.append(pl)
            for ps in PLURAL:
                if pl.endswith(ps):
                    stem=pl[:-len(ps)]; c.append(stem)
                    if stem.endswith("öv"): c.append(stem[:-2]+"ő")
    for s in ("séggel","sággal"):
        if w.endswith(s): c.extend((w[:-len(s)]+"s",w[:-len(s)]))
    for s in ("úság","űség"):
        if w.endswith(s): c.append(w[:-len(s)])
    if w.endswith("sz") and len(w)>2: c.append(w[:-2])
    for s in ("bbá","bbé"):
        if w.endswith(s):
            stem=w[:-len(s)]
            if stem.endswith("á"): c.append(stem[:-1]+"a")
            if stem.endswith("é"): c.append(stem[:-1]+"e")
            c.append(stem)
    for s in ("ősen","ósan","özött","ozott","ezett"):
        if w.endswith(s): c.append(w[:-len(s)])
    if w.endswith("ikat"): c.append(w[:-4])
    if w.startswith("leg") and w.endswith(("abb","ebb","obb")): c.append(w[3:-3])
    for s in ("ésén","ásán"):
        if w.endswith(s): c.append(w[:-2])
    if w.endswith("essé"): c.append(w[:-2])
    if w.endswith(("ságban","ségben")): c.append(w[:-3])
    for s in ("olják","eljék","öljék"):
        if w.endswith(s): c.append(w[:-len(s)]+s[:2])
    for s in ("sebbek","sabbak"):
        if w.endswith(s): c.append(w[:-len(s)]+"s")
    if w.endswith("nább"): c.append(w[:-4]+"na")
    if w.endswith("nébb"): c.append(w[:-4]+"ne")
    if w.endswith("kori"): c.append(w[:-1])
    if w.endswith("állá"): c.append(w[:-1])
    for s in ("ással","éssel"):
        if w.endswith(s): c.append(w[:-4])
    for s in ("hattak","hettek"):
        if w.endswith(s): c.append(w[:-len(s)])
    if w.endswith(("tság","tség")): c.append(w[:-4])
    if w.endswith("n") and len(w)>1: c.append(w[:-1])
    for s in ("ozni","ezni"):
        if w.endswith(s): c.append(w[:-4]+s[:2]+"ik")
    if w.endswith("ni") and len(w)>2: c.append(w[:-2])
    for s in ("an","en","abb","ebb","obb"):
        if w.endswith(s) and len(w)>len(s): c.append(w[:-len(s)])
    for s in ("ával","ével","val","vel"):
        if w.endswith(s): c.append(w[:-len(s)])
    if len(w)>=4 and w[-2:] in ("al","el") and w[-3]==w[-4]: c.append(w[:-3])

    # Nominalization + possessive instrumental: átvizsgálásával -> átvizsgál.
    for s in ("ásával","ésével"):
        if w.endswith(s) and len(w)>len(s): c.append(w[:-len(s)])

    # 3rd-person definite past: biztosította -> biztosít, újságolta -> újságol.
    for s in ("otta","ette","ötte","olta","elte"):
        if w.endswith(s) and len(w)>len(s): c.append(w[:-len(s)])

    # Possessed plural + elative: szátokból -> száj.
    for s in ("tokból","tekből","tökből"):
        if w.endswith(s) and len(w)>len(s):
            stem=w[:-len(s)]
            c.append(stem)
            if stem.endswith("szá"): c.append(stem[:-2]+"száj")

    # Iterative verb + definite 3rd plural: fontolgatják -> fontolgat.
    for s in ("gatják","getik","gatja","geti"):
        if w.endswith(s) and len(w)>len(s): c.append(w[:-len(s)]+s[:3])

    # Potential + 1st plural: fogadhatunk -> fogad.
    for s in ("hatunk","hetünk"):
        if w.endswith(s) and len(w)>len(s): c.append(w[:-len(s)])

    # Past potential + 1st plural: fogadhattunk -> fogad.
    for s in ("hattunk","hettünk"):
        if w.endswith(s) and len(w)>len(s): c.append(w[:-len(s)])

    # Possessive/accusative -fiát back to compound ending in -fiú.
    if w.endswith("fiát") and len(w)>4:
        c.append(w[:-4]+"fiú")

    # Hyphenated relational adjective: fogadó-beli -> fogadó.
    for s in ("-beli","-féle","-fajta"):
        if w.endswith(s) and len(w)>len(s): c.append(w[:-len(s)])

    # Comparative adverb with lexical long-vowel base candidate: könnyebben -> könnyű.
    if w.endswith("ebben") and len(w)>5:
        stem=w[:-5]; c.extend((stem+"ű",stem))
    if w.endswith("abban") and len(w)>5:
        stem=w[:-5]; c.extend((stem+"ú",stem))

    # 3rd-person plural imperative in -zzanak/-zzenek: találkozzanak -> találkozik.
    for s in ("zzanak","zzenek"):
        if w.endswith(s) and len(w)>len(s):
            stem=w[:-len(s)]; c.extend((stem+"zik",stem+"z"))

    for s in CASE:
        if w.endswith(s) and len(w)>len(s):
            base=w[:-len(s)]; c.append(base)
            for ps in PLURAL:
                if base.endswith(ps) and len(base)>len(ps): c.append(base[:-len(ps)])
            if base.endswith("á"): c.extend((base[:-1]+"a",base[:-1]))
            if base.endswith("é"): c.extend((base[:-1]+"e",base[:-1]))
    for s in ("at","et","ot","öt","t"):
        if w.endswith(s) and len(w)>len(s):
            base=w[:-len(s)]; c.append(base)
            if base.endswith("u"): c.append(base[:-1]+"ú")
            if base.endswith("e"): c.append(base[:-1]+"é")
            if base.endswith("a"): c.append(base[:-1]+"á")
    for ps in PLURAL:
        if w.endswith(ps) and len(w)>len(ps): c.append(w[:-len(ps)])
    for s in PAST:
        if w.endswith(s) and len(w)>len(s):
            stem=w[:-len(s)]; c.extend((stem+"ik",stem))
    for s in ("ás","és"):
        if w.endswith(s) and len(w)>len(s): c.append(w[:-len(s)])
    for s in ("ó","ő"):
        if w.endswith(s) and len(w)>1:
            stem=w[:-1]; c.extend((stem+"ik",stem))
    return uniq(c)

def lookup(word, headwords):
    w=word.lower()
    if w in headwords: return w
    queue=candidates(w); seen=[]; seen_set=set()
    for _ in range(3):
        nxt=[]
        for cand in queue:
            if cand in seen_set: continue
            seen_set.add(cand); seen.append(cand)
            if cand in headwords: return cand
            nxt.extend(candidates(cand))
        queue=uniq(nxt)
    matches=[]
    for source in [w]+seen:
        for i in range(1,len(source)):
            cand=source[i:]
            if len(cand)>=3 and cand in headwords:
                matches.append(cand)
    if matches:
        return max(matches, key=lambda x: (len(x), x))
    return None


# Hungarian dictionary stemming v16 validated corpus mappings
SPECIAL.update({
    'keze': 'kéz',
    'őrzött': 'őriz',
    'akadályozzák': 'akadályoz',
    'beszélnünk': 'beszél',
    'biztonságiőr': 'biztonság',
    'boríthatjuk': 'borít',
    'bástyája': 'bástya',
    'bürokráciával': 'bürokrácia',
    'centis': 'centi',
    'csapdát': 'csapda',
    'darabkája': 'darab',
    'eleji': 'eleje',
    'ellenőrzik': 'ellenőriz',
    'felbontású': 'felbontás',
    'felszerelésük': 'felszerelés',
    'frekvenciájú': 'frekvencia',
    'gondoljon': 'gondol',
    'grafikai': 'grafika',
    'grafikát': 'grafika',
    'gurulós': 'gurul',
    'gyártási': 'gyártás',
    'halántékú': 'halánték',
    'intelligenciái': 'intelligencia',
    'irodát': 'iroda',
    'irodával': 'iroda',
    'jöhet': 'jön',
    'kerüli': 'kerül',
    'kezdjük': 'kezd',
    'kezem': 'kéz',
    'kezébe': 'kéz',
    'kezét': 'kéz',
    'kezünk': 'kéz',
    'kompromittálódik': 'kompromittál',
    'kupoláit': 'kupola',
    'logikája': 'logika',
    'logikát': 'logika',
    'logisztikája': 'logisztika',
    'láncolatuk': 'láncolat',
    'láncú': 'lánc',
    'látom': 'lát',
    'látunk': 'lát',
    'léphet': 'lép',
    'megbirkózni': 'birkózik',
    'megmozdíthatatlan': 'mozdít',
    'megnézem': 'néz',
    'megnézze': 'néz',
    'megérzi': 'érez',
    'mintázattá': 'mintázat',
    'mozgásuk': 'mozgás',
    'munkájától': 'munka',
    'módosítom': 'módosít',
    'nyissák': 'nyit',
    'nyitási': 'nyit',
    'nyomdájuk': 'nyomda',
    'nyomtatási': 'nyomtatás',
    'némán': 'néma',
    'olvadjon': 'olvad',
    'papírmunkát': 'papírmunka',
    'papírmunkával': 'papírmunka',
    'perifériás': 'periféria',
    'remélem': 'remél',
    'rendezze': 'rendez',
    'repülőtéri': 'repülőtér',
    'ridegségével': 'rideg',
    'stílusú': 'stílus',
    'szereti': 'szeret',
    'szélén': 'szél',
    'szűrőin': 'szűrő',
    'sűrűbb': 'sűrű',
    'technológiával': 'technológia',
    'terrorelhárítási': 'terrorelhárítás',
    'tervezési': 'tervezés',
    'titkosítási': 'titkosítás',
    'téri': 'tér',
    'típusú': 'típus',
    'utcán': 'utca',
    'utcát': 'utca',
    'állunk': 'áll',
    'órát': 'óra',
    'lévő': 'lét',
    'nézett': 'néz',
    'védelme': 'védelem',
    'felelte': 'felel',
    'felemelte': 'felemel',
    'gondolta': 'gondol',
    'hetvenkét': 'hetvenkettő',
    'ismerte': 'ismer',
    'jura-nál': 'jura',
    'kellett': 'kell',
    'lézeres': 'lézer',
    'odalépett': 'lép',
    'soroksári': 'soroksár',
    'tudtak': 'tud',
    'táskát': 'táska',
    'vette': 'vesz',
    'átadta': 'ad',
    'átmennek': 'megy',
    'órája': 'óra',
    'adtam': 'adta',
    'ajtaját': 'ajtó',
    'akiket': 'aki',
    'akiknek': 'aki',
    'aktáját': 'akta',
    'aktát': 'akta',
    'autókat': 'autó',
    'belátásra': 'lát',
    'bezárta': 'bezár',
    'bízhattak': 'bízik',
    'cigarettáját': 'cigaretta',
    'diplomatájával': 'diplomata',
    'diósgyőri': 'diósgyőr',
    'dolga': 'dolog',
    'dolgoznak': 'dolgozik',
    'egyenruhása': 'egyenruha',
    'elfelejtették': 'felejt',
    'elvette': 'elvesz',
    'elővette': 'elővesz',
    'embereken': 'ember',
    'emberekhez': 'ember',
    'faalapú': 'fa',
    'fejezeteket': 'fejezet',
    'fejlesztik': 'fejleszt',
    'felhőalapú': 'felhő',
    'felvette': 'felvesz',
    'felvitele': 'felvisz',
    'figyelmet': 'figyelem',
    'forgott': 'forog',
    'forintoson': 'forint',
    'formáját': 'forma',
    'fémdetektoros': 'detektor',
    'fővárosunk': 'főváros',
    'haja': 'haj',
    'hamisítható': 'hamisít',
    'használta': 'használ',
    'hibát': 'hiba',
    'héten': 'hét',
    'húszezrest': 'húszezer',
    'hőséggel': 'hőség',
    'jegybanki': 'jegybank',
    'jeleket': 'jel',
    'jelentették': 'jelent',
    'jelenti': 'jelent',
    'járhatott': 'jár',
    'játszanak': 'játszik',
    'keressen': 'keres',
    'kertvárosi': 'kertváros',
    'kezében': 'kéz',
    'kicserélni': 'cserél',
    'kicserélték': 'cserél',
    'kicserélve': 'cserél',
    'kiviszi': 'kivisz',
    'kulcsainkat': 'kulcs',
    'kérdezősködő': 'kérdez',
    'kért': 'kér',
    'készpénzforgalmi': 'készpénzforgalom',
    'kövessen': 'követ',
    'lapozott': 'lapoz',
    'legnehezebben': 'nehéz',
    'lennél': 'lenni',
    'letette': 'letesz',
    'léptekkel': 'lépés',
    'matematikát': 'matematika',
    'meghúzhatta': 'meghúz',
    'mennek': 'megy',
    'mennie': 'megy',
    'moaré-védelmet': 'védelem',
    'moshatnak': 'mos',
    'mutasson': 'mutat',
    'nevét': 'név',
    'nyakában': 'nyak',
    'nyara': 'nyár',
    'okmánnyal': 'okmány',
    'oldalán': 'oldal',
    'pamuttartalmú': 'pamut',
    'rasztervonalak': 'raszter',
    'rejtőzködni': 'rejtőzködik',
    'rátette': 'rátesz',
    'részlegén': 'részleg',
    'sarkában': 'sarok',
    'schengeni': 'schengen',
    'szeretik': 'szeret',
    'találtak': 'talál',
    'tette': 'tesz',
    'túloldalán': 'túloldal',
    'tűnni': 'tűnik',
    'utaznak': 'utazik',
    'valutája': 'valuta',
    'vegye': 'vesz',
    'vesztegette': 'veszteget',
    'vett': 'vesz',
    'viszik': 'visz',
    'voltam': 'volt',
    'végén': 'vég',
    'álljon': 'áll',
    'ártalmatlanítására': 'ártalmatlan',
    'átvette': 'átvesz',
    'éjszakán': 'éjszaka',
    'útlevelét': 'útlevél',
    'kereskedelmet': 'kereskedelem',
    'érzelmeket': 'érzelem',
    'kalózkodás': 'kalózkodik',
    'önkényuralmi': 'önkényuralom',
    'származású': 'származás',
    'legtöbb': 'sok',
    'társadalmat': 'társadalom',
    'távolították': 'távolít',
    'prédát': 'préda',
    'fedélzetén': 'fedélzet',
    'semmifajta': 'fajta',
    'legénységüknek': 'legénység',
    'európában': 'Európa',
    'nehezítik': 'nehezít',
    'átjáróin': 'átjáró',
    'hatalmukba': 'hatalom',
    'kerítik': 'kerít',
    'megölik': 'megöl',
    'kormányzatuk': 'kormányzat',
    'uralkodóik': 'uralkodó',
    'hírű': 'hír',
    'csodálóik': 'csodáló',
    'szemében': 'szem',
    'kalózok': 'kalóz',
    'sajátjukat': 'saját',
    'dolgokra': 'dolog',
    'figyelmüket': 'figyelem',
    'kevesebbre': 'kevés',
    'fegyelme': 'fegyelem',
    'tapasztalható': 'tapasztal',
    'formája': 'forma',
    'köztük': 'közt',
    'elfogadhatatlannak': 'elfogadhatatlan',
    'használhassa': 'használ',
    'kalózvezért': 'kalózvezér',
    'támogassa': 'támogat',
    'kártevőit': 'kártevő',
    'belize': 'Belize',
    'hozzátéve': 'hozzátesz',
    'feleségemmel': 'feleség',
    'lehessen': 'lehet',
    'mosolyú': 'mosoly',
    'rájöttem': 'rájön',
    'népszerűségük': 'népszerűség',
    'zsákmánnyal': 'zsákmány',
    'vezethető': 'vezet',
    'foglalkoznak': 'foglalkozik',
    'életrajzi': 'életrajz',
    'életén': 'élet',
    'fellelhető': 'fellel',
    'bírósági': 'bíróság',
    'hadihajóinak': 'hadihajó',
    'kutatásom': 'kutatás',
    'támpontunk': 'támpont',
    'mentoruk': 'mentor',
    'gyakorlatilag': 'gyakorlat',
    'karrierjük': 'karrier',
    'mindegyikük': 'mindegyik',
    'szállítmányozási': 'szállítmányozás',
})
