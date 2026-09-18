from pathlib import Path

def rep(path, old, new, label):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"CPHUN-139 {label}: expected 1 match, found {n}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

# ---------------------------------------------------------------------------
# Footnote popup: +100 px height, one header marker in braces, no repeated
# leading marker in the body.
# ---------------------------------------------------------------------------
rep("src/activities/reader/FootnotePopupActivity.cpp",
    "constexpr int POPUP_HEIGHT = 430;",
    "constexpr int POPUP_HEIGHT = 530;",
    "popup height")

rep("src/activities/reader/FootnotePopupActivity.cpp",
'''std::string trimCopy(std::string value) {
  auto isWs = [](unsigned char c) { return std::isspace(c) != 0; };
  while (!value.empty() && isWs(static_cast<unsigned char>(value.front()))) value.erase(value.begin());
  while (!value.empty() && isWs(static_cast<unsigned char>(value.back()))) value.pop_back();
  return value;
}
''',
'''std::string trimCopy(std::string value) {
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
''',
    "popup marker helpers")

rep("src/activities/reader/FootnotePopupActivity.cpp",
'''      label_(std::move(label)),
      text_(trimCopy(std::move(text))),
      canReturnToList_(canReturnToList) {}''',
'''      label_(footnoteLabelCore(std::move(label))),
      text_(stripRepeatedFootnoteMarker(std::move(text), label_)),
      canReturnToList_(canReturnToList) {}''',
    "popup constructor")

rep("src/activities/reader/FootnotePopupActivity.cpp",
'''  const std::string title = label_.empty() ? "Lábjegyzet" : "Lábjegyzet " + label_;''',
'''  const std::string title = label_.empty() ? "Lábjegyzet" : "Lábjegyzet {" + label_ + "}";''',
    "popup title")

# ---------------------------------------------------------------------------
# Reader menu: move Mód választó immediately before Auto. lapozás.
# ---------------------------------------------------------------------------
rep("src/activities/reader/EpubReaderMenuActivity.cpp",
'''  items.push_back({MenuAction::HIGHLIGHT, StrId::STR_LOOKUP, "Megjelölés"});
  items.push_back({MenuAction::EDIT, StrId::STR_LOOKUP, "Szerkesztés"});
  items.push_back({MenuAction::WORD_SELECTION_MODE, StrId::STR_LOOKUP, "Mód választó"});
  items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótár"});''',
'''  items.push_back({MenuAction::HIGHLIGHT, StrId::STR_LOOKUP, "Megjelölés"});
  items.push_back({MenuAction::EDIT, StrId::STR_LOOKUP, "Szerkesztés"});
  items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótár"});''',
    "remove old mode position")

rep("src/activities/reader/EpubReaderMenuActivity.cpp",
'''  if (Frontlight.present()) items.push_back({MenuAction::FRONTLIGHT, StrId::STR_FRONTLIGHT});
  items.push_back({MenuAction::AUTO_PAGE_TURN, StrId::STR_AUTO_TURN_PAGES_PER_MIN, "Auto. lapozás, lap/perc"});''',
'''  if (Frontlight.present()) items.push_back({MenuAction::FRONTLIGHT, StrId::STR_FRONTLIGHT});
  items.push_back({MenuAction::WORD_SELECTION_MODE, StrId::STR_LOOKUP, "Mód választó"});
  items.push_back({MenuAction::AUTO_PAGE_TURN, StrId::STR_AUTO_TURN_PAGES_PER_MIN, "Auto. lapozás, lap/perc"});''',
    "insert mode before auto turn")

# ---------------------------------------------------------------------------
# Search hardware button: current-page footnote first, then Back continues into
# the selected word mode; Close returns directly to the reader.
# ---------------------------------------------------------------------------
rep("src/activities/reader/EpubReaderActivity.h",
'''  void openReaderMenu(bool startOnBookTab = false);
  void openDictionaryWordSelect(WordSelectionMode mode = WordSelectionMode::Dictionary);
  void openEditKeyboard(HighlightResult selection);''',
'''  void openReaderMenu(bool startOnBookTab = false);
  void openDictionaryWordSelect(WordSelectionMode mode = WordSelectionMode::Dictionary);
  void openSearchFootnoteOrWordSelect(WordSelectionMode mode);
  void openEditKeyboard(HighlightResult selection);''',
    "search flow declaration")

p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text(encoding="utf-8")

anchor = '''}

namespace {
constexpr char SKIPPED_SPINES_FILE[] = "/skipped_spines.bin";
}'''
helper = '''}

void EpubReaderActivity::openSearchFootnoteOrWordSelect(const WordSelectionMode mode) {
  if (currentPageFootnotes.empty()) {
    openDictionaryWordSelect(mode);
    return;
  }

  const int sourceSpine = currentSpineIndex;
  auto openPopupThenMode = [this, mode, sourceSpine](const FootnoteEntry& note) {
    std::string text = extractFootnoteText(note, sourceSpine);
    if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";
    startActivityForResult(
        std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), true),
        [this, mode](const ActivityResult& popupResult) {
          if (popupResult.isCancelled) openDictionaryWordSelect(mode);
          else requestUpdate();
        });
  };

  if (currentPageFootnotes.size() == 1) {
    openPopupThenMode(currentPageFootnotes.front());
    return;
  }

  const auto notes = currentPageFootnotes;
  startActivityForResult(
      std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, notes),
      [this, mode, sourceSpine, notes](const ActivityResult& result) {
        if (result.isCancelled) {
          openDictionaryWordSelect(mode);
          return;
        }
        const auto& selected = std::get<FootnoteResult>(result.data);
        auto it = std::find_if(notes.begin(), notes.end(),
                               [&](const FootnoteEntry& e) { return selected.href == e.href; });
        if (it == notes.end()) {
          openDictionaryWordSelect(mode);
          return;
        }

        std::string text = extractFootnoteText(*it, sourceSpine);
        if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";
        startActivityForResult(
            std::make_unique<FootnotePopupActivity>(renderer, mappedInput, it->number, std::move(text), true),
            [this, mode](const ActivityResult& popupResult) {
              if (popupResult.isCancelled) openDictionaryWordSelect(mode);
              else requestUpdate();
            });
      });
}

namespace {
constexpr char SKIPPED_SPINES_FILE[] = "/skipped_spines.bin";
}'''
if s.count(anchor) != 1:
    raise SystemExit(f"CPHUN-139 helper insertion anchor matches={s.count(anchor)}")
s = s.replace(anchor, helper, 1)

old = '''    if (configured == ReaderAction::OpenDictionary) {
      WordSelectionMode mode = WordSelectionMode::Dictionary;
      if (SETTINGS.wordSelectionMode == 1) mode = WordSelectionMode::Highlight;
      else if (SETTINGS.wordSelectionMode == 2) mode = WordSelectionMode::Edit;
      openDictionaryWordSelect(mode);
      return true;
    }'''
new = '''    if (configured == ReaderAction::OpenDictionary) {
      WordSelectionMode mode = WordSelectionMode::Dictionary;
      if (SETTINGS.wordSelectionMode == 1) mode = WordSelectionMode::Highlight;
      else if (SETTINGS.wordSelectionMode == 2) mode = WordSelectionMode::Edit;
      openSearchFootnoteOrWordSelect(mode);
      return true;
    }'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-139 Search/OpenDictionary block matches={s.count(old)}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")

print("CPHUN-139 applied: footnote popup UX + Search footnote-first flow + menu reorder")
