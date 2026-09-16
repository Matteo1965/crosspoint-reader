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
#    headline. OptionDialog's normal title slot is intentionally single-line.
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

# The StrId + StrId-array overload also resets the mode.
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
    props.buttonText.font = fui::GfxRendererTarget::FONT_BODY;''',
    '''    props.titleText.font = fui::GfxRendererTarget::FONT_BODY;
    props.titleText.bold = true;
    props.titleText.align = fui::TextAlign::Center;
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
    '''  confirmPopup.show("Megjelölt szavak listájának mentése?", options, 3, 2, [this](int idx) {''',
    '''  confirmPopup.showMultilineTitle("Megjelölt szavak listájának mentése?", options, 3, 2, [this](int idx) {''',
)


# -----------------------------------------------------------------------------
# 3) Extended Hungarian hyphenation selection.
#
# A source long digraph/trigraph is rendered with replacement letters at the
# line end, e.g. source "összerakom" -> "ösz-" / "szerakom". The remainder's
# visible-source offset therefore advances by only 2 codepoints ("ös"), while
# the rendered prefix without the hyphen is 3 codepoints ("ösz"). Use that
# source-offset delta to recognise and remove only the synthetic replacement
# codepoints when reconstructing the logical lookup/highlight word.
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
  // Ordinary synthetic hyphenation has equal rendered/source prefix lengths.
  // Hungarian extended hyphenation may append one replacement codepoint
  // (ccs/ggy/lly/nny/ssz/tty/zzs/ddz) or two (ddzs) to the rendered prefix.
  // A real source hyphen instead makes sourcePrefixLength larger and is rejected.
  return sourcePrefixLength <= renderedPrefixLength && renderedPrefixLength - sourcePrefixLength <= 2;''',
)

replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''  std::string text = words[first].text ? words[first].text : "";
  if (!text.empty() && text.back() == '-') text.pop_back();
  else if (text.size() >= 3 && text.compare(text.size() - 3, 3, "\\xE2\\x80\\x91") == 0) text.resize(text.size() - 3);
  if (words[second].text) text += words[second].text;
  return text;''',
    '''  std::string text = words[first].text ? words[first].text : "";
  if (!text.empty() && text.back() == '-') text.pop_back();
  else if (text.size() >= 3 && text.compare(text.size() - 3, 3, "\\xE2\\x80\\x91") == 0) text.resize(text.size() - 3);

  // Remove only replacement codepoints that exist in the rendered line-end
  // prefix but not in the EPUB's visible source offsets. This restores the
  // original spelling: "ösz-" + "szerakom" -> "összerakom".
  const WordBox& a = words[first];
  const WordBox& b = words[second];
  if (a.block && b.block) {
    const uint32_t aOffset = a.block->wordVisibleTextOffset(a.tokenIndex);
    const uint32_t bOffset = b.block->wordVisibleTextOffset(b.tokenIndex);
    if (bOffset >= aOffset) {
      const uint32_t renderedPrefixLength = visibleCodepointLength(text.c_str());
      const uint32_t sourcePrefixLength = bOffset - aOffset;
      uint32_t syntheticCodepoints =
          renderedPrefixLength > sourcePrefixLength ? renderedPrefixLength - sourcePrefixLength : 0;
      syntheticCodepoints = std::min<uint32_t>(syntheticCodepoints, 2);
      while (syntheticCodepoints-- > 0 && !text.empty()) {
        size_t cut = text.size() - 1;
        while (cut > 0 && (static_cast<unsigned char>(text[cut]) & 0xC0) == 0x80) --cut;
        text.resize(cut);
      }
    }
  }
  if (words[second].text) text += words[second].text;
  return text;''',
)

# Build ID for this combined test revision.
replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260916-135-EXP-r2"',
    '#define CPHUN_BUILD_ID "CPHUN-260916-135-EXP-r3"',
)

print("CPHUN-135r3 UI and Hungarian split-word selection fixes applied")
