from pathlib import Path

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, text):
    Path(path).write_text(text, encoding="utf-8")

def replace_once(path, old, new, label):
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-182 UI {label}: expected one match, found {count}")
    write(path, text.replace(old, new, 1))

# ---------------------------------------------------------------------------
# 1) Restrict the Hungarian Edition UI language chooser to the 12 languages
#    that have an upstream 1.6.5 hyphenation trie (plus our Hungarian engine).
#    Keep all translation modules in the binary; only the selectable UI list is
#    constrained. Existing unsupported saved languages are normalized to HU.
# ---------------------------------------------------------------------------
p = "src/activities/settings/LanguageSelectActivity.h"
s = read(p)
s = s.replace(
    "  constexpr static uint8_t totalItems = getLanguageCount();",
    "  constexpr static uint8_t totalItems = 12;",
    1,
)
if "constexpr static uint8_t totalItems = 12;" not in s:
    raise SystemExit("CPHUN-182 UI language list: totalItems patch failed")
write(p, s)

p = "src/activities/settings/LanguageSelectActivity.cpp"
s = read(p)
anchor = "namespace fui = freeink::ui;\n"
if anchor not in s:
    raise SystemExit("CPHUN-182 UI language list: namespace anchor missing")
langs = """namespace {
constexpr Language UI_LANGUAGES[] = {
    Language::HU, Language::EN, Language::DE, Language::ES,
    Language::IT, Language::FR, Language::P2, Language::PL,
    Language::FI, Language::RU, Language::SV, Language::UK,
};
static_assert(std::size(UI_LANGUAGES) == 12);
}  // namespace

"""
s = s.replace(anchor, anchor + "\n" + langs, 1)

old_enter = """  const auto currentLang = static_cast<uint8_t>(I18N.getLanguage());
  const auto* begin = std::begin(SORTED_LANGUAGE_INDICES);
  const auto* end = std::end(SORTED_LANGUAGE_INDICES);
  const auto* it = std::find(begin, end, currentLang);
  nav.selected = (it != end) ? static_cast<int>(std::distance(begin, it)) : 0;"""
new_enter = """  const Language currentLang = I18N.getLanguage();
  nav.selected = 0;
  for (int i = 0; i < totalItems; ++i) {
    if (UI_LANGUAGES[i] == currentLang) {
      nav.selected = i;
      break;
    }
  }"""
if old_enter not in s:
    raise SystemExit("CPHUN-182 UI language list: onEnter selection anchor missing")
s = s.replace(old_enter, new_enter, 1)

s = s.replace(
    "    item.label = I18N.getLanguageName(static_cast<Language>(SORTED_LANGUAGE_INDICES[i]));\n"
    "    if (SORTED_LANGUAGE_INDICES[i] == currentLang) {",
    "    item.label = I18N.getLanguageName(UI_LANGUAGES[i]);\n"
    "    if (UI_LANGUAGES[i] == currentLang) {",
    1,
)
s = s.replace(
    "  const uint8_t langIndex = SORTED_LANGUAGE_INDICES[index];",
    "  const uint8_t langIndex = static_cast<uint8_t>(UI_LANGUAGES[index]);",
    1,
)
if "SORTED_LANGUAGE_INDICES" in s:
    raise SystemExit("CPHUN-182 UI language list: legacy full-language table still used")
write(p, s)

# I18N singleton itself starts in Hungarian before settings are loaded.
replace_once(
    "lib/I18n/I18n.h",
    "  I18n() : _language(Language::EN) {}",
    "  I18n() : _language(Language::HU) {}",
    "I18n default HU",
)

# Settings default is also Hungarian, so a brand-new settings file cannot
# overwrite the singleton back to English during first boot.
p = "src/CrossPointSettings.h"
s = read(p)
if "#include <I18n.h>" not in s:
    s = s.replace("#include <ArduinoJson.h>\n", "#include <ArduinoJson.h>\n#include <I18n.h>\n", 1)
s = s.replace(
    "  // Language setting (Language enum index, default 0 = EN)\n  uint8_t language = 0;",
    "  // Hungarian Edition default UI language. Persisted as a stable BCP-47/code string.\n"
    "  uint8_t language = static_cast<uint8_t>(Language::HU);",
    1,
)
if "language = static_cast<uint8_t>(Language::HU);" not in s:
    raise SystemExit("CPHUN-182 UI language list: settings default HU patch failed")
write(p, s)

# Normalize a previously saved language that is no longer offered by the
# Hungarian Edition selector. This prevents an untested module from remaining
# active invisibly after a firmware upgrade.
p = "src/CrossPointSettings.cpp"
s = read(p)
old_load = """  // Language -- stored as code string for stability across enum reorders.
  if (doc["language"].is<const char*>()) {
    language = static_cast<uint8_t>(I18n::languageFromCode(doc["language"].as<const char*>()));
  }"""
new_load = """  // Language -- stored as code string for stability across enum reorders.
  // Hungarian Edition deliberately exposes only the 12 tested reading/UI
  // languages. Any older saved choice outside this set falls back to Magyar.
  if (doc["language"].is<const char*>()) {
    const Language loadedLanguage = I18n::languageFromCode(doc["language"].as<const char*>());
    switch (loadedLanguage) {
      case Language::HU:
      case Language::EN:
      case Language::DE:
      case Language::ES:
      case Language::IT:
      case Language::FR:
      case Language::P2:
      case Language::PL:
      case Language::FI:
      case Language::RU:
      case Language::SV:
      case Language::UK:
        language = static_cast<uint8_t>(loadedLanguage);
        break;
      default:
        language = static_cast<uint8_t>(Language::HU);
        needsResave = true;
        break;
    }
  }"""
if old_load not in s:
    raise SystemExit("CPHUN-182 UI language list: settings load anchor missing")
s = s.replace(old_load, new_load, 1)
write(p, s)

# ---------------------------------------------------------------------------
# 2) Fix English Text Settings -> Layout crash/corruption.
#    The generated CPHUN-137 threshold row was the only row whose displayed
#    value was observed corrupt immediately before abort(). Do not hand the UI
#    a c_str() owned by a mutable std::string for this row; use a stable literal
#    selected from the six valid persisted values.
# ---------------------------------------------------------------------------
p = "src/activities/settings/TextSettingsActivity.cpp"
s = read(p)
helper_anchor = """std::string lineSpacingLabel(const uint8_t value) {"""
idx = s.find(helper_anchor)
if idx < 0:
    raise SystemExit("CPHUN-182 UI threshold: helper anchor missing")
end_marker = "\n}\nconstexpr StrId ALIGNMENT_IDS[]"
end = s.find(end_marker, idx)
if end < 0:
    raise SystemExit("CPHUN-182 UI threshold: lineSpacing helper end missing")
threshold_helper = """
const char* letterSpacingThresholdLabel(const uint8_t value) {
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
s = s[:end+2] + "\n" + threshold_helper + s[end+2:]

old_value_assign = """    rowItems_[i].value = rowValues_[i].empty() ? nullptr : rowValues_[i].c_str();"""
new_value_assign = """    if (tab_ == Tab::Layout && i == static_cast<int>(LayoutRow::LetterSpacingOptimizationThreshold)) {
      // Stable literal: avoids the English Layout crash seen when the longer
      // label caused the UI to consume a stale mutable-string value pointer.
      rowItems_[i].value = letterSpacingThresholdLabel(SETTINGS.letterSpacingOptimizationThreshold);
    } else {
      rowItems_[i].value = rowValues_[i].empty() ? nullptr : rowValues_[i].c_str();
    }"""
if old_value_assign not in s:
    raise SystemExit("CPHUN-182 UI threshold: row value assignment anchor missing")
s = s.replace(old_value_assign, new_value_assign, 1)

# Keep layoutValueText deterministic too; no temporary numeric conversion for
# the threshold row anywhere in the render path.
old_threshold_value = """    case LayoutRow::LetterSpacingOptimizationThreshold:
      return std::to_string(SETTINGS.letterSpacingOptimizationThreshold);"""
new_threshold_value = """    case LayoutRow::LetterSpacingOptimizationThreshold:
      return letterSpacingThresholdLabel(SETTINGS.letterSpacingOptimizationThreshold);"""
# Historical generated chains express this value in slightly different forms.
# The actual crash fix is the stable literal assigned to rowItems_ above; this
# normalization is optional and only applied when the exact old form is present.
if old_threshold_value in s:
    s = s.replace(old_threshold_value, new_threshold_value, 1)
write(p, s)

# ---------------------------------------------------------------------------
# 3) RoundedRaff Home: cache exactly the real 400px cover image, including the
#    +14px image offset used by RoundedRaffTheme. The old cache started 14px too
#    high, so its bottom 14px were lost after a menu-selection repaint.
# ---------------------------------------------------------------------------
p = "src/activities/home/HomeActivity.cpp"
s = read(p)
old_cover_rect = """  coverRectX = 0;
  coverRectY = metrics.homeTopPadding + 24;
  coverRectW = pageWidth;
  coverRectH = metrics.homeCoverTileHeight;"""
new_cover_rect = """  coverRectX = 0;
  const bool roundedRaffHome =
      static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) == CrossPointSettings::UI_THEME::ROUNDEDRAFF;
  coverRectY = metrics.homeTopPadding + 24 + (roundedRaffHome ? 14 : 0);
  coverRectW = pageWidth;
  coverRectH = roundedRaffHome ? metrics.homeCoverHeight : metrics.homeCoverTileHeight;"""
if old_cover_rect not in s:
    raise SystemExit("CPHUN-182 UI home cache: cover rect anchor missing")
s = s.replace(old_cover_rect, new_cover_rect, 1)
write(p, s)

print("CPHUN-182 UI stability applied: 12-language chooser + HU default + English Layout threshold fix + RR cover cache")
