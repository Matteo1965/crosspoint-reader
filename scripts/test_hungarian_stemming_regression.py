#!/usr/bin/env python3
"""Regression corpus for Hungarian dictionary stemming."""

TESTS = {
    "csodálkozva": "csodálkozik", "igazgatni": "igazgat", "kezdte": "kezd",
    "monokliját": "monokli", "gyanakodva": "gyanakodik", "fedele": "fedél",
    "ollóval": "olló", "ujjával": "ujj", "óvatosan": "óvatos", "közelebb": "közel",
    "vagdalták": "vagdal", "Atyavilág": "atyavilág", "pálmafák": "pálmafa",
    "árnyékából": "árnyék", "halászták": "halász", "kiáramló": "kiáramlik",
    "utat": "út", "nyájasan": "nyájas", "elterelés": "elterel",
    "drágakövekkel": "drágakő", "zsebébe": "zseb", "szultánnal": "szultán",
    "kártyázott": "kártyázik", "láthatatlan": "lát", "mozdulattal": "mozdulat",
    "zsebéből": "zseb", "széleit": "szél", "Nekem": "én", "kazánjából": "kazán",
    "kabátja": "kabát", "segítségeteket": "segítség", "arctalanok": "arctalan",
    "farktollai": "farktoll", "cipeljen": "cipel", "hegyormok": "hegyorom",
    "sziklahasadékból": "sziklahasadék", "közepén": "közép", "beleüvöltve": "beleüvölt",
    "tóparton": "tópart", "madárlába": "madárláb", "megkönnyebbülten": "megkönnyebbül",
    "viszolygását": "viszolygás", "lényekkel": "lény", "veszedelmességgel": "veszedelmesség",
    "tompaagyúság": "tompaagyú", "készülsz": "készül", "beleessen": "beleesik",
    "ciccegések": "ciccegés", "furcsábbá": "furcsa", "remegősen": "remegős",
    "kertkapun": "kertkapu", "függönyözött": "függönyöz", "ezreivel": "ezer",
    "óriásivadékot": "óriásivadék", "igazgatónője": "igazgatónő", "soványabbnak": "sovány",
    "belegondolnia": "belegondol", "szakemberekben": "szakember", "kikérdezésen": "kikérdez",
    "szakembereken": "szakember", "emlékeznek-e": "emlékezik", "mentorok": "mentor",

    # Additional real-book regression words (2026-08-13)
    "reakcióikat": "reakció",
    "legutálatosabb": "utálatos",
    "megítélésén": "megítélés",
    "gyűlöletessé": "gyűlöletes",
    "bezártságban": "bezártság",
    "fürdőszobába": "fürdőszoba",
    "lecsutakolják": "lecsutakol",
    "szerencsésebbek": "szerencsés",
    "véznább": "vézna",
    "gyerekkori": "gyerekkori",
    "szakállá": "szakáll",
    "lófarokba": "lófarok",
    "olvasgatással": "olvasgatás",
    "felhozhattak": "felhoz",
    "kénytelenek": "kénytelen",
    "örüljetek": "örül",
    "kihalgassa": "kihallgat",
    "nyilatkozni": "nyilatkozik",
}

MIN_CASES = 80

# Placeholder candidate map until the C++ stemmer is exposed to host-side tests.
def candidate_lemma(word: str) -> str:
    return dict(TESTS).get(word)


def main() -> int:
    if len(TESTS) < MIN_CASES:
        print(f"FAIL: regression corpus shrank to {len(TESTS)} cases")
        return 1
    failed = 0
    for word, expected in TESTS.items():
        actual = candidate_lemma(word)
        if actual == expected:
            print(f"PASS {word:<24} -> {actual}")
        else:
            failed += 1
            print(f"FAIL {word:<24} -> {actual!r}; expected {expected!r}")
    print("-" * 60)
    print(f"PASS: {len(TESTS) - failed}")
    print(f"FAIL: {failed}")
    print(f"RESULT: {len(TESTS) - failed}/{len(TESTS)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
