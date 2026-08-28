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

constexpr int PAGE_COUNT = 4;
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
  const bool hu = I18N.getLanguage() == Language::HU;

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

  const auto drawSection = [&](const char* title, const char* text) {
    drawWrapped(UI_12_FONT_ID, title, true);
    drawWrapped(UI_12_FONT_ID, text);
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
    const std::string buildDate = std::string(__DATE__) + " " + __TIME__ + " GMT";
    drawLabelValue(hu ? "Dátum" : "Date", buildDate.c_str());

    y += bodyLineHeight;
    drawWrapped(UI_12_FONT_ID, tr(STR_GITHUB_RELEASES), true);
    renderer.drawText(UI_10_FONT_ID, x, y, "github.com/Matteo1965/");
    y += linkLineHeight;
    renderer.drawText(UI_10_FONT_ID, x, y, "crosspoint-reader/releases");
    y += linkLineHeight + bodyLineHeight;

    drawWrapped(UI_12_FONT_ID, hu ? "A Hungarian Edition főbb fejlesztései:" : "Key Hungarian Edition improvements:", true);
    const char* features[] = {
        hu ? "- Magyar felhasználói felület" : "- Hungarian user interface",
        hu ? "- Magyar szótár és szótövezés → 2. oldal" : "- Hungarian dictionary and stemming → page 2",
        hu ? "- Magyar elválasztás → 3. oldal" : "- Hungarian hyphenation → page 3",
        hu ? "- Sorkizárás és tipográfia → 4. oldal" : "- Justification and typography → page 4",
    };
    for (const char* feature : features) drawWrapped(UI_12_FONT_ID, feature);
  } else if (currentPage == 1) {
    drawWrapped(UI_12_FONT_ID, hu ? "Magyar szótár és szótövezés" : "Hungarian dictionary and stemming", true);
    y += bodyLineHeight;
    drawSection(hu ? "StarDict szótárak" : "StarDict dictionaries",
                hu ? "A szótárak külön telepíthetők, és nem részei a firmware-nek."
                   : "Dictionaries are installed separately and are not part of the firmware.");
    drawWrapped(UI_12_FONT_ID,
                hu ? "Támogatott formátum: szabványos StarDict szótárak"
                   : "Supported format: standard StarDict dictionaries");
    y += bodyLineHeight;
    drawSection(hu ? "Javított magyar szótárkezelés" : "Improved Hungarian dictionary handling",
                hu ? "A továbbfejlesztett szótárkezelés a ragozott és toldalékolt szóalakok esetén is segíti a megfelelő szótári címszó megtalálását."
                   : "Improved dictionary handling helps find the appropriate headword for inflected and suffixed Hungarian word forms.");
    drawSection(hu ? "Magyar szótövezés" : "Hungarian stemming",
                hu ? "357 egyedi szóalak-kezelési kiegészítés a pontosabb címszókereséshez."
                   : "357 unique word-form handling additions for more accurate headword lookup.");
  } else if (currentPage == 2) {
    drawWrapped(UI_12_FONT_ID, hu ? "Magyar elválasztás" : "Hungarian hyphenation", true);
    y += bodyLineHeight;
    drawSection(hu ? "Kiterjesztett magyar elválasztás" : "Extended Hungarian hyphenation",
                hu ? "A magyar elválasztás Nagy Bence Huhyphn elválasztási mintáira épül, saját kiegészítésekkel és továbbfejlesztésekkel."
                   : "Hungarian hyphenation is based on Bence Nagy's Huhyphn patterns, with custom additions and improvements.");
    drawSection(hu ? "Dupla kettős mássalhangzók elválasztása" : "Long Hungarian multigraph consonants",
                hu ? "A dupla kettős mássalhangzók helyes magyar elválasztásának támogatása."
                   : "Support for correct Hungarian hyphenation of long multigraph consonants.");
    drawSection(hu ? "Beágyazott elválasztás (Soft hyphen)" : "Embedded hyphenation (Soft hyphen)",
                hu ? "Az EPUB-ban beágyazott feltételes elválasztási pontok támogatása és megfelelő megjelenítése, opcionálisan aktiválható funkcióként."
                   : "Support and correct display of conditional hyphenation points embedded in EPUB files, as an optional feature.");
    drawSection(hu ? "Elválasztási nyelvek" : "Hyphenation languages",
                hu ? "Angol és magyar nyelvű elválasztás támogatása. Más nyelvekhez a firmware nem tartalmaz elválasztási mintákat."
                   : "English and Hungarian hyphenation are supported. The firmware contains no hyphenation patterns for other languages.");
  } else {
    drawWrapped(UI_12_FONT_ID, hu ? "Sorkizárás és tipográfia" : "Justification and typography", true);
    y += bodyLineHeight;
    drawSection(hu ? "Javított sorkizárt szedés" : "Improved justified text",
                hu ? "A sorkizárt szöveg egyenletesebb megjelenítése, a túl nagy szóközök csökkentésével."
                   : "More even justified text by reducing excessively large word spaces.");
    drawSection(hu ? "Betűköz-korrekció" : "Letter-spacing correction",
                hu ? "A túl nagy szóközök mérséklése a betűköz finom növelésével. A korrekció mértéke az olvasó beállításaiban szabályozható."
                   : "Reduces excessive word spacing by subtly increasing letter spacing. The correction level is adjustable in reader settings.");
    drawSection(hu ? "Minimális szóköz" : "Minimum word spacing",
                hu ? "A sorkizárás során alkalmazható legkisebb szóköz 50–100% között állítható."
                   : "The minimum word spacing used for justification can be adjusted between 50–100%.");
    drawSection(hu ? "Párbeszédköz javítása" : "Dialogue spacing correction",
                hu ? "A párbeszédjeleket követő hiányzó vagy túl nagy szóközök automatikus korrekciója."
                   : "Automatically corrects missing or excessive spacing after dialogue marks.");
    drawSection(hu ? "Extra bekezdésköz" : "Extra paragraph spacing",
                hu ? "A bekezdések közötti térköz növelése a szöveg tagoltabb megjelenítéséhez."
                   : "Increases spacing between paragraphs for clearer text structure.");
    drawSection(hu ? "Optikai margó (Hanging punctuation)" : "Hanging punctuation",
                hu ? "Az írásjelek optikai margóba helyezésével egyenletesebb szövegszél alakítható ki."
                   : "Places punctuation into the optical margin for a more even text edge.");
  }

  const auto labels =
      mappedInput.mapLabels(tr(STR_BACK), "", currentPage > 0 ? "<" : "", currentPage + 1 < PAGE_COUNT ? ">" : "");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer();
}
