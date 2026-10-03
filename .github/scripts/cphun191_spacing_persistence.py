from pathlib import Path

p = Path("src/CrossPointSettings.cpp")
s = p.read_text(encoding="utf-8")

# --- Save path --------------------------------------------------------------
# Ensure all three spacing settings are explicitly persisted. Older generated
# sources may have only letterSpacingLimitPercent here.
save_anchor = '  doc["letterSpacingLimitPercent"] = letterSpacingLimitPercent;\n'
if save_anchor not in s:
    raise SystemExit("CPHUN-191: letterSpacingLimitPercent save anchor missing")

if 'doc["letterSpacingOptimization"] = letterSpacingOptimization;' not in s:
    s = s.replace(
        save_anchor,
        save_anchor + '  doc["letterSpacingOptimization"] = letterSpacingOptimization;\n',
        1,
    )

if 'doc["letterSpacingOptimizationThreshold"] = letterSpacingOptimizationThreshold;' not in s:
    anchor = '  doc["letterSpacingOptimization"] = letterSpacingOptimization;\n'
    s = s.replace(
        anchor,
        anchor + '  doc["letterSpacingOptimizationThreshold"] = letterSpacingOptimizationThreshold;\n',
        1,
    )

# --- Load path --------------------------------------------------------------
# Replace the complete correction-value load/migration region.
# Canonical persisted UI values since CPHUN-184:
# 0=Off, 10=Weak, 40=Medium, 70=Strong.
# Older internal physical thresholds 550/460/280 migrate once to 10/40/70.
start = s.find('  letterSpacingLimitPercent = doc["letterSpacingLimitPercent"] | (uint16_t)0;')
end = s.find('  minimumSpacePercent = doc["minimumSpacePercent"] | (uint8_t)100;', start)
if start < 0 or end < 0:
    raise SystemExit("CPHUN-191: letter-spacing load region not found")

canonical = '''  letterSpacingLimitPercent = doc["letterSpacingLimitPercent"] | (uint16_t)0;
  // CPHUN-191: preserve the canonical CPHUN-184 UI values across
  // restart/deep-sleep wake: 0=Off, 10=Weak, 40=Medium, 70=Strong.
  if (letterSpacingLimitPercent == 550) {
    letterSpacingLimitPercent = 10;
    needsResave = true;
  } else if (letterSpacingLimitPercent == 460) {
    letterSpacingLimitPercent = 40;
    needsResave = true;
  } else if (letterSpacingLimitPercent == 280) {
    letterSpacingLimitPercent = 70;
    needsResave = true;
  } else if (letterSpacingLimitPercent != 0 &&
             letterSpacingLimitPercent != 10 &&
             letterSpacingLimitPercent != 40 &&
             letterSpacingLimitPercent != 70) {
    // One-time migration for other historical physical threshold values.
    constexpr uint16_t legacyPhysical[] = {550, 460, 280};
    constexpr uint16_t canonical[] = {10, 40, 70};
    int bestIndex = 0;
    uint16_t bestDiff = letterSpacingLimitPercent > legacyPhysical[0]
                            ? letterSpacingLimitPercent - legacyPhysical[0]
                            : legacyPhysical[0] - letterSpacingLimitPercent;
    for (int i = 1; i < 3; ++i) {
      const uint16_t d = letterSpacingLimitPercent > legacyPhysical[i]
                             ? letterSpacingLimitPercent - legacyPhysical[i]
                             : legacyPhysical[i] - letterSpacingLimitPercent;
      if (d < bestDiff) {
        bestDiff = d;
        bestIndex = i;
      }
    }
    letterSpacingLimitPercent = canonical[bestIndex];
    needsResave = true;
  }

  // Persist optimizer ON/OFF independently from the correction level.
  letterSpacingOptimization =
      (doc["letterSpacingOptimization"] | (uint8_t)0) ? 4 : 0;

  // CPHUN-183/184 semantics: Off / Weak / Medium / Strong = 0/50/60/70.
  letterSpacingOptimizationThreshold =
      doc["letterSpacingOptimizationThreshold"] | (uint8_t)60;
  if (letterSpacingOptimizationThreshold != 0 &&
      letterSpacingOptimizationThreshold != 50 &&
      letterSpacingOptimizationThreshold != 60 &&
      letterSpacingOptimizationThreshold != 70) {
    letterSpacingOptimizationThreshold = 60;
    needsResave = true;
  }

'''

s = s[:start] + canonical + s[end:]
p.write_text(s, encoding="utf-8")

# --- Fields -----------------------------------------------------------------
hpath = Path("src/CrossPointSettings.h")
h = hpath.read_text(encoding="utf-8")

if 'uint8_t letterSpacingOptimization = 0;' not in h:
    anchor = '  uint16_t letterSpacingLimitPercent = 0;\n'
    if anchor not in h:
        raise SystemExit("CPHUN-191: letterSpacingLimitPercent field anchor missing")
    h = h.replace(
        anchor,
        anchor +
        '  // Letter-spacing pair optimization: 0=off, 4=on.\n'
        '  uint8_t letterSpacingOptimization = 0;\n',
        1,
    )

if 'uint8_t letterSpacingOptimizationThreshold = 60;' not in h:
    anchor = '  uint8_t letterSpacingOptimization = 0;\n'
    h = h.replace(
        anchor,
        anchor +
        '  // Pair-score threshold: 0=off, 50=weak, 60=medium, 70=strong.\n'
        '  uint8_t letterSpacingOptimizationThreshold = 60;\n',
        1,
    )

hpath.write_text(h, encoding="utf-8")

# Final source-level assertions.
final = p.read_text(encoding="utf-8")
required = [
    'doc["letterSpacingLimitPercent"] = letterSpacingLimitPercent;',
    'doc["letterSpacingOptimization"] = letterSpacingOptimization;',
    'doc["letterSpacingOptimizationThreshold"] = letterSpacingOptimizationThreshold;',
    'doc["letterSpacingOptimization"] | (uint8_t)0',
    'doc["letterSpacingOptimizationThreshold"] | (uint8_t)60',
    'letterSpacingLimitPercent != 10',
    'letterSpacingLimitPercent != 40',
    'letterSpacingLimitPercent != 70',
    'letterSpacingLimitPercent == 550',
    'letterSpacingLimitPercent == 460',
    'letterSpacingLimitPercent == 280',
    'letterSpacingOptimizationThreshold != 0',
    'letterSpacingOptimizationThreshold != 50',
    'letterSpacingOptimizationThreshold != 60',
    'letterSpacingOptimizationThreshold != 70',
]
for token in required:
    if token not in final:
        raise SystemExit(f"CPHUN-191: final persistence token missing: {token}")

print("CPHUN-191 applied: correction, optimization and threshold persist across reload/wake")
