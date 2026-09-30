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

constexpr int PAGE_COUNT = 5;
constexpr int SIDE_PADDING = 20;

std::string hungarianEditionLabel() {
  const std::string buildId = CPHUN_BUILD_ID;
  const size_t firstDash = buildId.find('-');
  const size_t secondDash = firstDash == std::string::npos ? std::string::npos : buildId.find('-', firstDash + 1);
  const size_t thirdDash = secondDash == std::string::npos ? std::string::npos : buildId.find('-', secondDash + 1);
  if (secondDash == std::string::npos || thirdDash == std::string::npos || thirdDash <= secondDash + 1) {
    return "Hungarian Edition";
  }
  return "Hungarian Edition v." + buildId.substr(secondDash + 1, thirdDash - secondDash - 1);
}

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

  const auto drawMixedSection = [&](const char* title, const char* suffix, const char* text) {
    renderer.drawText(UI_12_FONT_ID, x, y, title, true, EpdFontFamily::BOLD);
    const int suffixX = x + renderer.getTextAdvanceX(UI_12_FONT_ID, title, EpdFontFamily::BOLD);
    renderer.drawText(UI_12_FONT_ID, suffixX, y, suffix);
    y += bodyLineHeight;
    drawWrapped(UI_12_FONT_ID, text);
    y += bodyLineHeight;
  };

  if (currentPage == 0) {
    const auto drawLabelValue = [&](const char* label, const char* value) {
      const std::string line = std::string(label) + ": " + value;
      drawWrapped(UI_12_FONT_ID, line.c_str());
    };

    drawLabelValue(tr(STR_CROSSPOINT_VERSION), CROSSPOINT_VERSION);
    const std::string editionLabel = hungarianEditionLabel();
    drawLabelValue(tr(STR_EDITION), editionLabel.c_str());
    drawWrapped(UI_12_FONT_ID, CPHUN_BUILD_ID);
    drawLabelValue(hu ? "Dátum" : "Date", CPHUN_BUILD_DATE);

    y += bodyLineHeight;
    drawWrapped(UI_12_FONT_ID, tr(STR_GITHUB_RELEASES), true);
    renderer.drawText(UI_10_FONT_ID, x, y, "github.com/Matteo1965/");
    y += linkLineHeight;
    renderer.drawText(UI_10_FONT_ID, x, y, "crosspoint-reader/releases");
    y += linkLineHeight + bodyLineHeight;

    drawWrapped(UI_12_FONT_ID, hu ? "A Hungarian Edition fő fejlesztései:" : "Key Hungarian Edition improvements:", true);
    const char* features[] = {
        hu ? "- Magyar felület, billentyűzet és Könyvtár" : "- Hungarian UI, keyboard and Library",
        hu ? "- Szótár, szótövezés és szerkesztés → 2. oldal" : "- Dictionary, stemming and editing → page 2",
        hu ? "- Kiterjesztett magyar elválasztás → 3. oldal" : "- Extended Hungarian hyphenation → page 3",
        hu ? "- Sorkizárás és optikai tipográfia → 4. oldal" : "- Justification and optical typography → page 4",
        hu ? "- Újdonságok, szinkron és főoldal → 5. oldal" : "- New features, sync and Home screen → page 5",
    };
    for (const char* feature : features) drawWrapped(UI_12_FONT_ID, feature);
  } else if (currentPage == 1) {
    drawWrapped(UI_12_FONT_ID, hu ? "Magyar szótár, szótövezés és szerkesztés"
                                  : "Hungarian dictionary, stemming and editing", true);
    y += bodyLineHeight;
    drawSection(hu ? "StarDict és ragozott szóalakok" : "StarDict and inflected forms",
                hu ? "Szabványos StarDict szótárak, továbbfejlesztett magyar címszókereséssel és szótövezéssel."
                   : "Standard StarDict dictionaries with improved Hungarian headword lookup and stemming.");
    drawSection(hu ? "Kijelölés és szerkesztés" : "Highlight and edit",
                hu ? "Szavak kijelölése, javítása magyar billentyűzettel, valamint a módok közvetlen váltása."
                   : "Word highlighting and correction with the Hungarian keyboard, with direct mode switching.");
    drawSection(hu ? "TSV export" : "TSV export",
                hu ? "A megjelölt és szerkesztett bejegyzések exportálhatók további EPUB-javításhoz."
                   : "Highlighted and edited entries can be exported for later EPUB correction.");
  } else if (currentPage == 2) {
    drawWrapped(UI_12_FONT_ID, hu ? "Magyar elválasztás" : "Hungarian hyphenation", true);
    y += bodyLineHeight;
    drawSection(hu ? "Kiterjesztett magyar elválasztás" : "Extended Hungarian hyphenation",
                hu ? "Huhyphn minták saját kiegészítésekkel, a hosszú többjegyű mássalhangzók és magyar kivételek kezelésével."
                   : "Huhyphn patterns with custom extensions for long multigraph consonants and Hungarian exceptions.");
    drawSection(hu ? "Elválasztási küszöb" : "Hyphenation threshold",
                hu ? "A szó elején és végén megtartandó minimum 1-1, 1-2, 2-2, 2-3 vagy 3-3 értékre állítható."
                   : "Minimum prefix/suffix can be set to 1-1, 1-2, 2-2, 2-3 or 3-3.");
    drawSection(hu ? "Soft hyphen és rövid elválasztójel" : "Soft hyphen and short hyphen",
                hu ? "Beágyazott feltételes elválasztás és opcionális rövid elválasztójel SD-kártyás fontokhoz is."
                   : "Embedded conditional hyphenation and optional short hyphen, including SD-card fonts.");
  } else if (currentPage == 3) {
    drawWrapped(UI_12_FONT_ID, hu ? "Sorkizárás és tipográfia" : "Justification and typography", true);
    y += bodyLineHeight;
    drawSection(hu ? "Betűköz-korrekció és optimalizálás" : "Letter-spacing correction and optimization",
                hu ? "Több fokozatban csökkenti a túl nagy szóközöket; betűpár- és ABA/AA-védelemmel."
                   : "Multi-level reduction of excessive word spacing with pair and ABA/AA protection.");
    drawSection(hu ? "Optikai margó és sorvég-korrekció" : "Optical margin and line-end correction",
                hu ? "Írásjelek optikai kilógatása és a sorvég látható tintaszélének finom, legfeljebb 8 px-es korrekciója."
                   : "Hanging punctuation and fine visible-ink line-end correction up to 8 px.");
    drawSection(hu ? "Szóköz, párbeszéd és bekezdés" : "Spacing, dialogue and paragraphs",
                hu ? "Állítható minimális szóköz, párbeszédköz-javítás és extra bekezdésköz."
                   : "Adjustable minimum word spacing, dialogue-spacing repair and extra paragraph spacing.");
  } else {
    drawWrapped(UI_12_FONT_ID, hu ? "Újdonságok és javítások" : "New features and fixes", true);
    y += bodyLineHeight;
    const char* updates[] = {
        hu ? "- Könyvtár nézet és Borítórács főoldal" : "- Library view and Cover Grid home",
        hu ? "- KOReader szinkron és rejtett EPUB-elemek" : "- KOReader sync and hidden EPUB elements",
        hu ? "- Továbbfejlesztett lábjegyzet-kezelés" : "- Improved footnote handling",
        hu ? "- Fejezet újraindexelése és beállításmentés" : "- Chapter reindexing and settings persistence",
        hu ? "- SD-font memória- és gyorsítótár-javítások" : "- SD-font memory and cache improvements",
        hu ? "- X4 és X4 Classic kompatibilitás" : "- X4 and X4 Classic compatibility",
    };
    for (const char* update : updates) drawWrapped(UI_12_FONT_ID, update);

    y += bodyLineHeight;
    drawWrapped(UI_12_FONT_ID, "CrossPoint 1.6.5:", true);
    const char* releaseUpdates[] = {
        hu ? "- Rövid gombnyomás és lista-újrarajzolás javítások" : "- Short-press and list-redraw fixes",
        hu ? "- Alvóképernyő átlátszóság és fejezetpozíció" : "- Sleep-screen transparency and chapter position",
        hu ? "- Stabilitási és kompatibilitási javítások" : "- Stability and compatibility fixes",
    };
    for (const char* update : releaseUpdates) drawWrapped(UI_12_FONT_ID, update);
  }

  const auto labels =
      mappedInput.mapLabels(tr(STR_BACK), "", currentPage > 0 ? "<" : "", currentPage + 1 < PAGE_COUNT ? ">" : "");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer();
}
