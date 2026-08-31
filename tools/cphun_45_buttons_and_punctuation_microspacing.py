from pathlib import Path

# CPHUN-45:
# - final 16-action picker: remove Screenshot, add Back + cyclic font/line-spacing steps
# - keep CPHUN-44 explicit-hyphen microspacing at +4/+4 px
# - add independent +1/+1 px microspacing around standalone . , ; : ! ? tokens

# 1) Final 16-action picker and labels.
p = Path('src/activities/settings/ButtonFunctionsActivity.cpp')
t = p.read_text(encoding='utf-8')
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
    ReaderAction::ReaderBack,
    ReaderAction::FontSizeDown,
    ReaderAction::FontSizeUp,
    ReaderAction::LineSpacingPrevious,
    ReaderAction::LineSpacingNext,
};''' + t[b:]

label_replacements = {
    'case ReaderAction::FontSizeUp: return hu ? "Betűméret +" : "Font size +";':
        'case ReaderAction::FontSizeUp: return hu ? "Betűméret +" : "Font size +";',
    'case ReaderAction::FontSizeDown: return hu ? "Betűméret −" : "Font size -";':
        'case ReaderAction::FontSizeDown: return hu ? "Betűméret −" : "Font size -";',
    'case ReaderAction::LineSpacingNext: return hu ? "Sorköz +" : "Line spacing +";':
        'case ReaderAction::LineSpacingNext: return hu ? "Soremelés +" : "Line spacing +";',
    'case ReaderAction::LineSpacingPrevious: return hu ? "Sorköz −" : "Line spacing -";':
        'case ReaderAction::LineSpacingPrevious: return hu ? "Soremelés −" : "Line spacing -";',
}
for old, new in label_replacements.items():
    if old not in t:
        raise SystemExit(f'CPHUN-45 label anchor missing: {old}')
    t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')

# 2) Cyclic font-size and line-spacing actions in the reader.
p = Path('src/activities/reader/EpubReaderActivity.cpp')
r = p.read_text(encoding='utf-8')
include_anchor = '#include "ReaderUtils.h"\n'
if '#include "ReaderFontSizes.h"\n' not in r:
    if include_anchor not in r:
        raise SystemExit('CPHUN-45 ReaderFontSizes include anchor missing')
    r = r.replace(include_anchor, '#include "ReaderFontSizes.h"\n' + include_anchor, 1)

action_anchor = '''    if (configured == ReaderAction::OpenDictionary) { openDictionaryWordSelect(); return true; }
    if (configured == ReaderAction::ToggleBookmark) { addBookmark(); return true; }'''
action_insert = '''    if (configured == ReaderAction::OpenDictionary) { openDictionaryWordSelect(); return true; }
    if (configured == ReaderAction::FontSizeUp || configured == ReaderAction::FontSizeDown) {
      const auto points = readerFontPointSizes(&sdFontSystem.registry(), SETTINGS.sdFontFamilyName);
      if (!points.empty()) {
        const uint8_t current = snapToNearestPointSize(points, SETTINGS.fontPointSize);
        auto it = std::find(points.begin(), points.end(), current);
        size_t idx = it == points.end() ? 0 : static_cast<size_t>(std::distance(points.begin(), it));
        if (configured == ReaderAction::FontSizeUp) idx = (idx + 1) % points.size();
        else idx = (idx + points.size() - 1) % points.size();
        {
          RenderLock lock;
          SETTINGS.fontPointSize = points[idx];
          sdFontSystem.ensureLoaded(renderer);
        }
        SETTINGS.saveToFile();
        cphun36RebuildReader();
      }
      return true;
    }
    if (configured == ReaderAction::LineSpacingNext || configured == ReaderAction::LineSpacingPrevious) {
      constexpr uint8_t kLineSpacingCount = 4;
      const uint8_t current = SETTINGS.lineSpacing < kLineSpacingCount ? SETTINGS.lineSpacing : 1;
      SETTINGS.lineSpacing = configured == ReaderAction::LineSpacingNext
                                 ? static_cast<uint8_t>((current + 1) % kLineSpacingCount)
                                 : static_cast<uint8_t>((current + kLineSpacingCount - 1) % kLineSpacingCount);
      SETTINGS.saveToFile();
      cphun36RebuildReader();
      return true;
    }
    if (configured == ReaderAction::ToggleBookmark) { addBookmark(); return true; }'''
if action_anchor not in r:
    raise SystemExit('CPHUN-45 reader-action anchor missing')
r = r.replace(action_anchor, action_insert, 1)
p.write_text(r, encoding='utf-8')

# 3) Independent punctuation microspacing for justified LTR non-last lines.
p = Path('lib/Epub/Epub/ParsedText.cpp')
s = p.read_text(encoding='utf-8')
helper_anchor = "bool isStandaloneExplicitHyphenToken(const std::string& token) { return token.size() == 1 && token[0] == '-'; }\n"
helper_new = helper_anchor + '''
bool isStandalonePunctuationMicroToken(const std::string& token) {
  if (token.size() != 1) return false;
  switch (token[0]) {
    case '.':
    case ',':
    case ';':
    case ':':
    case '!':
    case '?':
      return true;
    default:
      return false;
  }
}
'''
if helper_anchor not in s:
    raise SystemExit('CPHUN-45 punctuation helper anchor missing')
s = s.replace(helper_anchor, helper_new, 1)

spare_anchor = '''  // CPHUN-44: up to +4 px before and +4 px after each explicit ASCII hyphen.
  size_t hyphenMicroOpportunityCount = 0;
  if (effectiveAlignment == CssTextAlign::Justify && !isLastLine && !blockStyle.isRtl && spareSpace > 0) {
    for (size_t wordIdx = 1; wordIdx < lineWordCount; ++wordIdx) {
      if (isStandaloneExplicitHyphenToken(lineWords[wordIdx]) ||
          isStandaloneExplicitHyphenToken(lineWords[wordIdx - 1])) ++hyphenMicroOpportunityCount;
    }
  }
  const int hyphenMicroTotal = std::min<int>(spareSpace, static_cast<int>(hyphenMicroOpportunityCount) * 4);
'''
spare_new = '''  // CPHUN-44/45: independent render-only microspacing on justified LTR non-last lines.
  // Explicit ASCII hyphen: up to +4 px at each adjacent token boundary.
  // . , ; : ! ? punctuation: up to +1 px at each adjacent token boundary.
  size_t hyphenMicroOpportunityCount = 0;
  size_t punctuationMicroOpportunityCount = 0;
  if (effectiveAlignment == CssTextAlign::Justify && !isLastLine && !blockStyle.isRtl && spareSpace > 0) {
    for (size_t wordIdx = 1; wordIdx < lineWordCount; ++wordIdx) {
      if (isStandaloneExplicitHyphenToken(lineWords[wordIdx]) ||
          isStandaloneExplicitHyphenToken(lineWords[wordIdx - 1])) ++hyphenMicroOpportunityCount;
      if (isStandalonePunctuationMicroToken(lineWords[wordIdx]) ||
          isStandalonePunctuationMicroToken(lineWords[wordIdx - 1])) ++punctuationMicroOpportunityCount;
    }
  }
  const int hyphenMicroTotal = std::min<int>(spareSpace, static_cast<int>(hyphenMicroOpportunityCount) * 4);
  const int punctuationMicroTotal =
      std::min<int>(std::max(0, spareSpace - hyphenMicroTotal), static_cast<int>(punctuationMicroOpportunityCount));
'''
if spare_anchor not in s:
    raise SystemExit('CPHUN-45 spare-space anchor missing')
s = s.replace(spare_anchor, spare_new, 1)

adjust_anchor = '  const int adjustedSpareSpace = spareSpace - hyphenMicroTotal - (letterSpacingPx ? trackingExtraTotal : 0);'
if adjust_anchor not in s:
    raise SystemExit('CPHUN-45 adjusted-spare anchor missing')
s = s.replace(adjust_anchor,
              '  const int adjustedSpareSpace = spareSpace - hyphenMicroTotal - punctuationMicroTotal - (letterSpacingPx ? trackingExtraTotal : 0);',
              1)

ltr_anchor = '''      size_t justifyGapIndex = 0;
      int hyphenMicroRemaining = hyphenMicroTotal;
      for (size_t wordIdx = 0; wordIdx < lineWordCount; wordIdx++) {
        if (wordIdx > 0 && hyphenMicroRemaining > 0 &&
            (isStandaloneExplicitHyphenToken(lineWords[wordIdx]) ||
             isStandaloneExplicitHyphenToken(lineWords[wordIdx - 1]))) {
          const int micro = std::min(4, hyphenMicroRemaining);
          xpos += micro;
          hyphenMicroRemaining -= micro;
        }
        lineXPos.push_back(static_cast<int16_t>(xpos));'''
ltr_new = '''      size_t justifyGapIndex = 0;
      int hyphenMicroRemaining = hyphenMicroTotal;
      int punctuationMicroRemaining = punctuationMicroTotal;
      for (size_t wordIdx = 0; wordIdx < lineWordCount; wordIdx++) {
        if (wordIdx > 0 && hyphenMicroRemaining > 0 &&
            (isStandaloneExplicitHyphenToken(lineWords[wordIdx]) ||
             isStandaloneExplicitHyphenToken(lineWords[wordIdx - 1]))) {
          const int micro = std::min(4, hyphenMicroRemaining);
          xpos += micro;
          hyphenMicroRemaining -= micro;
        }
        if (wordIdx > 0 && punctuationMicroRemaining > 0 &&
            (isStandalonePunctuationMicroToken(lineWords[wordIdx]) ||
             isStandalonePunctuationMicroToken(lineWords[wordIdx - 1]))) {
          xpos += 1;
          punctuationMicroRemaining -= 1;
        }
        lineXPos.push_back(static_cast<int16_t>(xpos));'''
if ltr_anchor not in s:
    raise SystemExit('CPHUN-45 LTR microspacing anchor missing')
s = s.replace(ltr_anchor, ltr_new, 1)
p.write_text(s, encoding='utf-8')

# Static verification.
ui = Path('src/activities/settings/ButtonFunctionsActivity.cpp').read_text(encoding='utf-8')
picker = ui[ui.index('constexpr ReaderAction ACTIONS[] = {'):ui.index('};', ui.index('constexpr ReaderAction ACTIONS[] = {'))]
required_actions = [
    'ReaderAction::None', 'ReaderAction::PreviousPage', 'ReaderAction::NextPage',
    'ReaderAction::OpenReaderMenu', 'ReaderAction::OpenTextSettings', 'ReaderAction::OpenDictionary',
    'ReaderAction::GoHome', 'ReaderAction::ScreenMarginDown', 'ReaderAction::ScreenMarginUp',
    'ReaderAction::ToggleBookmark', 'ReaderAction::OpenBookmarks', 'ReaderAction::ReaderBack',
    'ReaderAction::FontSizeDown', 'ReaderAction::FontSizeUp',
    'ReaderAction::LineSpacingPrevious', 'ReaderAction::LineSpacingNext',
]
assert picker.count('ReaderAction::') == 16
for needle in required_actions: assert needle in picker, needle
assert 'ReaderAction::Screenshot' not in picker
for needle in ['Vissza', 'Betűméret +', 'Betűméret −', 'Soremelés +', 'Soremelés −']:
    assert needle in ui, needle

reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
for needle in [
    '#include "ReaderFontSizes.h"', 'readerFontPointSizes(&sdFontSystem.registry()',
    'configured == ReaderAction::FontSizeUp || configured == ReaderAction::FontSizeDown',
    '(idx + 1) % points.size()', '(idx + points.size() - 1) % points.size()',
    'configured == ReaderAction::LineSpacingNext || configured == ReaderAction::LineSpacingPrevious',
    '(current + 1) % kLineSpacingCount', '(current + kLineSpacingCount - 1) % kLineSpacingCount',
    'Button::Power', 'Button::PageBack', 'Button::PageForward',
]: assert needle in reader, needle

parsed = Path('lib/Epub/Epub/ParsedText.cpp').read_text(encoding='utf-8')
for needle in [
    'isStandalonePunctuationMicroToken', 'punctuationMicroOpportunityCount', 'punctuationMicroTotal',
    'punctuationMicroRemaining', 'std::min(4, hyphenMicroRemaining)',
    "case '.'", "case ','", "case ';'", "case ':'", "case '!'", "case '?'",
]: assert needle in parsed, needle

print('Applied CPHUN-45: 16-action picker, cyclic font/line stepping, hyphen +4/+4 and punctuation +1/+1 microspacing')
