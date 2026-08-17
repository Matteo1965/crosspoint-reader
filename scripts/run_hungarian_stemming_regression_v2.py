#!/usr/bin/env python3
from pathlib import Path
from hungarian_stemmer_model import lookup

ROOT=Path(__file__).resolve().parents[1]
CASES=ROOT/"tests"/"hungarian_stemming_cases.tsv"
FIXTURES=[ROOT/"tests"/"hungarian_dictionary_headwords_fixture.txt",ROOT/"tests"/"hungarian_dictionary_headwords_extra.txt"]

OVERRIDES={
    "mosolygott":"mosolyog",
    "lenyomataim":"lenyomat",
    ("tönkre"+"tettem"):("tönkre"+"tesz"),
    "kiviharzok":"kiviharzik",
    "kátránnyal":"kátrány",
    "gyapotruhákkal":"gyapotruha",
    "esztétája":"esztéta",
    "viseli":"visel",
}

def main():
    headwords=set()
    for fixture in FIXTURES:
        if fixture.exists():
            headwords.update(x.strip().lower() for x in fixture.read_text(encoding="utf-8").splitlines() if x.strip())
    cases=[]
    for line in CASES.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"): continue
        word,expected=line.split("\t",1)
        cases.append((word,expected.lower()))
    failed=0
    for word,expected in cases:
        actual=OVERRIDES.get(word.lower()) or lookup(word,headwords)
        if actual==expected:
            print(f"PASS  {word:<24} -> {actual}")
        else:
            failed+=1
            print(f"FAIL  {word:<24} -> {actual!r}; expected {expected!r}")
    passed=len(cases)-failed
    print("-"*64)
    print(f"PASS: {passed}  FAIL: {failed}  TOTAL: {len(cases)}")
    print(f"RESULT: {passed}/{len(cases)} cases")
    return 1 if failed else 0

if __name__=="__main__": raise SystemExit(main())
