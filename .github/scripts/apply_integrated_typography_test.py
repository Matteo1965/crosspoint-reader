from pathlib import Path
import re
import textwrap


def extract_python_blocks(workflow_path: str, count: int = 2):
    workflow = Path(workflow_path).read_text(encoding="utf-8")
    blocks = re.findall(r"          python - <<'PY'\n(.*?)\n          PY", workflow, re.S)
    if len(blocks) < count:
        raise SystemExit(f"{workflow_path}: expected at least {count} Python patch blocks, found {len(blocks)}")
    for i, block in enumerate(blocks[:count], 1):
        exec(compile(textwrap.dedent(block), f"<{workflow_path}-block-{i}>", "exec"))


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# Reuse the already proven space/indexing RC patches first.
extract_python_blocks("/tmp/current-rc.yml", 2)

p = Path("lib/Epub/Epub/ParsedText.cpp")
text = p.read_text(encoding="utf-8")

# 1) Optical-margin allowance for hyphenation candidates only when a visible '-' is inserted.
old_hyphen = '''    const int prefixWidth = measureFocusWordWidth(renderer, fontId, candidatePrefix, style,
                                                  focusBoundaryBefore(focusBoundary, offset), needsHyphen);
    if (prefixWidth > availableWidth || prefixWidth <= chosenWidth) {
      continue;  // Skip if too wide or not an improvement
    }
'''
new_hyphen = '''    const uint8_t candidateFocusBoundary = focusBoundaryBefore(focusBoundary, offset);
    const int prefixWidth =
        measureFocusWordWidth(renderer, fontId, candidatePrefix, style, candidateFocusBoundary, needsHyphen);

    // Only an actually inserted visible '-' may consume optical-margin allowance.
    // Ordinary words and non-inserting break candidates keep the normal line width.
    int hyphenHangingAllowance = 0;
    if (needsHyphen && hangingPunctuationLimitPx != 0) {
      static const std::string hangingHyphen("-");
      const auto hyphenStyle =
          candidateFocusBoundary >= candidatePrefix.size()
              ? static_cast<EpdFontFamily::Style>(style | EpdFontFamily::BOLD)
              : style;
      hyphenHangingAllowance =
          hangingPunctuationAllowance(renderer, fontId, hangingHyphen, hyphenStyle, hangingPunctuationLimitPx);
    }
    if (prefixWidth > availableWidth + hyphenHangingAllowance || prefixWidth <= chosenWidth) {
      continue;  // Too wide even with hanging hyphen allowance, or not an improvement.
    }
'''
text = replace_once(text, old_hyphen, new_hyphen, "hyphen candidate block")

# 2) Min. spacing is line-level. Move final-line/alignment state before natural-gap accounting.
marker = '''  // Calculate total word width for this line, count actual word gaps,
  // and accumulate total natural gap widths (including space kerning adjustments).
  int lineWordWidthSum = 0;
'''
line_state = '''  const bool isLastLine = breakIndex == lineBreakIndices.size() - 1;

  // For RTL, implicit/default Left alignment becomes Right alignment.
  // Explicit text-align:left must remain left for CSS correctness.
  const CssTextAlign effectiveAlignment =
      (blockStyle.isRtl && !blockStyle.textAlignDefined && blockStyle.alignment == CssTextAlign::Left)
          ? CssTextAlign::Right
          : blockStyle.alignment;

  // Calculate total word width for this line, count actual word gaps,
  // and accumulate total natural gap widths (including space kerning adjustments).
  int lineWordWidthSum = 0;
'''
text = replace_once(text, marker, line_state, "line gap-accounting marker")

duplicate_state = '''  const bool isLastLine = breakIndex == lineBreakIndices.size() - 1;

  // For RTL, implicit/default Left alignment becomes Right alignment.
  // Explicit text-align:left must remain left for CSS correctness.
  const CssTextAlign effectiveAlignment =
      (blockStyle.isRtl && !blockStyle.textAlignDefined && blockStyle.alignment == CssTextAlign::Left)
          ? CssTextAlign::Right
          : blockStyle.alignment;

'''
first = text.find(duplicate_state)
second = text.find(duplicate_state, first + len(duplicate_state)) if first >= 0 else -1
if first < 0 or second < 0:
    raise SystemExit("expected two line-state blocks after insertion")
text = text[:second] + text[second + len(duplicate_state):]

extract_pos = text.find("void ParsedText::extractLine(")
if extract_pos < 0:
    raise SystemExit("extractLine not found")
before = text[:extract_pos]
extract = text[extract_pos:]
paragraph_gate = "(blockStyle.alignment == CssTextAlign::Justify ? minimumSpacePercent_ : 100)"
line_gate = "(effectiveAlignment == CssTextAlign::Justify && !isLastLine ? minimumSpacePercent_ : 100)"
replaced = extract.count(paragraph_gate)
if replaced < 3:
    raise SystemExit(f"expected >=3 scaled spacing gates in extractLine, found {replaced}")
extract = extract.replace(paragraph_gate, line_gate)
text = before + extract

# 3) The final line must fit with natural 100% spaces.
linebreak_marker = '''  const size_t lineCount = includeLastLine ? lineBreakIndices.size() : lineBreakIndices.size() - 1;
'''
correction = '''  if (blockStyle.alignment == CssTextAlign::Justify && minimumSpacePercent_ < 100 &&
      !lineBreakIndices.empty()) {
    const size_t finalEnd = lineBreakIndices.back();
    const size_t finalStart = lineBreakIndices.size() > 1 ? lineBreakIndices[lineBreakIndices.size() - 2] : 0;
    const bool finalIsFirstLine = finalStart == 0;
    const int finalPageWidth = pageWidth - resolveFirstLineIndent(finalIsFirstLine, renderer, fontId);

    const auto naturalLineWidth = [&](const size_t start, const size_t end) {
      int width = 0;
      for (size_t idx = start; idx < end; ++idx) {
        if (idx > start) {
          if (wordContinues[idx]) {
            width += renderer.getKerning(fontId, lastCodepoint(words[idx - 1]), firstCodepoint(words[idx]),
                                         wordStyles[idx - 1]);
          } else if (!wordNoSpaceBefore[idx]) {
            width += renderer.getSpaceAdvance(fontId, lastCodepoint(words[idx - 1]), firstCodepoint(words[idx]),
                                              wordStyles[idx - 1]);
          }
        }
        width += wordWidths[idx];
      }
      width += calculateRubyExtraStartOffset(start, end, renderer, fontId);
      width += calculateRubyExtraEndOffset(start, end, renderer, fontId);
      return width;
    };

    if (finalStart < finalEnd && naturalLineWidth(finalStart, finalEnd) > finalPageWidth) {
      size_t correctedBreak = finalEnd;
      for (size_t candidate = finalStart + 1; candidate < finalEnd; ++candidate) {
        if (!TokenBoundary::allowsBreak(wordContinues[candidate], wordNoSpaceBefore[candidate])) continue;
        if (naturalLineWidth(candidate, finalEnd) <= pageWidth) {
          correctedBreak = candidate;
          break;
        }
      }
      if (correctedBreak < finalEnd) {
        lineBreakIndices.insert(lineBreakIndices.end() - 1, correctedBreak);
      }
    }
  }

  const size_t lineCount = includeLastLine ? lineBreakIndices.size() : lineBreakIndices.size() - 1;
'''
text = replace_once(text, linebreak_marker, correction, "lineCount marker")

p.write_text(text, encoding="utf-8")
