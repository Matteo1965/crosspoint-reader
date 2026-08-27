from pathlib import Path
import re


def load(path):
    return Path(path).read_text(encoding='utf-8')


def save(path, text):
    Path(path).write_text(text, encoding='utf-8')


def once(text, old, new, label):
    c = text.count(old)
    if c != 1:
        raise SystemExit(f'{label}: expected 1 marker, found {c}')
    return text.replace(old, new, 1)

# Build id
Path('src/CPHUNBuildId.h').write_text('#pragma once\n\n#define CPHUN_BUILD_ID "CPHUN-260827-19"\n', encoding='utf-8')

# -----------------------------------------------------------------------------
# Settings + render spec
# -----------------------------------------------------------------------------
p = 'src/CrossPointSettings.h'
s = load(p)
s = once(s,
'''  // Keep the gap after a paragraph-opening en/em dash fixed and unbreakable.\n  uint8_t fixedDialogueSpacing = 0;\n  // Minimum natural word-space width in justified text: 50..100 percent.\n  uint8_t minimumSpacePercent = 100;\n''',
'''  // Keep the gap after a paragraph-opening en/em dash fixed and unbreakable.\n  uint8_t fixedDialogueSpacing = 0;\n  // 0 disables the post-layout +1 px letter-spacing correction; otherwise the\n  // value is the word-space stretch threshold in percent (120..240).\n  uint8_t letterSpacingLimitPercent = 0;\n  // Minimum natural word-space width in justified text: 50..100 percent.\n  uint8_t minimumSpacePercent = 100;\n''', 'settings letter spacing field')
s = once(s,
'''  uint8_t hyphenationEnabled = 0;\n  uint8_t hungarianHyphenationExtended = 0;\n''',
'''  uint8_t hyphenationEnabled = 0;\n  uint8_t hungarianHyphenationExtended = 0;\n  // Use U+00AD soft-hyphen opportunities embedded in the EPUB independently\n  // from the language hyphenation algorithm.\n  uint8_t softHyphenEnabled = 0;\n''', 'settings soft hyphen field')
save(p, s)

p = 'lib/Epub/Epub/ReaderRenderSpec.h'
s = load(p)
s = once(s,
'''  bool hyphenationEnabled = false;\n  bool hungarianHyphenationExtended = false;\n''',
'''  bool hyphenationEnabled = false;\n  bool hungarianHyphenationExtended = false;\n  bool softHyphenEnabled = false;\n''', 'render spec soft hyphen')
s = once(s,
'''  bool fixedDialogueSpacing = false;\n  uint8_t minimumSpacePercent = 100;\n''',
'''  bool fixedDialogueSpacing = false;\n  uint8_t letterSpacingLimitPercent = 0;\n  uint8_t minimumSpacePercent = 100;\n''', 'render spec letter spacing')
save(p, s)

p = 'src/CrossPointSettings.cpp'
s = load(p)
s = once(s,
'''  doc["hangingPunctuation"] = hangingPunctuation;\n  doc["fixedDialogueSpacing"] = fixedDialogueSpacing;\n  doc["minimumSpacePercent"] = minimumSpacePercent;\n''',
'''  doc["hangingPunctuation"] = hangingPunctuation;\n  doc["fixedDialogueSpacing"] = fixedDialogueSpacing;\n  doc["letterSpacingLimitPercent"] = letterSpacingLimitPercent;\n  doc["softHyphenEnabled"] = softHyphenEnabled;\n  doc["minimumSpacePercent"] = minimumSpacePercent;\n''', 'settings toJson')
s = once(s,
'''  fixedDialogueSpacing = (doc["fixedDialogueSpacing"] | (uint8_t)0) ? 1 : 0;\n  minimumSpacePercent = doc["minimumSpacePercent"] | (uint8_t)100;\n''',
'''  fixedDialogueSpacing = (doc["fixedDialogueSpacing"] | (uint8_t)0) ? 1 : 0;\n  softHyphenEnabled = (doc["softHyphenEnabled"] | (uint8_t)0) ? 1 : 0;\n  letterSpacingLimitPercent = doc["letterSpacingLimitPercent"] | (uint8_t)0;\n  if (letterSpacingLimitPercent != 0 &&\n      (letterSpacingLimitPercent < 120 || letterSpacingLimitPercent > 240 || letterSpacingLimitPercent % 20 != 0)) {\n    letterSpacingLimitPercent = 0;\n    needsResave = true;\n  }\n  minimumSpacePercent = doc["minimumSpacePercent"] | (uint8_t)100;\n''', 'settings fromJson')
old_spec = '''  spec.hyphenationEnabled = hyphenationEnabled != 0;\n  spec.hungarianHyphenationExtended = hungarianHyphenationExtended != 0;\n  // High nibble: percentage step (1=25% .. 4=100%). Low nibble: overhang cap in 4-pixel units.\n  // The physical cap is 80% of the selected margin: 5->4, 10->8, ... 40->32 px.\n  const uint8_t hangingLimitUnits = static_cast<uint8_t>((screenMargin * 4 / 5) / 4);\n  spec.hangingPunctuationLimitPx =\n      static_cast<uint8_t>(((SETTINGS.hangingPunctuation / 20) << 5) | (SETTINGS.screenMargin > 1 ? SETTINGS.screenMargin - 1 : 0));\n  spec.fixedDialogueSpacing = fixedDialogueSpacing != 0;\n  spec.minimumSpacePercent = minimumSpacePercent;\n'''
new_spec = '''  spec.hyphenationEnabled = hyphenationEnabled != 0;\n  spec.hungarianHyphenationExtended = hungarianHyphenationExtended != 0;\n  spec.softHyphenEnabled = softHyphenEnabled != 0;\n  // Optikai margó is now a simple Off/On setting. On means full (100%)\n  // punctuation overhang, with no reserved physical safety pixel.\n  spec.hangingPunctuationLimitPx = hangingPunctuation ? screenMargin : 0;\n  spec.fixedDialogueSpacing = fixedDialogueSpacing != 0;\n  spec.letterSpacingLimitPercent = letterSpacingLimitPercent;\n  spec.minimumSpacePercent = minimumSpacePercent;\n'''
s = once(s, old_spec, new_spec, 'readerRenderSpec')
save(p, s)

# -----------------------------------------------------------------------------
# Text settings UI
# -----------------------------------------------------------------------------
p = 'src/activities/settings/TextSettingsActivity.h'
s = load(p)
s = once(s,
'''    Alignment,\n    MinimumSpace,\n    ScreenMargin,\n''',
'''    Alignment,\n    MinimumSpace,\n    LetterSpacingCorrection,\n    ScreenMargin,\n''', 'layout row enum')
s = once(s,
'''  enum class StyleRow { FocusReading, Hyphenation, HungarianHyphenation, EmbeddedStyle, AntiAliasing, Count };\n''',
'''  enum class StyleRow { FocusReading, Hyphenation, SoftHyphen, EmbeddedStyle, AntiAliasing, Count };\n''', 'style row enum')
save(p, s)

p = 'src/activities/settings/TextSettingsActivity.cpp'
s = load(p)
s = once(s,
'''        } else if (i == static_cast<int>(LayoutRow::ScreenMargin)) {\n          item.label = I18N.get(StrId::STR_SCREEN_MARGIN);\n''',
'''        } else if (i == static_cast<int>(LayoutRow::LetterSpacingCorrection)) {\n          item.label = I18N.getLanguage() == Language::HU ? "Betűköz korrekció" : "Letter spacing correction";\n        } else if (i == static_cast<int>(LayoutRow::ScreenMargin)) {\n          item.label = I18N.get(StrId::STR_SCREEN_MARGIN);\n''', 'letter spacing label')
s = once(s,
'''      case Tab::Style:\n        item.label = i == static_cast<int>(StyleRow::HungarianHyphenation) ? "Magyar elválasztás"\n                                                                           : I18N.get(STYLE_ROW_NAME_IDS[i]);\n        break;\n''',
'''      case Tab::Style:\n        if (i == static_cast<int>(StyleRow::SoftHyphen)) {\n          item.label = I18N.getLanguage() == Language::HU ? "Beágyazott elválasztás" : "Embedded hyphenation";\n        } else {\n          item.label = I18N.get(STYLE_ROW_NAME_IDS[i]);\n        }\n        break;\n''', 'style labels')
# Optikai margó picker -> toggle
start = s.index('    case LayoutRow::HangingPunctuation: {')
end = s.index('    case LayoutRow::MinimumSpace:', start)
s = s[:start] + '''    case LayoutRow::HangingPunctuation:\n      SETTINGS.hangingPunctuation = SETTINGS.hangingPunctuation ? 0 : 100;\n      SETTINGS.saveToFile();\n      requestUpdate();\n      break;\n''' + s[end:]
# Insert letter spacing popup after MinimumSpace case
marker = '''    case LayoutRow::FixedDialogueSpacing:\n'''
insert = '''    case LayoutRow::LetterSpacingCorrection: {\n      const char* options[] = {tr(STR_STATE_OFF), "120%", "140%", "160%", "180%", "200%", "220%", "240%"};\n      int cur = 0;\n      if (SETTINGS.letterSpacingLimitPercent >= 120 && SETTINGS.letterSpacingLimitPercent <= 240) {\n        cur = 1 + (SETTINGS.letterSpacingLimitPercent - 120) / 20;\n      }\n      optionPopup_.show(I18N.getLanguage() == Language::HU ? "Betűköz korrekció" : "Letter spacing correction",\n                        options, 8, cur, [](int idx) {\n                          SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint8_t>(100 + idx * 20);\n                          SETTINGS.saveToFile();\n                        });\n      requestUpdate();\n      break;\n    }\n'''
s = once(s, marker, insert + marker, 'letter spacing popup')
s = once(s,
'''    case LayoutRow::HangingPunctuation:\n      return SETTINGS.hangingPunctuation ? std::to_string(SETTINGS.hangingPunctuation) + "%" : tr(STR_STATE_OFF);\n''',
'''    case LayoutRow::HangingPunctuation:\n      return SETTINGS.hangingPunctuation ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);\n    case LayoutRow::LetterSpacingCorrection:\n      return SETTINGS.letterSpacingLimitPercent ? std::to_string(SETTINGS.letterSpacingLimitPercent) + "%"\n                                                : tr(STR_STATE_OFF);\n''', 'layout value text')
# Replace style handler/value with 3-state algorithm + independent soft hyphen
old = '''void TextSettingsActivity::confirmStyleRow(int row) {\n  switch (static_cast<StyleRow>(row)) {\n    case StyleRow::FocusReading:\n      SETTINGS.focusReadingEnabled = !SETTINGS.focusReadingEnabled;\n      break;\n    case StyleRow::Hyphenation:\n      SETTINGS.hyphenationEnabled = !SETTINGS.hyphenationEnabled;\n      break;\n    case StyleRow::HungarianHyphenation:\n      SETTINGS.hungarianHyphenationExtended = !SETTINGS.hungarianHyphenationExtended;\n      break;\n'''
new = '''void TextSettingsActivity::confirmStyleRow(int row) {\n  switch (static_cast<StyleRow>(row)) {\n    case StyleRow::FocusReading:\n      SETTINGS.focusReadingEnabled = !SETTINGS.focusReadingEnabled;\n      break;\n    case StyleRow::Hyphenation: {\n      const char* optionsHu[] = {"KI", "Alap", "Kiterjesztett magyar"};\n      const char* optionsEn[] = {"Off", "Basic", "Extended Hungarian"};\n      const char** options = I18N.getLanguage() == Language::HU ? optionsHu : optionsEn;\n      const int cur = !SETTINGS.hyphenationEnabled ? 0 : (SETTINGS.hungarianHyphenationExtended ? 2 : 1);\n      optionPopup_.show(I18N.get(StrId::STR_HYPHENATION), options, 3, cur, [](int idx) {\n        SETTINGS.hyphenationEnabled = idx == 0 ? 0 : 1;\n        SETTINGS.hungarianHyphenationExtended = idx == 2 ? 1 : 0;\n        SETTINGS.saveToFile();\n      });\n      requestUpdate();\n      return;\n    }\n    case StyleRow::SoftHyphen:\n      SETTINGS.softHyphenEnabled = !SETTINGS.softHyphenEnabled;\n      break;\n'''
s = once(s, old, new, 'style handler')
s = once(s,
'''    case StyleRow::Hyphenation:\n      return SETTINGS.hyphenationEnabled ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);\n    case StyleRow::HungarianHyphenation:\n      return SETTINGS.hungarianHyphenationExtended ? "Kiterjesztett" : "Alap";\n''',
'''    case StyleRow::Hyphenation:\n      if (!SETTINGS.hyphenationEnabled) return tr(STR_STATE_OFF);\n      return SETTINGS.hungarianHyphenationExtended\n                 ? (I18N.getLanguage() == Language::HU ? "Kiterjesztett magyar" : "Extended Hungarian")\n                 : (I18N.getLanguage() == Language::HU ? "Alap" : "Basic");\n    case StyleRow::SoftHyphen:\n      return SETTINGS.softHyphenEnabled ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);\n''', 'style value')
s = s.replace('StyleRow::HungarianHyphenation', 'StyleRow::SoftHyphen')
save(p, s)

# -----------------------------------------------------------------------------
# Hyphenator: independently switch EPUB U+00AD opportunities
# -----------------------------------------------------------------------------
p = 'lib/Epub/Epub/hyphenation/Hyphenator.h'
s = load(p)
s = once(s,
'''  static std::vector<BreakInfo> breakOffsets(const std::string& word, bool includeFallback);\n''',
'''  static std::vector<BreakInfo> breakOffsets(const std::string& word, bool includeFallback);\n  // Returns only explicit U+00AD opportunities, used when language hyphenation is Off.\n  static std::vector<BreakInfo> softHyphenBreakOffsets(const std::string& word);\n''', 'hyphenator soft API')
s = once(s,
'''  static void setHungarianExtended(bool enabled);\n''',
'''  static void setHungarianExtended(bool enabled);\n  static void setSoftHyphenEnabled(bool enabled);\n''', 'hyphenator setter')
s = once(s,
'''  static bool hungarianExtended_;\n''',
'''  static bool hungarianExtended_;\n  static bool softHyphenEnabled_;\n''', 'hyphenator static field')
save(p, s)

p = 'lib/Epub/Epub/hyphenation/Hyphenator.cpp'
s = load(p)
s = once(s,
'''bool Hyphenator::hungarianExtended_ = false;\n''',
'''bool Hyphenator::hungarianExtended_ = false;\nbool Hyphenator::softHyphenEnabled_ = false;\n''', 'soft static init')
s = once(s,
'''  auto cps = collectCodepoints(word);\n  if (preferredLanguageIsHungarian_) {\n''',
'''  auto cps = collectCodepoints(word);\n  if (!softHyphenEnabled_) {\n    cps.erase(std::remove_if(cps.begin(), cps.end(), [](const CodepointInfo& cp) { return isSoftHyphen(cp.value); }),\n              cps.end());\n  }\n  if (preferredLanguageIsHungarian_) {\n''', 'ignore soft when disabled')
insert_before = '''std::vector<Hyphenator::BreakInfo> Hyphenator::breakOffsetsForLanguage'''
soft_fn = '''std::vector<Hyphenator::BreakInfo> Hyphenator::softHyphenBreakOffsets(const std::string& word) {\n  auto cps = collectCodepoints(word);\n  std::vector<BreakInfo> out;\n  for (size_t i = 1; i + 1 < cps.size(); ++i) {\n    if (isSoftHyphen(cps[i].value) && isAlphabetic(cps[i - 1].value) && isAlphabetic(cps[i + 1].value)) {\n      out.push_back({cps[i + 1].byteOffset, true});\n    }\n  }\n  return out;\n}\n\n'''
s = once(s, insert_before, soft_fn + insert_before, 'soft-only break fn')
s = once(s,
'''void Hyphenator::setHungarianExtended(const bool enabled) { hungarianExtended_ = enabled; }\n''',
'''void Hyphenator::setHungarianExtended(const bool enabled) { hungarianExtended_ = enabled; }\n\nvoid Hyphenator::setSoftHyphenEnabled(const bool enabled) { softHyphenEnabled_ = enabled; }\n''', 'soft setter impl')
save(p, s)

# -----------------------------------------------------------------------------
# ParsedText: render-only last line, fixed dialogue gap, embedded SHY, tracking
# -----------------------------------------------------------------------------
p = 'lib/Epub/Epub/ParsedText.h'
s = load(p)
s = once(s,
'''  bool hyphenationEnabled;\n  bool focusReadingEnabled;\n''',
'''  bool hyphenationEnabled;\n  bool softHyphenEnabled;\n  bool focusReadingEnabled;\n''', 'ParsedText soft field')
s = once(s,
'''  bool fixedDialogueSpacing;\n  bool isNaturalAlign;\n''',
'''  bool fixedDialogueSpacing;\n  uint8_t letterSpacingLimitPercent;\n  bool isNaturalAlign;\n''', 'ParsedText tracking field')
s = once(s,
'''  explicit ParsedText(const uint8_t extraParagraphSpacing, const bool hyphenationEnabled = false,\n                      const bool focusReadingEnabled = false, const uint8_t hangingPunctuationLimitPx = 0,\n                      const bool fixedDialogueSpacing = false, const BlockStyle& blockStyle = BlockStyle())\n''',
'''  explicit ParsedText(const uint8_t extraParagraphSpacing, const bool hyphenationEnabled = false,\n                      const bool softHyphenEnabled = false, const bool focusReadingEnabled = false,\n                      const uint8_t hangingPunctuationLimitPx = 0, const bool fixedDialogueSpacing = false,\n                      const uint8_t letterSpacingLimitPercent = 0, const BlockStyle& blockStyle = BlockStyle())\n''', 'ParsedText ctor signature')
s = once(s,
'''        hyphenationEnabled(hyphenationEnabled),\n        focusReadingEnabled(focusReadingEnabled),\n''',
'''        hyphenationEnabled(hyphenationEnabled),\n        softHyphenEnabled(softHyphenEnabled),\n        focusReadingEnabled(focusReadingEnabled),\n''', 'ParsedText ctor soft init')
s = once(s,
'''        fixedDialogueSpacing(fixedDialogueSpacing),\n        isNaturalAlign(false),\n''',
'''        fixedDialogueSpacing(fixedDialogueSpacing),\n        letterSpacingLimitPercent(letterSpacingLimitPercent),\n        isNaturalAlign(false),\n''', 'ParsedText ctor tracking init')
save(p, s)

p = 'lib/Epub/Epub/ParsedText.cpp'
s = load(p)
# Standalone ASCII hyphen surrounded by source word boundaries becomes en dash in-memory.
s = once(s,
'''  if (fixedDialogueSpacing && words.empty() && !attachToPrevious && word == "-") {\n    word = "\\xE2\\x80\\x93";\n  }\n''',
'''  if (!attachToPrevious && word == "-") {\n    word = "\\xE2\\x80\\x93";\n  }\n''', 'ASCII dash normalization')
# Greedy breaker runs when either source of hyphenation opportunities is active.
s = s.replace('renderer.ensureSdCardFontReady(fontId, words, hyphenationEnabled, styleMask);',
              'renderer.ensureSdCardFontReady(fontId, words, hyphenationEnabled || softHyphenEnabled, styleMask);')
s = once(s,
'''  if (hyphenationEnabled) {\n    // Use greedy layout that can split words mid-loop when a hyphenated prefix fits.\n''',
'''  if (hyphenationEnabled || softHyphenEnabled) {\n    // Use greedy layout that can split words mid-loop when a hyphenated prefix fits.\n''', 'greedy activation')
s = once(s,
'''  auto breakInfos = Hyphenator::breakOffsets(word, allowFallbackBreaks);\n''',
'''  auto breakInfos = hyphenationEnabled ? Hyphenator::breakOffsets(word, allowFallbackBreaks)\n                                      : Hyphenator::softHyphenBreakOffsets(word);\n''', 'break source selection')
# Fixed dialogue gap is always the font's natural space, independent of Min. szóköz.
pat = re.compile(r'(if \(fixedDialogueSpacing[^\{]*\{)(.*?)(\n\s*\})', re.S)
def naturalize(m):
    body = m.group(2)
    body2 = re.sub(r'scaledNormalSpaceAdvance\((renderer\.getSpaceAdvance\(.*?\)),\s*minimumSpacePercent_\)', r'\1', body, flags=re.S)
    return m.group(1) + body2 + m.group(3)
s = pat.sub(naturalize, s)
# Mark whether the already-selected final line can be drawn at natural spacing.
s = once(s,
'''  const int effectivePageWidth = pageWidth - firstLineIndent;\n  const bool isLastLine = breakIndex == lineBreakIndices.size() - 1;\n\n  // A paragraph's last justified line should use natural (100%) spaces whenever it fits.\n''',
'''  const int effectivePageWidth = pageWidth - firstLineIndent;\n  const bool isLastLine = breakIndex == lineBreakIndices.size() - 1;\n  bool useNaturalLastLineSpacing = false;\n\n  // A paragraph's last justified line should use natural (100%) spaces whenever it fits.\n''', 'last line flag')
s = once(s,
'''    if (lineWordWidthSum + natural100 + extraStartOffset + extraEndOffset <= effectivePageWidth) {\n      totalNaturalGaps = natural100;\n    }\n''',
'''    if (lineWordWidthSum + natural100 + extraStartOffset + extraEndOffset <= effectivePageWidth) {\n      totalNaturalGaps = natural100;\n      useNaturalLastLineSpacing = true;\n    }\n''', 'last line flag set')
# Compute optional +1 px intra-word tracking only after line breaks are final.
old = '''  const int spareSpace =\n      effectivePageWidth + hangingAllowance - extraStartOffset - extraEndOffset - lineWordWidthSum - totalNaturalGaps;\n  const int justifyExtra = (effectiveAlignment == CssTextAlign::Justify && !isLastLine)\n                               ? computeJustifyExtra(spareSpace, actualGapCount)\n                               : 0;\n'''
new = '''  const int spareSpace =\n      effectivePageWidth + hangingAllowance - extraStartOffset - extraEndOffset - lineWordWidthSum - totalNaturalGaps;\n\n  uint8_t letterSpacingPx = 0;\n  int trackingExtraTotal = 0;\n  if (letterSpacingLimitPercent > 0 && effectiveAlignment == CssTextAlign::Justify && !isLastLine &&\n      !blockStyle.isRtl && !hasRtlWord && !focusReadingEnabled && rubyTexts.empty() && actualGapCount > 0) {\n    int natural100Gaps = 0;\n    size_t normalGapCount = 0;\n    for (size_t wordIdx = 1; wordIdx < lineWordCount; ++wordIdx) {\n      const size_t boundaryIdx = lastBreakAt + wordIdx;\n      if (!continuesVec[boundaryIdx] && !noSpaceBeforeVec[boundaryIdx]) {\n        natural100Gaps += renderer.getSpaceAdvance(fontId, lastCodepoint(lineWords[wordIdx - 1]),\n                                                   firstCodepoint(lineWords[wordIdx]), lineWordStyles[wordIdx - 1]);\n        normalGapCount++;\n      }\n    }\n    if (normalGapCount > 0 && natural100Gaps > 0) {\n      const int finalAverageGap = (totalNaturalGaps + std::max(0, spareSpace)) / static_cast<int>(actualGapCount);\n      const int naturalAverageGap = natural100Gaps / static_cast<int>(normalGapCount);\n      if (finalAverageGap * 100 > naturalAverageGap * letterSpacingLimitPercent) {\n        for (const auto& w : lineWords) {\n          const uint32_t cps = countCodepoints(w);\n          if (cps > 1) trackingExtraTotal += static_cast<int>(cps - 1);\n        }\n        if (trackingExtraTotal > 0 && trackingExtraTotal < spareSpace) letterSpacingPx = 1;\n      }\n    }\n  }\n  const int adjustedSpareSpace = spareSpace - (letterSpacingPx ? trackingExtraTotal : 0);\n  const int justifyExtra = (effectiveAlignment == CssTextAlign::Justify && !isLastLine)\n                               ? computeJustifyExtra(adjustedSpareSpace, actualGapCount)\n                               : 0;\n'''
s = once(s, old, new, 'tracking calculation')
s = once(s,
'''      const int justifyRemainder = (effectiveAlignment == CssTextAlign::Justify && !isLastLine && actualGapCount > 0)\n                                   ? spareSpace - justifyExtra * static_cast<int>(actualGapCount)\n                                   : 0;\n''',
'''      const int justifyRemainder = (effectiveAlignment == CssTextAlign::Justify && !isLastLine && actualGapCount > 0)\n                                   ? adjustedSpareSpace - justifyExtra * static_cast<int>(actualGapCount)\n                                   : 0;\n''', 'tracking remainder') if '      const int justifyRemainder' in s else s
# The source indentation is two spaces, handle exact current form too.
s = s.replace('''  const int justifyRemainder = (effectiveAlignment == CssTextAlign::Justify && !isLastLine && actualGapCount > 0)\n                                   ? spareSpace - justifyExtra * static_cast<int>(actualGapCount)\n                                   : 0;''',
'''  const int justifyRemainder = (effectiveAlignment == CssTextAlign::Justify && !isLastLine && actualGapCount > 0)\n                                   ? adjustedSpareSpace - justifyExtra * static_cast<int>(actualGapCount)\n                                   : 0;''')
# In the plain LTR positioning branch only, use natural last-line gap and account for tracked word width.
needle = '''    } else {\n      // LTR: position words from left to right\n      int xpos = firstLineIndent + extraStartOffset;\n'''
replacement = '''    } else {\n      // LTR: position words from left to right. Final-line natural spacing and\n      // optional +1 px tracking are render-only corrections: line breaks are unchanged.\n      const uint8_t ltrSpacePercent =\n          (useNaturalLastLineSpacing && effectiveAlignment == CssTextAlign::Justify) ? 100\n                                                                                     : (blockStyle.alignment == CssTextAlign::Justify ? minimumSpacePercent_ : 100);\n      int xpos = firstLineIndent + extraStartOffset;\n'''
s = once(s, needle, replacement, 'LTR spacing selector')
# Only inside the LTR branch, switch normal spaces to ltrSpacePercent.
ltr_start = s.index('// LTR: position words from left to right. Final-line natural spacing')
ltr_end = s.index('\n    }\n  }\n\n  const auto focusBoundaryAt', ltr_start)
ltr = s[ltr_start:ltr_end]
ltr = ltr.replace('(blockStyle.alignment == CssTextAlign::Justify ? minimumSpacePercent_ : 100)', 'ltrSpacePercent')
# Naturalize fixed dialogue continuation in LTR if the generic block rewrite missed it.
ltr = re.sub(r'scaledNormalSpaceAdvance\((renderer\.getSpaceAdvance\(.*?\)),\s*minimumSpacePercent_\)', r'\1', ltr, flags=re.S)
# Add tracking extra to each word's advance in the LTR branch.
ltr = ltr.replace('int advance = wordWidths[lastBreakAt + wordIdx];',
                  'int advance = wordWidths[lastBreakAt + wordIdx] + (letterSpacingPx ? static_cast<int>(std::max<uint32_t>(1, countCodepoints(lineWords[wordIdx])) - 1) : 0);')
ltr = ltr.replace('xpos += wordWidths[lastBreakAt + wordIdx] + gap;',
                  'xpos += wordWidths[lastBreakAt + wordIdx] + (letterSpacingPx ? static_cast<int>(std::max<uint32_t>(1, countCodepoints(lineWords[wordIdx])) - 1) : 0) + gap;')
s = s[:ltr_start] + ltr + s[ltr_end:]
# Pass tracking to TextBlock.
s = s.replace('blockStyle, std::move(lineRubyTexts));', 'blockStyle, std::move(lineRubyTexts), letterSpacingPx);')
save(p, s)

# -----------------------------------------------------------------------------
# Parser wiring
# -----------------------------------------------------------------------------
p = 'lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h'
s = load(p)
s = once(s,
'''  bool hyphenationEnabled;\n  bool focusReadingEnabled;\n''',
'''  bool hyphenationEnabled;\n  bool softHyphenEnabled;\n  bool focusReadingEnabled;\n''', 'parser soft member')
s = once(s,
'''  bool fixedDialogueSpacing;\n  const CssParser* cssParser;\n''',
'''  bool fixedDialogueSpacing;\n  uint8_t letterSpacingLimitPercent;\n  const CssParser* cssParser;\n''', 'parser tracking member')
s = once(s,
'''      const uint16_t viewportWidth, const uint16_t viewportHeight, const bool hyphenationEnabled,\n      const bool focusReadingEnabled, const uint8_t hangingPunctuationLimitPx, const bool fixedDialogueSpacing,\n''',
'''      const uint16_t viewportWidth, const uint16_t viewportHeight, const bool hyphenationEnabled,\n      const bool softHyphenEnabled, const bool focusReadingEnabled, const uint8_t hangingPunctuationLimitPx,\n      const bool fixedDialogueSpacing, const uint8_t letterSpacingLimitPercent,\n''', 'parser ctor signature')
s = once(s,
'''        hyphenationEnabled(hyphenationEnabled),\n        focusReadingEnabled(focusReadingEnabled),\n''',
'''        hyphenationEnabled(hyphenationEnabled),\n        softHyphenEnabled(softHyphenEnabled),\n        focusReadingEnabled(focusReadingEnabled),\n''', 'parser soft init')
s = once(s,
'''        fixedDialogueSpacing(fixedDialogueSpacing),\n        completePageFn(completePageFn),\n''',
'''        fixedDialogueSpacing(fixedDialogueSpacing),\n        letterSpacingLimitPercent(letterSpacingLimitPercent),\n        completePageFn(completePageFn),\n''', 'parser tracking init')
save(p, s)

p = 'lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp'
s = load(p)
s = once(s,
'''  currentTextBlock.reset(new ParsedText(extraParagraphSpacing, hyphenationEnabled, focusReadingEnabled,\n                                        hangingPunctuationLimitPx, fixedDialogueSpacing, blockStyle));\n''',
'''  currentTextBlock.reset(new ParsedText(extraParagraphSpacing, hyphenationEnabled, softHyphenEnabled,\n                                        focusReadingEnabled, hangingPunctuationLimitPx, fixedDialogueSpacing,\n                                        letterSpacingLimitPercent, blockStyle));\n''', 'parser ParsedText construction')
save(p, s)

# -----------------------------------------------------------------------------
# TextBlock: persist and render per-line +1 px tracking
# -----------------------------------------------------------------------------
p = 'lib/Epub/Epub/blocks/TextBlock.h'
s = load(p)
s = once(s,
'''  bool focusPresent = false;\n  bool simpleRender = false;\n''',
'''  bool focusPresent = false;\n  uint8_t letterSpacingPx = 0;\n  bool simpleRender = false;\n''', 'TextBlock tracking field')
s = once(s,
'''                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle = BlockStyle(),\n                     std::vector<std::string> rubyTexts = {});\n''',
'''                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle = BlockStyle(),\n                     std::vector<std::string> rubyTexts = {}, uint8_t letterSpacingPx = 0);\n''', 'TextBlock ctor signature')
save(p, s)

p = 'lib/Epub/Epub/blocks/TextBlock.cpp'
s = load(p)
s = once(s, '#include <Logging.h>\n', '#include <Logging.h>\n#include <Utf8.h>\n', 'Utf8 include')
s = once(s,
'''                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle,\n                     std::vector<std::string> rubyTexts)\n    : blockStyle(blockStyle), rubyTexts(std::move(rubyTexts)) {\n''',
'''                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle,\n                     std::vector<std::string> rubyTexts, const uint8_t letterSpacingPx)\n    : blockStyle(blockStyle), letterSpacingPx(letterSpacingPx), rubyTexts(std::move(rubyTexts)) {\n''', 'TextBlock ctor impl')
helper_marker = 'void TextBlock::render(const GfxRenderer& renderer, const int fontId, const int x, const int y) const {'
helper = '''namespace {\nvoid drawTrackedLtrWord(const GfxRenderer& renderer, const int fontId, int x, const int y, const char* text,\n                        const EpdFontFamily::Style style, const BidiUtils::BidiBaseDir baseDir,\n                        const uint8_t letterSpacingPx) {\n  const auto* ptr = reinterpret_cast<const unsigned char*>(text);\n  while (*ptr) {\n    const auto* start = ptr;\n    const uint32_t cp = utf8NextCodepoint(&ptr);\n    const size_t len = static_cast<size_t>(ptr - start);\n    char glyph[5] = {};\n    memcpy(glyph, start, std::min<size_t>(len, 4));\n    renderer.drawText(fontId, x, y, glyph, true, style, baseDir);\n    if (*ptr) {\n      const auto* peek = ptr;\n      const uint32_t nextCp = utf8NextCodepoint(&peek);\n      x += renderer.getTextAdvanceX(fontId, glyph, style);\n      x += renderer.getKerning(fontId, cp, nextCp, style);\n      x += letterSpacingPx;\n    }\n  }\n}\n}  // namespace\n\n'''
s = once(s, helper_marker, helper + helper_marker, 'tracked draw helper')
s = once(s,
'''      renderer.drawText(fontId, xposArr[i] + x, y, wordText(i), true, wordStyle(i), baseDir);\n''',
'''      if (letterSpacingPx > 0 && baseDir != BidiUtils::BidiBaseDir::RTL) {\n        drawTrackedLtrWord(renderer, fontId, xposArr[i] + x, y, wordText(i), wordStyle(i), baseDir, letterSpacingPx);\n      } else {\n        renderer.drawText(fontId, xposArr[i] + x, y, wordText(i), true, wordStyle(i), baseDir);\n      }\n''', 'simple tracked render')
s = once(s,
'''  serialization::writePod(file, textBytes);\n''',
'''  serialization::writePod(file, textBytes);\n  serialization::writePod(file, letterSpacingPx);\n''', 'serialize tracking')
s = once(s,
'''  uint16_t textBytes;\n  serialization::readPod(file, wc);\n  serialization::readPod(file, hasFocus);\n  serialization::readPod(file, textBytes);\n''',
'''  uint16_t textBytes;\n  uint8_t letterSpacingPx;\n  serialization::readPod(file, wc);\n  serialization::readPod(file, hasFocus);\n  serialization::readPod(file, textBytes);\n  serialization::readPod(file, letterSpacingPx);\n''', 'deserialize tracking read')
s = once(s,
'''  block->focusPresent = hasFocus != 0;\n''',
'''  block->focusPresent = hasFocus != 0;\n  block->letterSpacingPx = letterSpacingPx;\n''', 'deserialize tracking assign')
save(p, s)

# -----------------------------------------------------------------------------
# Section cache + parser construction
# -----------------------------------------------------------------------------
p = 'lib/Epub/Epub/Section.cpp'
s = load(p)
# version bump
s = re.sub(r'constexpr uint8_t SECTION_FILE_VERSION = (\d+);',
           lambda m: f'constexpr uint8_t SECTION_FILE_VERSION = {int(m.group(1)) + 1};', s, count=1)
# Header size gets bool softHyphen + uint8 letterSpacing.
s = once(s,
'''                                 sizeof(bool) + sizeof(uint8_t) + sizeof(bool) + sizeof(uint8_t) + sizeof(bool) + sizeof(uint8_t) +\n                                 sizeof(uint32_t) + sizeof(uint32_t) + sizeof(uint32_t) + sizeof(uint32_t) +\n''',
'''                                 sizeof(bool) + sizeof(bool) + sizeof(uint8_t) + sizeof(bool) + sizeof(uint8_t) + sizeof(uint8_t) + sizeof(bool) + sizeof(uint8_t) +\n                                 sizeof(uint32_t) + sizeof(uint32_t) + sizeof(uint32_t) + sizeof(uint32_t) +\n''', 'header size fields')
s = once(s,
'''                                   sizeof(spec.hyphenationEnabled) + sizeof(spec.hungarianHyphenationExtended) +\n                                   sizeof(spec.hangingPunctuationLimitPx) + sizeof(spec.fixedDialogueSpacing) +\n                                   sizeof(spec.minimumSpacePercent) + sizeof(spec.embeddedStyle) + sizeof(spec.imageRendering) +\n''',
'''                                   sizeof(spec.hyphenationEnabled) + sizeof(spec.hungarianHyphenationExtended) +\n                                   sizeof(spec.softHyphenEnabled) + sizeof(spec.hangingPunctuationLimitPx) +\n                                   sizeof(spec.fixedDialogueSpacing) + sizeof(spec.letterSpacingLimitPercent) +\n                                   sizeof(spec.minimumSpacePercent) + sizeof(spec.embeddedStyle) + sizeof(spec.imageRendering) +\n''', 'header assert fields')
s = once(s,
'''  serialization::writePod(file, spec.hyphenationEnabled);\n  serialization::writePod(file, spec.hungarianHyphenationExtended);\n  serialization::writePod(file, spec.hangingPunctuationLimitPx);\n  serialization::writePod(file, spec.fixedDialogueSpacing);\n  serialization::writePod(file, spec.minimumSpacePercent);\n''',
'''  serialization::writePod(file, spec.hyphenationEnabled);\n  serialization::writePod(file, spec.hungarianHyphenationExtended);\n  serialization::writePod(file, spec.softHyphenEnabled);\n  serialization::writePod(file, spec.hangingPunctuationLimitPx);\n  serialization::writePod(file, spec.fixedDialogueSpacing);\n  serialization::writePod(file, spec.letterSpacingLimitPercent);\n  serialization::writePod(file, spec.minimumSpacePercent);\n''', 'header write')
s = once(s,
'''    bool fileHungarianHyphenationExtended;\n    uint8_t fileHangingPunctuationLimitPx;\n    bool fileFixedDialogueSpacing;\n    uint8_t fileMinimumSpacePercent;\n''',
'''    bool fileHungarianHyphenationExtended;\n    bool fileSoftHyphenEnabled;\n    uint8_t fileHangingPunctuationLimitPx;\n    bool fileFixedDialogueSpacing;\n    uint8_t fileLetterSpacingLimitPercent;\n    uint8_t fileMinimumSpacePercent;\n''', 'header locals')
s = once(s,
'''    serialization::readPod(file, fileHyphenationEnabled);\n    serialization::readPod(file, fileHungarianHyphenationExtended);\n    serialization::readPod(file, fileHangingPunctuationLimitPx);\n    serialization::readPod(file, fileFixedDialogueSpacing);\n    serialization::readPod(file, fileMinimumSpacePercent);\n''',
'''    serialization::readPod(file, fileHyphenationEnabled);\n    serialization::readPod(file, fileHungarianHyphenationExtended);\n    serialization::readPod(file, fileSoftHyphenEnabled);\n    serialization::readPod(file, fileHangingPunctuationLimitPx);\n    serialization::readPod(file, fileFixedDialogueSpacing);\n    serialization::readPod(file, fileLetterSpacingLimitPercent);\n    serialization::readPod(file, fileMinimumSpacePercent);\n''', 'header read')
s = once(s,
'''        spec.hyphenationEnabled != fileHyphenationEnabled ||\n        spec.hungarianHyphenationExtended != fileHungarianHyphenationExtended ||\n        spec.hangingPunctuationLimitPx != fileHangingPunctuationLimitPx ||\n        spec.fixedDialogueSpacing != fileFixedDialogueSpacing || spec.minimumSpacePercent != fileMinimumSpacePercent ||\n''',
'''        spec.hyphenationEnabled != fileHyphenationEnabled ||\n        spec.hungarianHyphenationExtended != fileHungarianHyphenationExtended ||\n        spec.softHyphenEnabled != fileSoftHyphenEnabled ||\n        spec.hangingPunctuationLimitPx != fileHangingPunctuationLimitPx ||\n        spec.fixedDialogueSpacing != fileFixedDialogueSpacing ||\n        spec.letterSpacingLimitPercent != fileLetterSpacingLimitPercent ||\n        spec.minimumSpacePercent != fileMinimumSpacePercent ||\n''', 'header compare')
s = once(s,
'''      spec.paragraphAlignment, spec.viewportWidth, spec.viewportHeight, spec.hyphenationEnabled,\n      spec.focusReadingEnabled, spec.hangingPunctuationLimitPx, spec.fixedDialogueSpacing,\n''',
'''      spec.paragraphAlignment, spec.viewportWidth, spec.viewportHeight, spec.hyphenationEnabled,\n      spec.softHyphenEnabled, spec.focusReadingEnabled, spec.hangingPunctuationLimitPx, spec.fixedDialogueSpacing,\n      spec.letterSpacingLimitPercent,\n''', 'parser args')
s = once(s,
'''  Hyphenator::setHungarianExtended(spec.hungarianHyphenationExtended);\n''',
'''  Hyphenator::setHungarianExtended(spec.hungarianHyphenationExtended);\n  Hyphenator::setSoftHyphenEnabled(spec.softHyphenEnabled);\n''', 'soft hyphen runtime setter')
save(p, s)

# -----------------------------------------------------------------------------
# Floating punctuation now means full punctuation advance, plain pixel cap.
# -----------------------------------------------------------------------------
p = 'lib/Epub/Epub/ParsedText.cpp'
s = load(p)
old = '''int hangingPunctuationAllowance(const GfxRenderer& renderer, const int fontId, const std::string& word,\n                                const EpdFontFamily::Style style, const uint8_t packedSetting) {\n  const uint8_t percentStep = packedSetting >> 5;\n  const uint8_t pixelLimit = static_cast<uint8_t>(packedSetting & 0x1F);\n  if (percentStep == 0 || pixelLimit == 0 || word.empty()) return 0;\n'''
new = '''int hangingPunctuationAllowance(const GfxRenderer& renderer, const int fontId, const std::string& word,\n                                const EpdFontFamily::Style style, const uint8_t pixelLimit) {\n  if (pixelLimit == 0 || word.empty()) return 0;\n'''
s = once(s, old, new, 'floating unpack removal')
s = once(s,
'''  const int proportionalAdvance = (punctuationAdvance * std::min<int>(percentStep, 5) + 4) / 5;\n  return std::min<int>(pixelLimit, proportionalAdvance);\n''',
'''  return std::min<int>(pixelLimit, punctuationAdvance);\n''', 'floating full advance')
save(p, s)

print('CPHUN-260827-19 patch applied')
