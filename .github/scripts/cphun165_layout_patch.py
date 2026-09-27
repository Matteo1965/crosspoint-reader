#!/usr/bin/env python3
"""CPHUN-165: save optical line targets and gap eligibility, not premature pixels."""
from pathlib import Path

p=Path("lib/Epub/Epub/ParsedText.cpp")
s=p.read_text(encoding="utf-8")
start=s.index("  // CPHUN-164: final visible-ink closure (never an EPUB-text modification).")
end=s.index("  const auto focusBoundaryAt =",start)
old=s[start:end]
assert "trailingStrongInkInset" in old and "OpticalLineCorrection::extraForSlot" in old
new="""  // CPHUN-165: final-glyph bitmap inspection must happen AFTER glyph prewarm
  // in TextBlock::render(), never during metadata-only layout.
  uint16_t opticalTargetRightX = 0;
  uint16_t opticalLastWordAdvance = 0;
  std::vector<uint8_t> opticalGaps;
  if (!willReorder && !isLastLine && effectiveAlignment == CssTextAlign::Justify &&
      !blockStyle.isRtl && !hasRtlWord && !focusReadingEnabled &&
      !lineHasRubyAnnotation && hangingAllowance == 0 &&
      actualGapCount > 0 && !lineWords.empty() &&
      lineXPos.size() == lineWords.size() &&
      LetterSpacingOptimization::isLatinLetter(lastCodepoint(lineWords.back()))) {
    const auto fontIt = renderer.getFontMap().find(fontId);
    if (fontIt != renderer.getFontMap().end() &&
        fontIt->second.hasCodepoint(lastCodepoint(lineWords.back()),
                                    lineWordStyles.back())) {
      opticalGaps.assign(lineWordCount, 0);
      unsigned eligible = 0;
      for (size_t i = 1; i < lineWordCount; ++i) {
        if (TokenBoundary::isJustifiableGap(
                continuesVec[lastBreakAt + i], noSpaceBeforeVec[lastBreakAt + i],
                lineWords[i] == " ")) {
          opticalGaps[i] = 1;
          ++eligible;
        }
      }
      if (eligible > 0) {
        const int advance = static_cast<int>(
            wordWidths[lastBreakAt + lineWordCount - 1]) + lastWordTrackingExtra;
        if (pageWidth > 0 && pageWidth <= UINT16_MAX &&
            advance > 0 && advance <= UINT16_MAX) {
          opticalTargetRightX = static_cast<uint16_t>(pageWidth);
          opticalLastWordAdvance = static_cast<uint16_t>(advance);
        }
      }
      if (opticalTargetRightX == 0) opticalGaps.clear();
    }
  }

"""
s=s[:start]+new+s[end:]
needle="std::move(lineRubyTexts), letterSpacingPx);"
assert s.count(needle)==1, "single-block constructor anchor"
s=s.replace(needle, "std::move(lineRubyTexts), letterSpacingPx,\n"
                    "                                              opticalTargetRightX, opticalLastWordAdvance, opticalGaps);",1)
p.write_text(s,encoding="utf-8")
p=Path("lib/Epub/Epub/Section.cpp")
s=p.read_text(encoding="utf-8")
old="constexpr uint8_t SECTION_FILE_VERSION = 65;"
assert s.count(old)==1
p.write_text(s.replace(old,"""// CPHUN-165: cached optical target/gaps and per-line render-time closure.
constexpr uint8_t SECTION_FILE_VERSION = 66;""",1),encoding="utf-8")
print("CPHUN-165 layout metadata and cache v66 applied")
