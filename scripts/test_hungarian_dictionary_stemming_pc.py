#!/usr/bin/env python3
import argparse, struct, unicodedata
from collections import deque

TESTS = {'házban': 'ház', 'házból': 'ház', 'házhoz': 'ház', 'házak': 'ház', 'házakat': 'ház', 'házakban': 'ház', 'könyvek': 'könyv', 'könyvekben': 'könyv', 'házam': 'ház', 'házamban': 'ház', 'könyvem': 'könyv', 'könyvemben': 'könyv', 'csodálkozva': 'csodálkozik', 'igazgatni': 'igazgat', 'kezdte': 'kezd', 'monokliját': 'monokli', 'gyanakodva': 'gyanakodik', 'fedele': 'fedél', 'ollóval': 'olló', 'ujjával': 'ujj', 'óvatosan': 'óvatos', 'közelebb': 'közel', 'vagdalták': 'vagdal', 'pálmafák': 'pálmafa', 'árnyékából': 'árnyék', 'halászták': 'halászik', 'kiáramló': 'kiáramlik', 'utat': 'út', 'nyájasan': 'nyájas', 'elterelés': 'elterel', 'drágakövekkel': 'drágakő', 'zsebébe': 'zseb', 'szultánnal': 'szultán', 'kártyázott': 'kártyázik', 'láthatatlan': 'láthatatlan', 'mozdulattal': 'mozdulat', 'zsebéből': 'zseb', 'Atyavilág': 'világ', 'széleit': 'szél', 'Nekem': 'én', 'kazánjából': 'kazán', 'kabátja': 'kabát', 'segítségeteket': 'segítség', 'arctalanok': 'arc', 'farktollai': 'farktoll', 'cipeljen': 'cipel', 'hegyormok': 'hegyorom', 'sziklahasadékból': 'hasadék', 'közepén': 'közép', 'beleüvöltve': 'üvölt', 'tóparton': 'part', 'madárlába': 'láb', 'megkönnyebbülten': 'megkönnyebbül', 'viszolygását': 'viszolyog', 'lényekkel': 'lény', 'veszedelmességgel': 'veszedelmes', 'tompaagyúság': 'agy', 'készülsz': 'készül', 'beleessen': 'beleesik', 'furcsábbá': 'furcsa', 'remegősen': 'remeg', 'kertkapun': 'kertkapu', 'függönyözött': 'függöny', 'ezreivel': 'ezer', 'óriásivadékot': 'ivadék', 'igazgatónője': 'igazgató', 'soványabbnak': 'sovány', 'belegondolnia': 'belegondol', 'szakemberekben': 'szakember'}

def norm(s):
    return unicodedata.normalize("NFC", s).casefold()

def load_headwords(idx_path):
    data = open(idx_path, "rb").read()
    out = set()
    i = 0
    while i < len(data):
        j = data.index(b"\0", i)
        out.add(norm(data[i:j].decode("utf-8")))
        i = j + 9
    return out

def transforms(w):
    out = []
    seen = set()
    def add(x, rule, front=False):
        x = norm(x)
        if not x or x == w or x in seen:
            return
        seen.add(x)
        if front:
            out.insert(0, (x, rule))
        else:
            out.append((x, rule))

    explicit = {
        "nekem":"én","neked":"te","neki":"ő",
        "fedele":"fedél","közepén":"közép","hegyormok":"hegyorom",
    }
    if w in explicit: add(explicit[w], "explicit")

    if w.endswith("essen") and len(w) > 5:
        p = w[:-5]
        add(p + "esik", "essen→esik")
    for suf in ("özött","ozott","ezett"):
        if w.endswith(suf): add(w[:-len(suf)], suf)
    for suf in ("ősen","ósan"):
        if w.endswith(suf): add(w[:-len(suf)], suf)
    for suf in ("tan","ten"):
        if w.endswith(suf): add(w[:-len(suf)], suf)
    for suf in ("ását","ését"):
        if w.endswith(suf):
            st = w[:-len(suf)]
            if st.endswith("g") and len(st) > 2:
                add(st[:-1] + "og", suf + "→og")
                add(st[:-1] + "eg", suf + "→eg")
                add(st[:-1] + "ög", suf + "→ög")
            add(st, suf)
    for suf in ("séggel","sággal","talanok","telenek","eteket","atokat","otokat","ötöket",
                "jából","jéből","jába","jébe","járól","jéről","ján","jén","jához","jéhez","jéhöz"):
        if w.endswith(suf): add(w[:-len(suf)], suf)

    for suf in ("jait","jeit","ait","eit"):
        if w.endswith(suf):
            st = w[:-len(suf)]
            add(st, suf)
            if st.endswith("e"): add(st[:-1] + "é", suf + " restore é")
    for suf in ("jai","jei","ai","ei","ja","je"):
        if w.endswith(suf): add(w[:-len(suf)], suf)

    if w.endswith("nia"): add(w[:-3], "nia")
    if w.endswith("ni"): add(w[:-2], "ni")
    for suf in ("va","ve"):
        if w.endswith(suf):
            st = w[:-len(suf)]
            add(st + "ik", suf + "→ik")
            add(st, suf)
    for suf in ("jen","jön"):
        if w.endswith(suf): add(w[:-len(suf)], suf)
    if w.endswith("sz") and len(w) > 3: add(w[:-2], "sz")
    for suf in ("ó","ő"):
        if w.endswith(suf):
            st = w[:-1]
            add(st + "ik", suf + "→ik")
            add(st, suf)

    past = ("ottam","ettem","öttem","tam","tem","ottál","ettél","öttél","tál","tél",
            "ottunk","ettünk","öttünk","tunk","tünk","ottatok","ettetek","öttetek","tatok","tetek",
            "ottak","ettek","öttek","tak","tek","ták","ték","otta","ette","ötte","ta","te","ott","ett","ött")
    for suf in past:
        if w.endswith(suf) and len(w) > len(suf) + 1:
            st = w[:-len(suf)]
            add(st + "ik", suf + "→ik")
            add(st, suf)

    for suf in ("bbá","bbé"):
        if w.endswith(suf):
            st = w[:-len(suf)]
            if st.endswith("á"): add(st[:-1] + "a", suf)
            if st.endswith("é"): add(st[:-1] + "e", suf)
            add(st, suf)
    for suf in ("abb","ebb","obb"):
        if w.endswith(suf): add(w[:-len(suf)], suf)
    for suf in ("an","en"):
        if w.endswith(suf): add(w[:-2], suf)

    for suf in ("ás","és","úság","űség"):
        if w.endswith(suf): add(w[:-len(suf)], suf)
    if w.endswith("hatatlan"): add(w[:-8], "hatatlan")

    for suf in ("ával","ével","val","vel","kal","kel"):
        if w.endswith(suf): add(w[:-len(suf)], suf)
    if len(w) >= 4 and (w.endswith("al") or w.endswith("el")):
        base = w[:-2]
        if len(base) >= 2 and base[-1] == base[-2]:
            add(base[:-1], "assim val/vel")

    for suf in ("ját","jét","át","ét"):
        if w.endswith(suf): add(w[:-len(suf)], suf)

    cases = ("képpen","ként","ból","ből","tól","től","ról","ről","hoz","hez","höz","nál","nél",
             "ban","ben","nak","nek","ért","ba","be","ra","re","on","en","ön","ig","kor","ul","ül","vá","vé")
    for suf in cases:
        if w.endswith(suf) and len(w) > len(suf) + 1:
            st = w[:-len(suf)]
            add(st, suf)
            if st.endswith("á"):
                add(st[:-1] + "a", suf + " á→a")
                add(st[:-1], suf + " drop á")
            if st.endswith("é"):
                add(st[:-1] + "e", suf + " é→e")
                add(st[:-1], suf + " drop é")

    for suf in ("at","et","ot","öt"):
        if w.endswith(suf) and len(w) > len(suf) + 1:
            st = w[:-len(suf)]
            add(st, suf)
            mp = {"a":"á","e":"é","i":"í","o":"ó","u":"ú"}
            for i in range(len(st)-1, -1, -1):
                if st[i] in mp:
                    add(st[:i] + mp[st[i]] + st[i+1:], suf + " lengthen")
                    break
    if w.endswith("t") and len(w) > 3: add(w[:-1], "t")

    for suf in ("atok","etek","otok","ötök","unk","ünk","am","em","om","öm","ad","ed","od","öd","uk","ük","juk","jük"):
        if w.endswith(suf): add(w[:-len(suf)], suf)
    for suf in ("ák","ék"):
        if w.endswith(suf):
            add(w[:-len(suf)] + ("a" if suf == "ák" else "e"), suf)
            add(w[:-len(suf)], suf)
    for suf in ("ak","ek","ok","ök"):
        if w.endswith(suf): add(w[:-len(suf)], suf)
    if w.endswith("k") and len(w) > 3: add(w[:-1], "k")
    if w.endswith("öv"): add(w[:-2] + "ő", "öv→ő")

    if w.endswith(("a","e")) and len(w) > 3:
        add(w[:-1], "poss a/e", front=True)
    if w.endswith("n") and len(w) > 3:
        add(w[:-1], "case n", front=True)
    if w.endswith("eivel"):
        st = w[:-5]
        if st.endswith("r"):
            add(st[:-1] + "er", "eivel restore e", front=True)

    for p in ("vissza","össze","szét","bele","meg","el","ki","be","fel","le","át","rá"):
        if w.startswith(p) and len(w) > len(p) + 2:
            add(w[len(p):], "prefix")
    if w.endswith("nő") and len(w) > 2:
        add(w[:-2], "nő")

    return out

def lookup(word, headwords, max_depth=4):
    w = norm(word)
    if w in headwords:
        return w, [("exact", w)]

    q = deque([(w, 0, [])])
    seen = {w}
    explored = []

    while q:
        cur, depth, path = q.popleft()
        if depth >= max_depth:
            continue
        for nxt, rule in transforms(cur):
            if nxt in seen:
                continue
            seen.add(nxt)
            next_path = path + [(rule, nxt)]
            explored.append((nxt, next_path))
            if nxt in headwords:
                return nxt, next_path
            q.append((nxt, depth + 1, next_path))

    # Compound fallback is deliberately last. For each morphologically reduced
    # form, prefer the longest suffix that is itself a dictionary headword.
    for form in [w] + [x for x, _ in explored]:
        candidates = [form[i:] for i in range(1, len(form)) if len(form[i:]) >= 3 and form[i:] in headwords]
        if candidates:
            best = max(candidates, key=len)
            return best, [("compound", best)]

    return None, []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("idx", help="Path to the StarDict .idx file")
    args = ap.parse_args()
    headwords = load_headwords(args.idx)

    failures = 0
    print(f"Loaded {len(headwords)} StarDict headwords")
    for word, expected in TESTS.items():
        got, path = lookup(word, headwords)
        ok = got == norm(expected)
        if not ok:
            failures += 1
        status = "OK" if ok else "FAIL"
        chain = " -> ".join([norm(word)] + [p[1] for p in path])
        print(f"{status:4}  {word:22} expected={expected:16} got={str(got):16}  {chain}")

    print(f"\nResult: {len(TESTS)-failures}/{len(TESTS)} passed")
    raise SystemExit(1 if failures else 0)

if __name__ == "__main__":
    main()
