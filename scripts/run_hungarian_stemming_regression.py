#!/usr/bin/env python3
from pathlib import Path
from hungarian_stemmer_model import lookup

ROOT=Path(__file__).resolve().parents[1]
CASES=ROOT/"tests"/"hungarian_stemming_cases.tsv"
FIXTURE=ROOT/"tests"/"hungarian_dictionary_headwords_fixture.txt"
EXTRA=ROOT/"tests"/"hungarian_dictionary_headwords_extra.txt"


def main():
    headwords={x.strip().lower() for x in FIXTURE.read_text(encoding="utf-8").splitlines() if x.strip()}
    if EXTRA.exists():
        headwords.update(x.strip().lower() for x in EXTRA.read_text(encoding="utf-8").splitlines() if x.strip())
    cases=[]
    for line in CASES.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"): continue
        word, expected=line.split("\t",1)
        cases.append((word, None if expected=="-" else expected.lower()))
    failed=0; xfail=0
    for word, expected in cases:
        actual=lookup(word,headwords)
        if expected is None:
            if actual is None:
                xfail+=1; print(f"XFAIL {word:<24} -> no usable StarDict headword")
            else:
                failed+=1; print(f"FAIL  {word:<24} -> {actual!r}; expected no hit")
        elif actual==expected:
            print(f"PASS  {word:<24} -> {actual}")
        else:
            failed+=1; print(f"FAIL  {word:<24} -> {actual!r}; expected {expected!r}")
    searchable=len(cases)-xfail
    passed=searchable-failed
    print("-"*64)
    print(f"PASS: {passed}  XFAIL: {xfail}  FAIL: {failed}  TOTAL: {len(cases)}")
    print(f"RESULT: {passed}/{searchable} searchable cases; {xfail} known dictionary gap")
    return 1 if failed else 0

if __name__=="__main__": raise SystemExit(main())
