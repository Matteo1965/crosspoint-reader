from pathlib import Path

p = Path('lib/Epub/Epub/ParsedText.cpp')
s = p.read_text(encoding='utf-8')
old = '''  uint8_t letterSpacingPx = 0;\n  int trackingExtraTotal = 0;\n  const bool lineHasRubyAnnotation =\n      std::any_of(lineRubyTexts.begin(), lineRubyTexts.end(), [](const std::string& ruby) { return !ruby.empty(); });\n  if (letterSpacingLimitPercent > 0 && effectiveAlignment == CssTextAlign::Justify && !isLastLine &&\n      !blockStyle.isRtl && !hasRtlWord && !focusReadingEnabled && !lineHasRubyAnnotation && actualGapCount > 0) {\n'''
new = '''  uint8_t letterSpacingPx = 0;\n  int trackingExtraTotal = 0;\n  const bool lineHasRubyAnnotation =\n      std::any_of(lineRubyTexts.begin(), lineRubyTexts.end(), [](const std::string& ruby) { return !ruby.empty(); });\n\n  // CPHUN-260827-22 diagnostic: force clearly visible +2 px tracking on\n  // normal justified LTR non-last lines. This intentionally bypasses the\n  // 120/240% activation threshold so we can verify the layout->TextBlock->render path.\n  if (effectiveAlignment == CssTextAlign::Justify && !isLastLine && !blockStyle.isRtl && !hasRtlWord &&\n      !focusReadingEnabled && !lineHasRubyAnnotation && actualGapCount > 0) {\n    for (const auto& w : lineWords) {\n      const uint32_t cps = countCodepoints(w);\n      if (cps > 1) trackingExtraTotal += static_cast<int>(cps - 1) * 2;\n    }\n    if (trackingExtraTotal > 0 && trackingExtraTotal < spareSpace) letterSpacingPx = 2;\n  } else if (letterSpacingLimitPercent > 0 && effectiveAlignment == CssTextAlign::Justify && !isLastLine &&\n      !blockStyle.isRtl && !hasRtlWord && !focusReadingEnabled && !lineHasRubyAnnotation && actualGapCount > 0) {\n'''
if old not in s:
    raise SystemExit('tracking activation marker not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('Applied CPHUN-260827-22 forced +2px tracking diagnostic')
