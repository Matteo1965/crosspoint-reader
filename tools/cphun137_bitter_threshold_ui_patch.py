from pathlib import Path
import re

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, s):
    Path(path).write_text(s, encoding="utf-8")

# CPHUN-137 EXP preparation:
# Persist and expose the Bitter pair-safety score threshold.
# Valid test values: 50,55,60,65,70,75. Default = 60.
#
# NOTE: This patch only adds the persisted UI/control value. The size-specific
# scored pair tables are attached by the following measurement/table patch,
# so the threshold is not consumed by LetterSpacingOptimization here yet.

p = "src/CrossPointSettings.h"
s = read(p)
anchor = "  uint8_t letterSpacingOptimization = 0;"
if s.count(anchor) != 1:
    raise SystemExit(f"CPHUN-137: letterSpacingOptimization field matches={s.count(anchor)}")
s = s.replace(
    anchor,
    anchor + "\n"
    "  // Experimental Bitter pair-safety score threshold. Test scale: 50..75 in 5-point steps.\n"
    "  uint8_t letterSpacingPairThreshold = 60;",
    1,
)
write(p, s)

p = "src/CrossPointSettings.cpp"
s = read(p)

save_anchor = '  doc["letterSpacingOptimization"] = letterSpacingOptimization;'
if s.count(save_anchor) != 1:
    raise SystemExit(f"CPHUN-137: threshold save anchor matches={s.count(save_anchor)}")
s = s.replace(
    save_anchor,
    save_anchor + '\n  doc["letterSpacingPairThreshold"] = letterSpacingPairThreshold;',
    1,
)

# Load directly after the optimization flag/profile normalization. Accept only
# the six explicit test values, otherwise normalize to the default 60.
load_re = re.compile(
    r'(  letterSpacingOptimization\s*=\s*\n?\s*\(doc\["letterSpacingOptimization"\]\s*\|\s*\(uint8_t\)0\)\s*\?\s*4\s*:\s*0;\n)'
)
m = load_re.search(s)
if not m:
    raise SystemExit("CPHUN-137: letterSpacingOptimization load block not found")
load = m.group(1) + '''  letterSpacingPairThreshold = doc["letterSpacingPairThreshold"] | (uint8_t)60;
  if (letterSpacingPairThreshold != 50 && letterSpacingPairThreshold != 55 &&
      letterSpacingPairThreshold != 60 && letterSpacingPairThreshold != 65 &&
      letterSpacingPairThreshold != 70 && letterSpacingPairThreshold != 75) {
    letterSpacingPairThreshold = 60;
    needsResave = true;
  }
'''
s = s[:m.start()] + load + s[m.end():]
write(p, s)

# Add a Text Settings row directly after Betűköz optimalizálás.
p = "src/activities/settings/TextSettingsActivity.h"
s = read(p)
enum_anchor = "    LetterSpacingOptimization,\n"
if s.count(enum_anchor) != 1:
    raise SystemExit(f"CPHUN-137: LayoutRow optimization enum matches={s.count(enum_anchor)}")
s = s.replace(enum_anchor, enum_anchor + "    LetterSpacingPairThreshold,\n", 1)
write(p, s)

p = "src/activities/settings/TextSettingsActivity.cpp"
s = read(p)

# Label mapping in buildScreen/list construction.
label_anchor = '''        } else if (i == static_cast<int>(LayoutRow::LetterSpacingOptimization)) {
          item.label = I18N.getLanguage() == Language::HU ? "Betűköz optimalizálás" : "Letter spacing optimization";
'''
if s.count(label_anchor) != 1:
    raise SystemExit(f"CPHUN-137: optimization label anchor matches={s.count(label_anchor)}")
s = s.replace(
    label_anchor,
    label_anchor +
    '''        } else if (i == static_cast<int>(LayoutRow::LetterSpacingPairThreshold)) {
          item.label = I18N.getLanguage() == Language::HU ? "Optimalizációs küszöb" : "Optimization threshold";
''',
    1,
)

# Activation: insert after the final OFF/ON optimization case.
case_anchor = '''    case LayoutRow::LetterSpacingOptimization:
      if (SETTINGS.letterSpacingLimitPercent == 0) {
        requestUpdate();
        break;
      }
      SETTINGS.letterSpacingOptimization = SETTINGS.letterSpacingOptimization ? 0 : 4;
      SETTINGS.saveToFile();
      requestUpdate();
      break;'''
if s.count(case_anchor) != 1:
    raise SystemExit(f"CPHUN-137: final optimization toggle case matches={s.count(case_anchor)}")
s = s.replace(
    case_anchor,
    case_anchor +
    '''
    case LayoutRow::LetterSpacingPairThreshold: {
      const char* options[] = {"50", "55", "60", "65", "70", "75"};
      int cur = 2;
      switch (SETTINGS.letterSpacingPairThreshold) {
        case 50: cur = 0; break;
        case 55: cur = 1; break;
        case 60: cur = 2; break;
        case 65: cur = 3; break;
        case 70: cur = 4; break;
        case 75: cur = 5; break;
        default: cur = 2; break;
      }
      optionPopup_.show(
          I18N.getLanguage() == Language::HU ? "Optimalizációs küszöb" : "Optimization threshold",
          options, 6, cur, [](int idx) {
            static constexpr uint8_t values[] = {50, 55, 60, 65, 70, 75};
            if (idx >= 0 && idx < 6) {
              SETTINGS.letterSpacingPairThreshold = values[idx];
              SETTINGS.saveToFile();
            }
          });
      requestUpdate();
      break;
    }''',
    1,
)

# Current value display.
value_anchor = '''    case LayoutRow::LetterSpacingOptimization:
      return SETTINGS.letterSpacingOptimization ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);'''
if s.count(value_anchor) != 1:
    raise SystemExit(f"CPHUN-137: optimization value case matches={s.count(value_anchor)}")
s = s.replace(
    value_anchor,
    value_anchor +
    '''
    case LayoutRow::LetterSpacingPairThreshold:
      return std::to_string(SETTINGS.letterSpacingPairThreshold);''',
    1,
)
write(p, s)

# Semantic checks.
all_text = (
    read("src/CrossPointSettings.h") +
    read("src/CrossPointSettings.cpp") +
    read("src/activities/settings/TextSettingsActivity.h") +
    read("src/activities/settings/TextSettingsActivity.cpp")
)
for token in [
    "letterSpacingPairThreshold = 60",
    'doc["letterSpacingPairThreshold"]',
    "LetterSpacingPairThreshold",
    '"Optimalizációs küszöb"',
    '{"50", "55", "60", "65", "70", "75"}',
]:
    if token not in all_text:
        raise SystemExit(f"CPHUN-137: threshold infrastructure missing: {token}")

print("CPHUN-137 preparation applied: persistent 50/55/60/65/70/75 optimization threshold UI")
