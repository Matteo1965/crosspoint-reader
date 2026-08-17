from pathlib import Path

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

anchor = '''    location = locate(session, cleaned.c_str(), &matchedHeadwordOut);\n    searchFailed = location.readError;\n'''

insert = r'''

    // Hungarian dictionary lookup v8: direct high-priority lemma probes.
    // These run immediately after an exact miss and before the broader preferred
    // and generic stemming candidates, so an unrelated existing headword cannot
    // win first.
    if (!location.found) {
      const auto tryDirectHungarianV8 = [&](const std::string& candidate) {
        if (candidate.empty()) return false;
        location = locate(session, candidate.c_str(), &matchedHeadwordOut);
        searchFailed = searchFailed || location.readError;
        return location.found;
      };

      // 3rd-person singular possessive: kabátja -> kabát.
      // Female occupational compounds also fall back one component further:
      // igazgatónője -> igazgatónő (if present) -> igazgató.
      for (const char* suffix : {"ja", "je"}) {
        const size_t suffixLen = strlen(suffix);
        if (cleaned.size() <= suffixLen ||
            cleaned.compare(cleaned.size() - suffixLen, suffixLen, suffix) != 0)
          continue;

        const std::string base = cleaned.substr(0, cleaned.size() - suffixLen);
        if (tryDirectHungarianV8(base)) break;

        const char* femaleSuffix = "nő";
        const size_t femaleLen = strlen(femaleSuffix);
        if (base.size() > femaleLen &&
            base.compare(base.size() - femaleLen, femaleLen, femaleSuffix) == 0) {
          if (tryDirectHungarianV8(base.substr(0, base.size() - femaleLen))) break;
        }
      }
    }
'''

if "Hungarian dictionary lookup v8" not in text:
    if anchor not in text:
        raise SystemExit("v8 lookup anchor not found")
    text = text.replace(anchor, anchor + insert, 1)

path.write_text(text, encoding="utf-8")

check = path.read_text(encoding="utf-8")
for marker in (
    "Hungarian dictionary lookup v8",
    "tryDirectHungarianV8",
    'femaleSuffix = "nő"',
):
    if marker not in check:
        raise SystemExit(f"Missing v8 marker: {marker}")

print("Hungarian dictionary lookup v8 applied")
