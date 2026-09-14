from pathlib import Path

path = Path("lib/Epub/Epub/ParsedText.cpp")
text = path.read_text(encoding="utf-8")

old = '''          xpos += wordWidths[lastBreakAt + wordIdx] + wordTrackingExtra + gap;
        }
      }
    }
  }

  const auto focusBoundaryAt = [&](const size_t idx) {'''

new = '''          xpos += wordWidths[lastBreakAt + wordIdx] + wordTrackingExtra + gap;
        }
      }

      // CPHUN-122: close any residual right-edge gap left by the independent
      // width-accounting and positioning paths.  The normal justify remainder
      // already distributes integer division leftovers, but token-boundary
      // kerning/microspacing/tracking can still make the actually accumulated
      // X positions finish a few pixels short.  Measure the final accumulated
      // endpoint and spread only that real positive residual across the same
      // justifiable gaps.  This preserves word widths and glyph internals while
      // making the physical layout endpoint equal the requested right edge.
      if (effectiveAlignment == CssTextAlign::Justify && !isLastLine && actualGapCount > 0) {
        const int targetEndX = effectivePageWidth + hangingAllowance - extraEndOffset;
        const int rightEdgeResidual = targetEndX - xpos;
        if (rightEdgeResidual > 0) {
          const int residualPerGap = rightEdgeResidual / static_cast<int>(actualGapCount);
          const int residualRemainder = rightEdgeResidual % static_cast<int>(actualGapCount);
          int cumulativeResidualShift = 0;
          size_t residualGapIndex = 0;
          for (size_t wordIdx = 1; wordIdx < lineWordCount; ++wordIdx) {
            const size_t boundaryIdx = lastBreakAt + wordIdx;
            const bool isSpaceToken = lineWords[wordIdx] == " ";
            if (TokenBoundary::isJustifiableGap(continuesVec[boundaryIdx], noSpaceBeforeVec[boundaryIdx],
                                                isSpaceToken)) {
              cumulativeResidualShift += residualPerGap +
                                         (static_cast<int>(residualGapIndex) < residualRemainder ? 1 : 0);
              ++residualGapIndex;
            }
            lineXPos[wordIdx] = static_cast<int16_t>(lineXPos[wordIdx] + cumulativeResidualShift);
          }
          xpos += rightEdgeResidual;
        }
      }
    }
  }

  const auto focusBoundaryAt = [&](const size_t idx) {'''

count = text.count(old)
if count != 1:
    raise SystemExit(f"CPHUN-122: expected exactly one LTR loop tail, found {count}")

text = text.replace(old, new, 1)

required = [
    "const int rightEdgeResidual = targetEndX - xpos;",
    "residualPerGap",
    "cumulativeResidualShift",
    "TokenBoundary::isJustifiableGap",
]
for marker in required:
    if marker not in text:
        raise SystemExit(f"CPHUN-122: missing marker: {marker}")

path.write_text(text, encoding="utf-8")
