from pathlib import Path

def rep(path, old, new, label):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"CPHUN-141 {label}: expected 1 match, found {n}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

rep("src/activities/reader/FootnotePopupActivity.cpp",
    "constexpr int POPUP_HEIGHT = 580;",
    "constexpr int POPUP_HEIGHT = 600;",
    "popup height")

rep("src/activities/reader/FootnotePopupActivity.cpp",
    "const int popupY = std::max(0, (screenH - popupH) / 2 - 30);",
    "const int popupY = std::max(0, (screenH - popupH) / 2 - 40);",
    "popup Y offset")

p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text(encoding="utf-8")

old = '''  const auto notes = currentPageFootnotes;
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
      });'''

new = '''  // EpubReaderFootnotesActivity stores its input vector by reference. Use the
  // reader-owned vector (same lifetime-safe source as the Reader-menu path),
  // never a local copy that dies while the list activity is still open.
  startActivityForResult(
      std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, currentPageFootnotes),
      [this, mode, sourceSpine](const ActivityResult& result) {
        if (result.isCancelled) {
          openDictionaryWordSelect(mode);
          return;
        }
        const auto& selected = std::get<FootnoteResult>(result.data);
        auto it = std::find_if(currentPageFootnotes.begin(), currentPageFootnotes.end(),
                               [&](const FootnoteEntry& e) { return selected.href == e.href; });
        if (it == currentPageFootnotes.end()) {
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
      });'''

if s.count(old) != 1:
    raise SystemExit(f"CPHUN-141 shortcut multi-footnote block matches={s.count(old)}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")

print("CPHUN-141 applied: 600px/-40 popup + lifetime-safe multi-footnote shortcut list")
