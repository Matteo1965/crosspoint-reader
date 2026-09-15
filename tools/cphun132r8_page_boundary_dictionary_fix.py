from pathlib import Path
import re


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-132r8: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def regex_replace_once(path, pattern, replacement):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    text2, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"CPHUN-132r8: {path}: regex expected one match, found {count}: {pattern[:180]!r}")
    p.write_text(text2, encoding="utf-8")


# -----------------------------------------------------------------------------
# 1) Page-boundary synthetic hyphen reconstruction.
#    Keep only the neighboring page's boundary word+offset, not the whole page,
#    so the dictionary path does not retain three Page objects in heap.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    '''  void onEnter() override;
  void loop() override;
  void render(RenderLock&&) override;''',
    '''  void onEnter() override;
  void loop() override;
  void render(RenderLock&&) override;
  void setPreviousBoundaryPage(std::unique_ptr<Page> previousPage);
  void setNextBoundaryPage(std::unique_ptr<Page> nextPage);''',
)

replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    '''  std::vector<WordBox> words;
  int selected = 0;''',
    '''  std::vector<WordBox> words;
  std::string previousBoundaryText;
  uint32_t previousBoundaryOffset = 0;
  std::string nextBoundaryText;
  uint32_t nextBoundaryOffset = 0;
  int selected = 0;''',
)

insert_marker = '''void DictionaryWordSelectActivity::extractWords() {
'''
addition = r'''namespace {

bool pageBoundaryWord(const Page& page, const bool last, std::string& textOut, uint32_t& offsetOut) {
  if (!last) {
    for (const auto& element : page.elements) {
      if (element->getTag() != TAG_PageLine) continue;
      const auto* line = static_cast<const PageLine*>(element.get());
      const auto& block = line->getBlock();
      if (!block || !block->valid()) continue;
      for (uint16_t i = 0; i < block->wordCount(); ++i) {
        const char* text = block->wordText(i);
        if (!isSelectableToken(text)) continue;
        textOut = text ? text : "";
        offsetOut = block->wordVisibleTextOffset(i);
        return true;
      }
    }
    return false;
  }

  for (auto eit = page.elements.rbegin(); eit != page.elements.rend(); ++eit) {
    if ((*eit)->getTag() != TAG_PageLine) continue;
    const auto* line = static_cast<const PageLine*>((*eit).get());
    const auto& block = line->getBlock();
    if (!block || !block->valid()) continue;
    for (int i = static_cast<int>(block->wordCount()) - 1; i >= 0; --i) {
      const char* text = block->wordText(static_cast<uint16_t>(i));
      if (!isSelectableToken(text)) continue;
      textOut = text ? text : "";
      offsetOut = block->wordVisibleTextOffset(static_cast<uint16_t>(i));
      return true;
    }
  }
  return false;
}

bool stripSyntheticLineEndHyphen(std::string& text) {
  if (!text.empty() && text.back() == '-') {
    text.pop_back();
    return true;
  }
  if (text.size() >= 3 && text.compare(text.size() - 3, 3, "\xE2\x80\x91") == 0) {
    text.resize(text.size() - 3);
    return true;
  }
  return false;
}

}  // namespace

void DictionaryWordSelectActivity::setPreviousBoundaryPage(std::unique_ptr<Page> previousPage) {
  previousBoundaryText.clear();
  previousBoundaryOffset = 0;
  if (previousPage) pageBoundaryWord(*previousPage, true, previousBoundaryText, previousBoundaryOffset);
}

void DictionaryWordSelectActivity::setNextBoundaryPage(std::unique_ptr<Page> nextPage) {
  nextBoundaryText.clear();
  nextBoundaryOffset = 0;
  if (nextPage) pageBoundaryWord(*nextPage, false, nextBoundaryText, nextBoundaryOffset);
}

'''
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    insert_marker,
    addition + insert_marker,
)

old_logical = r'''std::string DictionaryWordSelectActivity::logicalWordText(const int index) const {
  if (words.empty() || index < 0 || index >= static_cast<int>(words.size())) return {};
  const int first = logicalWordFirst(index);
  const int second = logicalWordSecond(first);
  if (first == second) return words[first].text ? words[first].text : "";
  std::string text = words[first].text ? words[first].text : "";
  if (!text.empty() && text.back() == '-') text.pop_back();
  else if (text.size() >= 3 && text.compare(text.size() - 3, 3, "\xE2\x80\x91") == 0) text.resize(text.size() - 3);
  if (words[second].text) text += words[second].text;
  return text;
}'''

new_logical = r'''std::string DictionaryWordSelectActivity::logicalWordText(const int index) const {
  if (words.empty() || index < 0 || index >= static_cast<int>(words.size())) return {};
  const int first = logicalWordFirst(index);
  const int second = logicalWordSecond(first);
  if (first != second) {
    std::string text = words[first].text ? words[first].text : "";
    stripSyntheticLineEndHyphen(text);
    if (words[second].text) text += words[second].text;
    return text;
  }

  const WordBox& current = words[index];
  const uint32_t currentOffset = current.block ? current.block->wordVisibleTextOffset(current.tokenIndex) : 0;

  // Current page begins with the second half of a synthetic page-boundary split.
  if (index == 0 && !previousBoundaryText.empty()) {
    std::string prefix = previousBoundaryText;
    if (stripSyntheticLineEndHyphen(prefix) &&
        currentOffset == previousBoundaryOffset + visibleCodepointLength(prefix.c_str())) {
      if (current.text) prefix += current.text;
      return prefix;
    }
  }

  // Current page ends with the first half of a synthetic page-boundary split.
  if (index == static_cast<int>(words.size()) - 1 && !nextBoundaryText.empty()) {
    std::string prefix = current.text ? current.text : "";
    if (stripSyntheticLineEndHyphen(prefix) &&
        nextBoundaryOffset == currentOffset + visibleCodepointLength(prefix.c_str())) {
      prefix += nextBoundaryText;
      return prefix;
    }
  }

  return current.text ? current.text : "";
}'''
replace_once("src/activities/reader/DictionaryWordSelectActivity.cpp", old_logical, new_logical)

# Build a selector first, feed boundary pages one-by-one (so each is released
# immediately after its boundary token is copied), then start the activity.
# Match semantically instead of depending on clang-format line wrapping. Earlier
# CPHUN-132 revisions may reflow this constructor call before r8 is applied.
selector_pattern = (
    r'  highlightStore\.reset\(\);\n'
    r'  startActivityForResult\(\s*\n'
    r'\s*std::make_unique<DictionaryWordSelectActivity>\(renderer, mappedInput, std::move\(page\),\s*'
    r'orientedMarginLeft,\s*orientedMarginTop,\s*currentSpineIndex,\s*mode\),\s*\n'
    r'\s*\[this, highlightBookPath\]\(const ActivityResult& result\) \{'
)
selector_replacement = '''  highlightStore.reset();
  auto selector = std::make_unique<DictionaryWordSelectActivity>(renderer, mappedInput, std::move(page),
                                                                 orientedMarginLeft, orientedMarginTop,
                                                                 currentSpineIndex, mode);
  if (section->currentPage > 0) selector->setPreviousBoundaryPage(section->loadPage(section->currentPage - 1));
  if (section->currentPage + 1 < static_cast<int>(section->pageCount))
    selector->setNextBoundaryPage(section->loadPage(section->currentPage + 1));
  startActivityForResult(
      std::move(selector),
      [this, highlightBookPath](const ActivityResult& result) {'''
regex_replace_once("src/activities/reader/EpubReaderActivity.cpp", selector_pattern, selector_replacement)

# -----------------------------------------------------------------------------
# 2) DictZip hard deadline. A bad/corrupt definition entry must not keep the
#    reader inside uzlib forever. This is intentionally below the dictionary's
#    outer lookup deadline because readDefinition() happens after index lookup.
# -----------------------------------------------------------------------------
replace_once(
    "src/util/DictZip.cpp",
    '''  uint32_t remaining = 0;  // compressed bytes left in this chunk
  bool readFailed = false;
  uint8_t buf[INPUT_BUF_BYTES] = {};''',
    '''  uint32_t remaining = 0;  // compressed bytes left in this chunk
  unsigned long deadlineMs = 0;
  bool readFailed = false;
  bool timedOut = false;
  uint8_t buf[INPUT_BUF_BYTES] = {};''',
)

replace_once(
    "src/util/DictZip.cpp",
    '''int chunkReadCb(uzlib_uncomp* u) {
  auto* src = reinterpret_cast<ChunkSource*>(u);
  if (src->remaining == 0) return -1;''',
    '''int chunkReadCb(uzlib_uncomp* u) {
  auto* src = reinterpret_cast<ChunkSource*>(u);
  if (src->deadlineMs != 0 && static_cast<long>(millis() - src->deadlineMs) >= 0) {
    src->timedOut = true;
    return -1;
  }
  if (src->remaining == 0) return -1;''',
)

replace_once(
    "src/util/DictZip.cpp",
    '''  src->file = &file;
  src->remaining = compressedSize;''',
    '''  src->file = &file;
  src->remaining = compressedSize;
  constexpr unsigned long MAX_DICTZIP_SLICE_MS = 1500;
  src->deadlineMs = millis() + MAX_DICTZIP_SLICE_MS;''',
)

replace_once(
    "src/util/DictZip.cpp",
    '''  const auto decodeFail = [&src, &fail] {
    return fail(src->readFailed ? ExtractError::ReadError : ExtractError::Decompress);
  };''',
    '''  const auto decodeFail = [&src, &fail] {
    return fail((src->readFailed || src->timedOut) ? ExtractError::ReadError : ExtractError::Decompress);
  };''',
)

replace_once(
    "src/util/DictZip.cpp",
    '''  while (discardSize > 0) {
    batch = discardSize < 512 ? discardSize : 512;
    if (!src->reader.read(buf.get(), batch)) return decodeFail();''',
    '''  while (discardSize > 0) {
    if (static_cast<long>(millis() - src->deadlineMs) >= 0) { src->timedOut = true; return decodeFail(); }
    batch = discardSize < 512 ? discardSize : 512;
    if (!src->reader.read(buf.get(), batch)) return decodeFail();''',
)

replace_once(
    "src/util/DictZip.cpp",
    '''  while (extractSize > 0) {
    batch = extractSize < 512 ? extractSize : 512;
    if (!src->reader.read(buf.get(), batch)) return decodeFail();''',
    '''  while (extractSize > 0) {
    if (static_cast<long>(millis() - src->deadlineMs) >= 0) { src->timedOut = true; return decodeFail(); }
    batch = extractSize < 512 ? extractSize : 512;
    if (!src->reader.read(buf.get(), batch)) return decodeFail();''',
)

# Avoid the known false-positive 2-letter morphology result seen from page-top
# fragments (e.g. tyában -> ty) even when a malformed EPUB prevents boundary
# reconstruction. Genuine short headwords still work via exact lookup.
replace_once(
    "src/util/Dictionary.cpp",
    '''    for (const auto& cand : queue) {
      if (std::find(seen.begin(), seen.end(), cand) != seen.end()) continue;
      seen.push_back(cand);
      if (out.size() < MAX_STEM_VARIANTS) addUnique(out, cand);''',
    '''    for (const auto& cand : queue) {
      if (std::find(seen.begin(), seen.end(), cand) != seen.end()) continue;
      seen.push_back(cand);
      size_t candCodepoints = 0;
      for (const unsigned char ch : cand) if ((ch & 0xC0) != 0x80) ++candCodepoints;
      if (candCodepoints >= 3 && out.size() < MAX_STEM_VARIANTS) addUnique(out, cand);''',
)

print("CPHUN-132r8 page-boundary logical-word + DictZip deadline fixes applied")
