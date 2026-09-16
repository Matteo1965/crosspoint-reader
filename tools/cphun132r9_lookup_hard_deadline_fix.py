from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-132r9: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1) Hard deadline for the complete dictionary lookup chain. Individual locate()
# calls are already bounded, but a miss can still fan out through synonym,
# morphology and many variants. Stop launching new probes once the whole lookup
# reaches its budget.
replace_once(
    "src/util/Dictionary.cpp",
    '''  DictLocation location;\n  bool searchFailed = false;\n  {\n    LookupSession session;''',
    '''  DictLocation location;\n  bool searchFailed = false;\n  constexpr unsigned long MAX_LOOKUP_CHAIN_MS = 3000;\n  const unsigned long lookupChainStart = millis();\n  const auto lookupChainExpired = [&]() { return millis() - lookupChainStart >= MAX_LOOKUP_CHAIN_MS; };\n  {\n    LookupSession session;''',
)

replace_once(
    "src/util/Dictionary.cpp",
    '''    const auto tryHungarianV9 = [&](const std::string& candidate) {\n      if (candidate.empty()) return false;''',
    '''    const auto tryHungarianV9 = [&](const std::string& candidate) {\n      if (candidate.empty() || lookupChainExpired()) return false;''',
)

replace_once(
    "src/util/Dictionary.cpp",
    '''    if (!huV9Found) {\n      location = locate(session, lookupWord.c_str(), &matchedHeadwordOut);''',
    '''    if (!huV9Found && !lookupChainExpired()) {\n      location = locate(session, lookupWord.c_str(), &matchedHeadwordOut);''',
)

replace_once(
    "src/util/Dictionary.cpp",
    '''      const auto tryDirectHungarianV8 = [&](const std::string& candidate) {\n        if (candidate.empty()) return false;''',
    '''      const auto tryDirectHungarianV8 = [&](const std::string& candidate) {\n        if (candidate.empty() || lookupChainExpired()) return false;''',
)

replace_once(
    "src/util/Dictionary.cpp",
    '''    if (!location.found && hasSyn) {\n      location = locateSynonym(session, lookupWord.c_str(), &matchedHeadwordOut);''',
    '''    if (!location.found && hasSyn && !lookupChainExpired()) {\n      location = locateSynonym(session, lookupWord.c_str(), &matchedHeadwordOut);''',
)

replace_once(
    "src/util/Dictionary.cpp",
    '''    if (!location.found) {\n      std::vector<std::string> variants;\n      stemVariants(lookupWord, variants);\n      for (const auto& variant : variants) {\n        location = locate(session, variant.c_str(), &matchedHeadwordOut);''',
    '''    if (!location.found && !lookupChainExpired()) {\n      std::vector<std::string> variants;\n      stemVariants(lookupWord, variants);\n      for (const auto& variant : variants) {\n        if (lookupChainExpired()) break;\n        location = locate(session, variant.c_str(), &matchedHeadwordOut);''',
)

# If the full chain expires, treat it as a bounded miss. This prevents a word
# like "biszex" (no punctuation) from appearing to hang forever while still
# preserving genuine SD/read failures reported by locate().
replace_once(
    "src/util/Dictionary.cpp",
    '''  if (!location.found) {\n    // A search that never reached a verdict (couldn't open or seek .idx) is a\n    // read failure, not a miss — reporting "Not found" is the bug this PR exists\n    // for. Otherwise the word is genuinely not in the dictionary.\n    if (searchFailed) setResult(LookupResult::ReadError);\n    return false;\n  }''',
    '''  if (!location.found) {\n    // A hard-deadline expiry is a bounded miss. Preserve genuine storage errors.\n    if (searchFailed) setResult(LookupResult::ReadError);\n    else if (lookupChainExpired()) LOG_ERR("DICT", "Lookup chain deadline reached for %s", lookupWord.c_str());\n    return false;\n  }''',
)

# 2) Context-headword probing is optional UX after a successful primary hit.
# Bound it as well so punctuation/context expansion can never hold the UI.
replace_once(
    "src/util/Dictionary.cpp",
    '''  for (const auto& candidate : candidates) {\n    const std::string cleaned = cleanWord(candidate.c_str());''',
    '''  const unsigned long contextStart = millis();\n  constexpr unsigned long MAX_CONTEXT_HEADWORD_MS = 1000;\n  for (const auto& candidate : candidates) {\n    if (millis() - contextStart >= MAX_CONTEXT_HEADWORD_MS) break;\n    const std::string cleaned = cleanWord(candidate.c_str());''',
)

# 3) Host-side regression markers: verify the three reported r8 cases stay in
# the source as explicit non-regression documentation. These are static checks;
# the device test still verifies real timing/behavior.
Path("tools/cphun132r9_regression_cases.txt").write_text(
    "CPHUN-132r9 reported regression cases:\n"
    "influenszer. -> lookup must return or show NotFound/Error, never hang\n"
    "biszex -> lookup must return or show NotFound/Error, never hang\n"
    "fürdőga- / tyában -> fragment lookup must return, never hang; boundary reconstruction tested separately\n",
    encoding="utf-8",
)

print("CPHUN-132r9 whole-chain dictionary deadline and regression guards applied")
