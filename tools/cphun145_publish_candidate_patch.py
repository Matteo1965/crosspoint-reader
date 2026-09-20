from pathlib import Path
import re

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, text):
    Path(path).write_text(text, encoding="utf-8")

def replace_once(path, old, new, label):
    s = read(path)
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"CPHUN-145 {label}: expected 1 match, found {n}")
    write(path, s.replace(old, new, 1))

# ---------------------------------------------------------------------------
# Footnote popup: extend 40 px downward only, normalize title marker to digits,
# and show a small drawn down-arrow while more body text remains.
# ---------------------------------------------------------------------------
p = "src/activities/reader/FootnotePopupActivity.cpp"
s = read(p)

if "constexpr int POPUP_TOP_REFERENCE_HEIGHT" not in s:
    s = s.replace(
        "constexpr int POPUP_HEIGHT = 640;\n",
        "constexpr int POPUP_HEIGHT = 680;\nconstexpr int POPUP_TOP_REFERENCE_HEIGHT = 640;\n",
        1,
    )
else:
    raise SystemExit("CPHUN-145 popup constants already patched")

# Keep the #144 top edge and grow only downwards.
s = s.replace(
    "const int popupY = std::max(0, (screenH - popupH) / 2 - 40);",
    "const int popupY = std::max(0, (screenH - POPUP_TOP_REFERENCE_HEIGHT) / 2 - 40);",
    1,
)

# Numeric-only display label, without changing navigation/source identity.
helper_anchor = '''std::string stripRepeatedFootnoteMarker(std::string text, const std::string& label) {
'''
helper_pos = s.find(helper_anchor)
if helper_pos < 0:
    raise SystemExit("CPHUN-145 footnote marker helper anchor missing")

# Insert helper immediately before stripRepeatedFootnoteMarker.
numeric_helper = r'''std::string footnoteNumberOnly(const std::string& label) {
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

'''
s = s[:helper_pos] + numeric_helper + s[helper_pos:]

old_title = 'const std::string title = label_.empty() ? "Lábjegyzet" : "Lábjegyzet {" + label_ + "}";'
new_title = '''const std::string number = footnoteNumberOnly(label_);
  const std::string title = number.empty() ? "Lábjegyzet" : "Lábjegyzet {" + number + "}";'''
if s.count(old_title) != 1:
    raise SystemExit(f"CPHUN-145 popup title anchor count={s.count(old_title)}")
s = s.replace(old_title, new_title, 1)

arrow_anchor = '''  const bool canUp = firstLine_ > 0;
  const bool canDown = firstLine_ + visibleLines < static_cast<int>(lines_.size());
  const auto labels = mappedInput.mapLabels(
'''
arrow_replacement = '''  const bool canUp = firstLine_ > 0;
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
'''
if s.count(arrow_anchor) != 1:
    raise SystemExit(f"CPHUN-145 continuation arrow anchor count={s.count(arrow_anchor)}")
s = s.replace(arrow_anchor, arrow_replacement, 1)

write(p, s)

# ---------------------------------------------------------------------------
# CrossPoint Version pages: compact paragraph spacing on pages 2..5 and update
# pages 4/5 + 5/5 with current Hungarian Edition features.
# ---------------------------------------------------------------------------
p = "src/activities/settings/CrossPointVersionActivity.cpp"
s = read(p)
if "#include <algorithm>" not in s:
    s = s.replace("#include <cstdio>\\n", "#include <algorithm>\\n#include <cstdio>\\n", 1)

old = '''  const int bodyLineHeight = renderer.getLineHeight(UI_12_FONT_ID);
  const int linkLineHeight = renderer.getLineHeight(UI_10_FONT_ID);
  const bool hu = I18N.getLanguage() == Language::HU;
'''
new = '''  const int bodyLineHeight = renderer.getLineHeight(UI_12_FONT_ID);
  const int linkLineHeight = renderer.getLineHeight(UI_10_FONT_ID);
  const bool hu = I18N.getLanguage() == Language::HU;
  // Page 1 keeps its existing generous spacing; pages 2..5 use half the
  // paragraph gap to make room for the expanded Hungarian Edition notes.
  const int paragraphSpacing = currentPage == 0 ? bodyLineHeight : std::max(1, bodyLineHeight / 2);
'''
if s.count(old) != 1:
    raise SystemExit("CPHUN-145 version spacing setup anchor mismatch")
s = s.replace(old, new, 1)

# Only the extra gap at the end of sections changes; line height stays untouched.
s = s.replace(
    '''    drawWrapped(UI_12_FONT_ID, text);
    y += bodyLineHeight;
  };

  const auto drawMixedSection''',
    '''    drawWrapped(UI_12_FONT_ID, text);
    y += paragraphSpacing;
  };

  const auto drawMixedSection''',
    1,
)
s = s.replace(
    '''    drawWrapped(UI_12_FONT_ID, text);
    y += bodyLineHeight;
  };

  if (currentPage == 0)''',
    '''    drawWrapped(UI_12_FONT_ID, text);
    y += paragraphSpacing;
  };

  if (currentPage == 0)''',
    1,
)

# Page-specific standalone paragraph gaps on pages 2..5.
s = s.replace(
    '''    y += bodyLineHeight;
    drawSection(hu ? "Javított magyar szótárkezelés"''',
    '''    y += paragraphSpacing;
    drawSection(hu ? "Javított magyar szótárkezelés"''',
    1,
)
s = s.replace(
    '''    y += bodyLineHeight;
    drawSection(hu ? "Kiterjesztett magyar elválasztás"''',
    '''    y += paragraphSpacing;
    drawSection(hu ? "Kiterjesztett magyar elválasztás"''',
    1,
)
s = s.replace(
    '''    y += bodyLineHeight;
    drawSection(hu ? "Javított sorkizárt szedés"''',
    '''    y += paragraphSpacing;
    drawSection(hu ? "Javított sorkizárt szedés"''',
    1,
)
s = s.replace(
    '''    y += bodyLineHeight;
    const char* updates[] = {''',
    '''    y += paragraphSpacing;
    const char* updates[] = {''',
    1,
)
s = s.replace(
    '''    y += bodyLineHeight;
    drawWrapped(UI_12_FONT_ID, "CrossPoint 1.6.0:", true);''',
    '''    y += paragraphSpacing;
    drawWrapped(UI_12_FONT_ID, "CrossPoint 1.6.0:", true);''',
    1,
)

old_page4 = '''    drawSection(hu ? "Javított sorkizárt szedés" : "Improved justified text",
                hu ? "Egyenletesebb szövegkép a túl nagy szóközök csökkentésével."
                   : "More even text by reducing excessively large word spaces.");
    drawSection(hu ? "Betűköz-korrekció" : "Letter-spacing correction",
                hu ? "A túl nagy szóközök mérséklése a betűköz finom növelésével."
                   : "Reduces excessive word spacing by subtly increasing letter spacing.");
    drawSection(hu ? "Szó- és párbeszédközök" : "Word and dialogue spacing",
                hu ? "A minimális szóköz 50–100% között állítható, a hibás párbeszédközök automatikusan javíthatók."
                   : "Minimum word spacing is adjustable between 50–100%, and incorrect dialogue spacing can be corrected automatically.");
    drawSection(hu ? "Extra bekezdésköz" : "Extra paragraph spacing",
                hu ? "A bekezdések közötti térköz növelése."
                   : "Increases spacing between paragraphs.");
    if (hu) {
      drawMixedSection("Optikai margó", " (Hanging punctuation)",
                       "Az írásjelek margóba helyezésével egyenletesebb szövegszélek.");
    } else {
      drawSection("Hanging punctuation",
                  "Places punctuation into the margin for a more even text edge.");
    }'''
new_page4 = '''    drawSection(hu ? "Javított sorkizárt szedés" : "Improved justified text",
                hu ? "Egyenletesebb szövegkép a túl nagy szóközök csökkentésével."
                   : "More even text by reducing excessively large word spaces.");
    drawSection(hu ? "Betűköz-korrekció" : "Letter-spacing correction",
                hu ? "A túl nagy szóközök mérséklése a betűköz finom növelésével."
                   : "Reduces excessive word spacing by subtly increasing letter spacing.");
    drawSection(hu ? "Betűköz-optimalizálás" : "Letter-spacing optimization",
                hu ? "Font- és betűpár-alapú korrekció, állítható optimalizációs küszöbbel."
                   : "Font- and letter-pair-based correction with an adjustable optimization threshold.");
    drawSection(hu ? "Szó- és párbeszédközök" : "Word and dialogue spacing",
                hu ? "A minimális szóköz szabályozható, a hibás párbeszédközök automatikusan javíthatók."
                   : "Minimum word spacing is adjustable, and incorrect dialogue spacing can be corrected automatically.");
    drawSection(hu ? "Sorköz és bekezdésköz" : "Line and paragraph spacing",
                hu ? "A sorköz 6 fokozatban állítható, és extra bekezdésköz is megadható."
                   : "Line spacing is adjustable in 6 steps, with optional extra paragraph spacing.");
    if (hu) {
      drawMixedSection("Optikai margó", " (Hanging punctuation)",
                       "Az írásjelek margóba helyezésével egyenletesebb szövegszélek.");
    } else {
      drawSection("Hanging punctuation",
                  "Places punctuation into the margin for a more even text edge.");
    }'''
if s.count(old_page4) != 1:
    raise SystemExit(f"CPHUN-145 page 4 block matches={s.count(old_page4)}")
s = s.replace(old_page4, new_page4, 1)

old_updates = '''    const char* updates[] = {
        hu ? "- Magyar billentyűzet" : "- Hungarian keyboard",
        hu ? "- Opcionális rövid / hosszú elválasztójel" : "- Optional short / long hyphen",
        hu ? "- Alsó gombok beállítása: 1×, 2× és Hosszú nyomás" : "- Bottom button setup: 1×, 2× and Long press",
        hu ? "- Sorköz 6 fokozatban állítható" : "- Line spacing adjustable in 6 steps",
        hu ? "- Automatikus Fejezet generálás" : "- Automatic Chapter generation",
    };'''
new_updates = '''    const char* updates[] = {
        hu ? "- Magyar billentyűzet" : "- Hungarian keyboard",
        hu ? "- Megjelölés és Szerkesztés mód" : "- Highlight and Edit modes",
        hu ? "- Mód választó: Szótár / Megjelölés / Szerkesztés" : "- Mode selector: Dictionary / Highlight / Edit",
        hu ? "- Szerkesztések exportálása TSV fájlba" : "- Export edits to TSV",
        hu ? "- Továbbfejlesztett lábjegyzet-kezelés" : "- Improved footnote handling",
        hu ? "- Több lábjegyzet kezelése és közvetlen megnyitása" : "- Multiple footnotes and direct opening",
        hu ? "- Alsó gombok: 1× / 2× / Hosszú nyomás" : "- Bottom buttons: 1× / 2× / Long press",
        hu ? "- Automatikus fejezetgenerálás" : "- Automatic chapter generation",
    };'''
if s.count(old_updates) != 1:
    raise SystemExit(f"CPHUN-145 page 5 updates matches={s.count(old_updates)}")
s = s.replace(old_updates, new_updates, 1)

write(p, s)

print("CPHUN-145 applied: 680px downward footnote popup + numeric title + continuation arrow + refreshed compact version pages")
