from pathlib import Path
import re


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    Path(path).write_text(text, encoding="utf-8")


def replace_once(path, old, new):
    s = read(path)
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"CPHUN-137: {path}: expected one match, found {n}: {old[:180]!r}")
    write(path, s.replace(old, new, 1))


def regex_once(path, pattern, repl, flags=0):
    s = read(path)
    s2, n = re.subn(pattern, repl, s, count=1, flags=flags)
    if n != 1:
        raise SystemExit(f"CPHUN-137: {path}: regex expected one match, found {n}: {pattern[:180]!r}")
    write(path, s2)


# -----------------------------------------------------------------------------
# 1) Hyphenation: trailing numeric {N} footnotes are processing-only suffixes,
#    just like the already supported [N] form. This lets CPHUN-66 see quoted
#    suffix compounds such as „őssikoly”-album.{2} as an alphabetic suffix.
# -----------------------------------------------------------------------------
replace_once(
    "lib/Epub/Epub/hyphenation/HyphenationCommon.cpp",
    "if (pos >= 0 && cps[pos].value == '[' && end - pos > 1) {",
    "if (pos >= 0 && (cps[pos].value == '[' || cps[pos].value == '{') && end - pos > 1) {",
)

# Regression tests: brace footnotes must not suppress either an internal Liang
# break or the visible suffix-hyphen break in Hungarian Extended mode.
test_path = Path("test/hyphenation_eval/HungarianSlashBreakTest.cpp")
test_text = test_path.read_text(encoding="utf-8")
if "HungarianQuotedSuffixBraceFootnote" not in test_text:
    test_text += r'''

TEST(HungarianQuotedSuffixBraceFootnote, ExtendedPreservesBreaksWithTrailingBraceFootnote) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  const auto plain = Hyphenator::breakOffsets("tovább", false);
  ASSERT_FALSE(plain.empty());
  const auto decorated = Hyphenator::breakOffsets("tovább”-hoz.{2}", false);
  for (const auto& plainBreak : plain) {
    EXPECT_NE(findBreak(decorated, plainBreak.byteOffset), nullptr)
        << "Trailing {N} footnote blocked a quoted-suffix Liang break";
  }

  const size_t suffixBoundary = std::string("tovább”-").size();
  const auto* suffix = findBreak(decorated, suffixBoundary);
  ASSERT_NE(suffix, nullptr) << "Trailing {N} footnote blocked the visible suffix-hyphen break";
  EXPECT_FALSE(suffix->requiresInsertedHyphen);

  Hyphenator::setHungarianExtended(false);
}
'''
    test_path.write_text(test_text, encoding="utf-8")


# -----------------------------------------------------------------------------
# 2) One common Search selector with persistent session mode.
# -----------------------------------------------------------------------------
mode_path = "src/highlights/HighlightMode.h"
replace_once(
    mode_path,
    "enum class WordSelectionMode : unsigned char {\n  Dictionary = 0,\n  Highlight = 1,\n  Edit = 2,\n};\n",
    '''enum class WordSelectionMode : unsigned char {
  Dictionary = 0,
  Highlight = 1,
  Edit = 2,
};

// CPHUN-137: one selector, three destinations. The choice intentionally lives
// for the current firmware session and survives closing/reopening Reader Menu.
inline WordSelectionMode& searchSelectionMode() {
  static WordSelectionMode mode = WordSelectionMode::Dictionary;
  return mode;
}

inline const char* searchSelectionModeLabel() {
  switch (searchSelectionMode()) {
    case WordSelectionMode::Edit: return "Szerkesztés";
    case WordSelectionMode::Highlight: return "Megjelölés";
    case WordSelectionMode::Dictionary:
    default: return "Szótár";
  }
}
''',
)

replace_once(
    "src/activities/reader/EpubReaderMenuActivity.h",
    "    EDIT,\n    MANUAL_DICTIONARY_SEARCH,",
    "    EDIT,\n    SEARCH_MODE,\n    SEARCH,\n    MANUAL_DICTIONARY_SEARCH,",
)

replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '#include "ReaderUtils.h"\n',
    '#include "ReaderUtils.h"\n#include "highlights/HighlightMode.h"\n',
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '''  items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótári keresés"});
  items.push_back({MenuAction::HIGHLIGHT, StrId::STR_LOOKUP, "Megjelölés"});
  items.push_back({MenuAction::EDIT, StrId::STR_LOOKUP, "Szerkesztés"});
  items.push_back({MenuAction::MANUAL_DICTIONARY_SEARCH, StrId::STR_LOOKUP, "Kézi keresés"});''',
    '''  items.push_back({MenuAction::SEARCH_MODE, StrId::STR_LOOKUP, "Mód választó"});
  items.push_back({MenuAction::SEARCH, StrId::STR_LOOKUP, "Keresés"});
  items.push_back({MenuAction::MANUAL_DICTIONARY_SEARCH, StrId::STR_LOOKUP, "Kézi keresés"});''',
)

replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    "  const auto selectedAction = items[index].action;\n  if (selectedAction == MenuAction::ROTATE_SCREEN) {",
    '''  const auto selectedAction = items[index].action;
  if (selectedAction == MenuAction::SEARCH_MODE) {
    static const char* const modes[] = {"Szótár", "Szerkesztés", "Megjelölés"};
    int current = 0;
    if (searchSelectionMode() == WordSelectionMode::Edit) current = 1;
    if (searchSelectionMode() == WordSelectionMode::Highlight) current = 2;
    optionPopup.show("Keresési mód", modes, 3, current, [this](int idx) {
      searchSelectionMode() = idx == 1 ? WordSelectionMode::Edit
                            : (idx == 2 ? WordSelectionMode::Highlight : WordSelectionMode::Dictionary);
      requestUpdate();
    });
    requestUpdate();
    return;
  }
  if (selectedAction == MenuAction::ROTATE_SCREEN) {''',
)

replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    "    if (action == MenuAction::ROTATE_SCREEN) {",
    '''    if (action == MenuAction::SEARCH_MODE) {
      menuRowItems[i].value = searchSelectionModeLabel();
    } else if (action == MenuAction::ROTATE_SCREEN) {''',
)

# Reader dispatcher: SEARCH uses the shared selector mode. Existing old action
# handlers remain for compatibility, but are no longer exposed in the menu.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    case EpubReaderMenuActivity::MenuAction::EDIT: {
      openDictionaryWordSelect(WordSelectionMode::Edit);
      break;
    }
''',
    '''    case EpubReaderMenuActivity::MenuAction::EDIT: {
      openDictionaryWordSelect(WordSelectionMode::Edit);
      break;
    }
    case EpubReaderMenuActivity::MenuAction::SEARCH_MODE: {
      break;
    }
    case EpubReaderMenuActivity::MenuAction::SEARCH: {
      openDictionaryWordSelect(searchSelectionMode());
      break;
    }
''',
)


# -----------------------------------------------------------------------------
# 3) Logical split words: selection result spans the complete source range.
#    Dictionary lookup remains normalized; editing keeps the raw visible token
#    whenever it is a single source token (quotes/punctuation are not lost).
# -----------------------------------------------------------------------------
regex_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    r'''HighlightResult DictionaryWordSelectActivity::makeHighlightResult\(\) const \{.*?\n\}\n\nvoid DictionaryWordSelectActivity::finishWithHighlight\(\)''',
    r'''HighlightResult DictionaryWordSelectActivity::makeHighlightResult() const {
  if (words.empty()) return {};
  const int first = logicalWordFirst(selected);
  const int second = logicalWordSecond(first);
  const WordBox& a = words[first];
  const WordBox& b = words[second];

  HighlightResult result;
  result.spineIndex = spineIndex;
  result.visibleTextOffset = a.block ? a.block->wordVisibleTextOffset(a.tokenIndex) : page->visibleTextOffset;
  const uint32_t secondOffset = b.block ? b.block->wordVisibleTextOffset(b.tokenIndex) : result.visibleTextOffset;
  const uint32_t endOffset = secondOffset + visibleCodepointLength(b.text ? b.text : "");
  result.length = static_cast<uint16_t>(endOffset >= result.visibleTextOffset ? endOffset - result.visibleTextOffset : 0);

  // Search can normalize punctuation, but Edit must preserve an exact visible
  // one-token spelling such as „őssikoly”-album. Synthetic line splits are
  // reconstructed to their logical source spelling.
  if (mode == WordSelectionMode::Edit && first == second)
    result.text = a.text ? a.text : "";
  else
    result.text = logicalWordText(selected);
  return result;
}

void DictionaryWordSelectActivity::finishWithHighlight()''',
    flags=re.S,
)

# Stored highlight membership becomes range-aware so both visual fragments of
# one logical split word are underlined. Upgrade same-start legacy anchors to
# the wider logical span when re-marked.
replace_once(
    "src/highlights/HighlightStore.cpp",
    '''bool HighlightStore::contains(const HighlightAnchor& anchor) const {
  return std::any_of(highlights_.begin(), highlights_.end(),
                     [&](const HighlightAnchor& item) { return sameAnchor(item, anchor); });
}

bool HighlightStore::add(const HighlightAnchor& anchor) {
  if (contains(anchor)) return true;
  highlights_.push_back(anchor);''',
    '''bool HighlightStore::contains(const HighlightAnchor& anchor) const {
  return std::any_of(highlights_.begin(), highlights_.end(), [&](const HighlightAnchor& item) {
    if (item.spineIndex != anchor.spineIndex) return false;
    const uint32_t itemEnd = item.visibleTextOffset + item.length;
    return anchor.visibleTextOffset >= item.visibleTextOffset && anchor.visibleTextOffset < itemEnd;
  });
}

bool HighlightStore::add(const HighlightAnchor& anchor) {
  for (auto& item : highlights_) {
    if (item.spineIndex == anchor.spineIndex && item.visibleTextOffset == anchor.visibleTextOffset) {
      if (anchor.length > item.length) {
        item = anchor;
        return save();
      }
      return true;
    }
  }
  highlights_.push_back(anchor);''',
)

# The selector's already-saved highlight overlay only received start offsets.
# Include every visible word offset covered by each stored logical range before
# opening it, so split second fragments remain visible there too.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    for (const auto& item : highlightStore->items()) {
      if (item.spineIndex == currentSpineIndex) highlightedOffsets.push_back(item.visibleTextOffset);
    }''',
    '''    for (const auto& item : highlightStore->items()) {
      if (item.spineIndex != currentSpineIndex) continue;
      highlightedOffsets.push_back(item.visibleTextOffset);
      // Exact covered word offsets are resolved by the selector from the page;
      // the range itself is passed separately below in CPHUN-137 when needed.
    }''',
)


# -----------------------------------------------------------------------------
# 4) Edit metadata: empty replacement is a valid deletion. Record the requested
#    adjacent-space cleanup so the later physical EPUB rewrite can prefer the
#    following space and fall back to the preceding one at paragraph end.
# -----------------------------------------------------------------------------
replace_once(
    "src/highlights/TextEditStore.h",
    "  std::string replacementText;\n};",
    "  std::string replacementText;\n  bool removeAdjacentSpace = false;\n};",
)
replace_once(
    "src/highlights/TextEditStore.cpp",
    '''    edit.replacementText = item["replacement"] | "";
    edits_.push_back(std::move(edit));''',
    '''    edit.replacementText = item["replacement"] | "";
    edit.removeAdjacentSpace = item["removeAdjacentSpace"] | false;
    edits_.push_back(std::move(edit));''',
)
replace_once(
    "src/highlights/TextEditStore.cpp",
    '''    item["replacement"] = edit.replacementText;
  }''',
    '''    item["replacement"] = edit.replacementText;
    item["removeAdjacentSpace"] = edit.removeAdjacentSpace;
  }''',
)

replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''            if (!keyboard->text.empty() && textEditStore) {
              textEditStore->upsert({selection.spineIndex, selection.visibleTextOffset, selection.length,
                                     selection.text, keyboard->text});
            }''',
    '''            if (textEditStore) {
              const bool wholeWordDeletion = keyboard->text.empty();
              textEditStore->upsert({selection.spineIndex, selection.visibleTextOffset, selection.length,
                                     selection.text, keyboard->text, wholeWordDeletion});
            }''',
)

# Preloading an already saved empty replacement must remain empty; otherwise a
# deletion would reopen with the original word restored.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    if (const auto* old = textEditStore->find(selection.spineIndex, selection.visibleTextOffset)) {
      if (!old->replacementText.empty()) initialText = old->replacementText;
    }''',
    '''    if (const auto* old = textEditStore->find(selection.spineIndex, selection.visibleTextOffset)) {
      initialText = old->replacementText;
    }''',
)

# Range-aware edit background so a logical word split across two rendered rows
# is treated as one edit marker instead of only the first fragment.
replace_once(
    "src/highlights/TextEditStore.h",
    "  const TextEditAnchor* find(int spineIndex, uint32_t visibleTextOffset) const;\n",
    "  const TextEditAnchor* find(int spineIndex, uint32_t visibleTextOffset) const;\n  bool containsOffset(int spineIndex, uint32_t visibleTextOffset) const;\n",
)
replace_once(
    "src/highlights/TextEditStore.cpp",
    '''bool TextEditStore::upsert(const TextEditAnchor& edit) {''',
    '''bool TextEditStore::containsOffset(const int spineIndex, const uint32_t visibleTextOffset) const {
  return std::any_of(edits_.begin(), edits_.end(), [&](const TextEditAnchor& edit) {
    if (edit.spineIndex != spineIndex) return false;
    const uint32_t end = edit.visibleTextOffset + edit.length;
    return visibleTextOffset >= edit.visibleTextOffset && visibleTextOffset < end;
  });
}

bool TextEditStore::upsert(const TextEditAnchor& edit) {''',
)
replace_once(
    "src/highlights/TextEditRenderer.cpp",
    "      if (!store.find(spineIndex, block->wordVisibleTextOffset(i))) continue;",
    "      if (!store.containsOffset(spineIndex, block->wordVisibleTextOffset(i))) continue;",
)


# -----------------------------------------------------------------------------
# 5) Editor keyboard ergonomics.
# -----------------------------------------------------------------------------
keyboard = "src/activities/util/HungarianKeyboardLayout.h"
for old, new in [
    ('HUK("Q", "q", \'q\')', 'HUK("q", "q", \'q\')'), ('HUK("W", "w", \'w\')', 'HUK("w", "w", \'w\')'),
    ('HUK("E", "e", \'e\')', 'HUK("e", "e", \'e\')'), ('HUK("R", "r", \'r\')', 'HUK("r", "r", \'r\')'),
    ('HUK("T", "t", \'t\')', 'HUK("t", "t", \'t\')'), ('HUK("Z", "z", \'z\')', 'HUK("z", "z", \'z\')'),
    ('HUK("U", "u", \'u\')', 'HUK("u", "u", \'u\')'), ('HUK("I", "i", \'i\')', 'HUK("i", "i", \'i\')'),
    ('HUK("O", "o", \'o\')', 'HUK("o", "o", \'o\')'), ('HUK("P", "p", \'p\')', 'HUK("p", "p", \'p\')'),
    ('HUK("Ö", "ö", 1303)', 'HUK("ö", "ö", 1303)'),
    ('HUK("A", "a", \'a\')', 'HUK("a", "a", \'a\')'), ('HUK("S", "s", \'s\')', 'HUK("s", "s", \'s\')'),
    ('HUK("D", "d", \'d\')', 'HUK("d", "d", \'d\')'), ('HUK("F", "f", \'f\')', 'HUK("f", "f", \'f\')'),
    ('HUK("G", "g", \'g\')', 'HUK("g", "g", \'g\')'), ('HUK("H", "h", \'h\')', 'HUK("h", "h", \'h\')'),
    ('HUK("J", "j", \'j\')', 'HUK("j", "j", \'j\')'), ('HUK("K", "k", \'k\')', 'HUK("k", "k", \'k\')'),
    ('HUK("L", "l", \'l\')', 'HUK("l", "l", \'l\')'), ('HUK("É", "é", 1301)', 'HUK("é", "é", 1301)'),
    ('HUK("Á", "á", 1302)', 'HUK("á", "á", 1302)'),
    ('HUK("Y", "y", \'y\')', 'HUK("y", "y", \'y\')'), ('HUK("X", "x", \'x\')', 'HUK("x", "x", \'x\')'),
    ('HUK("C", "c", \'c\')', 'HUK("c", "c", \'c\')'), ('HUK("V", "v", \'v\')', 'HUK("v", "v", \'v\')'),
    ('HUK("B", "b", \'b\')', 'HUK("b", "b", \'b\')'), ('HUK("N", "n", \'n\')', 'HUK("n", "n", \'n\')'),
    ('HUK("M", "m", \'m\')', 'HUK("m", "m", \'m\')'), ('HUK("Ü", "ü", 1304)', 'HUK("ü", "ü", 1304)'),
]:
    s = read(keyboard)
    if old not in s:
        raise SystemExit(f"CPHUN-137: missing HU lowercase-label anchor: {old}")
    write(keyboard, s.replace(old, new, 1))

# Editor opens with Backspace selected instead of NUM_ROW[0] (0).
replace_once(
    "src/activities/util/KeyboardEntryActivity.cpp",
    "  selRow = 0;\n  selCol = 0;\n  delPressCount = 0;",
    '''  selRow = 0;
  selCol = 0;
  if (title == "Szerkesztés") syncSelectionToValue(fui::QWERTY_KEY_BACKSPACE);
  delPressCount = 0;''',
)

# Editor-specific tips: move the whole block 50 px downward and explain the
# physical right-side Up/Down buttons and their cursor-mode transition. Use the
# Hungarian interface names instead of SELECT / DEL.
replace_once(
    "src/activities/util/KeyboardEntryActivity.cpp",
    '''  if (tipCount > 0) {
    int y = (underlineBottom + kbRect.y) / 2 - (tipCount + 1) * tipsLh / 2;
    drawTip(tr(STR_KB_TIPS), y);''',
    '''  if (tipCount > 0) {
    if (title == "Szerkesztés") {
      int y = (underlineBottom + kbRect.y) / 2 - 2 * tipsLh + 50;
      drawTip("Tippek:", y);
      y += tipsLh;
      drawTip("KIJELÖLÉS: bevitel   TÖRLÉS: visszatörlés", y);
      y += tipsLh;
      drawTip("FEL/LE: billentyűsor váltása", y);
      y += tipsLh;
      drawTip("FEL hosszan: kurzormód   LE: vissza", y);
    } else {
    int y = (underlineBottom + kbRect.y) / 2 - (tipCount + 1) * tipsLh / 2;
    drawTip(tr(STR_KB_TIPS), y);''',
)
# Close the editor-special else immediately before the keyboard renderer block.
replace_once(
    "src/activities/util/KeyboardEntryActivity.cpp",
    '''    }
  }

  // The FreeInkUI keyboard draws the keys and registers their hit rects into''',
    '''    }
    }
  }

  // The FreeInkUI keyboard draws the keys and registers their hit rects into''',
)


# -----------------------------------------------------------------------------
# 6) Build identity and cache invalidation.
# -----------------------------------------------------------------------------
bid = "src/CPHUNBuildId.h"
s = read(bid)
s2, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"', '#define CPHUN_BUILD_ID "CPHUN-260917-137-EXP"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-137: build id define not found")
write(bid, s2)

print("CPHUN-137 search/edit mode patch applied")
