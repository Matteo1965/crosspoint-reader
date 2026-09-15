from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-132r5: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# 1) Bookmarks/marked-words UX: export prompt on Back, no hidden export row.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/reader/EpubReaderBookmarksActivity.h",
    '''  std::string exportStatus;
  void rebuildRows();
  bool exportMarkedWords();
  bool confirmingDelete = false;
  OptionPopup confirmPopup;''',
    '''  std::string exportStatus;
  void rebuildRows();
  bool exportMarkedWords();
  void finishCancelled();
  void showExportConfirmation();
  bool confirmingDelete = false;
  bool confirmingExport = false;
  OptionPopup confirmPopup;''',
)

replace_once(
    "src/activities/reader/EpubReaderBookmarksActivity.cpp",
    '''  const size_t highlightCount = highlightStore ? highlightStore->items().size() : 0;
  const size_t total = bookmarks.size() + highlightCount + (highlightCount ? 1 : 0);
  rows.reserve(total); rowLabels.reserve(total); rowSubtitles.reserve(total); rowItems.reserve(total);''',
    '''  const size_t highlightCount = highlightStore ? highlightStore->items().size() : 0;
  const size_t total = bookmarks.size() + highlightCount;
  rows.reserve(total); rowLabels.reserve(total); rowSubtitles.reserve(total); rowItems.reserve(total);''',
)

replace_once(
    "src/activities/reader/EpubReaderBookmarksActivity.cpp",
    '''    if (!highlights.empty()) {
      rows.push_back({RowKind::Export, 0});
      rowLabels.push_back("Megjelölt szavak mentése");
      rowSubtitles.push_back(exportStatus.empty() ? "TXT" : exportStatus);
    }
''',
    '''''',
)

replace_once(
    "src/activities/reader/EpubReaderBookmarksActivity.cpp",
    '''  const RowRef row = rows[nav.selected];
  if (row.kind == RowKind::Export) {
    exportStatus = exportMarkedWords() ? exportStatus : "Mentési hiba";
    rebuildRows(); requestUpdate(true); return;
  }
  ProgressChangeResult result{};''',
    '''  const RowRef row = rows[nav.selected];
  ProgressChangeResult result{};''',
)

replace_once(
    "src/activities/reader/EpubReaderBookmarksActivity.cpp",
    '''void EpubReaderBookmarksActivity::onRowLongPress(const int index) {
  if (confirmPopup.isActive() || index < 0 || index >= listCount()) return;
  if (rows[index].kind == RowKind::Export) return;
  app.clearTapFlash(); nav.selected = index; showDeleteConfirmation();
}''',
    '''void EpubReaderBookmarksActivity::onRowLongPress(const int index) {
  if (confirmPopup.isActive() || index < 0 || index >= listCount()) return;
  app.clearTapFlash(); nav.selected = index; showDeleteConfirmation();
}''',
)

replace_once(
    "src/activities/reader/EpubReaderBookmarksActivity.cpp",
    '''bool EpubReaderBookmarksActivity::handleCustomInput() {
  if (confirmPopup.handleInput(mappedInput, [this] { requestUpdate(); })) return true;
  if (confirmingDelete) { confirmingDelete = false; requestUpdate(); return true; }
  return false;
}''',
    '''bool EpubReaderBookmarksActivity::handleCustomInput() {
  if (confirmPopup.handleInput(mappedInput, [this] { requestUpdate(); })) return true;
  if (confirmingDelete) { confirmingDelete = false; requestUpdate(); return true; }
  if (confirmingExport) { confirmingExport = false; requestUpdate(); return true; }
  return false;
}''',
)

replace_once(
    "src/activities/reader/EpubReaderBookmarksActivity.cpp",
    '''bool EpubReaderBookmarksActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    ActivityResult result; result.isCancelled = true; setResult(std::move(result)); finish(); return true;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    if (mappedInput.getHeldTime() > ENTER_DELETE_MODE_MS && !rows.empty() && rows[nav.selected].kind != RowKind::Export)
      showDeleteConfirmation();
    else openSelectedItem();
    return true;
  }
  return false;
}''',
    '''void EpubReaderBookmarksActivity::finishCancelled() {
  ActivityResult result;
  result.isCancelled = true;
  setResult(std::move(result));
  finish();
}

void EpubReaderBookmarksActivity::showExportConfirmation() {
  if (confirmPopup.isActive()) return;
  if (!highlightStore || highlightStore->items().empty()) { finishCancelled(); return; }
  confirmingExport = true;
  const char* options[] = {"IGEN", "NEM", "VISSZA"};
  confirmPopup.show("Megjelölt szavak listájának mentése?", options, 3, 2, [this](int idx) {
    confirmingExport = false;
    if (idx == 0) {
      exportStatus = exportMarkedWords() ? exportStatus : "Mentési hiba";
      finishCancelled();
      return;
    }
    if (idx == 1) {
      finishCancelled();
      return;
    }
    requestUpdate();
  });
  requestUpdate();
}

bool EpubReaderBookmarksActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    showExportConfirmation();
    return true;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    if (mappedInput.getHeldTime() > ENTER_DELETE_MODE_MS && !rows.empty())
      showDeleteConfirmation();
    else openSelectedItem();
    return true;
  }
  return false;
}''',
)

replace_once(
    "src/activities/reader/EpubReaderBookmarksActivity.cpp",
    '''  const RowRef row = rows[nav.selected];
  if (row.kind == RowKind::Export) return;
  confirmingDelete = true;''',
    '''  const RowRef row = rows[nav.selected];
  confirmingDelete = true;''',
)

replace_once(
    "src/activities/reader/EpubReaderBookmarksActivity.cpp",
    '''    GUI.drawHelpText(renderer, Rect{band.x, band.y + metrics.verticalSpacing, band.width, helpLineHeight},
                     tr(STR_HOLD_OPEN_TO_DELETE));''',
    '''    GUI.drawHelpText(renderer, Rect{band.x, band.y + metrics.verticalSpacing, band.width, helpLineHeight},
                     I18N.getLanguage() == Language::HU ? "Törléshez tartsd nyomva: Kijelölés"
                                                        : "Hold Select to Delete");''',
)

# -----------------------------------------------------------------------------
# 2) Dictionary hard-stop for genuine misses.
#    Never run locate/synonym search without a valid sampled sidecar, and keep
#    per-probe / morphology fallbacks short enough that a miss returns promptly.
# -----------------------------------------------------------------------------
replace_once(
    "src/util/Dictionary.cpp",
    '''  const uint32_t startByte = bisectSamples(session.qidx, session.idx, session.sampleCount, target);
  if (startByte == UINT32_MAX) { result.readError = true; return result; }''',
    '''  if (session.sampleCount == 0) { result.readError = true; return result; }
  const uint32_t startByte = bisectSamples(session.qidx, session.idx, session.sampleCount, target);
  if (startByte == UINT32_MAX) { result.readError = true; return result; }''',
)
replace_once(
    "src/util/Dictionary.cpp",
    '''    if (++locateProbes > SAMPLE_INTERVAL + 8 || millis() - locateStart > 1500) {''',
    '''    if (++locateProbes > 32 || millis() - locateStart > 350) {''',
)
replace_once(
    "src/util/Dictionary.cpp",
    '''  const uint32_t startByte = bisectSamples(session.sidx, session.syn, session.synSampleCount, target);
  if (startByte == UINT32_MAX) { result.readError = true; return result; }''',
    '''  if (session.synSampleCount == 0) { result.readError = true; return result; }
  const uint32_t startByte = bisectSamples(session.sidx, session.syn, session.synSampleCount, target);
  if (startByte == UINT32_MAX) { result.readError = true; return result; }''',
)
replace_once(
    "src/util/Dictionary.cpp",
    '''    if (++synonymProbes > SAMPLE_INTERVAL + 8 || millis() - synonymStart > 1500) {''',
    '''    if (++synonymProbes > 32 || millis() - synonymStart > 350) {''',
)
replace_once(
    "src/util/Dictionary.cpp",
    '''      constexpr size_t MAX_FALLBACK_PROBES = 48;
      constexpr unsigned long MAX_FALLBACK_MS = 4000;''',
    '''      constexpr size_t MAX_FALLBACK_PROBES = 16;
      constexpr unsigned long MAX_FALLBACK_MS = 1500;''',
)

# -----------------------------------------------------------------------------
# 3) Treat an automatically hyphenated line break as one logical selectable word.
#    The source-offset test distinguishes a synthetic line-end hyphen from an
#    explicit hyphen that really exists in the EPUB source.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    '''  void performLookup();
  HighlightResult makeHighlightResult() const;''',
    '''  void performLookup();
  bool syntheticHyphenPair(int first, int second) const;
  int logicalWordFirst(int index) const;
  int logicalWordSecond(int first) const;
  std::string logicalWordText(int index) const;
  HighlightResult makeHighlightResult() const;''',
)

replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''HighlightResult DictionaryWordSelectActivity::makeHighlightResult() const {
  if (words.empty()) return {};
  const WordBox& word = words[selected];
  HighlightResult result;
  result.spineIndex = spineIndex;
  result.visibleTextOffset = word.block ? word.block->wordVisibleTextOffset(word.tokenIndex) : page->visibleTextOffset;
  result.length = visibleCodepointLength(word.text);
  result.text = word.text ? word.text : "";
  return result;
}''',
    '''bool DictionaryWordSelectActivity::syntheticHyphenPair(const int first, const int second) const {
  if (first < 0 || second != first + 1 || second >= static_cast<int>(words.size())) return false;
  const WordBox& a = words[first];
  const WordBox& b = words[second];
  if (!a.block || !b.block || b.row != a.row + 1 || !a.text || !b.text) return false;
  const std::string left(a.text);
  size_t hyphenBytes = 0;
  if (!left.empty() && left.back() == '-') hyphenBytes = 1;
  else if (left.size() >= 3 && left.compare(left.size() - 3, 3, "\\xE2\\x80\\x91") == 0) hyphenBytes = 3;
  if (hyphenBytes == 0) return false;

  std::string prefix = left.substr(0, left.size() - hyphenBytes);
  const uint32_t aOffset = a.block->wordVisibleTextOffset(a.tokenIndex);
  const uint32_t bOffset = b.block->wordVisibleTextOffset(b.tokenIndex);
  // Synthetic hyphen is absent from source text, so the second half starts
  // immediately after the source prefix. An explicit source hyphen advances
  // the source offset by one more codepoint and therefore fails this test.
  return bOffset == aOffset + visibleCodepointLength(prefix.c_str());
}

int DictionaryWordSelectActivity::logicalWordFirst(const int index) const {
  if (syntheticHyphenPair(index, index + 1)) return index;
  if (syntheticHyphenPair(index - 1, index)) return index - 1;
  return index;
}

int DictionaryWordSelectActivity::logicalWordSecond(const int first) const {
  return syntheticHyphenPair(first, first + 1) ? first + 1 : first;
}

std::string DictionaryWordSelectActivity::logicalWordText(const int index) const {
  if (words.empty() || index < 0 || index >= static_cast<int>(words.size())) return {};
  const int first = logicalWordFirst(index);
  const int second = logicalWordSecond(first);
  if (first == second) return words[first].text ? words[first].text : "";
  std::string text = words[first].text ? words[first].text : "";
  if (!text.empty() && text.back() == '-') text.pop_back();
  else if (text.size() >= 3 && text.compare(text.size() - 3, 3, "\\xE2\\x80\\x91") == 0) text.resize(text.size() - 3);
  if (words[second].text) text += words[second].text;
  return text;
}

HighlightResult DictionaryWordSelectActivity::makeHighlightResult() const {
  if (words.empty()) return {};
  const int first = logicalWordFirst(selected);
  const WordBox& word = words[first];
  HighlightResult result;
  result.spineIndex = spineIndex;
  result.visibleTextOffset = word.block ? word.block->wordVisibleTextOffset(word.tokenIndex) : page->visibleTextOffset;
  result.text = logicalWordText(selected);
  result.length = visibleCodepointLength(result.text.c_str());
  return result;
}''',
)

replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''  // CPHUN-89: selected word first. Exact context headwords are alternatives.
  const bool found = ok && dict.lookup(words[selected].text, definition, headword, &result);''',
    '''  // CPHUN-89/132r5: look up the complete logical word, including both
  // halves of an automatically hyphenated line-break word.
  const std::string lookupWord = logicalWordText(selected);
  const bool found = ok && dict.lookup(lookupWord.c_str(), definition, headword, &result);''',
)

# Highlight both halves when a synthetic line-break split is selected. Snapshot
# fast-path is disabled only for this rare two-row case; normal words keep it.
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''bool DictionaryWordSelectActivity::drawHighlightWithSnapshot() {
  const WordBox& word = words[selected];''',
    '''bool DictionaryWordSelectActivity::drawHighlightWithSnapshot() {
  const int first = logicalWordFirst(selected);
  const int second = logicalWordSecond(first);
  if (first != second) {
    for (const int idx : {first, second}) {
      const WordBox& part = words[idx];
      const int hx = std::max(0, static_cast<int>(part.x) - 2);
      const int hy = std::max(0, static_cast<int>(part.y) - 2);
      const int hw = part.width + 4;
      const int hh = lineHeight + 4;
      renderer.fillRect(hx, hy, hw, hh, true);
      renderer.drawText(fontId, part.x, part.y, part.text, false, part.style);
    }
    snapshotIdx = -1;
    return false;
  }
  const WordBox& word = words[selected];''',
)

print("CPHUN-132r5 review fixes applied")
