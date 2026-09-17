from pathlib import Path
import re

# CPHUN-135r4k2f
# Preserve the footnote source spine across list -> popup -> list cycles.
# R4J intentionally keeps scanned hrefs source-relative, so resolving them
# against a newly sampled currentSpineIndex after returning from the popup can
# make later selections fail.

hdr = Path("src/activities/reader/EpubReaderActivity.h")
h = hdr.read_text(encoding="utf-8")
old = "  void openFootnotesList(bool wholeBook, bool returnToMenu);\n"
new = "  void openFootnotesList(bool wholeBook, bool returnToMenu, int sourceSpineIndex = -1);\n"
if old not in h:
    raise SystemExit("R4K2F: openFootnotesList declaration not found")
h = h.replace(old, new, 1)
hdr.write_text(h, encoding="utf-8")

cpp = Path("src/activities/reader/EpubReaderActivity.cpp")
s = cpp.read_text(encoding="utf-8")

# Replace the function header and source-spine capture.
old_head = '''void EpubReaderActivity::openFootnotesList(const bool wholeBook, const bool returnToMenu) {
  const auto& notes = wholeBook ? bookFootnotes : currentPageFootnotes;
'''
new_head = '''void EpubReaderActivity::openFootnotesList(const bool wholeBook, const bool returnToMenu,
                                                const int sourceSpineIndex) {
  const auto& notes = wholeBook ? bookFootnotes : currentPageFootnotes;
'''
if old_head not in s:
    raise SystemExit("R4K2F: openFootnotesList definition header not found")
s = s.replace(old_head, new_head, 1)

old_capture = '''  const int sourceSpine = currentSpineIndex;
  startActivityForResult(std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, notes),
                         [this, wholeBook, returnToMenu, sourceSpine](const ActivityResult& result) {
'''
new_capture = '''  // Keep one immutable source spine for the entire list/popup/list session.
  // Scanned hrefs are intentionally raw/source-relative since R4J.
  const int sourceSpine = sourceSpineIndex >= 0 ? sourceSpineIndex : currentSpineIndex;
  startActivityForResult(std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, notes),
                         [this, wholeBook, returnToMenu, sourceSpine](const ActivityResult& result) {
'''
if old_capture not in s:
    raise SystemExit("R4K2F: sourceSpine capture block not found")
s = s.replace(old_capture, new_capture, 1)

# The popup return must preserve the original source spine instead of sampling
# currentSpineIndex again.
old_return = '''                               [this, wholeBook, returnToMenu](const ActivityResult&) {
                                 openFootnotesList(wholeBook, returnToMenu);
                               });'''
new_return = '''                               [this, wholeBook, returnToMenu, sourceSpine](const ActivityResult&) {
                                 openFootnotesList(wholeBook, returnToMenu, sourceSpine);
                               });'''
if old_return not in s:
    # tolerate compact formatting used by the original R4B patch
    old_return = '''                               [this, wholeBook, returnToMenu](const ActivityResult&) { openFootnotesList(wholeBook, returnToMenu); });'''
    new_return = '''                               [this, wholeBook, returnToMenu, sourceSpine](const ActivityResult&) {
                                 openFootnotesList(wholeBook, returnToMenu, sourceSpine);
                               });'''
if old_return not in s:
    raise SystemExit("R4K2F: popup return callback not found")
s = s.replace(old_return, new_return, 1)

cpp.write_text(s, encoding="utf-8")
print("CPHUN-135r4k2f applied: stable footnote source spine across repeated popup selections")
