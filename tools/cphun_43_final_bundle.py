from pathlib import Path

# CPHUN-43: approved final bundle.
# - button action column X=250
# - approved 12-action picker and Hungarian labels
# - restore/guarantee factory 1x reader actions, especially page turning
# - justified explicit-hyphen microspacing: up to +2 px before and +2 px after

# ---------------------------------------------------------------------------
# Button configuration UI
p = Path('src/activities/settings/ButtonFunctionsActivity.cpp')
t = p.read_text(encoding='utf-8')
t = t.replace('constexpr int kActionX = 255;', 'constexpr int kActionX = 250;', 1)

a = t.index('constexpr ReaderAction ACTIONS[] = {')
b = t.index('};', a) + 2
t = t[:a] + '''constexpr ReaderAction ACTIONS[] = {
    ReaderAction::None,
    ReaderAction::PreviousPage,
    ReaderAction::NextPage,
    ReaderAction::OpenReaderMenu,
    ReaderAction::OpenTextSettings,
    ReaderAction::OpenDictionary,
    ReaderAction::GoHome,
    ReaderAction::ScreenMarginDown,
    ReaderAction::ScreenMarginUp,
    ReaderAction::ToggleBookmark,
    ReaderAction::OpenBookmarks,
    ReaderAction::Screenshot,
};''' + t[b:]

labels = {
    'case ReaderAction::OpenDictionary: return hu ? "Szótár" : "Dictionary";':
        'case ReaderAction::OpenDictionary: return hu ? "Keresés / Szótár" : "Search / Dictionary";',
    'case ReaderAction::ToggleBookmark: return hu ? "Könyvjelző váltás" : "Toggle bookmark";':
        'case ReaderAction::ToggleBookmark: return hu ? "Könyvjelző hozzáadása" : "Add bookmark";',
}
for old, new in labels.items():
    if old not in t:
        raise SystemExit(f'CPHUN-43 label anchor missing: {old}')
    t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')

# ---------------------------------------------------------------------------
# Reader gesture dispatcher.
# CPHUN-42 fixed the gesture slot lookup, but actions that were not explicitly
# specialized could still fall into the old hard-wired 2x compatibility tail.
# Implement every action exposed by the new picker and preserve factory 1x
# semantics for Back/Confirm/Left/Right.
p = Path('src/activities/reader/EpubReaderActivity.cpp')
r = p.read_text(encoding='utf-8')
anchor = '''    if (configured == ReaderAction::OpenTextSettings) { cphun36OpenLayout(); return true; }
    if (configured == ReaderAction::OpenLayoutMenu) { cphun36OpenLayout(); return true; }'''
insert = '''    if (configured == ReaderAction::ReaderBack) {
      if (footnoteDepth > 0) restoreSavedPosition();
      else if (SETTINGS.backShortToFileBrowser) activityManager.goToFileBrowser(bookPath);
      else onGoHome();
      return true;
    }
    if (configured == ReaderAction::PreviousPage || configured == ReaderAction::NextPage) {
      const bool previous = configured == ReaderAction::PreviousPage;
      const bool next = configured == ReaderAction::NextPage;
      if (handleEndOfBookPageTurn(previous, next)) return true;
      constexpr unsigned long kCphun43MinTurnGapMs = 200;
      if (RenderLock::peek() || (millis() - lastPageTurnTime) < kCphun43MinTurnGapMs) {
        pendingManualTurn = previous ? -1 : 1;
        return true;
      }
      if (!section) {
        requestUpdate();
        return true;
      }
      pageTurn(next);
      requestUpdate();
      return true;
    }
    if (configured == ReaderAction::OpenDictionary) {
      startActivityForResult(std::make_unique<DictionaryWordSelectActivity>(renderer, mappedInput, epub, section.get()),
                             dictionaryResultHandler);
      return true;
    }
    if (configured == ReaderAction::ToggleBookmark) { addBookmark(); return true; }
    if (configured == ReaderAction::OpenBookmarks) {
      startActivityForResult(
          std::make_unique<EpubReaderBookmarksActivity>(renderer, mappedInput, epub, epub->getPath()),
          progressChangeResultHandler);
      return true;
    }
    if (configured == ReaderAction::Screenshot) {
      { RenderLock lock; pendingScreenshot = true; }
      requestUpdate();
      return true;
    }
    if (configured == ReaderAction::OpenTextSettings) { cphun36OpenLayout(); return true; }
    if (configured == ReaderAction::OpenLayoutMenu) { cphun36OpenLayout(); return true; }'''
if anchor not in r:
    raise SystemExit('CPHUN-43 gesture action anchor missing')
r = r.replace(anchor, insert, 1)
p.write_text(r, encoding='utf-8')

# ---------------------------------------------------------------------------
# Justified explicit-hyphen microspacing.
# Explicit hyphenated compounds are tokenized into word / '-' / word segments.
# Treat each boundary immediately before/after a standalone ASCII hyphen as a
# render-only micro-adjustment opportunity. Each opportunity may absorb at most
# 2 px of positive justification spare space. No permanent spaces are inserted,
# line breaking is unchanged, and non-justified/last lines remain untouched.
p = Path('lib/Epub/Epub/ParsedText.cpp')
s = p.read_text(encoding='utf-8')
helper_anchor = '''bool endsWithBreakableHyphen(const std::string& token) {
  if (token.empty()) return false;
  return TokenBoundary::allowsBreakAfterExplicitHyphen(lastCodepoint(token));
}
'''
helper_new = helper_anchor + '''
bool isStandaloneExplicitHyphenToken(const std::string& token) { return token.size() == 1 && token[0] == '-'; }
'''
if helper_anchor not in s:
    raise SystemExit('CPHUN-43 hyphen helper anchor missing')
s = s.replace(helper_anchor, helper_new, 1)

spare_anchor = '''  const int spareSpace =
      effectivePageWidth + hangingAllowance - extraStartOffset - extraEndOffset - lineWordWidthSum - totalNaturalGaps;

  uint8_t letterSpacingPx = 0;'''
spare_new = '''  const int spareSpace =
      effectivePageWidth + hangingAllowance - extraStartOffset - extraEndOffset - lineWordWidthSum - totalNaturalGaps;

  // CPHUN-43: allow up to +2 px on each side of an explicit ASCII hyphen.
  // These are lower-impact justification opportunities than ordinary word gaps:
  // they consume only positive spare width and never alter pagination.
  size_t hyphenMicroOpportunityCount = 0;
  if (effectiveAlignment == CssTextAlign::Justify && !isLastLine && !blockStyle.isRtl && spareSpace > 0) {
    for (size_t wordIdx = 1; wordIdx < lineWordCount; ++wordIdx) {
      if (isStandaloneExplicitHyphenToken(lineWords[wordIdx]) ||
          isStandaloneExplicitHyphenToken(lineWords[wordIdx - 1])) {
        ++hyphenMicroOpportunityCount;
      }
    }
  }
  const int hyphenMicroTotal =
      std::min<int>(spareSpace, static_cast<int>(hyphenMicroOpportunityCount) * 2);

  uint8_t letterSpacingPx = 0;'''
if spare_anchor not in s:
    raise SystemExit('CPHUN-43 spare-space anchor missing')
s = s.replace(spare_anchor, spare_new, 1)

adjust_anchor = '  const int adjustedSpareSpace = spareSpace - (letterSpacingPx ? trackingExtraTotal : 0);'
adjust_new = '  const int adjustedSpareSpace = spareSpace - hyphenMicroTotal - (letterSpacingPx ? trackingExtraTotal : 0);'
if adjust_anchor not in s:
    raise SystemExit('CPHUN-43 adjusted-spare anchor missing')
s = s.replace(adjust_anchor, adjust_new, 1)

# Add a per-line counter to the standard LTR positioning path.
ltr_anchor = '''      size_t justifyGapIndex = 0;
      for (size_t wordIdx = 0; wordIdx < lineWordCount; wordIdx++) {
        lineXPos.push_back(static_cast<int16_t>(xpos));'''
ltr_new = '''      size_t justifyGapIndex = 0;
      int hyphenMicroRemaining = hyphenMicroTotal;
      for (size_t wordIdx = 0; wordIdx < lineWordCount; wordIdx++) {
        if (wordIdx > 0 && hyphenMicroRemaining > 0 &&
            (isStandaloneExplicitHyphenToken(lineWords[wordIdx]) ||
             isStandaloneExplicitHyphenToken(lineWords[wordIdx - 1]))) {
          const int micro = std::min(2, hyphenMicroRemaining);
          xpos += micro;
          hyphenMicroRemaining -= micro;
        }
        lineXPos.push_back(static_cast<int16_t>(xpos));'''
# There is one matching standard LTR loop; replace the last occurrence to avoid RTL/reordered paths.
pos = s.rfind(ltr_anchor)
if pos < 0:
    raise SystemExit('CPHUN-43 LTR positioning anchor missing')
s = s[:pos] + s[pos:].replace(ltr_anchor, ltr_new, 1)
p.write_text(s, encoding='utf-8')

# ---------------------------------------------------------------------------
# Static guards.
ui = Path('src/activities/settings/ButtonFunctionsActivity.cpp').read_text(encoding='utf-8')
assert 'constexpr int kActionX = 250;' in ui
picker = ui[ui.index('constexpr ReaderAction ACTIONS[] = {'):ui.index('};', ui.index('constexpr ReaderAction ACTIONS[] = {'))]
approved = [
    'ReaderAction::None', 'ReaderAction::PreviousPage', 'ReaderAction::NextPage',
    'ReaderAction::OpenReaderMenu', 'ReaderAction::OpenTextSettings', 'ReaderAction::OpenDictionary',
    'ReaderAction::GoHome', 'ReaderAction::ScreenMarginDown', 'ReaderAction::ScreenMarginUp',
    'ReaderAction::ToggleBookmark', 'ReaderAction::OpenBookmarks', 'ReaderAction::Screenshot',
]
assert picker.count('ReaderAction::') == 12
for action in approved: assert action in picker, action
for label in ['Keresés / Szótár', 'Könyvjelző hozzáadása', 'Könyvjelzők', 'Képernyőkép']:
    assert label in ui, label

reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
for needle in [
    'configured == ReaderAction::PreviousPage || configured == ReaderAction::NextPage',
    'configured == ReaderAction::ReaderBack', 'configured == ReaderAction::OpenDictionary',
    'configured == ReaderAction::ToggleBookmark', 'configured == ReaderAction::OpenBookmarks',
    'configured == ReaderAction::Screenshot', 'Button::Power', 'Button::PageBack', 'Button::PageForward',
]: assert needle in reader, needle

parsed = Path('lib/Epub/Epub/ParsedText.cpp').read_text(encoding='utf-8')
for needle in ['hyphenMicroOpportunityCount', 'hyphenMicroTotal', 'hyphenMicroRemaining',
               'std::min(2, hyphenMicroRemaining)']:
    assert needle in parsed, needle

print('Applied CPHUN-43 final bundle: X=250, approved picker, factory 1x actions, +2/+2 hyphen microspacing')
