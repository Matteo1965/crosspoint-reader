from pathlib import Path
import re


def replace(path, old, new):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"pattern not found in {path}: {old[:120]!r}")
    p.write_text(s.replace(old, new, 1))

# Build ID
replace("src/CPHUNBuildId.h", 'CPHUN-260911-94', 'CPHUN-260911-95')

# -----------------------------------------------------------------------------
# Reader menu: Olvasás | Könyv, direct book pages, clearer labels.
# -----------------------------------------------------------------------------
p = Path("src/activities/reader/EpubReaderMenuActivity.h")
s = p.read_text()
s = s.replace('    DICTIONARY,\n    BOOK_INFO\n', '    DICTIONARY,\n    BOOK_DESCRIPTION,\n    BOOK_METADATA,\n    BOOK_COVER\n')
s = s.replace('enum class Tab : uint8_t { Reading = 0, More = 1, Count = 2 };',
              'enum class Tab : uint8_t { Reading = 0, Book = 1, Count = 2 };')
p.write_text(s)

p = Path("src/activities/reader/EpubReaderMenuActivity.cpp")
s = p.read_text()
s = s.replace('items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP});',
              'items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótári keresés"});')
s = s.replace('items.push_back({MenuAction::AUTO_PAGE_TURN, StrId::STR_AUTO_TURN_PAGES_PER_MIN});',
              'items.push_back({MenuAction::AUTO_PAGE_TURN, StrId::STR_AUTO_TURN_PAGES_PER_MIN, "Auto. lapozás, lap/perc"});')
old_more = '''  return {\n      {MenuAction::BOOK_INFO, StrId::STR_TEXT_SETTINGS, "Könyv adatai"},\n      {MenuAction::TEXT_SETTINGS, StrId::STR_TEXT_SETTINGS},\n      {MenuAction::GO_HOME, StrId::STR_GO_HOME_BUTTON},\n      {MenuAction::SCREENSHOT, StrId::STR_SCREENSHOT_BUTTON},\n      {MenuAction::DISPLAY_QR, StrId::STR_DISPLAY_QR},\n      {MenuAction::SYNC, StrId::STR_SYNC_PROGRESS},\n      {MenuAction::DELETE_CACHE, StrId::STR_DELETE_CACHE},\n  };\n'''
new_more = '''  return {\n      {MenuAction::BOOK_DESCRIPTION, StrId::STR_TEXT_SETTINGS, "Fülszöveg"},\n      {MenuAction::BOOK_METADATA, StrId::STR_TEXT_SETTINGS, "Metaadatok"},\n      {MenuAction::BOOK_COVER, StrId::STR_TEXT_SETTINGS, "Borító"},\n      {MenuAction::TEXT_SETTINGS, StrId::STR_TEXT_SETTINGS},\n      {MenuAction::GO_HOME, StrId::STR_GO_HOME_BUTTON},\n      {MenuAction::SCREENSHOT, StrId::STR_SCREENSHOT_BUTTON},\n      {MenuAction::DISPLAY_QR, StrId::STR_DISPLAY_QR},\n      {MenuAction::SYNC, StrId::STR_SYNC_PROGRESS},\n      {MenuAction::DELETE_CACHE, StrId::STR_DELETE_CACHE},\n  };\n'''
if old_more not in s:
    raise SystemExit("reader menu more-items block missing")
s = s.replace(old_more, new_more, 1)
s = s.replace('return tab_ == Tab::Reading ? readingItems : moreItems;',
              'return tab_ == Tab::Reading ? readingItems : moreItems;')
s = s.replace('return index == 0 ? "Olvasás" : "Továbbiak";', 'return index == 0 ? "Olvasás" : "Könyv";')
p.write_text(s)

# -----------------------------------------------------------------------------
# OPF metadata: collect every dc:subject as tags.
# -----------------------------------------------------------------------------
p = Path("lib/Epub/Epub/parsers/ContentOpfParser.h")
s = p.read_text()
s = s.replace('    IN_BOOK_IDENTIFIER,\n', '    IN_BOOK_IDENTIFIER,\n    IN_BOOK_SUBJECT,\n')
s = s.replace('  std::string seriesIndex;\n', '  std::string seriesIndex;\n  std::vector<std::string> subjects;\n  std::string currentSubject;\n')
p.write_text(s)

p = Path("lib/Epub/Epub/parsers/ContentOpfParser.cpp")
s = p.read_text()
needle = '''  if (self->state == IN_METADATA && xmlLocalNameEquals(name, "identifier")) {\n    self->state = IN_BOOK_IDENTIFIER;\n    return;\n  }\n'''
insert = needle + '''\n  if (self->state == IN_METADATA && xmlLocalNameEquals(name, "subject")) {\n    self->currentSubject.clear();\n    self->state = IN_BOOK_SUBJECT;\n    return;\n  }\n'''
if needle not in s:
    raise SystemExit("subject start insertion point missing")
s = s.replace(needle, insert, 1)
needle = '''  if (self->state == IN_BOOK_IDENTIFIER) {\n    if (self->identifier.empty()) self->identifier.append(s, len);\n    return;\n  }\n'''
insert = needle + '''  if (self->state == IN_BOOK_SUBJECT) {\n    self->currentSubject.append(s, len);\n    return;\n  }\n'''
if needle not in s:
    raise SystemExit("subject character insertion point missing")
s = s.replace(needle, insert, 1)
needle = '''  if (self->state == IN_BOOK_IDENTIFIER && xmlLocalNameEquals(name, "identifier")) {\n    self->state = IN_METADATA;\n    return;\n  }\n'''
insert = needle + '''  if (self->state == IN_BOOK_SUBJECT && xmlLocalNameEquals(name, "subject")) {\n    if (!self->currentSubject.empty()) self->subjects.push_back(self->currentSubject);\n    self->currentSubject.clear();\n    self->state = IN_METADATA;\n    return;\n  }\n'''
if needle not in s:
    raise SystemExit("subject end insertion point missing")
s = s.replace(needle, insert, 1)
p.write_text(s)

p = Path("lib/Epub/Epub.h")
s = p.read_text()
s = s.replace('    std::string seriesIndex;\n    std::string filename;\n',
              '    std::string seriesIndex;\n    std::vector<std::string> subjects;\n    std::string filename;\n')
p.write_text(s)

p = Path("lib/Epub/Epub.cpp")
s = p.read_text()
s = s.replace('  info.seriesIndex = parser.seriesIndex;\n  return true;\n}',
              '  info.seriesIndex = parser.seriesIndex;\n  info.subjects = parser.subjects;\n  return true;\n}', 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# BookInfoActivity becomes a direct Description/Metadata page (no intermediate tabs).
# Description markup is parsed with Expat into readable paragraphs instead of shown raw.
# -----------------------------------------------------------------------------
Path("src/activities/reader/BookInfoActivity.h").write_text(r'''#pragma once

#include <Epub.h>

#include <memory>
#include <string>
#include <vector>

#include "activities/UiTabListActivity.h"

class BookInfoActivity final : public UiTabListActivity {
 public:
  enum class Page : uint8_t { Description = 0, Metadata = 1 };

  BookInfoActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::shared_ptr<Epub> epub, Page page);
  void onEnter() override;

 private:
  int tabCount() const override { return 1; }
  int activeTab() const override { return 0; }
  const char* tabLabel(int) const override { return ""; }
  int tabWidthPercent(int) const override { return 100; }
  void onTabAction(int) override {}
  void stepTab(int) override {}
  int listCount() const override { return static_cast<int>(rows_.size()); }
  void activateIndex(int) override {}
  bool handleButtons() override;
  void buildScreen(UiScreen& screen) override;
  void drawChrome() override;

  void rebuildRows();
  void addDescriptionRows(const std::string& text);
  void addMetadataRow(const char* label, const std::string& value);

  std::shared_ptr<Epub> epub_;
  Epub::BookInfo info_;
  Page page_;
  std::vector<std::string> rowText_;
  std::vector<freeink::ui::ListItem> rows_;
};
''')

Path("src/activities/reader/BookInfoActivity.cpp").write_text(r'''#include "BookInfoActivity.h"

#include <GfxRenderer.h>
#include <expat.h>

#include <algorithm>
#include <cctype>

#include "MappedInputManager.h"
#include "components/UITheme.h"

namespace fui = freeink::ui;

namespace {
std::string trimCopy(std::string value) {
  auto isWs = [](unsigned char c) { return std::isspace(c) != 0; };
  while (!value.empty() && isWs(static_cast<unsigned char>(value.front()))) value.erase(value.begin());
  while (!value.empty() && isWs(static_cast<unsigned char>(value.back()))) value.pop_back();
  return value;
}

std::string localName(const char* raw) {
  if (!raw) return {};
  const char* colon = std::strchr(raw, ':');
  return colon ? std::string(colon + 1) : std::string(raw);
}

struct DescriptionParser {
  std::vector<std::string> paragraphs;
  std::string current;

  static void XMLCALL start(void* ctx, const XML_Char* name, const XML_Char**) {
    auto* self = static_cast<DescriptionParser*>(ctx);
    const std::string tag = localName(name);
    if (tag == "br") self->flush();
    else if (tag == "p" || tag == "div" || tag == "li" || tag == "h1" || tag == "h2" || tag == "h3" || tag == "h4") {
      self->flush();
      if (tag == "li") self->current = "• ";
    }
  }

  static void XMLCALL end(void* ctx, const XML_Char* name) {
    auto* self = static_cast<DescriptionParser*>(ctx);
    const std::string tag = localName(name);
    if (tag == "p" || tag == "div" || tag == "li" || tag == "h1" || tag == "h2" || tag == "h3" || tag == "h4") self->flush();
  }

  static void XMLCALL chars(void* ctx, const XML_Char* text, int len) {
    auto* self = static_cast<DescriptionParser*>(ctx);
    for (int i = 0; i < len; ++i) {
      const char c = text[i];
      if (c == '\r' || c == '\n' || c == '\t') {
        if (!self->current.empty() && self->current.back() != ' ') self->current.push_back(' ');
      } else {
        self->current.push_back(c);
      }
    }
  }

  void flush() {
    std::string value = trimCopy(current);
    if (!value.empty()) paragraphs.push_back(std::move(value));
    current.clear();
  }
};

std::vector<std::string> parseDescriptionFragment(const std::string& fragment) {
  if (fragment.empty()) return {};
  DescriptionParser out;
  XML_Parser parser = XML_ParserCreate(nullptr);
  if (!parser) return {fragment};
  XML_SetUserData(parser, &out);
  XML_SetElementHandler(parser, DescriptionParser::start, DescriptionParser::end);
  XML_SetCharacterDataHandler(parser, DescriptionParser::chars);
  const std::string wrapped = "<root>" + fragment + "</root>";
  const bool ok = XML_Parse(parser, wrapped.data(), static_cast<int>(wrapped.size()), XML_TRUE) == XML_STATUS_OK;
  XML_ParserFree(parser);
  if (!ok) {
    // Description is allowed to contain imperfect HTML. Retry as readable text by
    // replacing tags with spaces instead of exposing the markup to the user.
    out.paragraphs.clear();
    std::string plain;
    bool inTag = false;
    for (char c : fragment) {
      if (c == '<') { inTag = true; if (!plain.empty() && plain.back() != ' ') plain.push_back(' '); continue; }
      if (c == '>') { inTag = false; continue; }
      if (!inTag) plain.push_back(c);
    }
    plain = trimCopy(plain);
    if (!plain.empty()) out.paragraphs.push_back(std::move(plain));
    return out.paragraphs;
  }
  out.flush();
  return out.paragraphs;
}

std::string dateOnly(std::string value) {
  value = trimCopy(std::move(value));
  const size_t t = value.find('T');
  if (t != std::string::npos) return value.substr(0, t);
  const size_t space = value.find(' ');
  if (space != std::string::npos && value.find(':', space) != std::string::npos) return value.substr(0, space);
  return value;
}

std::string languageName(std::string value) {
  value = trimCopy(std::move(value));
  std::string code = value;
  std::transform(code.begin(), code.end(), code.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
  const size_t dash = code.find_first_of("-_");
  if (dash != std::string::npos) code = code.substr(0, dash);
  if (code == "hu" || code == "hun") return "magyar";
  if (code == "en" || code == "eng") return "angol";
  if (code == "de" || code == "deu" || code == "ger") return "német";
  if (code == "fr" || code == "fra" || code == "fre") return "francia";
  if (code == "es" || code == "spa") return "spanyol";
  if (code == "it" || code == "ita") return "olasz";
  if (code == "pt" || code == "por") return "portugál";
  if (code == "nl" || code == "nld" || code == "dut") return "holland";
  if (code == "pl" || code == "pol") return "lengyel";
  if (code == "cs" || code == "ces" || code == "cze") return "cseh";
  if (code == "sk" || code == "slk" || code == "slo") return "szlovák";
  if (code == "ro" || code == "ron" || code == "rum") return "román";
  if (code == "ru" || code == "rus") return "orosz";
  if (code == "uk" || code == "ukr") return "ukrán";
  if (code == "ja" || code == "jpn") return "japán";
  if (code == "zh" || code == "zho" || code == "chi") return "kínai";
  return value;
}

std::string fileFormat(const std::string& filename) {
  const size_t dot = filename.find_last_of('.');
  if (dot == std::string::npos || dot + 1 >= filename.size()) return {};
  std::string ext = filename.substr(dot + 1);
  std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
  return ext;
}

std::string joinTags(const std::vector<std::string>& values) {
  std::string out;
  for (const auto& raw : values) {
    const std::string v = trimCopy(raw);
    if (v.empty()) continue;
    if (!out.empty()) out += ", ";
    out += v;
  }
  // Two UI lines are reserved for tags. Keep a conservative glyph count and
  // truncate on a UTF-8 boundary; the underlying metadata remains untouched.
  constexpr size_t MAX_BYTES = 150;
  if (out.size() > MAX_BYTES) {
    size_t cut = MAX_BYTES;
    while (cut > 0 && (static_cast<unsigned char>(out[cut]) & 0xC0) == 0x80) --cut;
    out.resize(cut);
    out += "…";
  }
  return out;
}
}  // namespace

BookInfoActivity::BookInfoActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::shared_ptr<Epub> epub,
                                   const Page page)
    : UiTabListActivity("BookInfo", renderer, mappedInput), epub_(std::move(epub)), page_(page) {}

void BookInfoActivity::onEnter() {
  UiTabListActivity::onEnter();
  if (epub_) epub_->readBookInfo(info_);
  rebuildRows();
}

void BookInfoActivity::addDescriptionRows(const std::string& text) {
  const auto paragraphs = parseDescriptionFragment(text);
  if (paragraphs.empty()) {
    rowText_.push_back("Ehhez a könyvhöz nincs fülszöveg.");
    return;
  }
  for (const auto& paragraph : paragraphs) rowText_.push_back(paragraph);
}

void BookInfoActivity::addMetadataRow(const char* label, const std::string& value) {
  if (value.empty()) return;
  rowText_.push_back(std::string(label) + value);
}

void BookInfoActivity::rebuildRows() {
  rowText_.clear();
  rows_.clear();

  if (page_ == Page::Description) {
    addDescriptionRows(info_.description);
  } else {
    addMetadataRow("Cím: ", info_.title);
    addMetadataRow("Szerző: ", info_.author);
    addMetadataRow("Sorozat: ", info_.series);
    addMetadataRow("Sorozatszám: ", info_.seriesIndex);
    addMetadataRow("Kiadó: ", info_.publisher);
    addMetadataRow("Dátum: ", dateOnly(info_.date));
    addMetadataRow("Nyelv: ", languageName(info_.language));
    addMetadataRow("Címkék: ", joinTags(info_.subjects));
    addMetadataRow("Azonosító: ", info_.identifier);
    addMetadataRow("Fájlnév: ", info_.filename);
    addMetadataRow("Fájl formátum: ", fileFormat(info_.filename));
    if (info_.fileSize > 0) rowText_.push_back("Fájlméret: " + std::to_string(info_.fileSize) + " byte");
    if (rowText_.empty()) rowText_.push_back("Nincs megjeleníthető metaadat.");
  }

  rows_.reserve(rowText_.size());
  for (size_t i = 0; i < rowText_.size(); ++i) {
    fui::ListItem item;
    item.label = rowText_[i].c_str();
    item.actionValue = static_cast<int16_t>(i);
    rows_.push_back(item);
  }
}

bool BookInfoActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    finish();
    return true;
  }
  return false;
}

void BookInfoActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const Rect safe = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  screen.setContentMargin(fui::Insets{static_cast<int16_t>(safe.y + metrics.topPadding + metrics.headerHeight),
                                      static_cast<int16_t>(renderer.getScreenWidth() - (safe.x + safe.width)),
                                      static_cast<int16_t>(metrics.buttonHintsHeight), static_cast<int16_t>(safe.x)});
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));

  fui::ListProps props;
  props.items = rows_.data();
  props.count = static_cast<uint16_t>(rows_.size());
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch;
  props.labelText = screen.theme().bodyText;
  props.labelText.maxLines = 2;
  syncTabListViewport(screen, props);
  screen.list(props);
}

void BookInfoActivity::drawChrome() {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const Rect safe = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  const char* title = page_ == Page::Description ? "Fülszöveg" : "Metaadatok";
  GUI.drawHeader(renderer, Rect{safe.x, safe.y + metrics.topPadding, safe.width, metrics.headerHeight}, title);
}
''')

# -----------------------------------------------------------------------------
# Reader cover viewer mode: no sibling navigation, no sleep-cover command, Back
# returns to the reader activity.
# -----------------------------------------------------------------------------
p = Path("src/activities/util/BmpViewerActivity.h")
s = p.read_text()
s = s.replace('BmpViewerActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::string filePath);',
              'BmpViewerActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::string filePath, bool simpleBackOnly = false);')
s = s.replace('  int currentImageIndex = -1;\n', '  int currentImageIndex = -1;\n  bool simpleBackOnly = false;\n')
p.write_text(s)

p = Path("src/activities/util/BmpViewerActivity.cpp")
s = p.read_text()
s = s.replace('BmpViewerActivity::BmpViewerActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::string path)\n    : Activity("BmpViewer", renderer, mappedInput), filePath(std::move(path)) {}',
              'BmpViewerActivity::BmpViewerActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::string path, const bool backOnly)\n    : Activity("BmpViewer", renderer, mappedInput), filePath(std::move(path)), simpleBackOnly(backOnly) {}')
s = s.replace('  if (siblingImages.empty() && !filePath.empty()) {\n    loadSiblingImages();\n  }',
              '  if (!simpleBackOnly && siblingImages.empty() && !filePath.empty()) {\n    loadSiblingImages();\n  }')
# Replace all three main label constructions.
s = s.replace('const auto labels = mappedInput.mapLabels(tr(STR_BACK), canSetSleepCover() ? tr(STR_SET_SLEEP_COVER) : "",\n                                              hasPrevious ? "<" : "", hasNext ? ">" : "");',
              'const auto labels = simpleBackOnly ? mappedInput.mapLabels(tr(STR_BACK), "", "", "")\n                                         : mappedInput.mapLabels(tr(STR_BACK), canSetSleepCover() ? tr(STR_SET_SLEEP_COVER) : "",\n                                                                 hasPrevious ? "<" : "", hasNext ? ">" : "");')
s = s.replace('const auto labels = mappedInput.mapLabels(tr(STR_BACK), canSetSleepCover() ? tr(STR_SET_SLEEP_COVER) : "",\n                                                (hasPrevious ? "<" : ""), (hasNext ? ">" : ""));',
              'const auto labels = simpleBackOnly ? mappedInput.mapLabels(tr(STR_BACK), "", "", "")\n                                           : mappedInput.mapLabels(tr(STR_BACK), canSetSleepCover() ? tr(STR_SET_SLEEP_COVER) : "",\n                                                                   (hasPrevious ? "<" : ""), (hasNext ? ">" : ""));')
s = s.replace('  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {\n    activityManager.goToFileBrowser(filePath);\n    return;\n  }',
              '  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {\n    if (simpleBackOnly) finish();\n    else activityManager.goToFileBrowser(filePath);\n    return;\n  }')
s = s.replace('  const auto swipe = mappedInput.wasSwipe();',
              '  if (simpleBackOnly) return;\n\n  const auto swipe = mappedInput.wasSwipe();')
p.write_text(s)

# -----------------------------------------------------------------------------
# Reader actions for direct description / metadata / cover.
# -----------------------------------------------------------------------------
p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text()
if '#include "activities/util/BmpViewerActivity.h"' not in s:
    s = s.replace('#include "activities/settings/TextSettingsActivity.h"\n',
                  '#include "activities/settings/TextSettingsActivity.h"\n#include "activities/util/BmpViewerActivity.h"\n', 1)
old_case = '''    case EpubReaderMenuActivity::MenuAction::BOOK_INFO: {\n      startActivityForResult(std::make_unique<BookInfoActivity>(renderer, mappedInput, epub),\n                             [this](const ActivityResult&) { openReaderMenu(); });\n      break;\n    }\n'''
new_case = '''    case EpubReaderMenuActivity::MenuAction::BOOK_DESCRIPTION: {\n      startActivityForResult(\n          std::make_unique<BookInfoActivity>(renderer, mappedInput, epub, BookInfoActivity::Page::Description),\n          [this](const ActivityResult&) { openReaderMenu(); });\n      break;\n    }\n    case EpubReaderMenuActivity::MenuAction::BOOK_METADATA: {\n      startActivityForResult(\n          std::make_unique<BookInfoActivity>(renderer, mappedInput, epub, BookInfoActivity::Page::Metadata),\n          [this](const ActivityResult&) { openReaderMenu(); });\n      break;\n    }\n    case EpubReaderMenuActivity::MenuAction::BOOK_COVER: {\n      std::string coverPath = epub->getCoverBmpPath(false);\n      if (!Storage.exists(coverPath.c_str())) epub->generateCoverBmp(false);\n      if (Storage.exists(coverPath.c_str())) {\n        startActivityForResult(std::make_unique<BmpViewerActivity>(renderer, mappedInput, coverPath, true),\n                               [this](const ActivityResult&) { requestUpdate(); });\n      } else {\n        openReaderMenu();\n      }\n      break;\n    }\n'''
if old_case not in s:
    raise SystemExit("BOOK_INFO reader case missing")
s = s.replace(old_case, new_case, 1)

# Main malformed-book page hierarchy: title first, message second; popup contains buttons only.
s = s.replace('indexErrorPopup.show("Indexelési hiba - hibás könyv", options, 2, 0, [this](int idx) {',
              'indexErrorPopup.show("", options, 2, 0, [this](int idx) {', 1)
old_render = '''  if (indexErrorDialog == IndexErrorDialog::Main) {\n    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 105, "A könyv egyik része nem", true, EpdFontFamily::REGULAR);\n    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 135, "dolgozható fel.", true, EpdFontFamily::REGULAR);\n  } else if (indexErrorDialog == IndexErrorDialog::RepairConfirm) {\n'''
new_render = '''  if (indexErrorDialog == IndexErrorDialog::Main) {\n    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 45, "Indexelési hiba - hibás könyv", true, EpdFontFamily::BOLD);\n    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 100, "A könyv egyik része nem", true, EpdFontFamily::REGULAR);\n    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 130, "dolgozható fel.", true, EpdFontFamily::REGULAR);\n  } else if (indexErrorDialog == IndexErrorDialog::RepairConfirm) {\n'''
if old_render not in s:
    raise SystemExit("index error main render block missing")
s = s.replace(old_render, new_render, 1)
p.write_text(s)

print("CPHUN-95 patch applied")
