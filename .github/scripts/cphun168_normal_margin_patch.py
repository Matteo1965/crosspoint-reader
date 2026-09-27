#!/usr/bin/env python3
"""CPHUN-168: match the NORMAL optical margin using actually painted pixels.

CPHUN-167 uses the last strong (raw>=2) 2-bit font pixel. GfxRenderer BW
actually paints ALL non-white pixels (raw>=1), so it adds one pixel too much
when a weak antialiased edge lies beyond the dark edge. The "kerestek"
screenshots expose exactly this difference. Do not align to the next line's
hanging hyphen (which may extend intentionally beyond the normal margin).
"""
from pathlib import Path

def once(text, old, new, name):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"CPHUN-168 {name}: expected one anchor, found {n}")
    return text.replace(old, new, 1)

p = Path("lib/Epub/Epub/blocks/TextBlock.cpp")
s = p.read_text(encoding="utf-8")
if "renderedFinalWordInkInset" not in s or "OpticalLineDiagnostics::record" not in s:
    raise SystemExit("CPHUN-168: run after CPHUN-167 and CPHUN-166 patches")
s = once(s,
    """  int dark = -1;
  int any = -1;
  int pixel = 0;""",
    """  // GfxRenderer BW draws all nonwhite antialiasing pixels, not only >=2.
  int rightmostPainted = -1;
  int pixel = 0;""",
    "right-edge accumulator")
s = once(s,
    """      if (intensity != 0 && col > any) any = col;
      if (intensity >= 2 && col > dark) dark = col;""",
    """      if (OpticalLineCorrection::countsAsPaintedInk(intensity) && col > rightmostPainted)
        rightmostPainted = col;""",
    "2-bit and 1-bit painted pixel scan")
s = once(s,
    """  const int lastInk = dark >= 0 ? dark : any;""",
    """  const int lastInk = rightmostPainted;""",
    "rightmost painted pixel")
s = once(s,
    """        opticalInset, opticalGapCount, opticalExtra);""",
    """        opticalInset, opticalGapCount, opticalExtra, x);""",
    "actual screen text origin in diagnostics")
if "dark >= 0 ? dark : any" in s or "if (intensity >= 2 && col > dark)" in s:
    raise SystemExit("CPHUN-168: strong-ink-only last-word helper remains")
p.write_text(s, encoding="utf-8")

# Preserve the TXT sidecar and report the absolute, EXCLUSIVE screen margin.
# A normal (non-hyphenated) word should end with its last painted pixel at
# screen normalRightExclusive-1. Hanging hyphens are excluded deliberately.
p = Path("src/util/ScreenshotUtil.cpp")
s = p.read_text(encoding="utf-8")
s = once(s, '"CPHUN-166 optical line diagnostics\\n"',
         '"CPHUN-168 optical line diagnostics\\n"',
         "sidecar version")
s = once(s,
         r'ending\tstatus\ttargetX\tlastWordX\tadvance\tinkInset\tgaps\taddedPx\n',
         r'ending\tstatus\ttargetX\tlastWordX\tadvance\tinkInset\tgaps\taddedPx\tnormalRightExcl\tpaintedRightExcl\tmarginDelta\n',
         "sidecar column names")
s = once(s,
         r'"%s\t%s\t%d\t%d\t%d\t%d\t%d\t%d\n",',
         r'"%s\t%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n",',
         "sidecar row format")
s = once(s, """              e.finalAdvance, e.inset, e.gaps, e.correction);""",
         """              e.finalAdvance, e.inset, e.gaps, e.correction,
              e.normalRightExclusive, e.paintedRightExclusive, e.normalMarginDelta);""",
         "sidecar row values")
p.write_text(s, encoding="utf-8")

# The new pixel policy must invalidate all existing chapter positioning caches
# so no page carries cached geometry from the CPHUN-167 measurement pass.
p = Path("lib/Epub/Epub/Section.cpp")
s = p.read_text(encoding="utf-8")
s = once(s, "constexpr uint8_t SECTION_FILE_VERSION = 67;",
         "// CPHUN-168: painted-pixel ink closure; normal exclusive right margin.\n"
         "constexpr uint8_t SECTION_FILE_VERSION = 68;",
         "section cache")
p.write_text(s, encoding="utf-8")
print("CPHUN-168: all painted pixels, normal screen-right diagnostics and section cache v68 applied.")
