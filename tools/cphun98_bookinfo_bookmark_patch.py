from pathlib import Path

bookinfo_path = Path('src/activities/reader/BookInfoActivity.cpp')
bookinfo = bookinfo_path.read_text()
bookinfo = bookinfo.replace('const int rowHeight = lineHeight + (addFieldGap ? 3 : 0);',
                            'const int rowHeight = lineHeight + (addFieldGap ? 6 : 0);')
bookinfo = bookinfo.replace('line.metadataFieldEnd && i + 1 < static_cast<int>(lines_.size())) y += 3;',
                            'line.metadataFieldEnd && i + 1 < static_cast<int>(lines_.size())) y += 6;')
bookinfo = bookinfo.replace('add("Fájl formátum: ", fileFormat(info_.filename));',
                            'add("Formátum: ", fileFormat(info_.filename));')
old_header = '''  const char* title = page_ == Page::Description ? "Fülszöveg" : "Metaadatok";
  GUI.drawHeader(renderer, Rect{contentX, contentY + metrics.topPadding, contentWidth, metrics.headerHeight}, title);

  if (totalPages_ > 1) {
    char counter[16];
    std::snprintf(counter, sizeof(counter), "%d/%d", currentPage_ + 1, totalPages_);
    const int width = renderer.getTextWidth(UI_10_FONT_ID, counter);
    renderer.drawText(UI_10_FONT_ID, contentX + contentWidth - SIDE_PADDING - width,
                      contentY + metrics.topPadding + metrics.headerHeight - renderer.getLineHeight(UI_10_FONT_ID), counter);
  }
'''
new_header = '''  const char* title = page_ == Page::Description ? "Fülszöveg" : "Metaadatok";
  const int headerY = contentY + metrics.topPadding;
  GUI.drawHeader(renderer, Rect{contentX, headerY, contentWidth, metrics.headerHeight}, title);

  // BookInfo pages intentionally omit the standard header battery indicator.
  constexpr int headerStatusClearWidth = 112;
  const int clearX = contentX + std::max(0, contentWidth - headerStatusClearWidth);
  const int clearWidth = contentX + contentWidth - clearX;
  if (clearWidth > 0 && metrics.headerHeight > 1) {
    renderer.fillRect(clearX, headerY, clearWidth, metrics.headerHeight - 1, false);
  }

  if (totalPages_ > 1) {
    char counter[16];
    std::snprintf(counter, sizeof(counter), "%d/%d", currentPage_ + 1, totalPages_);
    const int width = renderer.getTextWidth(UI_10_FONT_ID, counter);
    const int counterY = headerY + (metrics.headerHeight - renderer.getLineHeight(UI_10_FONT_ID)) / 2;
    renderer.drawText(UI_10_FONT_ID, contentX + contentWidth - SIDE_PADDING - width, counterY, counter);
  }
'''
if old_header not in bookinfo:
    raise SystemExit('BookInfo header block not found')
bookinfo_path.write_text(bookinfo.replace(old_header, new_header, 1))

bookmark_path = Path('src/components/icons/bookmark.h')
bookmark = bookmark_path.read_text()
old_status = '''// size: 16x16
static const uint8_t BookmarkStatusIcon[] = {0x0F, 0xF8, 0x0F, 0xF8, 0x0F, 0xF8, 0x0F, 0xF8, 0x0F, 0xF8, 0x0F,
                                             0xF8, 0x0F, 0xF8, 0x0F, 0xF8, 0x0F, 0xF8, 0x0F, 0xF8, 0x0F, 0xF8,
                                             0x0F, 0x78, 0x0E, 0x38, 0x0C, 0x18, 0x08, 0x08, 0x00, 0x00};'''
new_status = '''// size: 16x16 — Hungarian Edition DOGEAR bookmark marker
static const uint8_t BookmarkStatusIcon[] = {
    0xBF, 0xFF, 0x9F, 0xFF, 0x8F, 0xFF, 0x87, 0xFF,
    0x83, 0xFF, 0x81, 0xFF, 0x80, 0xFF, 0x80, 0x7F,
    0x80, 0x3F, 0x80, 0x1F, 0x80, 0x0F, 0x80, 0x07,
    0x80, 0x03, 0x80, 0x01, 0x80, 0x00, 0xFF, 0xFF};'''
if old_status not in bookmark:
    raise SystemExit('BookmarkStatusIcon block not found')
bookmark_path.write_text(bookmark.replace(old_status, new_status, 1))

base_path = Path('src/components/themes/BaseTheme.cpp')
base = base_path.read_text()
base = base.replace('constexpr int bookmarkStatusIconHeight = 14;\nconstexpr int bookmarkStatusIconGap = 4;\nconstexpr int bookmarkStatusIconTopCrop = 2;\n',
                    'constexpr int bookmarkStatusIconHeight = 16;\n')
base = base.replace('const uint8_t byte = BookmarkStatusIcon[(row + bookmarkStatusIconTopCrop) * bytesPerRow + col / 8];',
                    'const uint8_t byte = BookmarkStatusIcon[row * bytesPerRow + col / 8];')
old_draw = '''  // Draw Bookmark
  if (showStatusBarTextLane && isPageBookmarked) {
    const int bookmarkGap = leftClusterWidth > 0 ? bookmarkStatusIconGap : 0;
    const int bookmarkX = leftClusterX + leftClusterWidth + bookmarkGap;
    const int bookmarkY = textY + 5;
    drawBookmarkStatusIcon(renderer, bookmarkX, bookmarkY);
    leftClusterWidth += bookmarkStatusIconWidth + bookmarkGap;
  }
'''
new_draw = '''  // Draw Bookmark as a full 16x16 corner marker. It no longer consumes
  // status-bar layout width and sits flush with the upper-right screen edge.
  if (isPageBookmarked) {
    drawBookmarkStatusIcon(renderer, renderer.getScreenWidth() - bookmarkStatusIconWidth, 0);
  }
'''
if old_draw not in base:
    raise SystemExit('Status-bar bookmark block not found')
base_path.write_text(base.replace(old_draw, new_draw, 1))

build_id_path = Path('src/CPHUNBuildId.h')
build_id = build_id_path.read_text()
if 'CPHUN-260911-97' not in build_id:
    raise SystemExit('Expected CPHUN-97 build id not found')
build_id_path.write_text(build_id.replace('CPHUN-260911-97', 'CPHUN-260911-98', 1))

print('Applied CPHUN-98 BookInfo and bookmark patch')
