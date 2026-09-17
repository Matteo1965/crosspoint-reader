from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-135r4a: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_after(path, marker, addition):
    replace_once(path, marker, marker + addition)


# -----------------------------------------------------------------------------
# 1) Full logical word rendering for line-end hyphenated words.
#    A stored highlight/edit anchor spans the full logical source range. Render
#    every visible word fragment whose source offset falls inside that range,
#    instead of matching only the first fragment's exact offset.
# -----------------------------------------------------------------------------
replace_once(
    "src/highlights/HighlightRenderer.cpp",
    '''      HighlightAnchor anchor;
      anchor.spineIndex = spineIndex;
      anchor.visibleTextOffset = block->wordVisibleTextOffset(i);
      if (!store.contains(anchor)) continue;''',
    '''      const uint32_t wordOffset = block->wordVisibleTextOffset(i);
      bool highlighted = false;
      for (const auto& anchor : store.items()) {
        const uint32_t end = anchor.visibleTextOffset + anchor.length;
        if (anchor.spineIndex == spineIndex && wordOffset >= anchor.visibleTextOffset && wordOffset < end) {
          highlighted = true;
          break;
        }
      }
      if (!highlighted) continue;''',
)

replace_once(
    "src/highlights/TextEditRenderer.cpp",
    '''    for (uint16_t i = 0; i < block->wordCount(); ++i) {
      if (!store.find(spineIndex, block->wordVisibleTextOffset(i))) continue;''',
    '''    for (uint16_t i = 0; i < block->wordCount(); ++i) {
      const uint32_t wordOffset = block->wordVisibleTextOffset(i);
      bool edited = false;
      for (const auto& edit : store.items()) {
        const uint32_t end = edit.visibleTextOffset + edit.length;
        if (edit.spineIndex == spineIndex && wordOffset >= edit.visibleTextOffset && wordOffset < end) {
          edited = true;
          break;
        }
      }
      if (!edited) continue;''',
)


# -----------------------------------------------------------------------------
# 2) Quotes / glued footnotes.
#
# Hyphenation: the existing processing-copy footnote stripper recognises [12].
# Extend it to {12}; this lets CPHUN-66 see the alphabetic suffix in e.g.
# „őssikoly”-album.{2} and keeps all original visible text untouched.
# -----------------------------------------------------------------------------
replace_once(
    "lib/Epub/Epub/hyphenation/HyphenationCommon.cpp",
    '''      if (pos >= 0 && cps[pos].value == '[' && end - pos > 1) {
        cps.erase(cps.begin() + pos, cps.end());
      }''',
    '''      if (pos >= 0 && (cps[pos].value == '[' || cps[pos].value == '{') && end - pos > 1) {
        cps.erase(cps.begin() + pos, cps.end());
      }''',
)

# Editing/marking: keep tightly attached opening/closing quotation marks as part
# of the original visible edit range, but exclude trailing sentence punctuation
# and a glued [n] / {n} footnote annotation. Dictionary lookup continues to use
# its own logical/normalised representation.
insert_after(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''uint16_t visibleCodepointLength(const char* text) {
  if (!text) return 0;
  const auto* p = reinterpret_cast<const uint8_t*>(text);
  uint16_t count = 0;
  while (*p && count != UINT16_MAX) {
    utf8NextCodepoint(&p);
    ++count;
  }
  return count;
}
''',
    '''
void trimSelectionTrailingAnnotation(std::string& text) {
  const auto trimSentencePunctuation = [&]() {
    while (!text.empty()) {
      const char c = text.back();
      if (c == '.' || c == ',' || c == '!' || c == '?' || c == ';' || c == ':')
        text.pop_back();
      else
        break;
    }
  };

  trimSentencePunctuation();
  if (!text.empty() && (text.back() == '}' || text.back() == ']')) {
    const char close = text.back();
    const char open = close == '}' ? '{' : '[';
    size_t p = text.size() - 1;
    const size_t digitsEnd = p;
    while (p > 0 && text[p - 1] >= '0' && text[p - 1] <= '9') --p;
    if (p < digitsEnd && p > 0 && text[p - 1] == open) text.resize(p - 1);
  }
  trimSentencePunctuation();
}
''',
)

replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''  result.text = logicalWordText(selected);
  result.length = visibleCodepointLength(result.text.c_str());
  return result;''',
    '''  result.text = logicalWordText(selected);
  trimSelectionTrailingAnnotation(result.text);
  result.length = visibleCodepointLength(result.text.c_str());
  return result;''',
)


# -----------------------------------------------------------------------------
# 6) Hungarian keyboard labels follow the active layer.
#    Default layer displays lowercase; Shift already selects the uppercase rows;
#    fn already selects the symbol rows.
# -----------------------------------------------------------------------------
layout = "src/activities/util/HungarianKeyboardLayout.h"
replace_once(
    layout,
    '''inline const fui::KeyboardKey ROW1[] = {
    HUK("Q", "q", 'q'), HUK("W", "w", 'w'), HUK("E", "e", 'e'), HUK("R", "r", 'r'),
    HUK("T", "t", 't'), HUK("Z", "z", 'z'), HUK("U", "u", 'u'), HUK("I", "i", 'i'),
    HUK("O", "o", 'o'), HUK("P", "p", 'p'), HUK("Ö", "ö", 1303)};''',
    '''inline const fui::KeyboardKey ROW1[] = {
    HUK("q", "q", 'q'), HUK("w", "w", 'w'), HUK("e", "e", 'e'), HUK("r", "r", 'r'),
    HUK("t", "t", 't'), HUK("z", "z", 'z'), HUK("u", "u", 'u'), HUK("i", "i", 'i'),
    HUK("o", "o", 'o'), HUK("p", "p", 'p'), HUK("ö", "ö", 1303)};''',
)
replace_once(
    layout,
    '''inline const fui::KeyboardKey ROW2[] = {
    HUK("A", "a", 'a'), HUK("S", "s", 's'), HUK("D", "d", 'd'), HUK("F", "f", 'f'),
    HUK("G", "g", 'g'), HUK("H", "h", 'h'), HUK("J", "j", 'j'), HUK("K", "k", 'k'),
    HUK("L", "l", 'l'), HUK("É", "é", 1301), HUK("Á", "á", 1302)};''',
    '''inline const fui::KeyboardKey ROW2[] = {
    HUK("a", "a", 'a'), HUK("s", "s", 's'), HUK("d", "d", 'd'), HUK("f", "f", 'f'),
    HUK("g", "g", 'g'), HUK("h", "h", 'h'), HUK("j", "j", 'j'), HUK("k", "k", 'k'),
    HUK("l", "l", 'l'), HUK("é", "é", 1301), HUK("á", "á", 1302)};''',
)
replace_once(
    layout,
    '''    HUK("Y", "y", 'y'), HUK("X", "x", 'x'), HUK("C", "c", 'c'), HUK("V", "v", 'v'),
    HUK("B", "b", 'b'), HUK("N", "n", 'n'), HUK("M", "m", 'm'), HUK("Ü", "ü", 1304),''',
    '''    HUK("y", "y", 'y'), HUK("x", "x", 'x'), HUK("c", "c", 'c'), HUK("v", "v", 'v'),
    HUK("b", "b", 'b'), HUK("n", "n", 'n'), HUK("m", "m", 'm'), HUK("ü", "ü", 1304),''',
)


# -----------------------------------------------------------------------------
# 7) Szerkesztés opens with Backspace selected.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/util/KeyboardEntryActivity.cpp",
    '''  interactionsReady = false;
  requestUpdate();''',
    '''  interactionsReady = false;
  if (title == "Szerkesztés") syncSelectionToValue(fui::QWERTY_KEY_BACKSPACE);
  requestUpdate();''',
)


# -----------------------------------------------------------------------------
# 8) Szerkesztés help block: move 60 px downward, use Hungarian control names,
#    and explain the right-side Up/Down buttons and their mode transition.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/util/KeyboardEntryActivity.cpp",
    '''  if (tipCount > 0) {
    int y = (underlineBottom + kbRect.y) / 2 - (tipCount + 1) * tipsLh / 2;
    drawTip(tr(STR_KB_TIPS), y);
    y += tipsLh;
    if (cursorMode) {''',
    '''  if (title == "Szerkesztés") {
    int y = (underlineBottom + kbRect.y) / 2 - 5 * tipsLh / 2 + 60;
    drawTip("Tippek:", y);
    y += tipsLh;
    drawTip("KIJELÖLÉS: aktuális gomb használata", y);
    y += tipsLh;
    drawTip("SHIFT: billentyűsor váltása", y);
    y += tipsLh;
    drawTip("FEL HOSSZAN: kurzor mód", y);
    y += tipsLh;
    drawTip("LE: billentyűzet mód", y);
    y += tipsLh;
    drawTip("TÖRLÉS HOSSZAN: teljes szó törlése", y);
  } else if (tipCount > 0) {
    int y = (underlineBottom + kbRect.y) / 2 - (tipCount + 1) * tipsLh / 2;
    drawTip(tr(STR_KB_TIPS), y);
    y += tipsLh;
    if (cursorMode) {''',
)


# Build identity. No Search-mode unification and no empty-replacement deletion
# are included in this validation build; those remain deliberately deferred.
replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260916-128B-EXP"',
    '#define CPHUN_BUILD_ID "CPHUN-260917-135R4A-EXP"',
)

print("CPHUN-135r4a applied: points 1, 2, 6, 7 and 8 only")
