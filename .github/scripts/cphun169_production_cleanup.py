#!/usr/bin/env python3
"""CPHUN-169 production cleanup: remove temporary screenshot TXT telemetry.

Run after all CPHUN-166..168 regeneration patches. Preserve the corrected
actual-visible-pixel optical alignment and the global screenshot counter.
"""
from pathlib import Path

p = Path("lib/Epub/Epub/blocks/TextBlock.cpp")
text = p.read_text(encoding="utf-8")
diag_include = '#include "../OpticalLineDiagnostics.h"\n'
assert text.count(diag_include) == 1, "CPHUN-169 missing diagnostic header"
text = text.replace(diag_include, "", 1)
start = text.index("  // CPHUN-166: capture diagnostics while the page is actually rendered,")
end = text.index("  int opticalGapIndex = 0;", start)
assert "OpticalLineDiagnostics::record" in text[start:end]
text = text[:start] + text[end:]
assert "renderedFinalWordInkInset" in text
assert "rightmostPainted" in text
assert "OpticalLineDiagnostics" not in text
p.write_text(text, encoding="utf-8")

p = Path("src/util/ScreenshotUtil.cpp")
text = p.read_text(encoding="utf-8")
diag_include = '#include "../../lib/Epub/Epub/OpticalLineDiagnostics.h"\n'
assert text.count(diag_include) == 1, "CPHUN-169 missing screenshot telemetry include"
text = text.replace(diag_include, "", 1)
start = text.index("  // CPHUN-166: sidecar shares the screenshot sequence number.")
end = text.index("  // Display a border around the screen to indicate a screenshot was taken", start)
assert ".txt" in text[start:end] and "OpticalLineDiagnostics" in text[start:end]
text = text[:start] + text[end:]
assert "ScreenshotSequence::formatId" in text
assert "OpticalLineDiagnostics" not in text
assert 'diagnosticPath' not in text
p.write_text(text, encoding="utf-8")

p = Path("lib/Epub/Epub/Section.cpp")
text = p.read_text(encoding="utf-8")
old = "constexpr uint8_t SECTION_FILE_VERSION = 68;"
assert text.count(old) == 1, "CPHUN-169 section cache mismatch"
text = text.replace(old, "// CPHUN-169: 8px optical closure, production without TXT diagnostics.\n"
                        "constexpr uint8_t SECTION_FILE_VERSION = 69;", 1)
p.write_text(text, encoding="utf-8")

p = Path("lib/Epub/Epub/OpticalLineCorrection.h")
text = p.read_text(encoding="utf-8")
assert "MAX_INK_CORRECTION_PX = 8;" in text
assert "MAX_INK_CORRECTION_PX = 5;" not in text
assert "countsAsPaintedInk" in text
print("CPHUN-169: 8px closure, pixel-exact ink, no TXT screenshot sidecars, cache v69.")
