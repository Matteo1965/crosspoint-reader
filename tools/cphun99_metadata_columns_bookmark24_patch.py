from pathlib import Path

# --- BookInfoActivity.h: metadata column bookkeeping ---
h_path = Path('src/activities/reader/BookInfoActivity.h')
h = h_path.read_text()
old_line = '''  struct Line {
    uint32_t start = 0;
    uint16_t len = 0;
    bool appendHyphen = false;
    bool justify = false;
    bool metadataFieldEnd = false;
  };'''
new_line = '''  struct Line {
    uint32_t start = 0;
    uint16_t len = 0;
    bool appendHyphen = false;
    bool justify = false;
    bool metadataFieldEnd = false;
    uint32_t metadataLabelStart = 0;
    uint16_t metadataLabelLen = 0;
    bool metadataFirstLine = false;
  };'''
if old_line not in h:
    raise SystemExit('BookInfoActivity.h Line block not found')
h_path.write_text(h.replace(old_line, new_line, 1))

# --- BookInfoActivity.cpp: fixed metadata value column at X=184 ---
cpp_path = Path('src/activities/reader/BookInfoActivity.cpp')
cpp = cpp_path.read_text()

cpp = cpp.replace('constexpr int SIDE_PADDING = 20;\n',
                  'constexpr int SIDE_PADDING = 20;\nconstexpr int METADATA_VALUE_X = 184;\n', 1)

# Tags are limited against the value-column width, not against label+value width.
old_prefix = '''  const int prefixWidth =
      renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, "Címkék: ", EpdFontFamily::REGULAR);
  const int spaceWidth = renderer.getSpaceWidth(NOTOSERIF_14_FONT_ID, EpdFontFamily::REGULAR);'''
new_prefix = '''  const int spaceWidth = renderer.getSpaceWidth(NOTOSERIF_14_FONT_ID, EpdFontFamily::REGULAR);'''
if old_prefix not in cpp:
    raise SystemExit('Címkék prefix-width block not found')
cpp = cpp.replace(old_prefix, new_prefix, 1)
cpp = cpp.replace('  int lineWidth = prefixWidth;\n', '  int lineWidth = 0;\n', 1)

old_build = '''  const auto add = [this](const char* label, const std::string& value) {
    if (value.empty()) return;
    if (!text_.empty()) text_ += '\\n';
    text_ += label;
    text_ += value;
  };
  add("Cím: ", info_.title);
  add("Szerző: ", info_.author);
  add("Sorozat: ", info_.series);
  add("Sorozatszám: ", info_.seriesIndex);
  add("Kiadó: ", info_.publisher);
  add("Dátum: ", dateOnly(info_.date));
  add("Nyelv: ", languageName(info_.language));
  const auto& metrics = UITheme::getInstance().getMetrics();
  const auto orientation = renderer.getOrientation();
  const bool isLandscape = orientation == GfxRenderer::Orientation::LandscapeClockwise ||
                           orientation == GfxRenderer::Orientation::LandscapeCounterClockwise;
  const int hintGutterWidth = isLandscape ? metrics.sideButtonHintsWidth : 0;
  const int metadataWidth = renderer.getScreenWidth() - hintGutterWidth - 2 * SIDE_PADDING;
  add("Címkék: ", limitTagsToTwoLines(joinTags(info_.subjects), renderer, metadataWidth));
  add("Azonosító: ", info_.identifier);
  add("Fájlnév: ", info_.filename);
  add("Formátum: ", fileFormat(info_.filename));
  if (info_.fileSize > 0) add("Fájlméret: ", formatFileSizeMb(info_.fileSize));'''
new_build = '''  const auto add = [this](const char* label, const std::string& value) {
    if (value.empty()) return;
    if (!text_.empty()) text_ += '\\n';
    text_ += label;
    text_ += '\\t';
    text_ += value;
  };
  add("Cím:", info_.title);
  add("Szerző:", info_.author);
  add("Sorozat:", info_.series);
  add("Sorozatszám:", info_.seriesIndex);
  add("Kiadó:", info_.publisher);
  add("Dátum:", dateOnly(info_.date));
  add("Nyelv:", languageName(info_.language));
  const auto& metrics = UITheme::getInstance().getMetrics();
  const auto orientation = renderer.getOrientation();
  const bool isLandscapeCw = orientation == GfxRenderer::Orientation::LandscapeClockwise;
  const bool isLandscapeCcw = orientation == GfxRenderer::Orientation::LandscapeCounterClockwise;
  const int hintGutterWidth = (isLandscapeCw || isLandscapeCcw) ? metrics.sideButtonHintsWidth : 0;
  const int contentX = isLandscapeCw ? hintGutterWidth : 0;
  const int contentWidth = renderer.getScreenWidth() - hintGutterWidth;
  const int metadataValueWidth = std::max(1, contentX + contentWidth - SIDE_PADDING - METADATA_VALUE_X);
  add("Címkék:", limitTagsToTwoLines(joinTags(info_.subjects), renderer, metadataValueWidth));
  add("Azonosító:", info_.identifier);
  add("Fájlnév:", info_.filename);
  add("Formátum:", fileFormat(info_.filename));
  if (info_.fileSize > 0) add("Fájlméret:", formatFileSizeMb(info_.fileSize));'''
if old_build not in cpp:
    raise SystemExit('Metadata build block not found')
cpp = cpp.replace(old_build, new_build, 1)

# Insert a dedicated metadata wrapper before the existing description wrapper.
needle = '''  const char* text = text_.c_str();
  const uint32_t n = static_cast<uint32_t>(text_.size());
  uint32_t lineStart = 0;'''
insert = '''  const char* text = text_.c_str();
  const uint32_t n = static_cast<uint32_t>(text_.size());

  if (page_ == Page::Metadata) {
    const bool isLandscapeCw = orientation == GfxRenderer::Orientation::LandscapeClockwise;
    const int contentX = isLandscapeCw ? hintGutterWidth : 0;
    const int contentWidth = renderer.getScreenWidth() - hintGutterWidth;
    const int valueWidth = std::max(1, contentX + contentWidth - SIDE_PADDING - METADATA_VALUE_X);

    uint32_t fieldStart = 0;
    while (fieldStart < n) {
      uint32_t fieldEnd = fieldStart;
      while (fieldEnd < n && text[fieldEnd] != '\\n') ++fieldEnd;

      uint32_t tabPos = fieldStart;
      while (tabPos < fieldEnd && text[tabPos] != '\\t') ++tabPos;
      const uint32_t labelStart = fieldStart;
      const uint16_t labelLen = static_cast<uint16_t>(tabPos - fieldStart);
      uint32_t valuePos = tabPos < fieldEnd ? tabPos + 1 : fieldStart;
      bool firstVisualLine = true;

      while (valuePos < fieldEnd) {
        while (valuePos < fieldEnd && text[valuePos] == ' ') ++valuePos;
        if (valuePos >= fieldEnd) break;

        const uint32_t visualStart = valuePos;
        uint32_t scan = valuePos;
        uint32_t bestEnd = valuePos;
        uint32_t lastSpace = valuePos;

        while (scan < fieldEnd) {
          if (text[scan] == ' ') lastSpace = scan;
          uint32_t next = scan + 1;
          while (next < fieldEnd && (static_cast<unsigned char>(text[next]) & 0xC0) == 0x80) ++next;
          if (measureSpan(text + visualStart, next - visualStart) > valueWidth) break;
          bestEnd = next;
          scan = next;
        }

        uint32_t visualEnd = bestEnd;
        uint32_t nextPos = bestEnd;
        if (scan < fieldEnd && lastSpace > visualStart && lastSpace < scan) {
          visualEnd = lastSpace;
          nextPos = lastSpace + 1;
        } else if (visualEnd == visualStart) {
          visualEnd = scan + 1;
          while (visualEnd < fieldEnd && (static_cast<unsigned char>(text[visualEnd]) & 0xC0) == 0x80) ++visualEnd;
          nextPos = visualEnd;
        }

        while (visualEnd > visualStart && text[visualEnd - 1] == ' ') --visualEnd;
        Line line;
        line.start = visualStart;
        line.len = static_cast<uint16_t>(visualEnd - visualStart);
        line.metadataLabelStart = labelStart;
        line.metadataLabelLen = firstVisualLine ? labelLen : 0;
        line.metadataFirstLine = firstVisualLine;
        line.metadataFieldEnd = nextPos >= fieldEnd;
        lines_.push_back(line);
        firstVisualLine = false;
        valuePos = nextPos;
      }

      if (firstVisualLine) {
        Line line;
        line.start = fieldEnd;
        line.len = 0;
        line.metadataLabelStart = labelStart;
        line.metadataLabelLen = labelLen;
        line.metadataFirstLine = true;
        line.metadataFieldEnd = true;
        lines_.push_back(line);
      }

      fieldStart = fieldEnd < n ? fieldEnd + 1 : n;
    }

    pageStarts_.clear();
    pageStarts_.push_back(0);
    int usedHeight = 0;
    for (int lineIndex = 0; lineIndex < static_cast<int>(lines_.size()); ++lineIndex) {
      const bool addFieldGap = lines_[lineIndex].metadataFieldEnd && lineIndex + 1 < static_cast<int>(lines_.size());
      const int rowHeight = lineHeight + (addFieldGap ? 6 : 0);
      if (usedHeight > 0 && usedHeight + rowHeight > availableHeight) {
        pageStarts_.push_back(lineIndex);
        usedHeight = 0;
      }
      usedHeight += rowHeight;
    }
    totalPages_ = std::max(1, static_cast<int>(pageStarts_.size()));
    return;
  }

  uint32_t lineStart = 0;'''
if needle not in cpp:
    raise SystemExit('wrapText insertion point not found')
cpp = cpp.replace(needle, insert, 1)

# Metadata draw path: labels stay in the left column, all values start at X=184.
draw_needle = '''  for (int i = firstLine; i < lastLine; ++i) {
    const Line& line = lines_[i];
    if (line.len == 0) {
      y += lineHeight;
      continue;
    }
    const size_t len = std::min(static_cast<size_t>(line.len), MAX_LINE_BYTES);'''
draw_insert = '''  for (int i = firstLine; i < lastLine; ++i) {
    const Line& line = lines_[i];

    if (page_ == Page::Metadata) {
      if (line.metadataFirstLine && line.metadataLabelLen > 0) {
        char labelBuf[MAX_LINE_BYTES + 1];
        const size_t labelLen = std::min(static_cast<size_t>(line.metadataLabelLen), MAX_LINE_BYTES);
        memcpy(labelBuf, text_.c_str() + line.metadataLabelStart, labelLen);
        labelBuf[labelLen] = '\\0';
        renderer.drawText(NOTOSERIF_14_FONT_ID, x, y, labelBuf, true, EpdFontFamily::BOLD);
      }
      if (line.len > 0) {
        const size_t valueLen = std::min(static_cast<size_t>(line.len), MAX_LINE_BYTES);
        memcpy(buf, text_.c_str() + line.start, valueLen);
        buf[valueLen] = '\\0';
        renderer.drawText(NOTOSERIF_14_FONT_ID, METADATA_VALUE_X, y, buf, true, EpdFontFamily::REGULAR);
      }
      y += lineHeight;
      if (line.metadataFieldEnd && i + 1 < static_cast<int>(lines_.size())) y += 6;
      continue;
    }

    if (line.len == 0) {
      y += lineHeight;
      continue;
    }
    const size_t len = std::min(static_cast<size_t>(line.len), MAX_LINE_BYTES);'''
if draw_needle not in cpp:
    raise SystemExit('drawBody insertion point not found')
cpp = cpp.replace(draw_needle, draw_insert, 1)

cpp_path.write_text(cpp)

# --- 24x24 DOGEAR bookmark icon ---
icon_path = Path('src/components/icons/bookmark.h')
icon = icon_path.read_text()
start = icon.index('// size: 16x16 — Hungarian Edition DOGEAR bookmark marker')
end = icon.index(';', start) + 1
new_icon = '''// size: 24x24 — Hungarian Edition DOGEAR bookmark marker
static const uint8_t BookmarkStatusIcon[] = {
    0x40, 0x00, 0x00, 0x60, 0x00, 0x00, 0x70, 0x00, 0x00,
    0x78, 0x00, 0x00, 0x7C, 0x00, 0x00, 0x7E, 0x00, 0x00,
    0x7F, 0x00, 0x00, 0x7F, 0x80, 0x00, 0x7F, 0xC0, 0x00,
    0x7F, 0xE0, 0x00, 0x7F, 0xF0, 0x00, 0x7F, 0xF8, 0x00,
    0x7F, 0xFC, 0x00, 0x7F, 0xFE, 0x00, 0x7F, 0xFF, 0x00,
    0x7F, 0xFF, 0x80, 0x7F, 0xFF, 0xC0, 0x7F, 0xFF, 0xE0,
    0x7F, 0xFF, 0xF0, 0x7F, 0xFF, 0xF8, 0x7F, 0xFF, 0xFC,
    0x7F, 0xFF, 0xFE, 0x7F, 0xFF, 0xFF, 0x00, 0x00, 0x00};'''
icon_path.write_text(icon[:start] + new_icon + icon[end:])

base_path = Path('src/components/themes/BaseTheme.cpp')
base = base_path.read_text()
if 'constexpr int bookmarkStatusIconWidth = 16;\nconstexpr int bookmarkStatusIconHeight = 16;' not in base:
    raise SystemExit('Expected CPHUN-98 bookmark dimensions not found')
base = base.replace('constexpr int bookmarkStatusIconWidth = 16;\nconstexpr int bookmarkStatusIconHeight = 16;',
                    'constexpr int bookmarkStatusIconWidth = 24;\nconstexpr int bookmarkStatusIconHeight = 24;', 1)
# Existing screenWidth - width placement becomes X=456 on the 480px X4, i.e. 8px left of the old X=464.
base_path.write_text(base)

build_id_path = Path('src/CPHUNBuildId.h')
build_id = build_id_path.read_text()
if 'CPHUN-260911-98' not in build_id:
    raise SystemExit('Expected CPHUN-98 build id not found')
build_id_path.write_text(build_id.replace('CPHUN-260911-98', 'CPHUN-260911-99', 1))

print('Applied CPHUN-99 metadata columns and 24x24 bookmark patch')
