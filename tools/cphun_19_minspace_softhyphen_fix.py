from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 marker, found {count}")
    return text.replace(old, new, 1)


path = Path("lib/Epub/Epub/ParsedText.cpp")
s = path.read_text(encoding="utf-8")

# 1) Min. word spacing: the final LTR positioning stage must use the same
# percentage as line measurement. The previous self-reference read an
# uninitialized value and destroyed justified right-edge geometry below 100%.
s = replace_once(
    s,
    """      const uint8_t ltrSpacePercent =
          (useNaturalLastLineSpacing && effectiveAlignment == CssTextAlign::Justify) ? 100
                                                                                     : ltrSpacePercent;
""",
    """      const uint8_t ltrSpacePercent =
          (useNaturalLastLineSpacing && effectiveAlignment == CssTextAlign::Justify)
              ? 100
              : (effectiveAlignment == CssTextAlign::Justify ? minimumSpacePercent_ : 100);
""",
    "LTR MinSpace percentage initialization",
)

# 2) Embedded soft hyphens are an independent breakpoint source. They must be
# usable when automatic language hyphenation is disabled.
s = replace_once(
    s,
    "renderer.ensureSdCardFontReady(fontId, words, hyphenationEnabled, styleMask);",
    "renderer.ensureSdCardFontReady(fontId, words, hyphenationEnabled || softHyphenEnabled, styleMask);",
    "SD font hyphen glyph preparation",
)

s = replace_once(
    s,
    """  std::vector<size_t> lineBreakIndices;
  if (hyphenationEnabled) {
""",
    """  std::vector<size_t> lineBreakIndices;
  if (hyphenationEnabled || softHyphenEnabled) {
""",
    "independent soft-hyphen layout path",
)

s = replace_once(
    s,
    "  auto breakInfos = Hyphenator::breakOffsets(word, allowFallbackBreaks);",
    """  auto breakInfos = hyphenationEnabled ? Hyphenator::breakOffsets(word, allowFallbackBreaks)
                                      : Hyphenator::softHyphenBreakOffsets(word);""",
    "soft-hyphen-only breakpoint selection",
)

path.write_text(s, encoding="utf-8")
print("CPHUN-19 MinSpace + independent soft-hyphen quickfix applied")
