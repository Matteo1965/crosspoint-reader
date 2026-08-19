from pathlib import Path
import re

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

if "Hungarian dictionary stemming v15" not in text:
    marker = "  // Hungarian dictionary stemming v14: validated real-book lexical restorations.\n"
    if marker not in text:
        raise SystemExit("v15 v14 marker not found")
    text = text.replace(
        marker,
        marker + "  // Hungarian dictionary stemming v15: reject short accidental compound-tail matches.\n",
        1,
    )

    # Keep a tiny explicit set of validated short compound fallbacks that would
    # otherwise be removed by the generic minimum-length guard.
    special_anchor = '{"esztétája","esztéta"},{"viseli","visel"}'
    if special_anchor not in text:
        raise SystemExit("v15 SPECIAL anchor not found")
    text = text.replace(
        special_anchor,
        special_anchor + ',{"tóparton","part"},{"lófarokba","farok"},{"beleüvöltve","üvölt"}',
        1,
    )

    # The v12 compound fallback used every 3+ codepoint suffix.  That makes
    # unrelated dictionary words such as 'ott', 'tél', 'eke', 'lik', etc.
    # win when the intended lemma is absent.  Require at least 6 codepoints.
    pattern = re.compile(r"(if\s*\(\s*cps\s*>=\s*)3(\s*\)\s*addUnique\s*\(\s*compound\s*,\s*tail\s*\)\s*;)")
    text, count = pattern.subn(r"\g<1>6\g<2>", text, count=1)
    if count != 1:
        raise SystemExit(f"v15 compound-tail guard replacement count={count}, expected 1")

path.write_text(text, encoding="utf-8")
check = path.read_text(encoding="utf-8")
for required in (
    "Hungarian dictionary stemming v15",
    '{"tóparton","part"}',
    '{"lófarokba","farok"}',
    '{"beleüvöltve","üvölt"}',
):
    if required not in check:
        raise SystemExit(f"Missing v15 marker: {required}")

if re.search(r"cps\s*>=\s*3\s*\)\s*addUnique\s*\(\s*compound\s*,\s*tail", check):
    raise SystemExit("Old 3-codepoint compound-tail guard still present")
if not re.search(r"cps\s*>=\s*6\s*\)\s*addUnique\s*\(\s*compound\s*,\s*tail", check):
    raise SystemExit("New 6-codepoint compound-tail guard missing")

print("Hungarian dictionary stemming v15 short-tail guard applied")
