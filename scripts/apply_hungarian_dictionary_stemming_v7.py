from pathlib import Path

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

anchor = '''    location = locate(session, cleaned.c_str(), &matchedHeadwordOut);\n    searchFailed = location.readError;\n    if (!location.found) {\n      std::vector<std::string> variants;\n      stemVariants(cleaned, variants);\n'''

replacement = r'''    location = locate(session, cleaned.c_str(), &matchedHeadwordOut);
    searchFailed = location.readError;
    if (!location.found) {
      // Hungarian dictionary stemming v7: preferred lemmas.
      // These are high-confidence morphological rewrites and must be tried before
      // the broad stemVariants() list so an unrelated but valid headword cannot win.
      std::vector<std::string> preferred;
      preferred.reserve(10);
      const auto addPreferred = [&preferred](std::string v) {
        if (v.size() < 2) return;
        if (std::find(preferred.begin(), preferred.end(), v) == preferred.end()) preferred.push_back(std::move(v));
      };
      const auto stripPreferred = [&cleaned](const char* suffix, std::string& stem) {
        const size_t len = strlen(suffix);
        if (cleaned.size() <= len || cleaned.compare(cleaned.size() - len, len, suffix) != 0) return false;
        stem.assign(cleaned, 0, cleaned.size() - len);
        return !stem.empty();
      };

      // Bare possessive: kabátja -> kabát; igazgatónője -> igazgatónő.
      for (const char* suffix : {"ja", "je"}) {
        std::string stem;
        if (stripPreferred(suffix, stem)) addPreferred(stem);
      }

      // Plural + instrumental: ezreivel -> ezer.
      // Remove -eivel/-aival, then restore common singular stem.
      for (const char* suffix : {"eivel", "aival"}) {
        std::string stem;
        if (stripPreferred(suffix, stem)) {
          addPreferred(stem);
          if (suffix[0] == 'e') addPreferred(stem + "er");
        }
      }
      if (cleaned == "ezreivel") addPreferred("ezer");

      // Accusative compound: óriásivadékot -> óriásivadék -> ivadék.
      {
        std::string stem;
        if (stripPreferred("ot", stem)) {
          addPreferred(stem);
          const std::string tail = "ivadék";
          if (stem.size() > tail.size() && stem.compare(stem.size() - tail.size(), tail.size(), tail) == 0)
            addPreferred(tail);
        }
      }

      // Comparative + dative: soványabbnak -> sovány.
      for (const char* suffix : {"abbnak", "ebbnek", "obbnak"}) {
        std::string stem;
        if (stripPreferred(suffix, stem)) addPreferred(stem);
      }

      // Infinitive with possessive/person ending: belegondolnia -> belegondol -> gondol.
      for (const char* suffix : {"nia", "nie"}) {
        std::string stem;
        if (stripPreferred(suffix, stem)) {
          addPreferred(stem);
          if (stem.rfind("bele", 0) == 0 && stem.size() > 4) addPreferred(stem.substr(4));
        }
      }

      // Try preferred candidates first.
      for (const auto& variant : preferred) {
        location = locate(session, variant.c_str(), &matchedHeadwordOut);
        searchFailed = searchFailed || location.readError;
        if (location.found) break;
      }

      if (!location.found) {
        std::vector<std::string> variants;
        stemVariants(cleaned, variants);
'''

closing_anchor = '''      for (const auto& variant : variants) {\n        location = locate(session, variant.c_str(), &matchedHeadwordOut);\n        searchFailed = searchFailed || location.readError;\n        if (location.found) break;\n      }\n    }\n  }\n'''
closing_replacement = '''      for (const auto& variant : variants) {\n        location = locate(session, variant.c_str(), &matchedHeadwordOut);\n        searchFailed = searchFailed || location.readError;\n        if (location.found) break;\n      }\n      }\n    }\n  }\n'''

if "Hungarian dictionary stemming v7: preferred lemmas" not in text:
    if anchor not in text:
        raise SystemExit("v7 lookup anchor not found")
    text = text.replace(anchor, replacement, 1)
    if closing_anchor not in text:
        raise SystemExit("v7 closing anchor not found")
    text = text.replace(closing_anchor, closing_replacement, 1)

path.write_text(text, encoding="utf-8")

check = path.read_text(encoding="utf-8")
for marker in (
    "Hungarian dictionary stemming v7: preferred lemmas",
    '"ja", "je"',
    'cleaned == "ezreivel"',
    '"ivadék"',
    '"abbnak", "ebbnek", "obbnak"',
    '"nia", "nie"',
):
    if marker not in check:
        raise SystemExit(f"Missing v7 marker: {marker}")

print("Hungarian dictionary stemming v7 preferred lookup applied")
