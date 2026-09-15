from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-132r6: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1) Bookmarks export confirmation: force two lines and default to NEM.
replace_once(
    "src/activities/reader/EpubReaderBookmarksActivity.cpp",
    '  confirmPopup.show("Megjelölt szavak listájának mentése?", options, 3, 2, [this](int idx) {',
    '  confirmPopup.show("Megjelölt szavak\\nlistájának mentése?", options, 3, 1, [this](int idx) {',
)

# 2) Restore the full sampled-window scan. The r5 32-entry cap could abort a
# perfectly valid miss before reaching the next sample boundary and incorrectly
# surface ReadError. Keep the r4 bounded window and a reasonable time guard.
replace_once(
    "src/util/Dictionary.cpp",
    '''    if (++locateProbes > 32 || millis() - locateStart > 350) {''',
    '''    if (++locateProbes > SAMPLE_INTERVAL + 8 || millis() - locateStart > 1500) {''',
)
replace_once(
    "src/util/Dictionary.cpp",
    '''    if (++synonymProbes > 32 || millis() - synonymStart > 350) {''',
    '''    if (++synonymProbes > SAMPLE_INTERVAL + 8 || millis() - synonymStart > 1500) {''',
)

# 3) Bound the whole lookup chain. This prevents one genuine miss from spending
# several seconds in exact/synonym/morphology probes even though each individual
# locate() is bounded. Expiry is a clean NotFound outcome, not a fake IO error.
replace_once(
    "src/util/Dictionary.cpp",
    '''  DictLocation location;
  bool searchFailed = false;
  {
    LookupSession session;''',
    '''  DictLocation location;
  bool searchFailed = false;
  constexpr unsigned long MAX_LOOKUP_MS = 3000;
  const unsigned long lookupStart = millis();
  const auto lookupExpired = [&]() { return millis() - lookupStart >= MAX_LOOKUP_MS; };
  {
    LookupSession session;''',
)

replace_once(
    "src/util/Dictionary.cpp",
    '''    const auto tryHungarianV9 = [&](const std::string& candidate) {
      if (candidate.empty()) return false;
      location = locate(session, candidate.c_str(), &matchedHeadwordOut);''',
    '''    const auto tryHungarianV9 = [&](const std::string& candidate) {
      if (candidate.empty() || lookupExpired()) return false;
      location = locate(session, candidate.c_str(), &matchedHeadwordOut);''',
)

replace_once(
    "src/util/Dictionary.cpp",
    '''    if (!huV9Found) {
      location = locate(session, lookupWord.c_str(), &matchedHeadwordOut);''',
    '''    if (!huV9Found && !lookupExpired()) {
      location = locate(session, lookupWord.c_str(), &matchedHeadwordOut);''',
)

replace_once(
    "src/util/Dictionary.cpp",
    '''      const auto tryDirectHungarianV8 = [&](const std::string& candidate) {
        if (candidate.empty()) return false;
        location = locate(session, candidate.c_str(), &matchedHeadwordOut);''',
    '''      const auto tryDirectHungarianV8 = [&](const std::string& candidate) {
        if (candidate.empty() || lookupExpired()) return false;
        location = locate(session, candidate.c_str(), &matchedHeadwordOut);''',
)

replace_once(
    "src/util/Dictionary.cpp",
    '''    if (!location.found && hasSyn) {
      location = locateSynonym(session, lookupWord.c_str(), &matchedHeadwordOut);''',
    '''    if (!location.found && hasSyn && !lookupExpired()) {
      location = locateSynonym(session, lookupWord.c_str(), &matchedHeadwordOut);''',
)

replace_once(
    "src/util/Dictionary.cpp",
    '''    if (!location.found) {
      std::vector<std::string> variants;
      stemVariants(lookupWord, variants);
      constexpr size_t MAX_FALLBACK_PROBES = 16;
      constexpr unsigned long MAX_FALLBACK_MS = 1500;
      const unsigned long fallbackStart = millis();
      size_t probes = 0;
      for (const auto& variant : variants) {
        if (probes >= MAX_FALLBACK_PROBES || millis() - fallbackStart >= MAX_FALLBACK_MS) break;
        location = locate(session, variant.c_str(), &matchedHeadwordOut);''',
    '''    if (!location.found && !lookupExpired()) {
      std::vector<std::string> variants;
      stemVariants(lookupWord, variants);
      constexpr size_t MAX_FALLBACK_PROBES = 12;
      constexpr unsigned long MAX_FALLBACK_MS = 1200;
      const unsigned long fallbackStart = millis();
      size_t probes = 0;
      for (const auto& variant : variants) {
        if (probes >= MAX_FALLBACK_PROBES || millis() - fallbackStart >= MAX_FALLBACK_MS || lookupExpired()) break;
        location = locate(session, variant.c_str(), &matchedHeadwordOut);''',
)

# 4) Context headword alternatives are optional UX. Cap the complete context
# scan so a successful primary lookup can never appear to hang while looking
# for extra phrase/compound alternatives.
replace_once(
    "src/util/Dictionary.cpp",
    '''  for (const auto& candidate : candidates) {
    const std::string cleaned = cleanWord(candidate.c_str());''',
    '''  const unsigned long contextStart = millis();
  constexpr unsigned long MAX_CONTEXT_LOOKUP_MS = 1200;
  for (const auto& candidate : candidates) {
    if (millis() - contextStart >= MAX_CONTEXT_LOOKUP_MS) break;
    const std::string cleaned = cleanWord(candidate.c_str());''',
)

print("CPHUN-132r6 dictionary guard + export prompt UI fixes applied")
