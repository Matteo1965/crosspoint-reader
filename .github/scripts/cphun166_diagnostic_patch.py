#!/usr/bin/env python3
"""CPHUN-166: add per-line render diagnostics AFTER regenerating CPHUN-165."""
from pathlib import Path

def replace_one(text, before, after, label):
    n = text.count(before)
    if n != 1:
        raise SystemExit(f"CPHUN-166 {label}: expected 1 anchor, got {n}")
    return text.replace(before, after, 1)

p = Path("lib/Epub/Epub/blocks/TextBlock.cpp")
s = p.read_text(encoding="utf-8")
s = replace_one(s, '#include "../OpticalLineCorrection.h"',
                '#include "../OpticalLineCorrection.h"\n#include "../OpticalLineDiagnostics.h"',
                "diagnostic include")
s = replace_one(s,
    """  int opticalExtra = 0;
  int opticalGapCount = 0;""",
    """  int opticalExtra = 0;
  int opticalGapCount = 0;
  int opticalInset = -1;""", "diagnostic inset")
s = replace_one(s,
    """    const int inset = renderedFinalInkInset(
        renderer, fontId, wordText(numWords - 1), wordStyle(numWords - 1));
    opticalExtra = OpticalLineCorrection::missingFinalInkPixels(
        opticalTargetRightX_, xposArr[numWords - 1], opticalLastWordAdvance_, inset);
    if (opticalExtra > 0) {
      for (uint16_t j = 1; j < numWords; ++j)
        opticalGapCount += opticalGapsArr[j] != 0;
    }
    if (opticalGapCount == 0) opticalExtra = 0;""",
    """    opticalInset = renderedFinalInkInset(
        renderer, fontId, wordText(numWords - 1), wordStyle(numWords - 1));
    opticalExtra = OpticalLineCorrection::missingFinalInkPixels(
        opticalTargetRightX_, xposArr[numWords - 1], opticalLastWordAdvance_, opticalInset);
    for (uint16_t j = 1; j < numWords; ++j)
      opticalGapCount += opticalGapsArr[j] != 0;
    if (opticalGapCount == 0) opticalExtra = 0;""",
    "inset, eligible gaps and correction")
s = replace_one(s, """  int opticalGapIndex = 0;""",
    """  // CPHUN-166: capture diagnostics while the page is actually rendered,
  // never during the preliminary glyph-cache scanning pass.
  if (!scanning && numWords > 0) {
    const char* reason = opticalTargetRightX_ == 0 ? "NO_LAYOUT_TARGET" :
        opticalInset < 0 ? "NO_BITMAP" :
        opticalGapCount == 0 ? "NO_GAPS" :
        opticalExtra == 0 ? "ZERO_CORRECTION" : "APPLIED";
    OpticalLineDiagnostics::record(
        wordText(numWords - 1), reason,
        opticalTargetRightX_,
        xposArr[numWords - 1], opticalLastWordAdvance_,
        opticalInset, opticalGapCount, opticalExtra);
  }
  int opticalGapIndex = 0;""", "render diagnostics")
p.write_text(s, encoding="utf-8")

p = Path("src/util/ScreenshotUtil.cpp")
s = p.read_text(encoding="utf-8")
s = replace_one(s, '#include "ScreenshotSequence.h"',
                '#include "ScreenshotSequence.h"\n#include "../../lib/Epub/Epub/OpticalLineDiagnostics.h"',
                "screenshot include")
anchor = """  // Display a border around the screen to indicate a screenshot was taken"""
diagnostic = """  // CPHUN-166: sidecar shares the screenshot sequence number. The firmware
  // does not need a clock or an external serial connection to report why
  // optical closure was skipped on the photographed page.
  std::string diagnosticPath(filename);
  if (diagnosticPath.size() >= 4) {
    diagnosticPath.replace(diagnosticPath.size() - 4, 4, ".txt");
    if (!Storage.exists(diagnosticPath.c_str())) {
      HalFile report;
      if (Storage.openFileForWrite("SCR", diagnosticPath.c_str(), report)) {
        constexpr const char* header =
            "CPHUN-166 optical line diagnostics\\n"
            "Last 64 rendered text lines, oldest first. Coordinates are relative to the text block.\\n"
            "ending\\tstatus\\ttargetX\\tlastWordX\\tadvance\\tinkInset\\tgaps\\taddedPx\\n";
        report.write(reinterpret_cast<const uint8_t*>(header), strlen(header));
        const auto& history = OpticalLineDiagnostics::store();
        char row[192];
        for (unsigned i = 0; i < history.used; ++i) {
          const auto& e = OpticalLineDiagnostics::oldestAt(i);
          const int len = snprintf(row, sizeof(row),
              "%s\\t%s\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\n",
              e.ending, e.status, e.target, e.finalWordX,
              e.finalAdvance, e.inset, e.gaps, e.correction);
          if (len > 0 && len < static_cast<int>(sizeof(row))) {
            report.write(reinterpret_cast<const uint8_t*>(row), static_cast<size_t>(len));
          }
        }
        report.close();
        LOG_DBG("SCR", "Optical diagnostic saved to %s", diagnosticPath.c_str());
      } else {
        LOG_ERR("SCR", "Failed to write optical diagnostic sidecar");
      }
    }
  }

"""
s = replace_one(s, anchor, diagnostic + anchor, "screenshot sidecar")
p.write_text(s, encoding="utf-8")
print("CPHUN-166: render-time optical diagnostics and screenshot sidecars installed.")
