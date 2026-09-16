from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-132r9: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# CPHUN-132r6 already puts a hard deadline around the complete lookup chain.
# The remaining unbounded path is locateByOrdinal(): a synonym hit can resolve
# to an ordinal and then scan .idx entry-by-entry. With a stale/corrupt sidecar
# or synonym ordinal this can take effectively forever on-device before the
# outer lookup regains control. Bound that inner scan directly.
replace_once(
    "src/util/Dictionary.cpp",
    '''  uint8_t suffix[8];
  for (uint32_t e = startOrdinal; e < ordinal; e++) {
    if (readWordInto(session.idx, wordBuf, sizeof(wordBuf)) < 0 || session.idx.read(suffix, 8) != 8) return result;
    if (static_cast<uint32_t>(session.idx.position()) >= session.idxSize) return result;  // ordinal past last entry
  }''',
    '''  uint8_t suffix[8];
  constexpr uint32_t MAX_ORDINAL_SCAN_ENTRIES = SAMPLE_INTERVAL + 8;
  constexpr unsigned long MAX_ORDINAL_SCAN_MS = 1200;
  const unsigned long ordinalScanStart = millis();
  uint32_t ordinalScans = 0;
  for (uint32_t e = startOrdinal; e < ordinal; e++) {
    if (++ordinalScans > MAX_ORDINAL_SCAN_ENTRIES || millis() - ordinalScanStart >= MAX_ORDINAL_SCAN_MS) {
      LOG_ERR("DICT", "Ordinal lookup guard reached: %lu -> %lu",
              static_cast<unsigned long>(startOrdinal), static_cast<unsigned long>(ordinal));
      return result;
    }
    if (readWordInto(session.idx, wordBuf, sizeof(wordBuf)) < 0 || session.idx.read(suffix, 8) != 8) return result;
    if (static_cast<uint32_t>(session.idx.position()) >= session.idxSize) return result;  // ordinal past last entry
  }''',
)

# A corrupt synonym sidecar can also hand locateByOrdinal() an out-of-range
# ordinal when entryCount is unavailable. Reject obviously impossible values
# before doing any scan.
replace_once(
    "src/util/Dictionary.cpp",
    '''DictLocation Dictionary::locateByOrdinal(LookupSession& session, uint32_t ordinal, std::string* matchedHeadwordOut) {
  DictLocation result;
''',
    '''DictLocation Dictionary::locateByOrdinal(LookupSession& session, uint32_t ordinal, std::string* matchedHeadwordOut) {
  DictLocation result;
  if (session.entryCount != 0 && ordinal >= session.entryCount) {
    LOG_ERR("DICT", "Synonym ordinal out of range: %lu >= %lu", static_cast<unsigned long>(ordinal),
            static_cast<unsigned long>(session.entryCount));
    return result;
  }
''',
)

# Keep the user-reported r8 regressions explicit in the branch so future patch
# chains cannot silently drop them from device testing.
Path("tools/cphun132r9_regression_cases.txt").write_text(
    "CPHUN-132r9 reported regression cases:\n"
    "influenszer. -> lookup must return or show NotFound/Error, never hang\n"
    "biszex -> lookup must return or show NotFound/Error, never hang\n"
    "fürdőga- -> fragment lookup must return, never hang\n"
    "tyában -> fragment lookup must return, never hang\n"
    "fürdőga-tyában -> page-boundary reconstruction tested separately\n",
    encoding="utf-8",
)

print("CPHUN-132r9 bounded synonym ordinal lookup guard applied")
