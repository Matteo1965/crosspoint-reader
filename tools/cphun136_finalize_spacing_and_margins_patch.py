from pathlib import Path
import re

# CPHUN-136
# 1) Betűköz optimalizálás: final OFF/ON UI, ON = validated 100% profile (4).
# 2) Screen margin choices: 5, 10, 12, 14, 16, 18, 20, 25 px.
# 3) Vertical text margin rule:
#      screenMargin == 5 -> 4 px
#      otherwise         -> max(0, screenMargin - 6)
#    Status-bar reservation may still enlarge the bottom occupied area.

def replace_once(path, old, new, label):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-136 {label}: expected 1 match, found {count}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")


# ---------------------------------------------------------------------------
# Letter-spacing optimization finalization
# ---------------------------------------------------------------------------

p = Path("src/CrossPointSettings.cpp")
s = p.read_text(encoding="utf-8")

# Legacy persisted profiles 1..4 all become ON=4.
old_load = '''  letterSpacingOptimization =
      std::min<uint8_t>(doc["letterSpacingOptimization"] | (uint8_t)0, 4);'''
if old_load in s:
    s = s.replace(
        old_load,
        '''  letterSpacingOptimization =
      (doc["letterSpacingOptimization"] | (uint8_t)0) ? 4 : 0;''',
        1,
    )
else:
    # Defensive variant if formatting changed.
    s, n = re.subn(
        r'  letterSpacingOptimization\s*=\s*\n\s*std::min<uint8_t>\(doc\["letterSpacingOptimization"\]\s*\|\s*\(uint8_t\)0,\s*4\);',
        '  letterSpacingOptimization =\\n      (doc["letterSpacingOptimization"] | (uint8_t)0) ? 4 : 0;',
        s,
        count=1,
    )
    if n != 1:
        raise SystemExit("CPHUN-136: letterSpacingOptimization load migration anchor not found")

p.write_text(s, encoding="utf-8")

p = Path("src/CrossPointSettings.h")
s = p.read_text(encoding="utf-8")
s = s.replace(
    '''  // 0=off, 1=25%, 2=50%, 3=75%, 4=100% (Bitter 16 pt pilot).
  uint8_t letterSpacingOptimization = 0;''',
    '''  // Final semantics: 0=off, 4=on (fixed validated 100% profile).
  // Legacy stored values 1..3 normalize to 4 on load.
  uint8_t letterSpacingOptimization = 0;''',
    1,
)
p.write_text(s, encoding="utf-8")

p = Path("src/activities/settings/TextSettingsActivity.cpp")
s = p.read_text(encoding="utf-8")

# Percentage picker -> direct toggle.
picker_pattern = re.compile(
    r'''    case LayoutRow::LetterSpacingOptimization: \{\n'''
    r'''      if \(SETTINGS\.letterSpacingLimitPercent == 0\) \{\n'''
    r'''        requestUpdate\(\);\n'''
    r'''        break;\n'''
    r'''      \}\n'''
    r'''      const char\* options\[\] = \{tr\(STR_STATE_OFF\), "25%", "50%", "75%", "100%"\};\n'''
    r'''      const int cur = std::clamp<int>\(SETTINGS\.letterSpacingOptimization, 0, 4\);\n'''
    r'''      optionPopup_\.show\(\n'''
    r'''          I18N\.getLanguage\(\) == Language::HU \? "Betűköz optimalizálás" : "Letter spacing optimization",\n'''
    r'''          options, 5, cur, \[\]\(int idx\) \{\n'''
    r'''            SETTINGS\.letterSpacingOptimization = static_cast<uint8_t>\(std::clamp\(idx, 0, 4\)\);\n'''
    r'''            SETTINGS\.saveToFile\(\);\n'''
    r'''          \}\);\n'''
    r'''      requestUpdate\(\);\n'''
    r'''      break;\n'''
    r'''    \}'''
)
toggle = '''    case LayoutRow::LetterSpacingOptimization:
      if (SETTINGS.letterSpacingLimitPercent == 0) {
        requestUpdate();
        break;
      }
      SETTINGS.letterSpacingOptimization = SETTINGS.letterSpacingOptimization ? 0 : 4;
      SETTINGS.saveToFile();
      requestUpdate();
      break;'''
s, n = picker_pattern.subn(toggle, s, count=1)
if n != 1:
    raise SystemExit("CPHUN-136: letter-spacing percentage picker not found")

value_pattern = re.compile(
    r'''    case LayoutRow::LetterSpacingOptimization: \{\n'''
    r'''      constexpr const char\* labels\[\] = \{"", "25%", "50%", "75%", "100%"\};\n'''
    r'''      const uint8_t profile = std::min<uint8_t>\(SETTINGS\.letterSpacingOptimization, 4\);\n'''
    r'''      return profile == 0 \? tr\(STR_STATE_OFF\) : labels\[profile\];\n'''
    r'''    \}'''
)
s, n = value_pattern.subn(
    '''    case LayoutRow::LetterSpacingOptimization:
      return SETTINGS.letterSpacingOptimization ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);''',
    s,
    count=1,
)
if n != 1:
    raise SystemExit("CPHUN-136: letter-spacing percentage value display not found")

# Explicit non-linear margin scale.
old_margin_consts = '''constexpr int MARGIN_MIN = CrossPointSettings::SCREEN_MARGIN_MIN;
constexpr int MARGIN_MAX = CrossPointSettings::SCREEN_MARGIN_MAX;
constexpr int MARGIN_STEP = CrossPointSettings::SCREEN_MARGIN_STEP;'''
new_margin_consts = '''constexpr uint8_t MARGIN_VALUES[] = {5, 10, 12, 14, 16, 18, 20, 25};

int marginUiIndex(const uint8_t value) {
  int best = 0;
  int bestDistance = 1000;
  for (int i = 0; i < static_cast<int>(std::size(MARGIN_VALUES)); ++i) {
    const int delta = static_cast<int>(value) - static_cast<int>(MARGIN_VALUES[i]);\n    const int distance = delta < 0 ? -delta : delta;
    if (distance < bestDistance) {
      bestDistance = distance;
      best = i;
    }
  }
  return best;
}'''
if old_margin_consts not in s:
    raise SystemExit("CPHUN-136: old linear margin constants not found")
s = s.replace(old_margin_consts, new_margin_consts, 1)

old_margin_ui = '''    case LayoutRow::ScreenMargin: {
      std::vector<std::string> options;
      options.reserve((MARGIN_MAX - MARGIN_MIN) / MARGIN_STEP + 1);
      for (int m = MARGIN_MIN; m <= MARGIN_MAX; m += MARGIN_STEP) options.push_back(std::to_string(m));
      const int cur = (std::clamp<int>(SETTINGS.screenMargin, MARGIN_MIN, MARGIN_MAX) - MARGIN_MIN) / MARGIN_STEP;
      optionPopup_.show(StrId::STR_SCREEN_MARGIN, options, cur, [](int idx) {
        SETTINGS.screenMargin = static_cast<uint8_t>(MARGIN_MIN + idx * MARGIN_STEP);
        SETTINGS.saveToFile();
      });
      requestUpdate();
      break;
    }'''
new_margin_ui = '''    case LayoutRow::ScreenMargin: {
      std::vector<std::string> options;
      options.reserve(std::size(MARGIN_VALUES));
      for (const uint8_t m : MARGIN_VALUES) options.push_back(std::to_string(m));
      const int cur = marginUiIndex(SETTINGS.screenMargin);
      optionPopup_.show(StrId::STR_SCREEN_MARGIN, options, cur, [](int idx) {
        if (idx >= 0 && idx < static_cast<int>(std::size(MARGIN_VALUES))) {
          SETTINGS.screenMargin = MARGIN_VALUES[idx];
          SETTINGS.saveToFile();
        }
      });
      requestUpdate();
      break;
    }'''
if old_margin_ui not in s:
    raise SystemExit("CPHUN-136: old linear ScreenMargin picker not found")
s = s.replace(old_margin_ui, new_margin_ui, 1)

p.write_text(s, encoding="utf-8")


# Hardware actions must not recreate the retired intermediate profiles.
p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text(encoding="utf-8")
old_actions = '''    if (configured == ReaderAction::LetterSpacingOptimizationUp ||
        configured == ReaderAction::LetterSpacingOptimizationDown) {
      int value = std::clamp<int>(SETTINGS.letterSpacingOptimization, 0, 4);
      if (configured == ReaderAction::LetterSpacingOptimizationUp && value < 4) ++value;
      if (configured == ReaderAction::LetterSpacingOptimizationDown && value > 0) --value;
      SETTINGS.letterSpacingOptimization = static_cast<uint8_t>(value);
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }'''
new_actions = '''    if (configured == ReaderAction::LetterSpacingOptimizationUp ||
        configured == ReaderAction::LetterSpacingOptimizationDown) {
      SETTINGS.letterSpacingOptimization =
          configured == ReaderAction::LetterSpacingOptimizationUp ? 4 : 0;
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }'''
if old_actions in s:
    s = s.replace(old_actions, new_actions, 1)
else:
    raise SystemExit("CPHUN-136: hardware optimization action block not found")

# Replace the accumulated historical -4 then -6 vertical adjustments with one
# explicit rule. There are two top-margin call sites: reader render + word selection.
old_top = '''  const int verticalScreenMargin = std::max(0, static_cast<int>(SETTINGS.screenMargin) - 4);
  orientedMarginTop += verticalScreenMargin;
  // CPHUN-57: move the visible top text boundary 6 px upward relative to CPHUN-54.
  orientedMarginTop = std::max(0, orientedMarginTop - 6);'''
new_top = '''  const int verticalScreenMargin =
      SETTINGS.screenMargin == 5 ? 4 : std::max(0, static_cast<int>(SETTINGS.screenMargin) - 6);
  orientedMarginTop += verticalScreenMargin;'''
top_count = s.count(old_top)
if top_count < 2:
    raise SystemExit(f"CPHUN-136: expected at least 2 vertical top-margin blocks, found {top_count}")
s = s.replace(old_top, new_top)

old_bottom = '''  // CPHUN-57: move the visible bottom text boundary 6 px downward relative to CPHUN-54.
  // Apply this after status-bar constraints so the 6 px expansion remains observable.
  orientedMarginBottom = std::max(0, orientedMarginBottom - 6);
'''
if old_bottom not in s:
    raise SystemExit("CPHUN-136: historical bottom -6 adjustment not found")
s = s.replace(old_bottom, "", 1)

p.write_text(s, encoding="utf-8")


# Expand valid stored range. UI remains the explicit eight-value list above.
p = Path("src/CrossPointSettings.h")
s = p.read_text(encoding="utf-8")
old_range = '''  static constexpr uint8_t SCREEN_MARGIN_MIN = 10;
  static constexpr uint8_t SCREEN_MARGIN_MAX = 24;
  static constexpr uint8_t SCREEN_MARGIN_STEP = 2;'''
new_range = '''  static constexpr uint8_t SCREEN_MARGIN_MIN = 5;
  static constexpr uint8_t SCREEN_MARGIN_MAX = 25;
  // UI uses the explicit non-linear list 5,10,12,14,16,18,20,25.
  static constexpr uint8_t SCREEN_MARGIN_STEP = 1;'''
if old_range not in s:
    raise SystemExit("CPHUN-136: screen margin range constants not found")
s = s.replace(old_range, new_range, 1)
p.write_text(s, encoding="utf-8")

print("CPHUN-136 applied: spacing optimization OFF/ON + new margin scale + vertical margin rule")
