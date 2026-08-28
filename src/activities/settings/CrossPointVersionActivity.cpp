#include "CrossPointVersionActivity.h"

#include <GfxRenderer.h>
#include <I18n.h>

#include <cstdio>
#include <string>

#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "fontIds.h"
#include "CPHUNBuildId.h"

namespace {

constexpr int PAGE_COUNT = 3;
constexpr int SIDE_PADDING = 20;

}  // namespace

void CrossPointVersionActivity::onEnter() {
  Activity::onEnter();
  currentPage = 0;
  requestUpdate();
}

void CrossPointVersionActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    finish();
    return;
  }

  int x = 0;
  int y = 0;
  if (mappedInput.wasScreenTapped(x, y)) {
    if (x < renderer.getScreenWidth() / 3) {
      if (currentPage > 0) {
        currentPage--;
        requestUpdate();
      }
    } else if (currentPage + 1 < PAGE_COUNT) {
      currentPage++;
      requestUpdate();
    }
    return;
  }

  const bool nextPage = mappedInput.wasReleased(MappedInputManager::Button::PageForward) ||
                        mappedInput.wasReleased(MappedInputManager::Button::Right);
  const bool previousPage = mappedInput.wasReleased(MappedInputManager::Button::PageBack) ||
                            mappedInput.wasReleased(MappedInputManager::Button::Left);
  if (nextPage && currentPage + 1 < PAGE_COUNT) {
    currentPage++;
    requestUpdate();
  } else if (previousPage && currentPage > 0) {
    currentPage--;
    requestUpdate();
  }
}

void CrossPointVersionActivity::render(RenderLock&&) {
  renderer.clearScreen();

  const auto& metrics = UITheme::getInstance().getMetrics();
  const int pageWidth = renderer.getScreenWidth();
  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, pageWidth, metrics.headerHeight}, tr(STR_CROSSPOINT_VERSION));

  char counter[16];
  snprintf(counter, sizeof(counter), "%d/%d", currentPage + 1, PAGE_COUNT);
  const int counterWidth = renderer.getTextWidth(UI_10_FONT_ID, counter);
  const int counterY = renderer.getScreenHeight() - metrics.buttonHintsHeight - metrics.verticalSpacing -
                       renderer.getLineHeight(UI_10_FONT_ID);
  renderer.drawText(UI_10_FONT_ID, pageWidth - SIDE_PADDING - counterWidth, counterY, counter);

  constexpr int x = SIDE_PADDING;
  const int maxWidth = pageWidth - 2 * SIDE_PADDING;
  int y = metrics.topPadding + metrics.headerHeight + metrics.verticalSpacing;
  const int bodyLineHeight = renderer.getLineHeight(UI_12_FONT_ID);
  const int linkLineHeight = renderer.getLineHeight(UI_10_FONT_ID);

  const auto drawWrapped = [&](const int fontId, const char* text, const bool bold = false) {
    const auto family = bold ? EpdFontFamily::BOLD : EpdFontFamily::REGULAR;
    std::string line;
    const std::string input(text);
    size_t pos = 0;
    while (pos < input.size()) {
      while (pos < input.size() && input[pos] == ' ') pos++;
      if (pos >= input.size()) break;
      const size_t wordStart = pos;
      while (pos < input.size() && input[pos] != ' ') pos++;
      const std::string word = input.substr(wordStart, pos - wordStart);
      const std::string candidate = line.empty() ? word : line + " " + word;
      if (!line.empty() && renderer.getTextAdvanceX(fontId, candidate.c_str(), family) > maxWidth) {
        renderer.drawText(fontId, x, y, line.c_str(), true, family);
        y += renderer.getLineHeight(fontId);
        line = word;
      } else {
        line = candidate;
      }
    }
    if (!line.empty()) {
      renderer.drawText(fontId, x, y, line.c_str(), true, family);
      y += renderer.getLineHeight(fontId);
    }
  };

  const auto drawParagraph = [&](const StrId id, const bool bold = false) {
    drawWrapped(UI_12_FONT_ID, I18N.get(id), bold);
    y += bodyLineHeight;
  };

  if (currentPage == 0) {
    const auto drawLabelValue = [&](const char* label, const char* value) {
      const std::string line = std::string(label) + ": " + value;
      drawWrapped(UI_12_FONT_ID, line.c_str());
    };

    drawLabelValue(tr(STR_CROSSPOINT_VERSION), CROSSPOINT_VERSION);
    drawLabelValue(tr(STR_EDITION), "Hungarian Edition");
    drawWrapped(UI_12_FONT_ID, CPHUN_BUILD_ID);
    const std::string buildDate = std::string(__DATE__) + " " + __TIME__;
    drawLabelValue(tr(STR_BUILD_DATE), buildDate.c_str());

    y += bodyLineHeight;
    drawWrapped(UI_12_FONT_ID, tr(STR_GITHUB_RELEASES), true);
    renderer.drawText(UI_10_FONT_ID, x, y, "github.com/Matteo1965/");
    y += linkLineHeight;
    renderer.drawText(UI_10_FONT_ID, x, y, "crosspoint-reader/releases");
    y += linkLineHeight + bodyLineHeight;

    drawWrapped(UI_12_FONT_ID, tr(STR_DIFFERENCES_FROM_BASE), true);
    const StrId features[] = {StrId::STR_FEATURE_HUNGARIAN_UI, StrId::STR_FEATURE_HUNGARIAN_HYPHENATION,
                              StrId::STR_FEATURE_HUNGARIAN_STEMMING, StrId::STR_FEATURE_DICTIONARY_DISPLAY};
    for (const StrId feature : features) {
      const char* featureText = feature == StrId::STR_FEATURE_HUNGARIAN_STEMMING
                                    ? "Magyar szótövezés: 357 új szóalak"
                                    : I18N.get(feature);
      const std::string line = std::string("- ") + featureText;
      drawWrapped(UI_12_FONT_ID, line.c_str());
    }
    const bool hu = I18N.getLanguage() == Language::HU;
    const char* extraFeatures[] = {
        hu ? "Kiterjesztett magyar elválasztás" : "Extended Hungarian hyphenation",
        hu ? "Beágyazott elválasztás (Soft hyphen)" : "Embedded hyphenation (Soft hyphen)",
        hu ? "Javított sorkizárt szedés" : "Improved justified text layout",
        hu ? "Optikai margó (Hanging punctuation)" : "Hanging punctuation",
        hu ? "Min. szóköz: 50–100%" : "Minimum word spacing: 50–100%",
        hu ? "Fix párbeszédköz: Min. szóköz szerint" : "Fixed dialogue space follows Min. word spacing",
        hu ? "Hiányzó párbeszédközök pótlása" : "Recover missing dialogue space",
    };
    for (const char* featureText : extraFeatures) {
      const std::string line = std::string("- ") + featureText;
      drawWrapped(UI_12_FONT_ID, line.c_str());
    }
  } else if (currentPage == 1) {
    const bool hu = I18N.getLanguage() == Language::HU;
    if (hu) {
      drawWrapped(UI_12_FONT_ID, "Szótár telepítése szükséges", true);
      y += bodyLineHeight;
      drawWrapped(UI_12_FONT_ID, I18N.get(StrId::STR_DICTIONARY_NOT_INCLUDED));
      drawWrapped(UI_12_FONT_ID, I18N.get(StrId::STR_DICTIONARY_INSTALL_SEPARATELY));
      drawWrapped(UI_12_FONT_ID, I18N.get(StrId::STR_STARDICT_FILES_INTRO));
      renderer.drawText(UI_12_FONT_ID, x, y, ".ifo + .idx + .dict");
      y += bodyLineHeight;
      drawWrapped(UI_12_FONT_ID, I18N.get(StrId::STR_DICTIONARY_LICENSE_NOTICE));
      y += bodyLineHeight;
      drawWrapped(UI_12_FONT_ID, "Javított magyar szótárkezelés", true);
      drawWrapped(UI_12_FONT_ID,
                  "A magyar nyelvhez külön továbbfejlesztett szótárkezelés ragozott és toldalékolt "
                  "szóalakok esetén is segíti a megfelelő szótári címszó megtalálását.");
    } else {
      drawParagraph(StrId::STR_DICTIONARY_REQUIRED, true);
      drawParagraph(StrId::STR_DICTIONARY_NOT_INCLUDED);
      drawParagraph(StrId::STR_DICTIONARY_INSTALL_SEPARATELY);
      drawParagraph(StrId::STR_STARDICT_FILES_INTRO);
      renderer.drawText(UI_12_FONT_ID, x, y, ".ifo + .idx + .dict");
      y += bodyLineHeight * 2;
      drawWrapped(UI_12_FONT_ID, I18N.get(StrId::STR_DICTIONARY_LICENSE_NOTICE));
    }
  } else {
    drawParagraph(StrId::STR_HYPHENATION_LANGUAGES, true);
    drawParagraph(StrId::STR_HYPHENATION_LANGUAGES_NOTICE);
    drawWrapped(UI_12_FONT_ID, I18N.get(StrId::STR_HYPHENATION_OTHER_LANGUAGES_NOTICE));
    if (I18N.getLanguage() == Language::HU) {
      y += bodyLineHeight;
      drawWrapped(UI_12_FONT_ID,
                  "A magyar elválasztás Nagy Bence Huhyphn elválasztási mintáira épül, amelyeket saját "
                  "kiegészítéseinkkel és továbbfejlesztéseinkkel bővítettünk.");
    }
  }

  const auto labels =
      mappedInput.mapLabels(tr(STR_BACK), "", currentPage > 0 ? "<" : "", currentPage + 1 < PAGE_COUNT ? ">" : "");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer();
}
