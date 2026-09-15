from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-132r3: {path}: expected one match, found {count}: {old[:140]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1) True toggle semantics for saved highlights.
replace_once(
    "src/highlights/HighlightStore.h",
    '''  bool contains(const HighlightAnchor& anchor) const;
  bool add(const HighlightAnchor& anchor);
  const std::vector<HighlightAnchor>& items() const { return highlights_; }''',
    '''  bool contains(const HighlightAnchor& anchor) const;
  bool add(const HighlightAnchor& anchor);
  bool remove(const HighlightAnchor& anchor);
  bool toggle(const HighlightAnchor& anchor);
  const std::vector<HighlightAnchor>& items() const { return highlights_; }''',
)

replace_once(
    "src/highlights/HighlightStore.cpp",
    '''bool HighlightStore::add(const HighlightAnchor& anchor) {
  if (contains(anchor)) return true;
  highlights_.push_back(anchor);
  if (save()) return true;
  highlights_.pop_back();
  return false;
}
''',
    '''bool HighlightStore::add(const HighlightAnchor& anchor) {
  if (contains(anchor)) return true;
  highlights_.push_back(anchor);
  if (save()) return true;
  highlights_.pop_back();
  return false;
}

bool HighlightStore::remove(const HighlightAnchor& anchor) {
  const auto it = std::find_if(highlights_.begin(), highlights_.end(),
                               [&](const HighlightAnchor& item) { return sameAnchor(item, anchor); });
  if (it == highlights_.end()) return true;
  const HighlightAnchor removed = *it;
  const size_t index = static_cast<size_t>(it - highlights_.begin());
  highlights_.erase(it);
  if (save()) return true;
  highlights_.insert(highlights_.begin() + index, removed);
  return false;
}

bool HighlightStore::toggle(const HighlightAnchor& anchor) {
  return contains(anchor) ? remove(anchor) : add(anchor);
}
''',
)

replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''              highlightStore->add({selected->spineIndex, selected->visibleTextOffset, selected->length, selected->text});''',
    '''              highlightStore->toggle({selected->spineIndex, selected->visibleTextOffset, selected->length, selected->text});''',
)

# 2) Bound expensive morphology fallback for genuine misses. Exact/synonym/high-priority probes still run first.
replace_once(
    "src/util/Dictionary.cpp",
    '''    if (!location.found) {
      std::vector<std::string> variants;
      stemVariants(lookupWord, variants);
      for (const auto& variant : variants) {
        location = locate(session, variant.c_str(), &matchedHeadwordOut);
        searchFailed = searchFailed || location.readError;
        if (location.found) break;
      }
    }''',
    '''    if (!location.found) {
      std::vector<std::string> variants;
      stemVariants(lookupWord, variants);
      constexpr size_t MAX_FALLBACK_PROBES = 48;
      constexpr unsigned long MAX_FALLBACK_MS = 4000;
      const unsigned long fallbackStart = millis();
      size_t probes = 0;
      for (const auto& variant : variants) {
        if (probes >= MAX_FALLBACK_PROBES || millis() - fallbackStart >= MAX_FALLBACK_MS) break;
        location = locate(session, variant.c_str(), &matchedHeadwordOut);
        ++probes;
        searchFailed = searchFailed || location.readError;
        if (location.found || location.readError) break;
        if ((probes & 0x07) == 0) vTaskDelay(1);
      }
    }''',
)

# Dictionary.cpp already has Arduino.h but not FreeRTOS task API in every build; use delay(1) instead of vTaskDelay.
replace_once(
    "src/util/Dictionary.cpp",
    "        if ((probes & 0x07) == 0) vTaskDelay(1);",
    "        if ((probes & 0x07) == 0) delay(1);",
)

print("CPHUN-132r3 highlight toggle + bounded not-found lookup patch applied")
