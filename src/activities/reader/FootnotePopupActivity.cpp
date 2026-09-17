#include "FootnotePopupActivity.h"

#include <GfxRenderer.h>

#include <algorithm>
#include <cctype>

#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "fontIds.h"

namespace {
constexpr int POPUP_SIDE_MARGIN = 18;
constexpr int POPUP_HEIGHT = 430;
constexpr int POPUP_PADDING = 18;
constexpr int POPUP_HEADER_HEIGHT = 34;

std::string trimCopy(std::string value) {
  auto isWs = [](unsigned char c) { return std::isspace(c) != 0; };
  while (!value.empty() && isWs(static_cast<unsigned char>(value.front()))) value.erase(value.begin());
  while (!value.empty() && isWs(static_cast<unsigned char>(value.back()))) value.pop_back();
  return value;
}
}  // namespace

FootnotePopupActivity::FootnotePopupActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                             std::string label, std::string text)
    : Activity("FootnotePopup", renderer, mappedInput), label_(std::move(label)), text_(trimCopy(std::move(text))) {}

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
  const int maxWidth = renderer.getScreenWidth() - 2 * (POPUP_SIDE_MARGIN + POPUP_PADDING);
  std::string line;
  std::string word;
  auto flushWord = [&]() {
    if (word.empty()) return;
    const std::string candidate = line.empty() ? word : line + " " + word;
    if (!line.empty() && renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, candidate.c_str(), EpdFontFamily::REGULAR) > maxWidth) {
      lines_.push_back(line);
      line = word;
    } else {
      line = candidate;
    }
    word.clear();
  };
  for (char c : text_) {
    if (c == '\r') continue;
    if (c == '\n') {
      flushWord();
      if (!line.empty()) lines_.push_back(line);
      line.clear();
      continue;
    }
    if (std::isspace(static_cast<unsigned char>(c))) {
      flushWord();
    } else {
      word.push_back(c);
    }
  }
  flushWord();
  if (!line.empty()) lines_.push_back(line);
  if (lines_.empty()) lines_.push_back("–");
  firstLine_ = std::clamp(firstLine_, 0, std::max(0, static_cast<int>(lines_.size()) - 1));
}

void FootnotePopupActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back) ||
      mappedInput.wasReleased(MappedInputManager::Button::Confirm) ||
      mappedInput.wasReleased(MappedInputManager::Button::Power)) {
    finish();
    return;
  }
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
}

void FootnotePopupActivity::render(RenderLock&&) {
  const int screenW = renderer.getScreenWidth();
  const int screenH = renderer.getScreenHeight();
  const int popupW = screenW - 2 * POPUP_SIDE_MARGIN;
  const int popupH = std::min(POPUP_HEIGHT, screenH - 80);
  const int popupX = POPUP_SIDE_MARGIN;
  const int popupY = (screenH - popupH) / 2;

  renderer.fillRect(popupX, popupY, popupW, popupH, true);
  renderer.fillRect(popupX + 2, popupY + 2, popupW - 4, popupH - 4, false);

  const std::string title = label_.empty() ? "Lábjegyzet" : "Lábjegyzet " + label_;
  renderer.drawText(NOTOSANS_14_FONT_ID, popupX + POPUP_PADDING, popupY + 12, title.c_str(), true,
                    EpdFontFamily::REGULAR);

  const int lineHeight = renderer.getLineHeight(NOTOSERIF_14_FONT_ID);
  const int bodyTop = popupY + POPUP_HEADER_HEIGHT + 12;
  const int bodyBottom = popupY + popupH - 42;
  const int visibleLines = std::max(1, (bodyBottom - bodyTop) / std::max(1, lineHeight));
  int y = bodyTop;
  for (int i = 0; i < visibleLines && firstLine_ + i < static_cast<int>(lines_.size()); ++i) {
    renderer.drawText(NOTOSERIF_14_FONT_ID, popupX + POPUP_PADDING, y, lines_[firstLine_ + i].c_str(), true,
                      EpdFontFamily::REGULAR);
    y += lineHeight;
  }

  const bool canUp = firstLine_ > 0;
  const bool canDown = firstLine_ + visibleLines < static_cast<int>(lines_.size());
  const auto labels = mappedInput.mapLabels("Vissza", "Bezárás", canUp ? "Fel" : "", canDown ? "Le" : "");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer(HalDisplay::FAST_REFRESH);
}
