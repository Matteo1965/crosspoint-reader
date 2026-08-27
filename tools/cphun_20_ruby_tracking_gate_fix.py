from pathlib import Path

path = Path("lib/Epub/Epub/ParsedText.cpp")
text = path.read_text(encoding="utf-8")

old = """  if (letterSpacingLimitPercent > 0 && effectiveAlignment == CssTextAlign::Justify && !isLastLine &&\n      !blockStyle.isRtl && !hasRtlWord && !focusReadingEnabled && rubyTexts.empty() && actualGapCount > 0) {\n"""

new = """  const bool lineHasRubyAnnotation =\n      std::any_of(lineRubyTexts.begin(), lineRubyTexts.end(), [](const std::string& ruby) { return !ruby.empty(); });\n  if (letterSpacingLimitPercent > 0 && effectiveAlignment == CssTextAlign::Justify && !isLastLine &&\n      !blockStyle.isRtl && !hasRtlWord && !focusReadingEnabled && !lineHasRubyAnnotation && actualGapCount > 0) {\n"""

count = text.count(old)
if count != 1:
    raise SystemExit(f"Expected exactly one tracking gate, found {count}")

path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Applied CPHUN-260827-20 ruby-aware letter-spacing activation gate fix")
