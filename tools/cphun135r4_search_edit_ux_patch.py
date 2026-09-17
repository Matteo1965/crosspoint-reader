from pathlib import Path
import re


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-135r4: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_after(path, marker, addition):
    replace_once(path, marker, marker + addition)


# -----------------------------------------------------------------------------
# 1) Reader menu: one shared Search entry, controlled by a persistent-in-session
#    mode selector directly above it. Existing Highlight/Edit actions remain as
#    internal dispatch targets so the reader-side code stays stable.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.h",
    "    DICTIONARY,\n    HIGHLIGHT,\n    EDIT,\n    MANUAL_DICTIONARY_SEARCH,",
    "    SEARCH_MODE,\n    DICTIONARY,\n    HIGHLIGHT,\n    EDIT,\n    MANUAL_DICTIONARY_SEARCH,",
)

replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    "namespace fui = freeink::ui;\n",
    '''namespace fui = freeink::ui;

namespace {
int selectedSearchMode = 0;
const char* const SEARCH_MODE_LABELS[] = {"Szótár", "Szerkesztés", "Megjelölés"};
}  // namespace
''',
)

replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '''  items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótári keresés"});
  items.push_back({MenuAction::HIGHLIGHT, StrId::STR_LOOKUP, "Kiemelés"});
  items.push_back({MenuAction::EDIT, StrId::STR_LOOKUP, "Szerkesztés"});
  items.push_back({MenuAction::MANUAL_DICTIONARY_SEARCH, StrId::STR_LOOKUP, "Kézi keresés"});''',
    '''  items.push_back({MenuAction::SEARCH_MODE, StrId::STR_LOOKUP, "Mód választó"});
  items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Keresés"});
  items.push_back({MenuAction::MANUAL_DICTIONARY_SEARCH, StrId::STR_LOOKUP, "Kézi keresés"});''',
)

replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '''  const auto selectedAction = items[index].action;
  if (selectedAction == MenuAction::ROTATE_SCREEN) {''',
    '''  const auto selectedAction = items[index].action;
  if (selectedAction == MenuAction::SEARCH_MODE) {
    optionPopup.show("Mód választó", SEARCH_MODE_LABELS, 3, selectedSearchMode, [this](int idx) {
      if (idx >= 0 && idx < 3) selectedSearchMode = idx;
      requestUpdate();
    });
    requestUpdate();
    return;
  }
  if (selectedAction == MenuAction::ROTATE_SCREEN) {''',
)

replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '''  setResult(MenuResult{static_cast<int>(selectedAction), pendingOrientation, selectedPageTurnOption});
  finish();''',
    '''  MenuAction resultAction = selectedAction;
  if (selectedAction == MenuAction::DICTIONARY) {
    if (selectedSearchMode == 1)
      resultAction = MenuAction::EDIT;
    else if (selectedSearchMode == 2)
      resultAction = MenuAction::HIGHLIGHT;
  }
  setResult(MenuResult{static_cast<int>(resultAction), pendingOrientation, selectedPageTurnOption});
  finish();''',
)

replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '''    if (action == MenuAction::ROTATE_SCREEN) {
      menuRowItems[i].value = I18N.get(orientationLabels[pendingOrientation]);''',
    '''    if (action == MenuAction::SEARCH_MODE) {
      menuRowItems[i].value = SEARCH_MODE_LABELS[selectedSearchMode];
    } else if (action == MenuAction::ROTATE_SCREEN) {
      menuRowItems[i].value = I18N.get(orientationLabels[pendingOrientation]);''',
)


# -----------------------------------------------------------------------------
# 2) Logical selection anchors: persistent Highlight/Edit rendering must cover
#    every visual fragment whose source offset lies inside the logical word.
#    This fixes e.g. Fel- / szippantottunk being marked only on the first line.
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

# Preserve tightly attached quotes for editing/marking, but exclude trailing
# sentence punctuation and a glued [n] / {n} footnote marker from the anchor.
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
  if (text.empty()) return;
  auto stripFootnote = [&](const char open, const char close) {
    if (text.empty() || text.back() != close) return false;
    size_t p = text.size() - 1;
    size_t digitsEnd = p;
    while (p > 0 && text[p - 1] >= '0' && text[p - 1] <= '9') --p;
    if (p == digitsEnd || p == 0 || text[p - 1] != open) return false;
    text.resize(p - 1);
    return true;
  };
  stripFootnote('{', '}') || stripFootnote('[', ']');
  while (!text.empty()) {
    const char c = text.back();
    if (c == '.' || c == ',' || c == '!' || c == '?' || c == ';' || c == ':')
      text.pop_back();
    else
      break;
  }
}
''',
)

replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''  result.text = logicalWordText(selected);
  result.length = visibleCodepointLength(result.text.c_str());
  return result;''',
    '''  result.text = logicalWordText(selected);
  // Keep opening/closing quotation marks that belong to the visible token.
  // A trailing footnote link marker such as {2}, and sentence punctuation
  // following the token, are deliberately outside the edit/highlight anchor.
  trimSelectionTrailingAnnotation(result.text);
  result.length = visibleCodepointLength(result.text.c_str());
  return result;''',
)


# -----------------------------------------------------------------------------
# 3) Empty replacement means delete. Keep the anchor identity on the selected
#    word and persist an automatic adjacent-space cleanup policy for the later
#    physical EPUB rewrite stage (prefer following whitespace, else preceding).
# -----------------------------------------------------------------------------
replace_once(
    "src/highlights/TextEditStore.h",
    '''  std::string originalText;
  std::string replacementText;
};''',
    '''  std::string originalText;
  std::string replacementText;
  bool trimAdjacentSpace = false;
};''',
)
replace_once(
    "src/highlights/TextEditStore.cpp",
    '''    edit.originalText = item["original"] | "";
    edit.replacementText = item["replacement"] | "";
    edits_.push_back(std::move(edit));''',
    '''    edit.originalText = item["original"] | "";
    edit.replacementText = item["replacement"] | "";
    edit.trimAdjacentSpace = item["trimAdjacentSpace"] | false;
    edits_.push_back(std::move(edit));''',
)
replace_once(
    "src/highlights/TextEditStore.cpp",
    '''    item["original"] = edit.originalText;
    item["replacement"] = edit.replacementText;
  }''',
    '''    item["original"] = edit.originalText;
    item["replacement"] = edit.replacementText;
    item["trimAdjacentSpace"] = edit.trimAdjacentSpace;
  }''',
)
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    if (const auto* old = textEditStore->find(selection.spineIndex, selection.visibleTextOffset)) {
      if (!old->replacementText.empty()) initialText = old->replacementText;
    }''',
    '''    if (const auto* old = textEditStore->find(selection.spineIndex, selection.visibleTextOffset)) {
      initialText = old->replacementText;
    }''',
)
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''          if (const auto* keyboard = std::get_if<KeyboardResult>(&result.data)) {
            if (!keyboard->text.empty() && textEditStore) {
              textEditStore->upsert({selection.spineIndex, selection.visibleTextOffset, selection.length,
                                     selection.text, keyboard->text});
            }
          }''',
    '''          if (const auto* keyboard = std::get_if<KeyboardResult>(&result.data)) {
            if (textEditStore) {
              textEditStore->upsert({selection.spineIndex, selection.visibleTextOffset, selection.length,
                                     selection.text, keyboard->text, keyboard->text.empty()});
            }
          }''',
)


# -----------------------------------------------------------------------------
# 4) Hungarian keyboard editing UX: lower-case labels by default, upper-case
#    only while Shift is active, symbols while fn is active; Backspace is the
#    initial selected key on the Szerkesztés screen.
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

replace_once(
    "src/activities/util/KeyboardEntryActivity.cpp",
    '''  interactionsReady = false;
  requestUpdate();''',
    '''  interactionsReady = false;
  if (title == "Szerkesztés") {
    syncSelectionToValue(fui::QWERTY_KEY_BACKSPACE);
  }
  requestUpdate();''',
)

# Szerkesztés-specific help: move 50 px downward and describe the physical
# up/down buttons and their keyboard/cursor mode transition in Hungarian.
replace_once(
    "src/activities/util/KeyboardEntryActivity.cpp",
    '''  if (tipCount > 0) {
    int y = (underlineBottom + kbRect.y) / 2 - (tipCount + 1) * tipsLh / 2;
    drawTip(tr(STR_KB_TIPS), y);''',
    '''  if (title == "Szerkesztés") {
    int y = (underlineBottom + kbRect.y) / 2 - 5 * tipsLh / 2 + 50;
    drawTip("Tippek:", y);
    y += tipsLh;
    drawTip("KIJELÖLÉS: a kijelölt billentyű használata", y);
    y += tipsLh;
    drawTip("Fel/le: billentyűsor váltása", y);
    y += tipsLh;
    drawTip("Fel hosszan: kurzor mód; Le: billentyűzet mód", y);
    y += tipsLh;
    drawTip("TÖRLÉS: karakter törlése; hosszan: teljes szó", y);
  } else if (tipCount > 0) {
    int y = (underlineBottom + kbRect.y) / 2 - (tipCount + 1) * tipsLh / 2;
    drawTip(tr(STR_KB_TIPS), y);''',
)


# -----------------------------------------------------------------------------
# 5) Hyphenation: {2} style footnote markers must be removed from the processing
#    copy just like [2], otherwise quoted-suffix normalization rejects the token.
# -----------------------------------------------------------------------------
replace_once(
    "lib/Epub/Epub/hyphenation/HyphenationCommon.cpp",
    "      if (pos >= 0 && cps[pos].value == '[' && end - pos > 1) {",
    "      if (pos >= 0 && (cps[pos].value == '[' || cps[pos].value == '{') && end - pos > 1) {",
)

# Build identity after the 128B experiment patch has changed r3 -> 128B.
replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260916-128B-EXP"',
    '#define CPHUN_BUILD_ID "CPHUN-260917-135-EXP-r4"',
)

print("CPHUN-135r4 search/edit UX patch applied")
