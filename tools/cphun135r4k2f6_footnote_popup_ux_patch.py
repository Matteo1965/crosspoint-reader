from pathlib import Path

# CPHUN-135r4k2f6
# Footnote UX:
# - one note: bypass list, open popup directly; Back/Close both return to reader
# - multiple notes: list -> popup; Back returns to list, Close returns to reader
# No new EPUB scans or allocations.

# 1) Popup: distinguish Back from Close and optionally suppress list return.
h = Path("src/activities/reader/FootnotePopupActivity.h")
s = h.read_text(encoding="utf-8")
s = s.replace(
'''  FootnotePopupActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::string label, std::string text);''',
'''  FootnotePopupActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::string label, std::string text,
                        bool canReturnToList = true);''',
1)
s = s.replace(
'''  int firstLine_ = 0;''',
'''  int firstLine_ = 0;
  bool canReturnToList_ = true;''',
1)
h.write_text(s, encoding="utf-8")

p = Path("src/activities/reader/FootnotePopupActivity.cpp")
s = p.read_text(encoding="utf-8")
s = s.replace(
'''FootnotePopupActivity::FootnotePopupActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                             std::string label, std::string text)
    : Activity("FootnotePopup", renderer, mappedInput), label_(std::move(label)), text_(trimCopy(std::move(text))) {}''',
'''FootnotePopupActivity::FootnotePopupActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                             std::string label, std::string text, const bool canReturnToList)
    : Activity("FootnotePopup", renderer, mappedInput),
      label_(std::move(label)),
      text_(trimCopy(std::move(text))),
      canReturnToList_(canReturnToList) {}''',
1)

old_loop = '''void FootnotePopupActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back) ||
      mappedInput.wasReleased(MappedInputManager::Button::Confirm) ||
      mappedInput.wasReleased(MappedInputManager::Button::Power)) {
    finish();
    return;
  }
'''
new_loop = '''void FootnotePopupActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    if (canReturnToList_) {
      ActivityResult result;
      result.isCancelled = true;
      setResult(std::move(result));
    }
    finish();
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm) ||
      mappedInput.wasReleased(MappedInputManager::Button::Power)) {
    // Normal completion means "Bezárás": return directly to the reader.
    finish();
    return;
  }
'''
if old_loop not in s:
    raise SystemExit("R4K2F6: popup loop block not found")
s = s.replace(old_loop, new_loop, 1)

s = s.replace(
'''  const auto labels = mappedInput.mapLabels("Vissza", "Bezárás", canUp ? "Fel" : "", canDown ? "Le" : "");''',
'''  const auto labels =
      mappedInput.mapLabels(canReturnToList_ ? "Vissza" : "", "Bezárás", canUp ? "Fel" : "", canDown ? "Le" : "");''',
1)
p.write_text(s, encoding="utf-8")

# 2) Reader: direct-open one-note case and branch popup result.
p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text(encoding="utf-8")

# Make the existing helper's direct popup explicitly non-list-returning.
s = s.replace(
'''  startActivityForResult(std::make_unique<FootnotePopupActivity>(renderer, mappedInput, footnote.number, std::move(text)),
                         [this](const ActivityResult&) { requestUpdate(); });''',
'''  startActivityForResult(
      std::make_unique<FootnotePopupActivity>(renderer, mappedInput, footnote.number, std::move(text), false),
      [this](const ActivityResult&) { requestUpdate(); });''',
1)

# Add one-note fast path inside openFootnotesList after sourceSpine is established.
needle = '''  // Keep one immutable source spine for the entire list/popup/list session.
  // Scanned hrefs are intentionally raw/source-relative since R4J.
  const int sourceSpine = sourceSpineIndex >= 0 ? sourceSpineIndex : currentSpineIndex;
  startActivityForResult(std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, notes),'''
replacement = '''  // Keep one immutable source spine for the entire list/popup/list session.
  // Scanned hrefs are intentionally raw/source-relative since R4J.
  const int sourceSpine = sourceSpineIndex >= 0 ? sourceSpineIndex : currentSpineIndex;

  // CPHUN-135r4k2f6: one note needs no intermediate list.
  if (notes.size() == 1) {
    const FootnoteEntry note = notes.front();
    std::string text = extractFootnoteText(note, sourceSpine);
    if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";
    startActivityForResult(
        std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), false),
        [this](const ActivityResult&) { requestUpdate(); });
    return;
  }

  startActivityForResult(std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, notes),'''
if needle not in s:
    raise SystemExit("R4K2F6: openFootnotesList sourceSpine/list block not found")
s = s.replace(needle, replacement, 1)

# Multiple-note popup: cancelled=Back -> reopen list; normal=Close -> reader.
old_cb = '''                               [this, wholeBook, returnToMenu, sourceSpine](const ActivityResult&) {
                                 openFootnotesList(wholeBook, returnToMenu, sourceSpine);
                               });'''
new_cb = '''                               [this, wholeBook, returnToMenu, sourceSpine](const ActivityResult& popupResult) {
                                 if (popupResult.isCancelled) {
                                   openFootnotesList(wholeBook, returnToMenu, sourceSpine);
                                 } else {
                                   requestUpdate();
                                 }
                               });'''
if old_cb not in s:
    raise SystemExit("R4K2F6: popup return callback not found")
s = s.replace(old_cb, new_cb, 1)

p.write_text(s, encoding="utf-8")
print("CPHUN-135r4k2f6 applied: direct single-note popup + Back/List vs Close/Reader")
