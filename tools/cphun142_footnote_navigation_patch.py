from pathlib import Path
import re

def read(p): return Path(p).read_text(encoding="utf-8")
def write(p,s): Path(p).write_text(s, encoding="utf-8")

# ---------------------------------------------------------------------------
# ActivityResult: popup sibling navigation result
# ---------------------------------------------------------------------------
p="src/activities/ActivityResult.h"
s=read(p)
anchor='''struct FootnoteResult {
  std::string href;
};
'''
if s.count(anchor)!=1:
    raise SystemExit("CPHUN-142 ActivityResult FootnoteResult anchor mismatch")
s=s.replace(anchor, anchor + '''
struct FootnotePopupNavResult {
  int8_t delta = 0;  // -1 = previous, +1 = next
};
''',1)
old='''                 PercentResult, IntervalResult, PageResult, ProgressChangeResult, NetworkModeResult, FootnoteResult,
                 FilePathResult>;'''
if s.count(old)!=1:
    old='''                 PercentResult, IntervalResult, PageResult, ProgressChangeResult, NetworkModeResult, FootnoteResult,
                 FilePathResult>;'''
if s.count(old)!=1:
    raise SystemExit("CPHUN-142 ResultVariant anchor mismatch")
new='''                 PercentResult, IntervalResult, PageResult, ProgressChangeResult, NetworkModeResult, FootnoteResult,
                 FootnotePopupNavResult, FilePathResult>;'''
s=s.replace(old,new,1)
write(p,s)

# ---------------------------------------------------------------------------
# FootnotePopupActivity: multi-note prev/next navigation on buttons 3/4.
# ---------------------------------------------------------------------------
p="src/activities/reader/FootnotePopupActivity.h"
s=read(p)
old='''  FootnotePopupActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::string label, std::string text,
                        bool canReturnToList = true);'''
new='''  FootnotePopupActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::string label, std::string text,
                        bool canReturnToList = true, bool canNavigateSiblings = false);'''
if s.count(old)!=1:
    raise SystemExit("CPHUN-142 popup ctor declaration mismatch")
s=s.replace(old,new,1)
old='''  bool canReturnToList_ = true;'''
new='''  bool canReturnToList_ = true;
  bool canNavigateSiblings_ = false;'''
if s.count(old)!=1:
    raise SystemExit("CPHUN-142 popup member anchor mismatch")
s=s.replace(old,new,1)
write(p,s)

p="src/activities/reader/FootnotePopupActivity.cpp"
s=read(p)
old='''FootnotePopupActivity::FootnotePopupActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                             std::string label, std::string text, const bool canReturnToList)
    : Activity("FootnotePopup", renderer, mappedInput),
      label_(footnoteLabelCore(std::move(label))),
      text_(stripRepeatedFootnoteMarker(std::move(text), label_)),
      canReturnToList_(canReturnToList) {}'''
new='''FootnotePopupActivity::FootnotePopupActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                             std::string label, std::string text, const bool canReturnToList,
                                             const bool canNavigateSiblings)
    : Activity("FootnotePopup", renderer, mappedInput),
      label_(footnoteLabelCore(std::move(label))),
      text_(stripRepeatedFootnoteMarker(std::move(text), label_)),
      canReturnToList_(canReturnToList),
      canNavigateSiblings_(canNavigateSiblings) {}'''
if s.count(old)!=1:
    raise SystemExit("CPHUN-142 popup ctor definition mismatch")
s=s.replace(old,new,1)

old='''  if (mappedInput.wasReleased(MappedInputManager::Button::Up)) {
    if (firstLine_ > 0) {
      --firstLine_;
      requestUpdate();
    }
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Down)) {
    if (firstLine_ + 1 < static_cast<int>(lines_.size())) {
      ++firstLine_;
      requestUpdate();
    }
    return;
  }
'''
new='''  if (mappedInput.wasReleased(MappedInputManager::Button::Up)) {
    if (canNavigateSiblings_) {
      setResult(FootnotePopupNavResult{-1});
      finish();
      return;
    }
    if (firstLine_ > 0) {
      --firstLine_;
      requestUpdate();
    }
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Down)) {
    if (canNavigateSiblings_) {
      setResult(FootnotePopupNavResult{1});
      finish();
      return;
    }
    if (firstLine_ + 1 < static_cast<int>(lines_.size())) {
      ++firstLine_;
      requestUpdate();
    }
    return;
  }
'''
if s.count(old)!=1:
    raise SystemExit("CPHUN-142 popup Up/Down block mismatch")
s=s.replace(old,new,1)

old='''  const auto labels =
      mappedInput.mapLabels(canReturnToList_ ? "Vissza" : "", "Bezárás", canUp ? "Fel" : "", canDown ? "Le" : "");'''
new='''  const auto labels = mappedInput.mapLabels(
      canReturnToList_ ? "Vissza" : "", "Bezárás",
      canNavigateSiblings_ ? "Előző" : (canUp ? "Fel" : ""),
      canNavigateSiblings_ ? "Következő" : (canDown ? "Le" : ""));'''
if s.count(old)!=1:
    raise SystemExit("CPHUN-142 popup footer labels mismatch")
s=s.replace(old,new,1)
write(p,s)

# ---------------------------------------------------------------------------
# Reader declarations for shared/menu and shortcut footnote sessions.
# ---------------------------------------------------------------------------
p="src/activities/reader/EpubReaderActivity.h"
s=read(p)
anchor='''  void openFootnotesList(bool wholeBook, bool returnToMenu, int sourceSpineIndex = -1);'''
if s.count(anchor)!=1:
    raise SystemExit("CPHUN-142 openFootnotesList declaration mismatch")
s=s.replace(anchor, anchor + '''
  void openFootnotePopupSession(bool wholeBook, bool returnToMenu, int sourceSpineIndex, int noteIndex);
''',1)

anchor='''  void openSearchFootnoteOrWordSelect(WordSelectionMode mode);'''
if s.count(anchor)!=1:
    raise SystemExit("CPHUN-142 search helper declaration mismatch")
s=s.replace(anchor, anchor + '''
  void openSearchFootnoteList(WordSelectionMode mode, int sourceSpineIndex);
  void openSearchFootnotePopup(WordSelectionMode mode, int sourceSpineIndex, int noteIndex);
''',1)
write(p,s)

# ---------------------------------------------------------------------------
# Reader: replace the final menu-driven list function with a session that can
# return to the list and can cycle previous/next without reopening the list.
# ---------------------------------------------------------------------------
p="src/activities/reader/EpubReaderActivity.cpp"
s=read(p)

pat=re.compile(r'''void EpubReaderActivity::openFootnotesList\(const bool wholeBook, const bool returnToMenu,\s*
\s*const int sourceSpineIndex\) \{.*?\n\}\n\n(?=void EpubReaderActivity::)''', re.S)
m=pat.search(s)
if not m:
    raise SystemExit("CPHUN-142 final openFootnotesList definition not found")

replacement=r'''void EpubReaderActivity::openFootnotePopupSession(const bool wholeBook, const bool returnToMenu,
                                                    const int sourceSpineIndex, int noteIndex) {
  const auto& notes = wholeBook ? bookFootnotes : currentPageFootnotes;
  if (notes.empty()) {
    requestUpdate();
    return;
  }

  const int count = static_cast<int>(notes.size());
  noteIndex = (noteIndex % count + count) % count;
  const FootnoteEntry note = notes[noteIndex];

  std::string text = extractFootnoteText(note, sourceSpineIndex);
  if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";

  startActivityForResult(
      std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), true, count > 1),
      [this, wholeBook, returnToMenu, sourceSpineIndex, noteIndex](const ActivityResult& popupResult) {
        if (popupResult.isCancelled) {
          openFootnotesList(wholeBook, returnToMenu, sourceSpineIndex);
          return;
        }
        if (const auto* nav = std::get_if<FootnotePopupNavResult>(&popupResult.data)) {
          openFootnotePopupSession(wholeBook, returnToMenu, sourceSpineIndex, noteIndex + nav->delta);
          return;
        }
        requestUpdate();  // Bezárás -> reader
      });
}

void EpubReaderActivity::openFootnotesList(const bool wholeBook, const bool returnToMenu,
                                           const int sourceSpineIndex) {
  const auto& notes = wholeBook ? bookFootnotes : currentPageFootnotes;
  if (notes.empty()) {
    if (returnToMenu) openReaderMenu();
    return;
  }

  const int sourceSpine = sourceSpineIndex >= 0 ? sourceSpineIndex : currentSpineIndex;

  // Preserve the existing one-note direct-popup behavior.
  if (notes.size() == 1) {
    const FootnoteEntry note = notes.front();
    std::string text = extractFootnoteText(note, sourceSpine);
    if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";
    startActivityForResult(
        std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), false, false),
        [this](const ActivityResult&) { requestUpdate(); });
    return;
  }

  startActivityForResult(
      std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, notes),
      [this, wholeBook, returnToMenu, sourceSpine](const ActivityResult& result) {
        if (result.isCancelled) {
          if (returnToMenu) openReaderMenu();
          else requestUpdate();
          return;
        }

        const auto& selected = std::get<FootnoteResult>(result.data);
        const auto& source = wholeBook ? bookFootnotes : currentPageFootnotes;
        const auto it = std::find_if(source.begin(), source.end(),
                                     [&](const FootnoteEntry& e) { return selected.href == e.href; });
        if (it == source.end()) {
          requestUpdate();
          return;
        }
        const int index = static_cast<int>(std::distance(source.begin(), it));
        openFootnotePopupSession(wholeBook, returnToMenu, sourceSpine, index);
      });
}

'''
s=s[:m.start()]+replacement+s[m.end():]

# Replace #139/#141 shortcut helper with list->popup->list semantics.
pat=re.compile(r'''void EpubReaderActivity::openSearchFootnoteOrWordSelect\(const WordSelectionMode mode\) \{.*?\n\}\n\n(?=namespace \{)''', re.S)
m=pat.search(s)
if not m:
    raise SystemExit("CPHUN-142 final shortcut helper not found")

replacement=r'''void EpubReaderActivity::openSearchFootnotePopup(const WordSelectionMode mode, const int sourceSpineIndex,
                                                   int noteIndex) {
  if (currentPageFootnotes.empty()) {
    openDictionaryWordSelect(mode);
    return;
  }

  const int count = static_cast<int>(currentPageFootnotes.size());
  noteIndex = (noteIndex % count + count) % count;
  const FootnoteEntry note = currentPageFootnotes[noteIndex];

  std::string text = extractFootnoteText(note, sourceSpineIndex);
  if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";

  startActivityForResult(
      std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), true, count > 1),
      [this, mode, sourceSpineIndex, noteIndex](const ActivityResult& popupResult) {
        if (popupResult.isCancelled) {
          if (currentPageFootnotes.size() > 1) {
            openSearchFootnoteList(mode, sourceSpineIndex);  // Vissza -> list
          } else {
            openDictionaryWordSelect(mode);                  // single note: Vissza -> word selector
          }
          return;
        }
        if (const auto* nav = std::get_if<FootnotePopupNavResult>(&popupResult.data)) {
          openSearchFootnotePopup(mode, sourceSpineIndex, noteIndex + nav->delta);
          return;
        }
        requestUpdate();  // Bezárás -> reader
      });
}

void EpubReaderActivity::openSearchFootnoteList(const WordSelectionMode mode, const int sourceSpineIndex) {
  if (currentPageFootnotes.empty()) {
    openDictionaryWordSelect(mode);
    return;
  }
  if (currentPageFootnotes.size() == 1) {
    openSearchFootnotePopup(mode, sourceSpineIndex, 0);
    return;
  }

  startActivityForResult(
      std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, currentPageFootnotes),
      [this, mode, sourceSpineIndex](const ActivityResult& result) {
        if (result.isCancelled) {
          openDictionaryWordSelect(mode);  // Vissza from list -> selected word mode
          return;
        }

        const auto& selected = std::get<FootnoteResult>(result.data);
        const auto it = std::find_if(currentPageFootnotes.begin(), currentPageFootnotes.end(),
                                     [&](const FootnoteEntry& e) { return selected.href == e.href; });
        if (it == currentPageFootnotes.end()) {
          openDictionaryWordSelect(mode);
          return;
        }
        const int index = static_cast<int>(std::distance(currentPageFootnotes.begin(), it));
        openSearchFootnotePopup(mode, sourceSpineIndex, index);
      });
}

void EpubReaderActivity::openSearchFootnoteOrWordSelect(const WordSelectionMode mode) {
  if (currentPageFootnotes.empty()) {
    openDictionaryWordSelect(mode);
    return;
  }

  const int sourceSpine = currentSpineIndex;
  if (currentPageFootnotes.size() == 1) {
    openSearchFootnotePopup(mode, sourceSpine, 0);
  } else {
    openSearchFootnoteList(mode, sourceSpine);
  }
}

'''
s=s[:m.start()]+replacement+s[m.end():]
write(p,s)

print("CPHUN-142 applied: unified multi-footnote Back semantics + cyclic Previous/Next")
