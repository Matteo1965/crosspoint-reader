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
    const std::string value = trimCopy(raw);
    if (value.empty()) continue;
    if (!out.empty()) out += ", ";
    out += value;
  }
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
    if (paragraphs.empty()) {
      text_ = "Ehhez a könyvhöz nincs fülszöveg.";
      return;
    }
    for (size_t i = 0; i < paragraphs.size(); ++i) {
      if (i > 0) text_ += "\n\n";
      text_ += paragraphs[i];
    }
    return;
  }

  const auto add = [this](const char* label, const std::string& value) {
    if (value.empty()) return;
    if (!text_.empty()) text_ += '\n';
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
  add("Címkék: ", joinTags(info_.subjects));
  add("Azonosító: ", info_.identifier);
  add("Fájlnév: ", info_.filename);
  add("Fájl formátum: ", fileFormat(info_.filename));
  if (info_.fileSize > 0) add("Fájlméret: ", std::to_string(info_.fileSize) + " byte");
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
  linesPerPage_ = std::max(1, (renderer.getScreenHeight() - topArea - bottomArea) / lineHeight);

  const char* text = text_.c_str();
  const uint32_t n = static_cast<uint32_t>(text_.size());
  uint32_t lineStart = 0;
  uint32_t lineEnd = 0;
  int lineWidth = 0;
  const int spaceWidth = renderer.getSpaceWidth(NOTOSERIF_14_FONT_ID, EpdFontFamily::REGULAR);
  const int hyphenWidth = renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, "-", EpdFontFamily::REGULAR);

  const auto flushLine = [&](const uint32_t nextStart, const bool appendHyphen = false, const bool justify = false) {
    lines_.push_back({lineStart, static_cast<uint16_t>(lineEnd - lineStart), appendHyphen, justify});
    lineStart = nextStart;
    lineEnd = nextStart;
    lineWidth = 0;
  };

  uint32_t i = 0;
  while (i < n) {
    const char c = text[i];
    if (c == '\n' || c == '\0') {
      flushLine(i + 1, false, false);
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

  totalPages_ = std::max(1, (static_cast<int>(lines_.size()) + linesPerPage_ - 1) / linesPerPage_);
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
  const int firstLine = currentPage_ * linesPerPage_;
  const int lastLine = std::min(firstLine + linesPerPage_, static_cast<int>(lines_.size()));
  const int lineHeight = renderer.getLineHeight(NOTOSERIF_14_FONT_ID);

  for (int i = firstLine; i < lastLine; ++i) {
    const Line& line = lines_[i];
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
        continue;
      }
    }

    renderer.drawText(NOTOSERIF_14_FONT_ID, x, y, buf, true, EpdFontFamily::REGULAR);
    if (line.appendHyphen) {
      const int hyphenX = x + renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, buf, EpdFontFamily::REGULAR);
      renderer.drawText(NOTOSERIF_14_FONT_ID, hyphenX, y, "-", true, EpdFontFamily::REGULAR);
    }
    y += lineHeight;
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
  GUI.drawHeader(renderer, Rect{contentX, contentY + metrics.topPadding, contentWidth, metrics.headerHeight}, title);

  if (totalPages_ > 1) {
    char counter[16];
    std::snprintf(counter, sizeof(counter), "%d/%d", currentPage_ + 1, totalPages_);
    const int width = renderer.getTextWidth(UI_10_FONT_ID, counter);
    renderer.drawText(UI_10_FONT_ID, contentX + contentWidth - SIDE_PADDING - width,
                      contentY + metrics.topPadding + metrics.headerHeight - renderer.getLineHeight(UI_10_FONT_ID), counter);
  }

  const int bodyY = contentY + metrics.topPadding + metrics.headerHeight + metrics.verticalSpacing;
  const int bodyWidth = contentWidth - 2 * SIDE_PADDING;
  auto* fcm = renderer.getFontCacheManager();
  auto scope = fcm->createPrewarmScope();
  drawBody(contentX + SIDE_PADDING, bodyY, bodyWidth);
  scope.endScanAndPrewarm();
  drawBody(contentX + SIDE_PADDING, bodyY, bodyWidth);

  const auto labels = mappedInput.mapLabels(tr(STR_BACK), "", currentPage_ > 0 ? "<" : "",
                                             currentPage_ + 1 < totalPages_ ? ">" : "");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer();
}
