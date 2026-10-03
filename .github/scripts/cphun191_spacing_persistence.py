from pathlib import Path
import re

p = Path("src/CrossPointSettings.cpp")
s = p.read_text(encoding="utf-8")

# CPHUN-191: canonical persistence for the four-state Hungarian letter-spacing
# correction. Current stored values are:
#   0=Off, 550=Weak, 460=Medium, 280=Strong.
#
# Older validators accepted only the historical 200..500 scale and therefore
# reset 550/460/280 to zero before the later migration code could see them.
# Replace the complete load/legacy-migration region with one canonical block.
start = s.find('  letterSpacingLimitPercent = doc["letterSpacingLimitPercent"] | (uint16_t)0;')
end = s.find('  minimumSpacePercent = doc["minimumSpacePercent"] | (uint8_t)100;', start)
if start < 0 or end < 0:
    raise SystemExit("CPHUN-191: letter-spacing persistence region not found")

canonical = '''  letterSpacingLimitPercent = doc["letterSpacingLimitPercent"] | (uint16_t)0;
  // CPHUN-191 persistence: preserve the current four-state correction values
  // across restart/deep-sleep wake. Any older non-zero value is migrated once
  // to the nearest current correction level.
  if (letterSpacingLimitPercent != 0 &&
      letterSpacingLimitPercent != 550 &&
      letterSpacingLimitPercent != 460 &&
      letterSpacingLimitPercent != 280) {
    constexpr uint16_t values[] = {550, 460, 280};
    uint16_t best = values[0];
    uint16_t diff = letterSpacingLimitPercent > best
                        ? letterSpacingLimitPercent - best
                        : best - letterSpacingLimitPercent;
    for (uint16_t value : values) {
      const uint16_t d = letterSpacingLimitPercent > value
                             ? letterSpacingLimitPercent - value
                             : value - letterSpacingLimitPercent;
      if (d < diff) {
        diff = d;
        best = value;
      }
    }
    letterSpacingLimitPercent = best;
    needsResave = true;
  }
'''

s = s[:start] + canonical + s[end:]

# The optimization ON/OFF state and threshold must also survive a settings
# reload. Do not silently add duplicate fields; fail if the reconstructed
# source no longer contains the accepted persistence wiring.
required = [
    'doc["letterSpacingOptimization"] = letterSpacingOptimization;',
    'doc["letterSpacingOptimizationThreshold"] = letterSpacingOptimizationThreshold;',
    'letterSpacingOptimization =',
    'doc["letterSpacingOptimization"] | (uint8_t)0',
    'letterSpacingOptimizationThreshold =',
    'doc["letterSpacingOptimizationThreshold"] | (uint8_t)60',
]
for token in required:
    if token not in s:
        raise SystemExit(f"CPHUN-191: missing optimization persistence token: {token}")

# Canonical threshold validation after CPHUN-183: only Off/50/60/70 are valid.
if not all(token in s for token in [
    'letterSpacingOptimizationThreshold != 0',
    'letterSpacingOptimizationThreshold != 50',
    'letterSpacingOptimizationThreshold != 60',
    'letterSpacingOptimizationThreshold != 70',
]):
    raise SystemExit("CPHUN-191: canonical optimization-threshold validation missing")

p.write_text(s, encoding="utf-8")

# CrossPointSettings.h must expose both persisted optimizer fields.
h = Path("src/CrossPointSettings.h").read_text(encoding="utf-8")
for token in [
    'uint8_t letterSpacingOptimization = 0;',
    'uint8_t letterSpacingOptimizationThreshold = 60;',
]:
    if token not in h:
        raise SystemExit(f"CPHUN-191: missing settings field: {token}")

print("CPHUN-191 applied: correction/optimization settings survive reload and deep-sleep wake")
