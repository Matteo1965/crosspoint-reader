from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-132r2: {path}: expected one match, found {count}: {old[:140]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_before(path, marker, addition):
    replace_once(path, marker, addition + marker)


def insert_after(path, marker, addition):
    replace_once(path, marker, marker + addition)


# 1) Keep previously saved highlights visible inside Dictionary/Highlight word-selection mode
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    '''  explicit DictionaryWordSelectActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                        std::unique_ptr<Page> page, int marginLeft, int marginTop,
                                        int spineIndex, WordSelectionMode mode = WordSelectionMode::Dictionary)
      : Activity("DictionaryWordSelect", renderer, mappedInput),
        page(std::move(page)),
        marginLeft(marginLeft),
        marginTop(marginTop),
        spineIndex(spineIndex),
        mode(mode) {}''',
    '''  explicit DictionaryWordSelectActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                        std::unique_ptr<Page> page, int marginLeft, int marginTop,
                                        int spineIndex, WordSelectionMode mode = WordSelectionMode::Dictionary,
                                        std::vector<uint32_t> highlightedOffsets = {})
      : Activity("DictionaryWordSelect", renderer, mappedInput),
        page(std::move(page)),
        marginLeft(marginLeft),
        marginTop(marginTop),
        spineIndex(spineIndex),
        mode(mode),
        highlightedOffsets(std::move(highlightedOffsets)) {}''',
)
insert_after(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    "  void drawHints() const;\n",
    "  void drawStoredHighlights() const;\n",
)
insert_after(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    "  const WordSelectionMode mode;\n",
    "  const std::vector<uint32_t> highlightedOffsets;\n",
)

insert_before(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    "bool DictionaryWordSelectActivity::drawHighlightWithSnapshot() {\n",
    '''void DictionaryWordSelectActivity::drawStoredHighlights() const {
  if (highlightedOffsets.empty()) return;
  for (const auto& word : words) {
    if (!word.block) continue;
    const uint32_t offset = word.block->wordVisibleTextOffset(word.tokenIndex);
    if (std::find(highlightedOffsets.begin(), highlightedOffsets.end(), offset) == highlightedOffsets.end()) continue;
    const int y = word.y + lineHeight - 2;
    renderer.drawLine(word.x, y, word.x + word.width, y, 2, true);
  }
}

''',
)
insert_after(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''  scope.endScanAndPrewarm();
  page->render(renderer, fontId, marginLeft, marginTop);
''',
    "  drawStoredHighlights();\n",
)

# 2) Lower foreground heap pressure during dictionary lookup, but re-enable fast cursor repaint afterwards.
insert_after(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    "void DictionaryWordSelectActivity::performLookup() {\n",
    '''  snapshot.reset();
  snapshotIdx = -1;
''',
)
insert_before(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''  if (!words.empty()) {
    drawHighlightWithSnapshot();
  }
''',
    '''  if (!snapshot) snapshot = makeUniqueNoThrow<uint8_t[]>(SNAPSHOT_CAPACITY);
''',
)

# Retry one transient SD/read failure before surfacing an error. Genuine NotFound is not retried.
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''  const bool found = ok && dict.lookup(words[selected].text, definition, headword, &result);

  if (found) {''',
    '''  bool found = ok && dict.lookup(words[selected].text, definition, headword, &result);
  if (!found && ok && result == Dictionary::LookupResult::ReadError) {
    vTaskDelay(1);
    definition.clear();
    headword.clear();
    result = Dictionary::LookupResult::NotFound;
    found = dict.lookup(words[selected].text, definition, headword, &result);
  }

  if (found) {''',
)

# 3) Do not silently turn short/interrupted .idx reads into false NotFound results.
replace_once(
    "src/util/Dictionary.cpp",
    '''    // Not flagged as readError: readWordInto returns -1 for EOF and IO error
    // alike, so a short tail can't be told from a truncated .idx. Treat it as
    // the end of the index rather than risk reporting a read failure for what
    // is really a miss.
    if (readWordInto(session.idx, wordBuf, sizeof(wordBuf)) < 0) break;
    uint8_t suffix[8];
    if (session.idx.read(suffix, 8) != 8) break;''',
    '''    if (readWordInto(session.idx, wordBuf, sizeof(wordBuf)) < 0) {
      if (static_cast<uint32_t>(session.idx.position()) < session.idxSize) result.readError = true;
      break;
    }
    uint8_t suffix[8];
    if (session.idx.read(suffix, 8) != 8) {
      result.readError = true;
      break;
    }''',
)

# 4) Pass only the tiny current-spine offset list into the selector, while the full store remains released.
insert_after(
    "src/activities/reader/EpubReaderActivity.cpp",
    "  const std::string highlightBookPath = epub->getPath();\n",
    '''  std::vector<uint32_t> highlightedOffsets;
  if (highlightStore) {
    for (const auto& item : highlightStore->items()) {
      if (item.spineIndex == currentSpineIndex) highlightedOffsets.push_back(item.visibleTextOffset);
    }
  }
''',
)
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''      std::make_unique<DictionaryWordSelectActivity>(renderer, mappedInput, std::move(page), orientedMarginLeft,
                                                     orientedMarginTop, currentSpineIndex, mode),''',
    '''      std::make_unique<DictionaryWordSelectActivity>(renderer, mappedInput, std::move(page), orientedMarginLeft,
                                                     orientedMarginTop, currentSpineIndex, mode,
                                                     std::move(highlightedOffsets)),''',
)

print("CPHUN-132r2 highlight visibility + dictionary reliability patch applied")
