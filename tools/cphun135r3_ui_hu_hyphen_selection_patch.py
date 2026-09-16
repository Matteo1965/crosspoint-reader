from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-135r3: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# 1) Metadata: move the value/second column 2 px to the left.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/reader/BookInfoActivity.cpp",
    "constexpr int METADATA_VALUE_X = 182;",
    "constexpr int METADATA_VALUE_X = 180;",
)


# -----------------------------------------------------------------------------
# 2) Bookmarks export confirmation: render the long question as a wrapped
#    headline. OptionDialog's normal title slot reserves only one line even
#    when titleText.maxLines is larger, while headline is measured/wrapped.
# -----------------------------------------------------------------------------
replace_once(
    "src/components/OptionPopup.h",
    '''  void show(const char* titleStr, const char* const* options, int optionCount, int currentIndex,
            std::function<void(int)> onSelect) {
    title = titleStr;
    ownedStrings.resize(optionCount);''',
    '''  void show(const char* titleStr, const char* const* options, int optionCount, int currentIndex,
            std::function<void(int)> onSelect) {
    title = titleStr;
    multilineTitle = false;
    ownedStrings.resize(optionCount);''',
)

replace_once(
    "src/components/OptionPopup.h",
    '''  void show(StrId titleId, const std::vector<std::string>& options, int currentIndex,
            std::function<void(int)> onSelect) {''',
    '''  void showMultilineTitle(const char* titleStr, const char* const* options, int optionCount, int currentIndex,
                          std::function<void(int)> onSelect) {
    title = titleStr;
    multilineTitle = true;
    ownedStrings.resize(optionCount);
    for (int i = 0; i < optionCount; i++) {
      ownedStrings[i] = options[i];
    }
    selectedIndex = currentIndex;
    onSelectCallback = std::move(onSelect);
    uiReady = false;
    active = true;
  }

  void show(StrId titleId, const std::vector<std::string>& options, int currentIndex,
            std::function<void(int)> onSelect) {''',
)

replace_once(
    "src/components/OptionPopup.h",
    '''    title = I18N.get(titleId);
    ownedStrings = options;''',
    '''    title = I18N.get(titleId);
    multilineTitle = false;
    ownedStrings = options;''',
)

replace_once(
    "src/components/OptionPopup.h",
    '''    title = I18N.get(titleId);
    ownedStrings.resize(optionCount);''',
    '''    title = I18N.get(titleId);
    multilineTitle = false;
    ownedStrings.resize(optionCount);''',
)

replace_once(
    "src/components/OptionPopup.h",
    '''    fui::OptionDialogProps props;
    props.title = title.c_str();
    props.options = options;''',
    '''    fui::OptionDialogProps props;
    props.title = multilineTitle ? nullptr : title.c_str();
    props.headline = multilineTitle ? title.c_str() : nullptr;
    props.options = options;''',
)

replace_once(
    "src/components/OptionPopup.h",
    '''    props.titleText.font = fui::GfxRendererTarget::FONT_BODY;
    props.titleText.bold = true;
    props.titleText.align = fui::TextAlign::Center;
    props.titleText.maxLines = title.find('\\n') != std::string::npos ? 2 : 1;
    props.buttonText.font = fui::GfxRendererTarget::FONT_BODY;''',
    '''    props.titleText.font = fui::GfxRendererTarget::FONT_BODY;
    props.titleText.bold = true;
    props.titleText.align = fui::TextAlign::Center;
    props.titleText.maxLines = title.find('\\n') != std::string::npos ? 2 : 1;
    props.headlineText.font = fui::GfxRendererTarget::FONT_BODY;
    props.headlineText.bold = true;
    props.headlineText.align = fui::TextAlign::Center;
    props.headlineText.maxLines = 3;
    props.buttonText.font = fui::GfxRendererTarget::FONT_BODY;''',
)

replace_once(
    "src/components/OptionPopup.h",
    '''  bool active = false;
  std::string title;''',
    '''  bool active = false;
  bool multilineTitle = false;
  std::string title;''',
)

replace_once(
    "src/activities/reader/EpubReaderBookmarksActivity.cpp",
    '''  confirmPopup.show("Megjelölt szavak\\nlistájának mentése?", options, 3, 1, [this](int idx) {''',
    '''  confirmPopup.showMultilineTitle("Megjelölt szavak listájának mentése?", options, 3, 1, [this](int idx) {''',
)


# -----------------------------------------------------------------------------
# 3) Extended Hungarian hyphenation selection.
#
# Source long digraphs/trigraphs may render with one or two replacement letters
# at line end, e.g. source "összerakom" -> rendered "ösz-" / "szerakom".
# visibleTextOffset remains source-based, so the offset delta tells us how many
# rendered replacement codepoints must be removed. The visible hyphen glyph
# itself (U+002D or U+2011) is stripped before this comparison and therefore
# cannot affect the result.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''  std::string prefix = left.substr(0, left.size() - hyphenBytes);
  const uint32_t aOffset = a.block->wordVisibleTextOffset(a.tokenIndex);
  const uint32_t bOffset = b.block->wordVisibleTextOffset(b.tokenIndex);
  // Synthetic hyphen is absent from source text, so the second half starts
  // immediately after the source prefix. An explicit source hyphen advances
  // the source offset by one more codepoint and therefore fails this test.
  return bOffset == aOffset + visibleCodepointLength(prefix.c_str());''',
    '''  const std::string prefix = left.substr(0, left.size() - hyphenBytes);
  const uint32_t aOffset = a.block->wordVisibleTextOffset(a.tokenIndex);
  const uint32_t bOffset = b.block->wordVisibleTextOffset(b.tokenIndex);
  if (bOffset < aOffset) return false;
  const uint32_t renderedPrefixLength = visibleCodepointLength(prefix.c_str());
  const uint32_t sourcePrefixLength = bOffset - aOffset;
  // Ordinary synthetic hyphenation: rendered == source.
  // Extended Hungarian split: rendered has 1 replacement codepoint, or 2 for ddzs.
  // A real source hyphen makes the source length larger and is therefore rejected.
  return sourcePrefixLength <= renderedPrefixLength && renderedPrefixLength - sourcePrefixLength <= 2;''',
)

replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    r'''std::string DictionaryWordSelectActivity::logicalWordText(const int index) const {
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
}''',
    r'''std::string DictionaryWordSelectActivity::logicalWordText(const int index) const {
  if (words.empty() || index < 0 || index >= static_cast<int>(words.size())) return {};

  const auto trimSyntheticReplacement = [](std::string& prefix, const uint32_t prefixOffset,
                                           const uint32_t secondOffset) {
    if (secondOffset < prefixOffset) return false;
    const uint32_t renderedLength = visibleCodepointLength(prefix.c_str());
    const uint32_t sourceLength = secondOffset - prefixOffset;
    if (sourceLength > renderedLength || renderedLength - sourceLength > 2) return false;
    uint32_t syntheticCodepoints = renderedLength - sourceLength;
    while (syntheticCodepoints-- > 0 && !prefix.empty()) {
      size_t cut = prefix.size() - 1;
      while (cut > 0 && (static_cast<unsigned char>(prefix[cut]) & 0xC0) == 0x80) --cut;
      prefix.resize(cut);
    }
    return true;
  };

  const int first = logicalWordFirst(index);
  const int second = logicalWordSecond(first);
  if (first != second) {
    std::string text = words[first].text ? words[first].text : "";
    if (!stripSyntheticLineEndHyphen(text)) return words[index].text ? words[index].text : "";
    const WordBox& a = words[first];
    const WordBox& b = words[second];
    const uint32_t aOffset = a.block ? a.block->wordVisibleTextOffset(a.tokenIndex) : 0;
    const uint32_t bOffset = b.block ? b.block->wordVisibleTextOffset(b.tokenIndex) : 0;
    if (!a.block || !b.block || !trimSyntheticReplacement(text, aOffset, bOffset))
      return words[index].text ? words[index].text : "";
    if (words[second].text) text += words[second].text;
    return text;
  }

  const WordBox& current = words[index];
  const uint32_t currentOffset = current.block ? current.block->wordVisibleTextOffset(current.tokenIndex) : 0;

  // Current page begins with the second half of a synthetic page-boundary split.
  if (index == 0 && !previousBoundaryText.empty()) {
    std::string prefix = previousBoundaryText;
    if (stripSyntheticLineEndHyphen(prefix) &&
        trimSyntheticReplacement(prefix, previousBoundaryOffset, currentOffset)) {
      if (current.text) prefix += current.text;
      return prefix;
    }
  }

  // Current page ends with the first half of a synthetic page-boundary split.
  if (index == static_cast<int>(words.size()) - 1 && !nextBoundaryText.empty()) {
    std::string prefix = current.text ? current.text : "";
    if (stripSyntheticLineEndHyphen(prefix) &&
        trimSyntheticReplacement(prefix, currentOffset, nextBoundaryOffset)) {
      prefix += nextBoundaryText;
      return prefix;
    }
  }

  return current.text ? current.text : "";
}''',
)

replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260916-135-EXP-r2"',
    '#define CPHUN_BUILD_ID "CPHUN-260916-135-EXP-r3"',
)

print("CPHUN-135r3 UI and Hungarian split-word selection fixes applied")
