#include "BookInfoActivity.h"

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
