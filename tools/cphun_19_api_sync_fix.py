from pathlib import Path


def patch_once(path, old, new, label):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 marker, found {count}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")


patch_once(
    "lib/Epub/Epub/Section.cpp",
    """      spec.paragraphAlignment, spec.viewportWidth, spec.viewportHeight, spec.hyphenationEnabled,\n      spec.focusReadingEnabled, spec.hangingPunctuationLimitPx, spec.fixedDialogueSpacing,\n      [this, ctxPtr](std::unique_ptr<Page> page, const uint16_t paragraphIndex, const uint16_t listItemIndex,\n""",
    """      spec.paragraphAlignment, spec.viewportWidth, spec.viewportHeight, spec.hyphenationEnabled,\n      spec.softHyphenEnabled, spec.focusReadingEnabled, spec.hangingPunctuationLimitPx, spec.fixedDialogueSpacing,\n      spec.letterSpacingLimitPercent,\n      [this, ctxPtr](std::unique_ptr<Page> page, const uint16_t paragraphIndex, const uint16_t listItemIndex,\n""",
    "Section parser constructor wiring",
)

patch_once(
    "src/util/DictHtmlPages.cpp",
    """        SETTINGS.extraParagraphSpacing, SETTINGS.paragraphAlignment, viewportWidth, viewportHeight,\n        SETTINGS.hyphenationEnabled, SETTINGS.focusReadingEnabled, /*hangingPunctuationLimitPx=*/0,\n        SETTINGS.fixedDialogueSpacing != 0,\n        [&pagesOut, &resourceLimitHit, &retainedElements](std::unique_ptr<Page> page, uint16_t, uint16_t, uint32_t) {\n""",
    """        SETTINGS.extraParagraphSpacing, SETTINGS.paragraphAlignment, viewportWidth, viewportHeight,\n        SETTINGS.hyphenationEnabled, SETTINGS.softHyphenEnabled, SETTINGS.focusReadingEnabled,\n        /*hangingPunctuationLimitPx=*/0, SETTINGS.fixedDialogueSpacing != 0, SETTINGS.letterSpacingLimitPercent,\n        [&pagesOut, &resourceLimitHit, &retainedElements](std::unique_ptr<Page> page, uint16_t, uint16_t, uint32_t) {\n""",
    "Dictionary parser constructor wiring",
)

patch_once(
    "lib/Epub/Epub/blocks/TextBlock.cpp",
    """TextBlock::TextBlock(const std::vector<std::string>& words, const std::vector<int16_t>& wordXpos,\n                     const std::vector<EpdFontFamily::Style>& wordStyles, const std::vector<uint8_t>& focusBoundary,\n                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle,\n                     std::vector<std::string> rubyTexts)\n    : blockStyle(blockStyle), rubyTexts(std::move(rubyTexts)) {\n""",
    """TextBlock::TextBlock(const std::vector<std::string>& words, const std::vector<int16_t>& wordXpos,\n                     const std::vector<EpdFontFamily::Style>& wordStyles, const std::vector<uint8_t>& focusBoundary,\n                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle,\n                     std::vector<std::string> rubyTexts, const uint8_t letterSpacingPx)\n    : blockStyle(blockStyle), rubyTexts(std::move(rubyTexts)), letterSpacingPx(letterSpacingPx) {\n""",
    "TextBlock constructor definition",
)

print("CPHUN-260827-19 API sync fix applied")
