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
    if w.endswith("essen"): c.extend((w[:-5]+"esik","esik"))
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
    return uniq(c)

def lookup(word, headwords):
    w=word.lower()
    if w in headwords: return w
    queue=candidates(w); seen=set()
    for _ in range(3):
        nxt=[]
        for cand in queue:
            if cand in seen: continue
            seen.add(cand)
            if cand in headwords: return cand
            nxt.extend(candidates(cand))
        queue=uniq(nxt)
    # Compound fallback is deliberately last: szakemberekben must reach szakember before berek.
    for source in [w]+list(seen):
        for i in range(1,len(source)):
            cand=source[i:]
            if len(cand)>=3 and cand in headwords: return cand
    return None
