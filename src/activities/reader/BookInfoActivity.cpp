#include "BookInfoActivity.h"

#include <Epub/hyphenation/Hyphenator.h>
#include <FontCacheManager.h>
#include <GfxRenderer.h>
#include <expat.h>

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <cstring>

#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "fontIds.h"

namespace {
constexpr size_t MAX_LINE_BYTES = 191;
constexpr int SIDE_PADDING = 20;
constexpr int METADATA_VALUE_X = 182;

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
    if (tag == "br") {
      self->flush();
    } else if (tag == "p" || tag == "div" || tag == "li" || tag == "h1" || tag == "h2" || tag == "h3" ||
               tag == "h4") {
      self->flush();
      if (tag == "li") self->current = "• ";
    }
  }

  static void XMLCALL end(void* ctx, const XML_Char* name) {
    auto* self = static_cast<DescriptionParser*>(ctx);
    const std::string tag = localName(name);
    if (tag == "p" || tag == "div" || tag == "li" || tag == "h1" || tag == "h2" || tag == "h3" || tag == "h4") {
      self->flush();
    }
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
  if (ok) {
    out.flush();
    return out.paragraphs;
  }

  out.paragraphs.clear();
  std::string plain;
  bool inTag = false;
  for (char c : fragment) {
    if (c == '<') {
      inTag = true;
      if (!plain.empty() && plain.back() != ' ') plain.push_back(' ');
      continue;
    }
    if (c == '>') {
      inTag = false;
      continue;
    }
    if (!inTag) plain.push_back(c);
  }
  plain = trimCopy(plain);
  if (!plain.empty()) out.paragraphs.push_back(std::move(plain));
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

std::string hungarianLowerCopy(const std::string& value) {
  std::string out;
  out.reserve(value.size());
  for (size_t i = 0; i < value.size();) {
    const unsigned char c = static_cast<unsigned char>(value[i]);
    if (c < 0x80) {
      out.push_back(static_cast<char>(std::tolower(c)));
      ++i;
      continue;
    }
    if (i + 1 < value.size()) {
      const unsigned char c2 = static_cast<unsigned char>(value[i + 1]);
      if (c == 0xC3) {
        const unsigned char lower =
            c2 == 0x81 ? 0xA1 : c2 == 0x89 ? 0xA9 : c2 == 0x8D ? 0xAD : c2 == 0x93 ? 0xB3 :
            c2 == 0x96 ? 0xB6 : c2 == 0x9A ? 0xBA : c2 == 0x9C ? 0xBC : c2;
        out.push_back(static_cast<char>(c));
        out.push_back(static_cast<char>(lower));
        i += 2;
        continue;
      }
      if (c == 0xC5 && (c2 == 0x90 || c2 == 0xB0)) {
        out.push_back(static_cast<char>(c));
        out.push_back(static_cast<char>(c2 + 1));
        i += 2;
        continue;
      }
    }
    out.push_back(value[i++]);
  }
  return out;
}

bool isWarningSeparator(const char c) {
  return std::isspace(static_cast<unsigned char>(c)) != 0 || c == ',' || c == '.' || c == '!' || c == ':';
}

std::string removeDescriptionWarning(std::string value) {
  const std::string lowered = hungarianLowerCopy(value);
  const std::string first = "vigyázat";
  const std::string second = "cselekményleírást";
  const std::string third = "tartalmaz";
  size_t search = 0;
  while (search < value.size()) {
    const size_t a = lowered.find(first, search);
    if (a == std::string::npos) break;
    size_t p = a + first.size();
    while (p < lowered.size() && isWarningSeparator(lowered[p])) ++p;
    if (lowered.compare(p, second.size(), second) != 0) { search = a + first.size(); continue; }
    p += second.size();
    while (p < lowered.size() && isWarningSeparator(lowered[p])) ++p;
    if (lowered.compare(p, third.size(), third) != 0) { search = a + first.size(); continue; }
    p += third.size();
    while (p < lowered.size() && isWarningSeparator(lowered[p])) ++p;
    value.erase(a, p - a);
    return trimCopy(value);
  }
  return trimCopy(value);
}

std::string filenameWithoutExtension(const std::string& filename) {
  const size_t slash = filename.find_last_of("/\\");
  const size_t baseStart = slash == std::string::npos ? 0 : slash + 1;
  const size_t dot = filename.find_last_of('.');
  if (dot == std::string::npos || dot <= baseStart) return filename.substr(baseStart);
  return filename.substr(baseStart, dot - baseStart);
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
    std::string value = raw;
    for (char& c : value) {
      if (c == '(' || c == ')' || c == '{' || c == '}' || c == '[' || c == ']') c = ' ';
    }
    std::string lowered = hungarianLowerCopy(value);
    for (const std::string phrase : {std::string("magyar nyelvű"), std::string("magyar nyelv")}) {
      size_t pos = 0;
      while ((pos = lowered.find(phrase, pos)) != std::string::npos) {
        value.erase(pos, phrase.size());
        lowered.erase(pos, phrase.size());
      }
    }
    value = trimCopy(value);
    std::string clean;
    bool pendingSpace = false;
    for (char c : value) {
      if (std::isspace(static_cast<unsigned char>(c))) { pendingSpace = !clean.empty(); continue; }
      if (c == ',') {
        while (!clean.empty() && clean.back() == ' ') clean.pop_back();
        if (!clean.empty() && clean.back() != ',') clean.push_back(',');
        pendingSpace = true;
        continue;
      }
      if (pendingSpace && !clean.empty() && clean.back() != ',') clean.push_back(' ');
      if (pendingSpace && !clean.empty() && clean.back() == ',') clean.push_back(' ');
      pendingSpace = false;
      clean.push_back(c);
    }
    clean = trimCopy(clean);
    while (!clean.empty() && clean.back() == ',') clean.pop_back();
    clean = trimCopy(clean);
    if (clean.empty()) continue;
    if (!out.empty()) out += ", ";
    out += clean;
  }
  return out;
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
  int lineWidth = 0;
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
          size_t cut = out.size() - 1;
          while (cut > 0 && (static_cast<unsigned char>(out[cut]) & 0xC0) == 0x80) --cut;
          out.resize(cut);
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
}  // namespace

BookInfoActivity::BookInfoActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::shared_ptr<Epub> epub,
                                   const Page page)
    : Activity("BookInfo", renderer, mappedInput), epub_(std::move(epub)), page_(page) {}

void BookInfoActivity::onEnter() {
  Activity::onEnter();
  renderer.setMissingGlyphFallbackFont(NOTOSERIF_14_FONT_ID);
  if (epub_) epub_->readBookInfo(info_);
  buildText();
  wrapText();
  requestUpdate();
}

void BookInfoActivity::onExit() {
  renderer.clearMissingGlyphFallbackFont();
  Activity::onExit();
  if (auto* fcm = renderer.getFontCacheManager()) fcm->releaseSdFontCaches();
}

void BookInfoActivity::buildText() {
  text_.clear();
  if (page_ == Page::Description) {
    const auto paragraphs = parseDescriptionFragment(info_.description);
    for (const auto& paragraph : paragraphs) {
      const std::string cleaned = removeDescriptionWarning(paragraph);
      if (cleaned.empty()) continue;
      if (!text_.empty()) text_ += "\n\n";
      text_ += cleaned;
    }
    if (text_.empty()) text_ = "Ehhez a könyvhöz nincs fülszöveg.";
    return;
  }

  const auto add = [this](const char* label, const std::string& value) {
    if (value.empty()) return;
    if (!text_.empty()) text_ += '\n';
    text_ += label;
    text_ += '\t';
    text_ += value;
  };
  add("Cím:", info_.title);
  add("Szerző:", info_.author);
  add("Sorozat:", info_.series);
  add("Sorszám:", info_.seriesIndex);
  const std::string publisher = trimCopy(info_.publisher);
  const std::string publisherLower = hungarianLowerCopy(publisher);
  if (!publisher.empty() && publisherLower != "ismeretlen" && publisherLower != "nincs" &&
      publisherLower != "nincs megadva" && publisher != "+" && publisher != "-" && publisherLower != "untitled") {
    add("Kiadó:", publisher);
  }
  const std::string displayDate = dateOnly(info_.date);
  bool showDate = false;
  if (displayDate.size() >= 4 && std::isdigit(static_cast<unsigned char>(displayDate[0])) &&
      std::isdigit(static_cast<unsigned char>(displayDate[1])) &&
      std::isdigit(static_cast<unsigned char>(displayDate[2])) &&
      std::isdigit(static_cast<unsigned char>(displayDate[3]))) {
    const int year = (displayDate[0] - '0') * 1000 + (displayDate[1] - '0') * 100 +
                     (displayDate[2] - '0') * 10 + (displayDate[3] - '0');
    showDate = year >= 1800;
  }
  if (showDate) add("Dátum:", displayDate);
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
  add("Fájlnév:", filenameWithoutExtension(info_.filename));
  add("Formátum:", fileFormat(info_.filename));
  if (info_.fileSize > 0) add("Fájlméret:", formatFileSizeMb(info_.fileSize));
  if (text_.empty()) text_ = "Nincs megjeleníthető metaadat.";
}

int BookInfoActivity::measureSpan(const char* text, size_t len) const {
  char buf[MAX_LINE_BYTES + 1];
  len = std::min(len, MAX_LINE_BYTES);
  memcpy(buf, text, len);
  buf[len] = '\0';
  return renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, buf, EpdFontFamily::REGULAR);
}

void BookInfoActivity::wrapText() {
  lines_.clear();
  lines_.reserve(text_.size() / 32 + 8);
  currentPage_ = 0;

  const auto& metrics = UITheme::getInstance().getMetrics();
  const auto orientation = renderer.getOrientation();
  const bool isLandscape = orientation == GfxRenderer::Orientation::LandscapeClockwise ||
                           orientation == GfxRenderer::Orientation::LandscapeCounterClockwise;
  const bool isInverted = orientation == GfxRenderer::Orientation::PortraitInverted;
  const int hintGutterWidth = isLandscape ? metrics.sideButtonHintsWidth : 0;
  const int maxWidth = renderer.getScreenWidth() - hintGutterWidth - 2 * SIDE_PADDING;
  const int lineHeight = renderer.getLineHeight(NOTOSERIF_14_FONT_ID);
  const int topArea = (isInverted ? metrics.buttonHintsHeight : 0) + metrics.topPadding + metrics.headerHeight +
                      metrics.verticalSpacing;
  const int bottomArea = metrics.buttonHintsHeight + metrics.verticalSpacing;
  const int availableHeight = renderer.getScreenHeight() - topArea - bottomArea + (page_ == Page::Metadata ? 2 : 0);

  const char* text = text_.c_str();
  const uint32_t n = static_cast<uint32_t>(text_.size());

  if (page_ == Page::Metadata) {
    const bool isLandscapeCw = orientation == GfxRenderer::Orientation::LandscapeClockwise;
    const int contentX = isLandscapeCw ? hintGutterWidth : 0;
    const int contentWidth = renderer.getScreenWidth() - hintGutterWidth;
    const int valueWidth = std::max(1, contentX + contentWidth - SIDE_PADDING - METADATA_VALUE_X);

    uint32_t fieldStart = 0;
    while (fieldStart < n) {
      uint32_t fieldEnd = fieldStart;
      while (fieldEnd < n && text[fieldEnd] != '\n') ++fieldEnd;

      uint32_t tabPos = fieldStart;
      while (tabPos < fieldEnd && text[tabPos] != '\t') ++tabPos;
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
      const int rowHeight = lineHeight + (addFieldGap ? 2 : 0);
      if (usedHeight > 0 && usedHeight + rowHeight > availableHeight) {
        pageStarts_.push_back(lineIndex);
        usedHeight = 0;
      }
      usedHeight += rowHeight;
    }
    totalPages_ = std::max(1, static_cast<int>(pageStarts_.size()));
    return;
  }

  uint32_t lineStart = 0;
  uint32_t lineEnd = 0;
  int lineWidth = 0;
  const int spaceWidth = renderer.getSpaceWidth(NOTOSERIF_14_FONT_ID, EpdFontFamily::REGULAR);
  const int hyphenWidth = renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, "-", EpdFontFamily::REGULAR);

  const auto flushLine = [&](const uint32_t nextStart, const bool appendHyphen = false, const bool justify = false,
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

  uint32_t i = 0;
  while (i < n) {
    const char c = text[i];
    if (c == '\n' || c == '\0') {
      flushLine(i + 1, false, false, page_ == Page::Metadata);
      ++i;
      continue;
    }
    if (c == ' ' || c == '\t' || c == '\r') {
      ++i;
      continue;
    }

    const uint32_t tokenStart = i;
    while (i < n && text[i] != ' ' && text[i] != '\t' && text[i] != '\r' && text[i] != '\n' && text[i] != '\0' &&
           i - tokenStart < MAX_LINE_BYTES) {
      ++i;
    }
    while (i - tokenStart > 1 && (static_cast<unsigned char>(text[i]) & 0xC0) == 0x80) --i;
    const uint32_t tokenLen = i - tokenStart;
    const std::string token(text + tokenStart, tokenLen);
    const auto breakInfos = page_ == Page::Description
                                ? Hyphenator::breakOffsetsForLanguageExtended(token, false, "hu")
                                : std::vector<Hyphenator::BreakInfo>{};

    uint32_t consumed = 0;
    while (consumed < tokenLen) {
      const uint32_t remainingLen = tokenLen - consumed;
      const int remainingWidth = measureSpan(text + tokenStart + consumed, remainingLen);
      const bool lineEmpty = lineEnd == lineStart;
      const int gapWidth = lineEmpty ? 0 : spaceWidth;

      if (lineWidth + gapWidth + remainingWidth <= maxWidth) {
        if (lineEmpty) lineStart = tokenStart + consumed;
        lineEnd = tokenStart + tokenLen;
        lineWidth += gapWidth + remainingWidth;
        consumed = tokenLen;
        continue;
      }

      const int availableWidth = maxWidth - lineWidth - gapWidth;
      uint32_t bestOffset = 0;
      bool bestNeedsHyphen = false;
      int bestWidth = 0;
      for (const auto& breakInfo : breakInfos) {
        if (breakInfo.byteOffset <= consumed || breakInfo.byteOffset >= tokenLen) continue;
        const uint32_t partLen = static_cast<uint32_t>(breakInfo.byteOffset) - consumed;
        const int partWidth = measureSpan(text + tokenStart + consumed, partLen) +
                              (breakInfo.requiresInsertedHyphen ? hyphenWidth : 0);
        if (partWidth <= availableWidth) {
          bestOffset = static_cast<uint32_t>(breakInfo.byteOffset);
          bestNeedsHyphen = breakInfo.requiresInsertedHyphen;
          bestWidth = partWidth;
        }
      }

      if (bestOffset > consumed) {
        if (lineEmpty) lineStart = tokenStart + consumed;
        lineEnd = tokenStart + bestOffset;
        lineWidth += gapWidth + bestWidth;
        flushLine(tokenStart + bestOffset, bestNeedsHyphen, page_ == Page::Description);
        consumed = bestOffset;
        continue;
      }

      if (page_ == Page::Metadata && !lineEmpty && remainingWidth > maxWidth && availableWidth > 0) {
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
      for (uint32_t partLen = 1; partLen <= remainingLen; ++partLen) {
        if (partLen == remainingLen || (static_cast<unsigned char>(text[tokenStart + consumed + partLen]) & 0xC0) != 0x80) {
          if (measureSpan(text + tokenStart + consumed, partLen) > maxWidth) break;
          lastFit = partLen;
        }
      }
      if (lastFit == 0) {
        lastFit = 1;
        while (lastFit < remainingLen &&
               (static_cast<unsigned char>(text[tokenStart + consumed + lastFit]) & 0xC0) == 0x80) {
          ++lastFit;
        }
      }
      lineStart = tokenStart + consumed;
      lineEnd = lineStart + lastFit;
      lineWidth = measureSpan(text + lineStart, lastFit);
      flushLine(lineEnd, false, false);
      consumed += lastFit;
    }
  }
  if (lineEnd > lineStart) flushLine(n, false, false);
  while (!lines_.empty() && lines_.back().len == 0) lines_.pop_back();

  pageStarts_.clear();
  pageStarts_.push_back(0);
  int usedHeight = 0;
  for (int lineIndex = 0; lineIndex < static_cast<int>(lines_.size()); ++lineIndex) {
    const bool addFieldGap = page_ == Page::Metadata && lines_[lineIndex].metadataFieldEnd &&
                             lineIndex + 1 < static_cast<int>(lines_.size());
    const int rowHeight = lineHeight + (addFieldGap ? 2 : 0);
    if (usedHeight > 0 && usedHeight + rowHeight > availableHeight) {
      pageStarts_.push_back(lineIndex);
      usedHeight = 0;
    }
    usedHeight += rowHeight;
  }
  totalPages_ = std::max(1, static_cast<int>(pageStarts_.size()));
}

void BookInfoActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    finish();
    return;
  }

  int tx = 0;
  int ty = 0;
  if (mappedInput.wasScreenTapped(tx, ty)) {
    if (tx < renderer.getScreenWidth() / 3) {
      if (currentPage_ > 0) {
        --currentPage_;
        requestUpdate();
      }
    } else if (currentPage_ + 1 < totalPages_) {
      ++currentPage_;
      requestUpdate();
    }
    return;
  }

  buttonNavigator_.onNext([this] {
    if (currentPage_ + 1 < totalPages_) {
      ++currentPage_;
      requestUpdate();
    }
  });
  buttonNavigator_.onPrevious([this] {
    if (currentPage_ > 0) {
      --currentPage_;
      requestUpdate();
    }
  });
}

void BookInfoActivity::drawBody(const int x, const int startY, const int maxWidth) const {
  int y = startY;
  char buf[MAX_LINE_BYTES + 1];
  char wordBuf[MAX_LINE_BYTES + 1];
  const int firstLine = pageStarts_.empty() ? 0 : pageStarts_[std::min(currentPage_, static_cast<int>(pageStarts_.size()) - 1)];
  const int lastLine = currentPage_ + 1 < static_cast<int>(pageStarts_.size())
                           ? pageStarts_[currentPage_ + 1]
                           : static_cast<int>(lines_.size());
  const int lineHeight = renderer.getLineHeight(NOTOSERIF_14_FONT_ID);

  for (int i = firstLine; i < lastLine; ++i) {
    const Line& line = lines_[i];

    if (page_ == Page::Metadata) {
      if (line.metadataFirstLine && line.metadataLabelLen > 0) {
        char labelBuf[MAX_LINE_BYTES + 1];
        const size_t labelLen = std::min(static_cast<size_t>(line.metadataLabelLen), MAX_LINE_BYTES);
        memcpy(labelBuf, text_.c_str() + line.metadataLabelStart, labelLen);
        labelBuf[labelLen] = '\0';
        renderer.drawText(NOTOSERIF_14_FONT_ID, x, y, labelBuf, true, EpdFontFamily::REGULAR);
      }
      if (line.len > 0) {
        const size_t valueLen = std::min(static_cast<size_t>(line.len), MAX_LINE_BYTES);
        memcpy(buf, text_.c_str() + line.start, valueLen);
        buf[valueLen] = '\0';
        renderer.drawText(NOTOSERIF_14_FONT_ID, METADATA_VALUE_X, y, buf, true, EpdFontFamily::REGULAR);
      }
      y += lineHeight;
      if (line.metadataFieldEnd && i + 1 < static_cast<int>(lines_.size())) y += 2;
      continue;
    }

    if (line.len == 0) {
      y += lineHeight;
      continue;
    }
    const size_t len = std::min(static_cast<size_t>(line.len), MAX_LINE_BYTES);
    memcpy(buf, text_.c_str() + line.start, len);
    buf[len] = '\0';

    if (line.justify && page_ == Page::Description) {
      int wordCount = 0;
      bool inWord = false;
      for (size_t j = 0; j < len; ++j) {
        const bool ws = buf[j] == ' ' || buf[j] == '\t' || buf[j] == '\r';
        if (ws) inWord = false;
        else if (!inWord) {
          ++wordCount;
          inWord = true;
        }
      }

      if (wordCount > 1) {
        int wordsWidth = 0;
        size_t pos = 0;
        while (pos < len) {
          while (pos < len && (buf[pos] == ' ' || buf[pos] == '\t' || buf[pos] == '\r')) ++pos;
          const size_t wordStart = pos;
          while (pos < len && buf[pos] != ' ' && buf[pos] != '\t' && buf[pos] != '\r') ++pos;
          const size_t wordLen = pos - wordStart;
          if (wordLen == 0) continue;
          memcpy(wordBuf, buf + wordStart, wordLen);
          wordBuf[wordLen] = '\0';
          wordsWidth += renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, wordBuf, EpdFontFamily::REGULAR);
        }

        const int gapCount = wordCount - 1;
        const int naturalSpace = renderer.getSpaceWidth(NOTOSERIF_14_FONT_ID, EpdFontFamily::REGULAR);
        const int hyphenWidth = line.appendHyphen
                                    ? renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, "-", EpdFontFamily::REGULAR)
                                    : 0;
        const int extra = std::max(0, maxWidth - wordsWidth - gapCount * naturalSpace - hyphenWidth);
        const int extraPerGap = extra / gapCount;
        const int remainder = extra % gapCount;
        int cursorX = x;
        int gapIndex = 0;
        pos = 0;
        while (pos < len) {
          while (pos < len && (buf[pos] == ' ' || buf[pos] == '\t' || buf[pos] == '\r')) ++pos;
          const size_t wordStart = pos;
          while (pos < len && buf[pos] != ' ' && buf[pos] != '\t' && buf[pos] != '\r') ++pos;
          const size_t wordLen = pos - wordStart;
          if (wordLen == 0) continue;
          memcpy(wordBuf, buf + wordStart, wordLen);
          wordBuf[wordLen] = '\0';
          renderer.drawText(NOTOSERIF_14_FONT_ID, cursorX, y, wordBuf, true, EpdFontFamily::REGULAR);
          cursorX += renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, wordBuf, EpdFontFamily::REGULAR);
          if (gapIndex < gapCount) {
            cursorX += naturalSpace + extraPerGap + (gapIndex < remainder ? 1 : 0);
            ++gapIndex;
          }
        }
        if (line.appendHyphen) renderer.drawText(NOTOSERIF_14_FONT_ID, cursorX, y, "-", true, EpdFontFamily::REGULAR);
        y += lineHeight;
        if (page_ == Page::Metadata && line.metadataFieldEnd && i + 1 < static_cast<int>(lines_.size())) y += 2;
        continue;
      }
    }

    renderer.drawText(NOTOSERIF_14_FONT_ID, x, y, buf, true, EpdFontFamily::REGULAR);
    if (line.appendHyphen) {
      const int hyphenX = x + renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, buf, EpdFontFamily::REGULAR);
      renderer.drawText(NOTOSERIF_14_FONT_ID, hyphenX, y, "-", true, EpdFontFamily::REGULAR);
    }
    y += lineHeight;
    if (page_ == Page::Metadata && line.metadataFieldEnd && i + 1 < static_cast<int>(lines_.size())) y += 2;
  }
}

void BookInfoActivity::render(RenderLock&&) {
  renderer.clearScreen();

  const auto& metrics = UITheme::getInstance().getMetrics();
  const auto orientation = renderer.getOrientation();
  const bool isLandscapeCw = orientation == GfxRenderer::Orientation::LandscapeClockwise;
  const bool isLandscapeCcw = orientation == GfxRenderer::Orientation::LandscapeCounterClockwise;
  const bool isInverted = orientation == GfxRenderer::Orientation::PortraitInverted;
  const int hintGutterWidth = (isLandscapeCw || isLandscapeCcw) ? metrics.sideButtonHintsWidth : 0;
  const int contentX = isLandscapeCw ? hintGutterWidth : 0;
  const int contentWidth = renderer.getScreenWidth() - hintGutterWidth;
  const int contentY = isInverted ? metrics.buttonHintsHeight : 0;

  const char* title = page_ == Page::Description ? "Fülszöveg" : "Metaadatok";
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

  const int bodyY = contentY + metrics.topPadding + metrics.headerHeight + metrics.verticalSpacing -
                    (page_ == Page::Metadata ? 2 : 0);
  const int bodyWidth = contentWidth - 2 * SIDE_PADDING;
  auto* fcm = renderer.getFontCacheManager();
  auto scope = fcm->createPrewarmScope();
  drawBody(contentX + SIDE_PADDING, bodyY, bodyWidth);
  scope.endScanAndPrewarm();
  drawBody(contentX + SIDE_PADDING, bodyY, bodyWidth);

  const auto labels = mappedInput.mapLabels("Vissza", "", currentPage_ > 0 ? "<" : "",
                                             currentPage_ + 1 < totalPages_ ? ">" : "");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer();
}