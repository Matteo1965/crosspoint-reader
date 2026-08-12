from pathlib import Path

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

anchor = '''  const auto stripSuffix = [](const std::string& s, const char* suffix, std::string& stem) {\n    const size_t len = strlen(suffix);\n    if (s.size() <= len || s.compare(s.size() - len, len, suffix) != 0) return false;\n    stem.assign(s, 0, s.size() - len);\n    return !stem.empty();\n  };\n'''

insert = r'''

  // Hungarian dictionary stemming v6: high-priority corrections found in real-book testing.
  // These must run before broad suffix/compound fallbacks so the correct lemma wins first.

  // 3rd-person singular possessive: kabátja -> kabát, sapkája -> sapka.
  for (const char* suffix : {"ja", "je"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) add(stem);
  }

  // Adverb formed from a past participle/adjective: megkönnyebbülten -> megkönnyebbül.
  // Strip -tan/-ten only as an early candidate; dictionary existence still decides the match.
  for (const char* suffix : {"tan", "ten"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) add(stem);
  }
'''

if "Hungarian dictionary stemming v6" not in text:
    if anchor not in text:
        raise SystemExit("v3 stripSuffix anchor not found")
    text = text.replace(anchor, anchor + insert, 1)

path.write_text(text, encoding="utf-8")

check = path.read_text(encoding="utf-8")
for marker in (
    "Hungarian dictionary stemming v6",
    '"ja", "je"',
    '"tan", "ten"',
):
    if marker not in check:
        raise SystemExit(f"Missing v6 marker: {marker}")

print("Hungarian dictionary stemming v6 applied")
