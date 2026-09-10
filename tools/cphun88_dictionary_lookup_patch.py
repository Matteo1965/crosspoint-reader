from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"Expected one match in {path}, found {text.count(old)}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")

replace_once("src/CPHUNBuildId.h", "CPHUN-260910-87", "CPHUN-260910-88")

# Preserve meaningful ASCII hyphens at headword edges. Other punctuation is
# still cleaned exactly as before. This lets dictionary-authored suffix entries
# such as -ista and -ság/-ség reach the exact-match path before stemming.
replace_once(
    "src/util/Dictionary.cpp",
    """  while (start < end) {\n    if (!isWordByte(b[start]))\n      start++;\n""",
    """  while (start < end) {\n    if (b[start] == '-' && start + 1 < end && isWordByte(b[start + 1]))\n      break;\n    if (!isWordByte(b[start]))\n      start++;\n""",
)
replace_once(
    "src/util/Dictionary.cpp",
    """  while (end > start) {\n    if (!isWordByte(b[end - 1]))\n      end--;\n""",
    """  while (end > start) {\n    if (b[end - 1] == '-' && end - start > 1 && isWordByte(b[end - 2]))\n      break;\n    if (!isWordByte(b[end - 1]))\n      end--;\n""",
)

# Longest exact lookup first: selected+next, then selected alone. Two-token
# lookup is deliberately bounded to adjacent selectable words on the same row;
# this keeps the first implementation cheap and avoids joining across layout
# lines. If the phrase misses, the existing one-word exact/stemming path runs.
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    """  std::string definition;\n  std::string headword;\n  Dictionary::LookupResult result = Dictionary::LookupResult::NotFound;\n  const bool found = ok && dict.lookup(words[selected].text, definition, headword, &result);\n\n  if (found) {\n""",
    """  std::string definition;\n  std::string headword;\n  Dictionary::LookupResult result = Dictionary::LookupResult::NotFound;\n  bool found = false;\n\n  // CPHUN-88: prefer a two-token exact phrase beginning at the selected word.\n  // Dictionary::lookup() already tries exact lookup before stemming, so a\n  // dictionary headword such as \"formális logika\" wins over \"formális\".\n  if (ok && selected + 1 < static_cast<int>(words.size()) &&\n      words[selected].row == words[selected + 1].row) {\n    const std::string phrase = std::string(words[selected].text) + \" \" + words[selected + 1].text;\n    found = dict.lookup(phrase.c_str(), definition, headword, &result);\n    if (!found && result != Dictionary::LookupResult::NotFound) {\n      // A real SD/decompression/OOM failure must not be hidden by a second\n      // lookup that happens to miss or succeed.\n      ok = false;\n    }\n  }\n  if (ok && !found) {\n    definition.clear();\n    headword.clear();\n    result = Dictionary::LookupResult::NotFound;\n    found = dict.lookup(words[selected].text, definition, headword, &result);\n  }\n\n  if (found) {\n""",
)

print("CPHUN-88 dictionary lookup patch applied")
