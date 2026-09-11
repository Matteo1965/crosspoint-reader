from pathlib import Path
import re

reader_path = Path("src/activities/reader/EpubReaderActivity.cpp")
menu_path = Path("src/activities/reader/EpubReaderMenuActivity.cpp")
book_h_path = Path("src/activities/reader/BookInfoActivity.h")
book_cpp_path = Path("src/activities/reader/BookInfoActivity.cpp")
build_id_path = Path("src/CPHUNBuildId.h")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 match, found {count}")
    return text.replace(old, new, 1)


# 1) Fülszöveg / Metaadatok -> Vissza returns to the Könyv tab.
reader = reader_path.read_text()
pattern = re.compile(
    r"(BookInfoActivity::Page::(?:Description|Metadata)\),\s*\n\s*)"
    r"\[this\]\(const ActivityResult&\) \{ openReaderMenu\(\); \}\);"
)
reader, changed = pattern.subn(
    r"\1[this](const ActivityResult&) { openReaderMenu(true); });", reader
)
already = reader.count("[this](const ActivityResult&) { openReaderMenu(true); });")
if already != 2:
    raise SystemExit(f"BookInfo return callbacks: expected 2 final callbacks, found {already} (changed {changed})")
reader_path.write_text(reader)

# 2) Reader Menu: right-side navigation behaves exactly like normal Fel/Le.
#    Kijelölés alone switches tabs while the tab band is focused.
menu = menu_path.read_text()
old_button_block = '''  if (mappedInput.wasReleased(MappedInputManager::Button::Left) && ringPos() == 0) {
    stepTab(-1);
    return true;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Right) && ringPos() == 0) {
    stepTab(1);
    return true;
  }
'''
if old_button_block in menu:
    menu = menu.replace(old_button_block, "", 1)

old_footer = '''void EpubReaderMenuActivity::drawFooter() {
  if (ringPos() == 0) {
    const char* switchLabel = tab_ == Tab::Reading ? "Könyv" : "Olvasás";
    const auto labels = mappedInput.mapLabels(tr(STR_BACK), switchLabel, "Olvasás", "Könyv");
    GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
    return;
  }
  UiTabListActivity::drawFooter();
}
'''
new_footer = '''void EpubReaderMenuActivity::drawFooter() { UiTabListActivity::drawFooter(); }
'''
if old_footer in menu:
    menu = menu.replace(old_footer, new_footer, 1)
if 'mappedInput.mapLabels(tr(STR_BACK), switchLabel, "Olvasás", "Könyv")' in menu:
    raise SystemExit("Reader Menu fixed Olvasás/Könyv footer is still present")
menu_path.write_text(menu)

# 3) Metadata line model: remember field ends and paginate by real pixel height.
book_h = book_h_path.read_text()
book_h = replace_once(
    book_h,
    '''    bool appendHyphen = false;
    bool justify = false;
''',
    '''    bool appendHyphen = false;
    bool justify = false;
    bool metadataFieldEnd = false;
''',
    "BookInfo Line metadata spacing flag",
)
book_h = replace_once(
    book_h,
    '''  int totalPages_ = 1;
  int linesPerPage_ = 1;
  ButtonNavigator buttonNavigator_;
''',
    '''  int totalPages_ = 1;
  std::vector<int> pageStarts_;
  ButtonNavigator buttonNavigator_;
''',
    "BookInfo page starts",
)
book_h_path.write_text(book_h)

book = book_cpp_path.read_text()

# Remove the old byte-based tag limit; rendered width below is authoritative.
old_join_tail = '''  constexpr size_t MAX_BYTES = 150;
  if (out.size() > MAX_BYTES) {
    size_t cut = MAX_BYTES;
    while (cut > 0 && (static_cast<unsigned char>(out[cut]) & 0xC0) == 0x80) --cut;
    out.resize(cut);
    out += "…";
  }
  return out;
}
'''
new_join_tail = '''  return out;
}

std::string formatFileSizeMb(const uint64_t bytes) {
  char buf[32];
  std::snprintf(buf, sizeof(buf), "%.2f MB", static_cast<double>(bytes) / (1024.0 * 1024.0));
  std::string out(buf);
  const auto dot = out.find('.');
  if (dot != std::string::npos) out[dot] = ',';
  return out;
}

std::string limitTagsToTwoLines(const std::string& value, GfxRenderer& renderer, const int maxWidth) {
  if (value.empty()) return value;
  const int prefixWidth =
      renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, "Címkék: ", EpdFontFamily::REGULAR);
  const int spaceWidth = renderer.getSpaceWidth(NOTOSERIF_14_FONT_ID, EpdFontFamily::REGULAR);
  const int ellipsisWidth = renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, "…", EpdFontFamily::REGULAR);

  std::vector<std::string> words;
  size_t pos = 0;
  while (pos < value.size()) {
    while (pos < value.size() && value[pos] == ' ') ++pos;
    const size_t start = pos;
    while (pos < value.size() && value[pos] != ' ') ++pos;
    if (pos > start) words.emplace_back(value.substr(start, pos - start));
  }

  std::string out;
  int line = 0;
  int lineWidth = prefixWidth;
  size_t secondLineStart = std::string::npos;
  for (size_t i = 0; i < words.size(); ++i) {
    const int wordWidth = renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, words[i].c_str(), EpdFontFamily::REGULAR);
    int gap = out.empty() ? 0 : spaceWidth;
    if (lineWidth + gap + wordWidth > maxWidth) {
      if (line == 0) {
        line = 1;
        lineWidth = 0;
        gap = 0;
        secondLineStart = out.empty() ? 0 : out.size() + 1;
      } else {
        while (!out.empty()) {
          const size_t tailStart = secondLineStart == std::string::npos ? 0 : secondLineStart;
          const std::string tail = out.substr(std::min(tailStart, out.size()));
          const int tailWidth = renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, tail.c_str(), EpdFontFamily::REGULAR);
          if (tailWidth + ellipsisWidth <= maxWidth) break;
          while (!out.empty() && out.back() == ' ') out.pop_back();
          if (out.empty()) break;
          do {
            out.pop_back();
          } while (!out.empty() && (static_cast<unsigned char>(out.back()) & 0xC0) == 0x80);
        }
        out += "…";
        return out;
      }
    }
    if (!out.empty()) out += ' ';
    out += words[i];
    lineWidth += gap + wordWidth;
  }
  return out;
}
'''
book = replace_once(book, old_join_tail, new_join_tail, "tag byte limit removal")

# Render-aware tag limit and MB file size.
old_tags_and_size = '''  add("Nyelv: ", languageName(info_.language));
  add("Címkék: ", joinTags(info_.subjects));
  add("Azonosító: ", info_.identifier);
  add("Fájlnév: ", info_.filename);
  add("Fájl formátum: ", fileFormat(info_.filename));
  if (info_.fileSize > 0) add("Fájlméret: ", std::to_string(info_.fileSize) + " byte");
'''
new_tags_and_size = '''  add("Nyelv: ", languageName(info_.language));
  const auto& metrics = UITheme::getInstance().getMetrics();
  const auto orientation = renderer.getOrientation();
  const bool isLandscape = orientation == GfxRenderer::Orientation::LandscapeClockwise ||
                           orientation == GfxRenderer::Orientation::LandscapeCounterClockwise;
  const int hintGutterWidth = isLandscape ? metrics.sideButtonHintsWidth : 0;
  const int metadataWidth = renderer.getScreenWidth() - hintGutterWidth - 2 * SIDE_PADDING;
  add("Címkék: ", limitTagsToTwoLines(joinTags(info_.subjects), renderer, metadataWidth));
  add("Azonosító: ", info_.identifier);
  add("Fájlnév: ", info_.filename);
  add("Fájl formátum: ", fileFormat(info_.filename));
  if (info_.fileSize > 0) add("Fájlméret: ", formatFileSizeMb(info_.fileSize));
'''
book = replace_once(book, old_tags_and_size, new_tags_and_size, "metadata formatting")

# Replace fixed line-count pagination with pixel-aware pagination.
old_layout = '''  const int bottomArea = metrics.buttonHintsHeight + metrics.verticalSpacing;
  linesPerPage_ = std::max(1, (renderer.getScreenHeight() - topArea - bottomArea) / lineHeight);

  const char* text = text_.c_str();
'''
new_layout = '''  const int bottomArea = metrics.buttonHintsHeight + metrics.verticalSpacing;
  const int availableHeight = renderer.getScreenHeight() - topArea - bottomArea;

  const char* text = text_.c_str();
'''
book = replace_once(book, old_layout, new_layout, "pixel pagination height")

old_flush = '''  const auto flushLine = [&](const uint32_t nextStart, const bool appendHyphen = false, const bool justify = false) {
    lines_.push_back({lineStart, static_cast<uint16_t>(lineEnd - lineStart), appendHyphen, justify});
    lineStart = nextStart;
    lineEnd = nextStart;
    lineWidth = 0;
  };
'''
new_flush = '''  const auto flushLine = [&](const uint32_t nextStart, const bool appendHyphen = false, const bool justify = false,
                             const bool metadataFieldEnd = false) {
    lines_.push_back(
        {lineStart, static_cast<uint16_t>(lineEnd - lineStart), appendHyphen, justify, metadataFieldEnd});
    lineStart = nextStart;
    lineEnd = nextStart;
    lineWidth = 0;
  };

  const auto fittingPrefix = [&](const uint32_t start, const uint32_t len, const int width) {
    uint32_t lastFit = 0;
    for (uint32_t partLen = 1; partLen <= len; ++partLen) {
      const bool boundary = partLen == len ||
                            (static_cast<unsigned char>(text[start + partLen]) & 0xC0) != 0x80;
      if (!boundary) continue;
      if (measureSpan(text + start, partLen) > width) break;
      lastFit = partLen;
    }
    return lastFit;
  };
'''
book = replace_once(book, old_flush, new_flush, "metadata field-end line model")

book = replace_once(
    book,
    '''    if (c == '\\n' || c == '\\0') {
      flushLine(i + 1, false, false);
''',
    '''    if (c == '\\n' || c == '\\0') {
      flushLine(i + 1, false, false, page_ == Page::Metadata);
''',
    "metadata field-end newline",
)

# Long unbroken metadata values use the remaining width after the label first.
needle = '''      if (!lineEmpty) {
        flushLine(tokenStart + consumed, false, page_ == Page::Description);
        continue;
      }

      uint32_t lastFit = 0;
'''
replacement = '''      if (page_ == Page::Metadata && !lineEmpty && remainingWidth > maxWidth && availableWidth > 0) {
        const uint32_t partial = fittingPrefix(tokenStart + consumed, remainingLen, availableWidth);
        if (partial > 0) {
          lineEnd = tokenStart + consumed + partial;
          lineWidth += gapWidth + measureSpan(text + tokenStart + consumed, partial);
          flushLine(lineEnd, false, false);
          consumed += partial;
          continue;
        }
      }

      if (!lineEmpty) {
        flushLine(tokenStart + consumed, false, page_ == Page::Description);
        continue;
      }

      uint32_t lastFit = 0;
'''
book = replace_once(book, needle, replacement, "long metadata partial fill")

old_total_pages = '''  totalPages_ = std::max(1, (static_cast<int>(lines_.size()) + linesPerPage_ - 1) / linesPerPage_);
}
'''
new_total_pages = '''  pageStarts_.clear();
  pageStarts_.push_back(0);
  int usedHeight = 0;
  for (int lineIndex = 0; lineIndex < static_cast<int>(lines_.size()); ++lineIndex) {
    const bool addFieldGap = page_ == Page::Metadata && lines_[lineIndex].metadataFieldEnd &&
                             lineIndex + 1 < static_cast<int>(lines_.size());
    const int rowHeight = lineHeight + (addFieldGap ? 3 : 0);
    if (usedHeight > 0 && usedHeight + rowHeight > availableHeight) {
      pageStarts_.push_back(lineIndex);
      usedHeight = 0;
    }
    usedHeight += rowHeight;
  }
  totalPages_ = std::max(1, static_cast<int>(pageStarts_.size()));
}
'''
book = replace_once(book, old_total_pages, new_total_pages, "pixel-aware total pages")

old_draw_page = '''  const int firstLine = currentPage_ * linesPerPage_;
  const int lastLine = std::min(firstLine + linesPerPage_, static_cast<int>(lines_.size()));
  const int lineHeight = renderer.getLineHeight(NOTOSERIF_14_FONT_ID);
'''
new_draw_page = '''  const int firstLine = pageStarts_.empty() ? 0 : pageStarts_[std::min(currentPage_, static_cast<int>(pageStarts_.size()) - 1)];
  const int lastLine = currentPage_ + 1 < static_cast<int>(pageStarts_.size())
                           ? pageStarts_[currentPage_ + 1]
                           : static_cast<int>(lines_.size());
  const int lineHeight = renderer.getLineHeight(NOTOSERIF_14_FONT_ID);
'''
book = replace_once(book, old_draw_page, new_draw_page, "draw page range")

# Add 3 px only after the final visual line of each metadata field.
book = book.replace(
    '''        y += lineHeight;
        continue;
''',
    '''        y += lineHeight;
        if (page_ == Page::Metadata && line.metadataFieldEnd && i + 1 < static_cast<int>(lines_.size())) y += 3;
        continue;
''',
    1,
)
old_final_y = '''    y += lineHeight;
  }
}

void BookInfoActivity::render'''
new_final_y = '''    y += lineHeight;
    if (page_ == Page::Metadata && line.metadataFieldEnd && i + 1 < static_cast<int>(lines_.size())) y += 3;
  }
}

void BookInfoActivity::render'''
book = replace_once(book, old_final_y, new_final_y, "metadata 3px spacing")

book_cpp_path.write_text(book)

# 4) Build ID.
build_id = build_id_path.read_text()
if 'CPHUN-260911-96' in build_id:
    build_id = build_id.replace('CPHUN-260911-96', 'CPHUN-260911-97', 1)
elif 'CPHUN-260911-97' not in build_id:
    raise SystemExit("Unexpected CPHUN build id")
build_id_path.write_text(build_id)

print("CPHUN-97 integrated: Book-tab return, metadata polish, and Fel/Kijelölés/Le Reader Menu navigation.")
