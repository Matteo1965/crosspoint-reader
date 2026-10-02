from pathlib import Path
import re

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, text):
    Path(path).write_text(text, encoding="utf-8")

def replace_once(path, old, new, label):
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-183 {label}: expected one match, found {count}")
    write(path, text.replace(old, new, 1))

# ---------------------------------------------------------------------------
# 1) Optimization threshold: final four-state semantics.
#    OFF=0, Weak=50, Medium=60, Strong=70.
#    Accept 0 on load (the previous validator silently normalized it to 60),
#    and never encode a threshold code for OFF.
# ---------------------------------------------------------------------------
p = "src/CrossPointSettings.cpp"
s = read(p)

# The reconstructed CPHUN chain has used a few whitespace/layout variants for
# this block. Match semantics, not formatting.
load_re = re.compile(
    r'  letterSpacingOptimizationThreshold\s*=\s*'
    r'doc\["letterSpacingOptimizationThreshold"\]\s*\|\s*\(uint8_t\)60;\s*'
    r'if\s*\([^\{]+\)\s*\{\s*'
    r'letterSpacingOptimizationThreshold\s*=\s*60;\s*'
    r'needsResave\s*=\s*true;\s*\}',
    re.S,
)
new_load = """  letterSpacingOptimizationThreshold =
      doc["letterSpacingOptimizationThreshold"] | (uint8_t)60;
  if (letterSpacingOptimizationThreshold != 0 &&
      letterSpacingOptimizationThreshold != 50 &&
      letterSpacingOptimizationThreshold != 60 &&
      letterSpacingOptimizationThreshold != 70) {
    letterSpacingOptimizationThreshold = 60;
    needsResave = true;
  }"""
s, count = load_re.subn(new_load, s, count=1)
if count != 1:
    # Diagnostic excerpt makes future generated-chain changes obvious in CI.
    pos = s.find('letterSpacingOptimizationThreshold')
    excerpt = s[max(0, pos-300):pos+900] if pos >= 0 else '<token absent>'
    raise SystemExit("CPHUN-183 threshold load validator not found. Excerpt:\n" + excerpt)

encode_re = re.compile(
    r'  const uint8_t optimizationThresholdCode\s*=\s*'
    r'letterSpacingLimitPercent\s*>\s*0\s*&&\s*letterSpacingOptimization\s*&&\s*'
    r'\(isBitterExperimentalSize\s*\|\|\s*isNotoSerif16\)\s*'
    r'\?\s*static_cast<uint8_t>\(\(letterSpacingOptimizationThreshold\s*-\s*45u\)\s*/\s*5u\)\s*'
    r':\s*0;',
    re.S,
)
new_encode = """  const uint8_t optimizationThresholdCode =
      letterSpacingLimitPercent > 0 && letterSpacingOptimization &&
              letterSpacingOptimizationThreshold >= 50 &&
              (isBitterExperimentalSize || isNotoSerif16)
          ? static_cast<uint8_t>((letterSpacingOptimizationThreshold - 45u) / 5u)
          : 0;"""
s, count = encode_re.subn(new_encode, s, count=1)
if count != 1:
    pos = s.find('optimizationThresholdCode')
    excerpt = s[max(0, pos-300):pos+900] if pos >= 0 else '<token absent>'
    raise SystemExit("CPHUN-183 threshold encode block not found. Excerpt:\n" + excerpt)
write(p, s)

# Stable display literals used by the CPHUN-182 English Layout crash fix.
p = "src/activities/settings/TextSettingsActivity.cpp"
s = read(p)
old_helper = """const char* letterSpacingThresholdLabel(const uint8_t value) {
  switch (value) {
    case 50: return "50";
    case 55: return "55";
    case 60: return "60";
    case 65: return "65";
    case 70: return "70";
    case 75: return "75";
    default: return "60";
  }
}
"""
new_helper = """const char* letterSpacingThresholdLabel(const uint8_t value) {
  switch (value) {
    case 0: return "0";
    case 50: return "50";
    case 60: return "60";
    case 70: return "70";
    default: return "60";
  }
}
"""
if old_helper not in s:
    raise SystemExit("CPHUN-183 stable threshold label helper missing")
s = s.replace(old_helper, new_helper, 1)

# Replace only the picker case inside confirmLayoutRow(), leaving the value
# display case in layoutValueText() untouched.
fn_start = s.find("void TextSettingsActivity::confirmLayoutRow(int row)")
fn_end = s.find("void TextSettingsActivity::confirmStyleRow", fn_start)
if fn_start < 0 or fn_end < 0:
    raise SystemExit("CPHUN-183 confirmLayoutRow boundaries missing")
section = s[fn_start:fn_end]
pattern = re.compile(
    r'    case LayoutRow::LetterSpacingOptimizationThreshold: \{.*?'
    r'\n    \}\n    case LayoutRow::ShortHyphen:',
    re.S,
)
replacement = """    case LayoutRow::LetterSpacingOptimizationThreshold: {
      const bool hu = I18N.getLanguage() == Language::HU;
      const char* options[] = {
          hu ? "KI" : "OFF",
          hu ? "Gyenge" : "Weak",
          hu ? "Közepes" : "Medium",
          hu ? "Erős" : "Strong",
      };
      int cur = 2;
      switch (SETTINGS.letterSpacingOptimizationThreshold) {
        case 0: cur = 0; break;
        case 50: cur = 1; break;
        case 60: cur = 2; break;
        case 70: cur = 3; break;
        default: cur = 2; break;
      }
      optionPopup_.show(
          hu ? "Optimalizációs küszöb" : "Optimization threshold",
          options, 4, cur, [](int idx) {
            static constexpr uint8_t values[] = {0, 50, 60, 70};
            if (idx >= 0 && idx < 4) {
              SETTINGS.letterSpacingOptimizationThreshold = values[idx];
              SETTINGS.saveToFile();
            }
          });
      requestUpdate();
      break;
    }
    case LayoutRow::ShortHyphen:"""
section2, count = pattern.subn(replacement, section, count=1)
if count != 1:
    raise SystemExit(f"CPHUN-183 threshold picker case matches={count}")
s = s[:fn_start] + section2 + s[fn_end:]
write(p, s)

# ---------------------------------------------------------------------------
# 2) Library View is EPUB-only. Browse Files is untouched.
#    Bump CLIX format so an existing mixed-format index is rejected and rebuilt.
# ---------------------------------------------------------------------------
replace_once(
    "lib/LibraryIndex/LibraryBuilder.cpp",
    """bool isBookName(const std::string& name) {
  return FsHelpers::checkFileExtension(name, ".epub") || FsHelpers::checkFileExtension(name, ".txt") ||
         FsHelpers::checkFileExtension(name, ".md") || FsHelpers::checkFileExtension(name, ".xtc");
}""",
    """bool isBookName(const std::string& name) {
  // Hungarian Edition Library View is an EPUB bookshelf. Other supported
  // formats remain available through Browse Files / Fájlböngésző.
  return FsHelpers::checkFileExtension(name, ".epub");
}""",
    "EPUB-only Library filter",
)

replace_once(
    "lib/LibraryIndex/LibraryFormat.h",
    "inline constexpr uint8_t CLIX_FORMAT_VERSION = 2;",
    "inline constexpr uint8_t CLIX_FORMAT_VERSION = 3;",
    "Library index migration version",
)

# ---------------------------------------------------------------------------
# 3) Version-page/build assertions.
# ---------------------------------------------------------------------------
build_id = read("src/CPHUNBuildId.h")
if 'CPHUN_BUILD_ID "CPHUN-261002-183-EXP"' not in build_id:
    raise SystemExit("CPHUN-183 build id missing")
version_page = read("src/activities/settings/CrossPointVersionActivity.cpp")
for token in ["hungarianEditionLabel()", "CPHUN_BUILD_ID", 'drawLabelValue(tr(STR_EDITION), editionLabel.c_str())']:
    if token not in version_page:
        raise SystemExit(f"CPHUN-183 version-page token missing: {token}")

# Final semantic checks.
settings = read("src/CrossPointSettings.cpp")
ui = read("src/activities/settings/TextSettingsActivity.cpp")
library = read("lib/LibraryIndex/LibraryBuilder.cpp")
fmt = read("lib/LibraryIndex/LibraryFormat.h")
checks = [
    ('letterSpacingOptimizationThreshold != 0', settings),
    ('letterSpacingOptimizationThreshold >= 50', settings),
    ('case 0: return "0";', ui),
    ('static constexpr uint8_t values[] = {0, 50, 60, 70};', ui),
    ('hu ? "KI" : "OFF"', ui),
    ('return FsHelpers::checkFileExtension(name, ".epub");', library),
    ('CLIX_FORMAT_VERSION = 3', fmt),
]
for token, text in checks:
    if token not in text:
        raise SystemExit(f"CPHUN-183 semantic check failed: {token}")

print("CPHUN-183 applied: threshold OFF/50/60/70 + English-safe picker + EPUB-only Library + forced index migration + v183 audit")
