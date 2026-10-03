#include "FootnotePopupActivity.h"

#include <GfxRenderer.h>
#include <Epub/hyphenation/Hyphenator.h>

#include <algorithm>
#include <cctype>

#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "fontIds.h"

namespace {
constexpr int POPUP_SIDE_MARGIN = 18;
constexpr int POPUP_HEIGHT = 680;
constexpr int POPUP_TOP_REFERENCE_HEIGHT = 640;
constexpr int POPUP_PADDING = 18;
constexpr int POPUP_HEADER_HEIGHT = 34;

std::string trimCopy(std::string value) {
  auto isWs = [](unsigned char c) { return std::isspace(c) != 0; };
  while (!value.empty() && isWs(static_cast<unsigned char>(value.front()))) value.erase(value.begin());
  while (!value.empty() && isWs(static_cast<unsigned char>(value.back()))) value.pop_back();
  return value;
}

std::string footnoteLabelCore(std::string label) {
  label = trimCopy(std::move(label));
  if (label.size() >= 2) {
    const char first = label.front();
    const char last = label.back();
    if ((first == '{' && last == '}') || (first == '[' && last == ']') ||
        (first == '(' && last == ')')) {
      label = trimCopy(label.substr(1, label.size() - 2));
    }
  }
  return label;
}

std::string footnoteNumberOnly(const std::string& label) {
  std::string digits;
  bool started = false;
  for (const unsigned char c : label) {
    if (std::isdigit(c)) {
      digits.push_back(static_cast<char>(c));
      started = true;
    } else if (started) {
      break;
    }
  }
  return digits;
}

std::string stripRepeatedFootnoteMarker(std::string text, const std::string& label) {
  text = trimCopy(std::move(text));
  const std::string core = footnoteLabelCore(label);
  if (core.empty() || text.empty()) return text;

  const std::string markers[] = {"{" + core + "}", "[" + core + "]", "(" + core + ")", core};
  for (const auto& marker : markers) {
    if (text.rfind(marker, 0) != 0) continue;
    const size_t end = marker.size();
    if (end < text.size()) {
      const unsigned char next = static_cast<unsigned char>(text[end]);
      if (!std::isspace(next) && text[end] != '.' && text[end] != ':' && text[end] != '-') {
        continue;
      }
    }
    text.erase(0, end);
    while (!text.empty() &&
           (std::isspace(static_cast<unsigned char>(text.front())) ||
            text.front() == '.' || text.front() == ':' || text.front() == '-')) {
      text.erase(text.begin());
    }
    return trimCopy(std::move(text));
  }
  return text;
}
}  // namespace

FootnotePopupActivity::FootnotePopupActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                             std::string label, std::string text, const bool canReturnToList,
                                             const bool canNavigateSiblings)
    : Activity("FootnotePopup", renderer, mappedInput),
      label_(footnoteLabelCore(std::move(label))),
      text_(stripRepeatedFootnoteMarker(std::move(text), label_)),
      canReturnToList_(canReturnToList),
      canNavigateSiblings_(canNavigateSiblings) {}

void FootnotePopupActivity::onEnter() {
  Activity::onEnter();
  renderer.setMissingGlyphFallbackFont(NOTOSERIF_14_FONT_ID);
  wrapText();
  requestUpdate();
}

void FootnotePopupActivity::onExit() {
  renderer.clearMissingGlyphFallbackFont();
  Activity::onExit();
}

void FootnotePopupActivity::wrapText() {
  lines_.clear();
  lineJustified_.clear();

  // Reserve one contiguous block up front to reduce repeated small heap
  // reallocations while switching among footnotes.
  const size_t estimatedLines = std::min<size_t>(64, std::max<size_t>(8, text_.size() / 48 + 1));
  lines_.reserve(estimatedLines);
  lineJustified_.reserve(estimatedLines);

  const int maxWidth = renderer.getScreenWidth() - 2 * (POPUP_SIDE_MARGIN + POPUP_PADDING);
  const int fontId = NOTOSERIF_14_FONT_ID;

  auto replacementSuffix = [](const Hyphenator::Replacement replacement) -> const char* {
    switch (replacement) {
      case Hyphenator::Replacement::AppendY:
        return "y";
      case Hyphenator::Replacement::AppendZ:
        return "z";
      case Hyphenator::Replacement::AppendS:
        return "s";
      case Hyphenator::Replacement::AppendZS:
        return "zs";
      case Hyphenator::Replacement::None:
      default:
        return "";
    }
  };

  auto pushLine = [&](std::string&& value, const bool justify) {
    if (value.empty()) return;
    lines_.push_back(std::move(value));
    lineJustified_.push_back(justify ? 1 : 0);
  };

  std::string line;
  std::string word;
  line.reserve(96);
  word.reserve(48);

  auto fitHyphenatedPrefix = [&](const std::string& source, const int availableWidth,
                                 std::string& left, std::string& right) -> bool {
    const auto breaks = Hyphenator::breakOffsetsForLanguageExtended(source, false, "hu");
    for (auto it = breaks.rbegin(); it != breaks.rend(); ++it) {
      if (it->byteOffset == 0 || it->byteOffset >= source.size()) continue;
      std::string candidate = source.substr(0, it->byteOffset);
      candidate += replacementSuffix(it->replacement);
      if (it->requiresInsertedHyphen) candidate += "-";
      if (renderer.getTextAdvanceX(fontId, candidate.c_str(), EpdFontFamily::REGULAR) <= availableWidth) {
        left = std::move(candidate);
        right = source.substr(it->byteOffset);
        return true;
      }
    }
    return false;
  };

  auto placeWord = [&](std::string incoming) {
    while (!incoming.empty()) {
      if (line.empty()) {
        if (renderer.getTextAdvanceX(fontId, incoming.c_str(), EpdFontFamily::REGULAR) <= maxWidth) {
          line = std::move(incoming);
          return;
        }

        std::string left, right;
        if (fitHyphenatedPrefix(incoming, maxWidth, left, right)) {
          pushLine(std::move(left), false);
          incoming = std::move(right);
          continue;
        }

        // Unbreakable token: keep it intact rather than corrupting UTF-8.
        line = std::move(incoming);
        return;
      }

      const std::string candidate = line + " " + incoming;
      if (renderer.getTextAdvanceX(fontId, candidate.c_str(), EpdFontFamily::REGULAR) <= maxWidth) {
        line = candidate;
        return;
      }

      const int used = renderer.getTextAdvanceX(fontId, line.c_str(), EpdFontFamily::REGULAR);
      const int available =
          std::max(0, maxWidth - used - renderer.getSpaceWidth(fontId, EpdFontFamily::REGULAR));
      std::string left, right;
      if (available > 0 && fitHyphenatedPrefix(incoming, available, left, right)) {
        line += " ";
        line += left;
        pushLine(std::move(line), true);
        line.clear();
        incoming = std::move(right);
        continue;
      }

      pushLine(std::move(line), true);
      line.clear();
    }
  };

  auto flushWord = [&]() {
    if (word.empty()) return;
    placeWord(std::move(word));
    word.clear();
  };

  auto finishParagraph = [&]() {
    flushWord();
    if (!line.empty()) {
      pushLine(std::move(line), false);
      line.clear();
    }
  };

  for (char c : text_) {
    if (c == '\r') continue;
    if (c == '\n') {
      finishParagraph();
      continue;
    }
    if (std::isspace(static_cast<unsigned char>(c))) {
      flushWord();
    } else {
      word.push_back(c);
    }
  }
  finishParagraph();

  if (lines_.empty()) {
    lines_.push_back("–");
    lineJustified_.push_back(0);
  }
  firstLine_ = std::clamp(firstLine_, 0, std::max(0, static_cast<int>(lines_.size()) - 1));
}

void FootnotePopupActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    if (canReturnToList_) {
      ActivityResult result;
      result.isCancelled = true;
      setResult(std::move(result));
    }
    finish();
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm) ||
      mappedInput.wasReleased(MappedInputManager::Button::Power)) {
    // Normal completion means "Bezárás": return directly to the reader.
    finish();
    return;
  }
  // Side Up/Down buttons always scroll the current footnote text.
  if (mappedInput.wasReleased(MappedInputManager::Button::Up)) {
    if (firstLine_ > 0) {
      --firstLine_;
      requestUpdate();
    }
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Down)) {
    if (firstLine_ + 1 < static_cast<int>(lines_.size())) {
      ++firstLine_;
      requestUpdate();
    }
    return;
  }

  // Front bottom buttons 3/4 are the Left/Right roles. Their labels are
  // already orientation-aware via mapLabels(), so mirror the semantic action
  // when that axis is swapped as well.
  if (canNavigateSiblings_ &&
      mappedInput.wasReleased(MappedInputManager::Button::Left)) {
    setResult(FootnotePopupNavResult{mappedInput.isNavDirectionSwapped() ? 1 : -1});
    finish();
    return;
  }
  if (canNavigateSiblings_ &&
      mappedInput.wasReleased(MappedInputManager::Button::Right)) {
    setResult(FootnotePopupNavResult{mappedInput.isNavDirectionSwapped() ? -1 : 1});
    finish();
    return;
  }
}

void FootnotePopupActivity::render(RenderLock&&) {
  const int screenW = renderer.getScreenWidth();
  const int screenH = renderer.getScreenHeight();
  const int popupW = screenW - 2 * POPUP_SIDE_MARGIN;
  const int popupH = std::min(POPUP_HEIGHT, screenH - 80);
  const int popupX = POPUP_SIDE_MARGIN;
  const int popupY = std::max(0, (screenH - POPUP_TOP_REFERENCE_HEIGHT) / 2 - 40);

  renderer.fillRect(popupX, popupY, popupW, popupH, true);
  renderer.fillRect(popupX + 2, popupY + 2, popupW - 4, popupH - 4, false);

  const std::string number = footnoteNumberOnly(label_);
  const std::string title = number.empty() ? "Lábjegyzet" : "Lábjegyzet {" + number + "}";
  renderer.drawText(NOTOSANS_14_FONT_ID, popupX + POPUP_PADDING, popupY + 12, title.c_str(), true,
                    EpdFontFamily::BOLD);

  const int lineHeight = renderer.getLineHeight(NOTOSERIF_14_FONT_ID);
  // CPHUN-144: keep an extra half line between the bold title and body.
  const int bodyTop = popupY + POPUP_HEADER_HEIGHT + 12 + lineHeight / 2;
  const int bodyBottom = popupY + popupH - 42;
  const int visibleLines = std::max(1, (bodyBottom - bodyTop) / std::max(1, lineHeight));
  const int textX = popupX + POPUP_PADDING;
  const int textWidth = popupW - 2 * POPUP_PADDING;

  auto drawBodyLine = [&](const std::string& line, const int y, const bool justify) {
    if (!justify) {
      renderer.drawText(NOTOSERIF_14_FONT_ID, textX, y, line.c_str(), true, EpdFontFamily::REGULAR);
      return;
    }

    int gaps = 0;
    for (char c : line) {
      if (c == ' ') ++gaps;
    }
    if (gaps <= 0) {
      renderer.drawText(NOTOSERIF_14_FONT_ID, textX, y, line.c_str(), true, EpdFontFamily::REGULAR);
      return;
    }

    std::string token;
    token.reserve(line.size());
    int wordsWidth = 0;
    for (size_t i = 0; i <= line.size(); ++i) {
      const char c = (i < line.size()) ? line[i] : ' ';
      if (c == ' ') {
        if (!token.empty()) {
          wordsWidth += renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, token.c_str(), EpdFontFamily::REGULAR);
          token.clear();
        }
      } else {
        token.push_back(c);
      }
    }

    const int normalSpace = renderer.getSpaceWidth(NOTOSERIF_14_FONT_ID, EpdFontFamily::REGULAR);
    const int extra = std::max(0, textWidth - wordsWidth - gaps * normalSpace);
    const int extraPerGap = extra / gaps;
    int remainder = extra % gaps;

    int x = textX;
    token.clear();
    int gapIndex = 0;
    for (size_t i = 0; i <= line.size(); ++i) {
      const char c = (i < line.size()) ? line[i] : ' ';
      if (c == ' ') {
        if (!token.empty()) {
          renderer.drawText(NOTOSERIF_14_FONT_ID, x, y, token.c_str(), true, EpdFontFamily::REGULAR);
          x += renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, token.c_str(), EpdFontFamily::REGULAR);
          token.clear();
          if (gapIndex < gaps) {
            x += normalSpace + extraPerGap + (remainder-- > 0 ? 1 : 0);
            ++gapIndex;
          }
        }
      } else {
        token.push_back(c);
      }
    }
  };

  int y = bodyTop;
  for (int i = 0; i < visibleLines && firstLine_ + i < static_cast<int>(lines_.size()); ++i) {
    const int lineIndex = firstLine_ + i;
    const bool justify = lineIndex < static_cast<int>(lineJustified_.size()) && lineJustified_[lineIndex] != 0;
    drawBodyLine(lines_[lineIndex], y, justify);
    y += lineHeight;
  }

  const bool canUp = firstLine_ > 0;
  const bool canDown = firstLine_ + visibleLines < static_cast<int>(lines_.size());

  // CPHUN-145: visual continuation cue. Draw it from primitives instead of a
  // Unicode arrow glyph so it never depends on font coverage/fallback.
  if (canDown) {
    const int arrowX = popupX + popupW - 17;
    const int arrowY = popupY + popupH - 31;
    renderer.drawLine(arrowX, arrowY, arrowX, arrowY + 9, 2, true);
    renderer.drawLine(arrowX - 5, arrowY + 5, arrowX, arrowY + 10, 2, true);
    renderer.drawLine(arrowX + 5, arrowY + 5, arrowX, arrowY + 10, 2, true);
  }

  const auto labels = mappedInput.mapLabels(
      canReturnToList_ ? "Vissza" : "", "Bezárás",
      canNavigateSiblings_ ? "Előző" : (canUp ? "Fel" : ""),
      canNavigateSiblings_ ? "Következő" : (canDown ? "Le" : ""));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer(HalDisplay::FAST_REFRESH);
}
