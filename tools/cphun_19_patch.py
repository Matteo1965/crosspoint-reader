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
'''  uint8_t hyphenationEnabled = 0;\n  uint8_t hungarianHyphenationExtended = 0;\n  uint8_t softHyphenEnabled = 0;\n''', 'settings soft hyphen field')
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
new_spec = '''  spec.hyphenationEnabled = hyphenationEnabled != 0;\n  spec.hungarianHyphenationExtended = hungarianHyphenationExtended != 0;\n  spec.softHyphenEnabled = softHyphenEnabled != 0;\n  spec.hangingPunctuationLimitPx = hangingPunctuation ? static_cast<uint8_t>(std::min<int>(31, screenMargin)) : 0;\n  spec.fixedDialogueSpacing = fixedDialogueSpacing != 0;\n  spec.letterSpacingLimitPercent = letterSpacingLimitPercent;\n  spec.minimumSpacePercent = minimumSpacePercent;\n'''
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
start = s.index('    case LayoutRow::HangingPunctuation: {')
end = s.index('    case LayoutRow::MinimumSpace:', start)
s = s[:start] + '''    case LayoutRow::HangingPunctuation:\n      SETTINGS.hangingPunctuation = SETTINGS.hangingPunctuation ? 0 : 100;\n      SETTINGS.saveToFile();\n      requestUpdate();\n      break;\n''' + s[end:]
marker = '''    case LayoutRow::FixedDialogueSpacing:\n'''
insert = '''    case LayoutRow::LetterSpacingCorrection: {\n      const char* options[] = {tr(STR_STATE_OFF), "120%", "140%", "160%", "180%", "200%", "220%", "240%"};\n      int cur = 0;\n      if (SETTINGS.letterSpacingLimitPercent >= 120 && SETTINGS.letterSpacingLimitPercent <= 240) {\n        cur = 1 + (SETTINGS.letterSpacingLimitPercent - 120) / 20;\n      }\n      optionPopup_.show(I18N.getLanguage() == Language::HU ? "Betűköz korrekció" : "Letter spacing correction",\n                        options, 8, cur, [](int idx) {\n                          SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint8_t>(100 + idx * 20);\n                          SETTINGS.saveToFile();\n                        });\n      requestUpdate();\n      break;\n    }\n'''
s = s.replace(marker, insert + marker, 1)
s = once(s,
'''    case LayoutRow::HangingPunctuation:\n      return SETTINGS.hangingPunctuation ? std::to_string(SETTINGS.hangingPunctuation) + "%" : tr(STR_STATE_OFF);\n''',
'''    case LayoutRow::HangingPunctuation:\n      return SETTINGS.hangingPunctuation ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);\n    case LayoutRow::LetterSpacingCorrection:\n      return SETTINGS.letterSpacingLimitPercent ? std::to_string(SETTINGS.letterSpacingLimitPercent) + "%"\n                                                : tr(STR_STATE_OFF);\n''', 'layout value text')
old = '''void TextSettingsActivity::confirmStyleRow(int row) {\n  switch (static_cast<StyleRow>(row)) {\n    case StyleRow::FocusReading:\n      SETTINGS.focusReadingEnabled = !SETTINGS.focusReadingEnabled;\n      break;\n    case StyleRow::Hyphenation:\n      SETTINGS.hyphenationEnabled = !SETTINGS.hyphenationEnabled;\n      break;\n    case StyleRow::HungarianHyphenation:\n      SETTINGS.hungarianHyphenationExtended = !SETTINGS.hungarianHyphenationExtended;\n      break;\n'''
new = '''void TextSettingsActivity::confirmStyleRow(int row) {\n  switch (static_cast<StyleRow>(row)) {\n    case StyleRow::FocusReading:\n      SETTINGS.focusReadingEnabled = !SETTINGS.focusReadingEnabled;\n      break;\n    case StyleRow::Hyphenation: {\n      const char* optionsHu[] = {"KI", "Alap", "Kiterjesztett magyar"};\n      const char* optionsEn[] = {"Off", "Basic", "Extended Hungarian"};\n      const char** options = I18N.getLanguage() == Language::HU ? optionsHu : optionsEn;\n      const int cur = !SETTINGS.hyphenationEnabled ? 0 : (SETTINGS.hungarianHyphenationExtended ? 2 : 1);\n      optionPopup_.show(I18N.get(StrId::STR_HYPHENATION), options, 3, cur, [](int idx) {\n        SETTINGS.hyphenationEnabled = idx == 0 ? 0 : 1;\n        SETTINGS.hungarianHyphenationExtended = idx == 2 ? 1 : 0;\n        SETTINGS.saveToFile();\n      });\n      requestUpdate();\n      return;\n    }\n    case StyleRow::SoftHyphen:\n      SETTINGS.softHyphenEnabled = !SETTINGS.softHyphenEnabled;\n      break;\n'''
s = once(s, old, new, 'style handler')
s = once(s,
'''    case StyleRow::Hyphenation:\n      return SETTINGS.hyphenationEnabled ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);\n    case StyleRow::HungarianHyphenation:\n      return SETTINGS.hungarianHyphenationExtended ? "Kiterjesztett" : "Alap";\n''',
'''    case StyleRow::Hyphenation:\n      if (!SETTINGS.hyphenationEnabled) return tr(STR_STATE_OFF);\n      return SETTINGS.hungarianHyphenationExtended\n                 ? (I18N.getLanguage() == Language::HU ? "Kiterjesztett magyar" : "Extended Hungarian")\n                 : (I18N.getLanguage() == Language::HU ? "Alap" : "Basic");\n    case StyleRow::SoftHyphen:\n      return SETTINGS.softHyphenEnabled ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);\n''', 'style value')
s = s.replace('StyleRow::HungarianHyphenation', 'StyleRow::SoftHyphen')
save(p, s)

# -----------------------------------------------------------------------------
# Hyphenator
# -----------------------------------------------------------------------------
p = 'lib/Epub/Epub/hyphenation/Hyphenator.h'
s = load(p)
s = once(s, '  static std::vector<BreakInfo> breakOffsets(const std::string& word, bool includeFallback);\n',
         '  static std::vector<BreakInfo> breakOffsets(const std::string& word, bool includeFallback);\n  static std::vector<BreakInfo> softHyphenBreakOffsets(const std::string& word);\n', 'hyphenator soft API')
s = once(s, '  static void setHungarianExtended(bool enabled);\n',
         '  static void setHungarianExtended(bool enabled);\n  static void setSoftHyphenEnabled(bool enabled);\n', 'hyphenator setter')
s = once(s, '  static bool hungarianExtended_;\n',
         '  static bool hungarianExtended_;\n  static bool softHyphenEnabled_;\n', 'hyphenator static field')
save(p, s)

p = 'lib/Epub/Epub/hyphenation/Hyphenator.cpp'
s = load(p)
s = once(s, 'bool Hyphenator::hungarianExtended_ = false;\n',
         'bool Hyphenator::hungarianExtended_ = false;\nbool Hyphenator::softHyphenEnabled_ = false;\n', 'soft static init')
s = once(s, '  auto cps = collectCodepoints(word);\n  if (preferredLanguageIsHungarian_) {\n',
         '  auto cps = collectCodepoints(word);\n  if (!softHyphenEnabled_) {\n    cps.erase(std::remove_if(cps.begin(), cps.end(), [](const CodepointInfo& cp) { return isSoftHyphen(cp.value); }), cps.end());\n  }\n  if (preferredLanguageIsHungarian_) {\n', 'ignore soft when disabled')
insert_before = 'std::vector<Hyphenator::BreakInfo> Hyphenator::breakOffsetsForLanguage'
soft_fn = '''std::vector<Hyphenator::BreakInfo> Hyphenator::softHyphenBreakOffsets(const std::string& word) {\n  auto cps = collectCodepoints(word);\n  std::vector<BreakInfo> out;\n  for (size_t i = 1; i + 1 < cps.size(); ++i) {\n    if (isSoftHyphen(cps[i].value) && isAlphabetic(cps[i - 1].value) && isAlphabetic(cps[i + 1].value)) {\n      out.push_back({cps[i + 1].byteOffset, true});\n    }\n  }\n  return out;\n}\n\n'''
s = once(s, insert_before, soft_fn + insert_before, 'soft function')
s = once(s, 'void Hyphenator::setHungarianExtended(const bool enabled) { hungarianExtended_ = enabled; }\n',
         'void Hyphenator::setHungarianExtended(const bool enabled) { hungarianExtended_ = enabled; }\nvoid Hyphenator::setSoftHyphenEnabled(const bool enabled) { softHyphenEnabled_ = enabled; }\n', 'soft setter impl')
save(p, s)

# -----------------------------------------------------------------------------
# ParsedText current inline-header layout
# -----------------------------------------------------------------------------
p = 'lib/Epub/Epub/ParsedText.h'
s = load(p)
s = once(s,
'''  bool hyphenationEnabled;\n  bool focusReadingEnabled;\n''',
'''  bool hyphenationEnabled;\n  bool softHyphenEnabled;\n  bool focusReadingEnabled;\n''', 'ParsedText soft member')
s = once(s,
'''  bool fixedDialogueSpacing;\n  bool isNaturalAlign;\n''',
'''  bool fixedDialogueSpacing;\n  uint8_t letterSpacingLimitPercent;\n  bool isNaturalAlign;\n''', 'ParsedText tracking member')
s = once(s,
'''  explicit ParsedText(const uint8_t extraParagraphSpacing, const bool hyphenationEnabled = false,\n                      const bool focusReadingEnabled = false, const uint8_t hangingPunctuationLimitPx = 0,\n                      const bool fixedDialogueSpacing = false, const BlockStyle& blockStyle = BlockStyle())\n      : blockStyle(blockStyle),\n        extraParagraphSpacing(extraParagraphSpacing),\n        hyphenationEnabled(hyphenationEnabled),\n        focusReadingEnabled(focusReadingEnabled),\n        hangingPunctuationLimitPx(hangingPunctuationLimitPx),\n        fixedDialogueSpacing(fixedDialogueSpacing),\n        isNaturalAlign(false),\n        hasRtlWord(false) {}\n''',
'''  explicit ParsedText(const uint8_t extraParagraphSpacing, const bool hyphenationEnabled = false,\n                      const bool softHyphenEnabled = false, const bool focusReadingEnabled = false,\n                      const uint8_t hangingPunctuationLimitPx = 0, const bool fixedDialogueSpacing = false,\n                      const uint8_t letterSpacingLimitPercent = 0, const BlockStyle& blockStyle = BlockStyle())\n      : blockStyle(blockStyle),\n        extraParagraphSpacing(extraParagraphSpacing),\n        hyphenationEnabled(hyphenationEnabled),\n        softHyphenEnabled(softHyphenEnabled),\n        focusReadingEnabled(focusReadingEnabled),\n        hangingPunctuationLimitPx(hangingPunctuationLimitPx),\n        fixedDialogueSpacing(fixedDialogueSpacing),\n        letterSpacingLimitPercent(letterSpacingLimitPercent),\n        isNaturalAlign(false),\n        hasRtlWord(false) {}\n''', 'ParsedText inline ctor')
save(p, s)

# ParsedText.cpp transformations
p = 'lib/Epub/Epub/ParsedText.cpp'
s = load(p)
s = s.replace('    const auto breaks = Hyphenator::breakOffsets(word, includeFallback);',
              '    const auto breaks = hyphenationEnabled ? Hyphenator::breakOffsets(word, includeFallback)\n                                            : (softHyphenEnabled ? Hyphenator::softHyphenBreakOffsets(word)\n                                                                 : std::vector<Hyphenator::BreakInfo>{});')
s = re.sub(r'scaledNormalSpaceAdvance\((renderer\.getSpaceAdvance\([^\n]+\)),\s*minimumSpacePercent_\)', r'\1', s)
s = s.replace('  int totalNaturalGaps = 0;\n', '  int totalNaturalGaps = 0;\n  bool useNaturalLastLineSpacing = false;\n', 1)
s = s.replace('''    if (lineWordWidthSum + natural100 + extraStartOffset + extraEndOffset <= effectivePageWidth) {\n      totalNaturalGaps = natural100;\n    }\n''',
'''    if (lineWordWidthSum + natural100 + extraStartOffset + extraEndOffset <= effectivePageWidth) {\n      totalNaturalGaps = natural100;\n      useNaturalLastLineSpacing = true;\n    }\n''', 1)
old = '''  const int spareSpace =\n      effectivePageWidth + hangingAllowance - extraStartOffset - extraEndOffset - lineWordWidthSum - totalNaturalGaps;\n  const int justifyExtra = (effectiveAlignment == CssTextAlign::Justify && !isLastLine)\n                               ? computeJustifyExtra(spareSpace, actualGapCount)\n                               : 0;\n'''
new = '''  const int spareSpace =\n      effectivePageWidth + hangingAllowance - extraStartOffset - extraEndOffset - lineWordWidthSum - totalNaturalGaps;\n\n  uint8_t letterSpacingPx = 0;\n  int trackingExtraTotal = 0;\n  if (letterSpacingLimitPercent > 0 && effectiveAlignment == CssTextAlign::Justify && !isLastLine &&\n      !blockStyle.isRtl && !hasRtlWord && !focusReadingEnabled && rubyTexts.empty() && actualGapCount > 0) {\n    int natural100Gaps = 0;\n    size_t normalGapCount = 0;\n    for (size_t wordIdx = 1; wordIdx < lineWordCount; ++wordIdx) {\n      const size_t boundaryIdx = lastBreakAt + wordIdx;\n      if (!continuesVec[boundaryIdx] && !noSpaceBeforeVec[boundaryIdx]) {\n        natural100Gaps += renderer.getSpaceAdvance(fontId, lastCodepoint(lineWords[wordIdx - 1]),\n                                                   firstCodepoint(lineWords[wordIdx]), lineWordStyles[wordIdx - 1]);\n        normalGapCount++;\n      }\n    }\n    if (normalGapCount > 0 && natural100Gaps > 0) {\n      const int finalAverageGap = (totalNaturalGaps + std::max(0, spareSpace)) / static_cast<int>(actualGapCount);\n      const int naturalAverageGap = natural100Gaps / static_cast<int>(normalGapCount);\n      if (finalAverageGap * 100 > naturalAverageGap * letterSpacingLimitPercent) {\n        for (const auto& w : lineWords) {\n          const uint32_t cps = countCodepoints(w);\n          if (cps > 1) trackingExtraTotal += static_cast<int>(cps - 1);\n        }\n        if (trackingExtraTotal > 0 && trackingExtraTotal < spareSpace) letterSpacingPx = 1;\n      }\n    }\n  }\n  const int adjustedSpareSpace = spareSpace - (letterSpacingPx ? trackingExtraTotal : 0);\n  const int justifyExtra = (effectiveAlignment == CssTextAlign::Justify && !isLastLine)\n                               ? computeJustifyExtra(adjustedSpareSpace, actualGapCount)\n                               : 0;\n'''
s = once(s, old, new, 'tracking calculation')
s = s.replace('? spareSpace - justifyExtra * static_cast<int>(actualGapCount)',
              '? adjustedSpareSpace - justifyExtra * static_cast<int>(actualGapCount)')
needle = '''    } else {\n      // LTR: position words from left to right\n      int xpos = firstLineIndent + extraStartOffset;\n'''
replacement = '''    } else {\n      // LTR: position words from left to right. Final-line natural spacing and\n      // optional +1 px tracking are render-only corrections: line breaks are unchanged.\n      const uint8_t ltrSpacePercent =\n          (useNaturalLastLineSpacing && effectiveAlignment == CssTextAlign::Justify) ? 100\n                                                                                     : (blockStyle.alignment == CssTextAlign::Justify ? minimumSpacePercent_ : 100);\n      int xpos = firstLineIndent + extraStartOffset;\n'''
s = once(s, needle, replacement, 'LTR spacing selector')
ltr_start = s.index('// LTR: position words from left to right. Final-line natural spacing')
ltr_end = s.index('\n    }\n  }\n\n  const auto focusBoundaryAt', ltr_start)
ltr = s[ltr_start:ltr_end]
ltr = ltr.replace('(blockStyle.alignment == CssTextAlign::Justify ? minimumSpacePercent_ : 100)', 'ltrSpacePercent')
ltr = ltr.replace('int advance = wordWidths[lastBreakAt + wordIdx];',
                  'int advance = wordWidths[lastBreakAt + wordIdx] + (letterSpacingPx ? static_cast<int>(std::max<uint32_t>(1, countCodepoints(lineWords[wordIdx])) - 1) : 0);')
ltr = ltr.replace('xpos += wordWidths[lastBreakAt + wordIdx] + gap;',
                  'xpos += wordWidths[lastBreakAt + wordIdx] + (letterSpacingPx ? static_cast<int>(std::max<uint32_t>(1, countCodepoints(lineWords[wordIdx])) - 1) : 0) + gap;')
s = s[:ltr_start] + ltr + s[ltr_end:]
s = s.replace('blockStyle, std::move(lineRubyTexts));', 'blockStyle, std::move(lineRubyTexts), letterSpacingPx);')
save(p, s)

# -----------------------------------------------------------------------------
# Parser wiring
# -----------------------------------------------------------------------------
p = 'lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h'
s = load(p)
s = once(s, '  bool hyphenationEnabled;\n  bool focusReadingEnabled;\n',
         '  bool hyphenationEnabled;\n  bool softHyphenEnabled;\n  bool focusReadingEnabled;\n', 'parser soft member')
s = once(s, '  bool fixedDialogueSpacing;\n  const CssParser* cssParser;\n',
         '  bool fixedDialogueSpacing;\n  uint8_t letterSpacingLimitPercent;\n  const CssParser* cssParser;\n', 'parser tracking member')
s = once(s,
'''      const uint16_t viewportWidth, const uint16_t viewportHeight, const bool hyphenationEnabled,\n      const bool focusReadingEnabled, const uint8_t hangingPunctuationLimitPx, const bool fixedDialogueSpacing,\n''',
'''      const uint16_t viewportWidth, const uint16_t viewportHeight, const bool hyphenationEnabled,\n      const bool softHyphenEnabled, const bool focusReadingEnabled, const uint8_t hangingPunctuationLimitPx,\n      const bool fixedDialogueSpacing, const uint8_t letterSpacingLimitPercent,\n''', 'parser ctor signature')
s = once(s, '        hyphenationEnabled(hyphenationEnabled),\n        focusReadingEnabled(focusReadingEnabled),\n',
         '        hyphenationEnabled(hyphenationEnabled),\n        softHyphenEnabled(softHyphenEnabled),\n        focusReadingEnabled(focusReadingEnabled),\n', 'parser soft init')
s = once(s, '        fixedDialogueSpacing(fixedDialogueSpacing),\n        completePageFn(completePageFn),\n',
         '        fixedDialogueSpacing(fixedDialogueSpacing),\n        letterSpacingLimitPercent(letterSpacingLimitPercent),\n        completePageFn(completePageFn),\n', 'parser tracking init')
save(p, s)

p = 'lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp'
s = load(p)
s = once(s,
'''  currentTextBlock.reset(new ParsedText(extraParagraphSpacing, hyphenationEnabled, focusReadingEnabled,\n                                        hangingPunctuationLimitPx, fixedDialogueSpacing, blockStyle));\n''',
'''  currentTextBlock.reset(new ParsedText(extraParagraphSpacing, hyphenationEnabled, softHyphenEnabled,\n                                        focusReadingEnabled, hangingPunctuationLimitPx, fixedDialogueSpacing,\n                                        letterSpacingLimitPercent, blockStyle));\n''', 'parser ParsedText construction')
save(p, s)

# -----------------------------------------------------------------------------
# TextBlock minimal storage hooks; renderer-specific patch remains separate
# -----------------------------------------------------------------------------
p = 'lib/Epub/Epub/blocks/TextBlock.h'
s = load(p)
s = once(s, '  bool focusPresent = false;\n  bool simpleRender = false;\n',
         '  bool focusPresent = false;\n  uint8_t letterSpacingPx = 0;\n  bool simpleRender = false;\n', 'TextBlock tracking field')
s = once(s,
'''                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle = BlockStyle(),\n                     std::vector<std::string> rubyTexts = {});\n''',
'''                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle = BlockStyle(),\n                     std::vector<std::string> rubyTexts = {}, uint8_t letterSpacingPx = 0);\n''', 'TextBlock ctor signature')
save(p, s)

print('CPHUN-260827-19 patch applied')