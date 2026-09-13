from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# CPHUN-117 keeps the known-good CPHUN-116 hardware/input path intact and
# only replaces the linear letter-spacing scale with the approved non-linear map.
settings_ui = Path("src/activities/settings/TextSettingsActivity.cpp")

replace_once(
    settings_ui,
    "constexpr StrId TAB_NAME_IDS[] = {StrId::STR_FONT, StrId::STR_SIZE, StrId::STR_LAYOUT, StrId::STR_STYLE};\n",
    "constexpr StrId TAB_NAME_IDS[] = {StrId::STR_FONT, StrId::STR_SIZE, StrId::STR_LAYOUT, StrId::STR_STYLE};\n\n"
    "constexpr uint16_t LETTER_SPACING_THRESHOLDS[] = {0, 550, 530, 500, 460, 410, 350, 280};\n\n"
    "int letterSpacingUiIndex(const uint16_t value) {\n"
    "  if (value == 0) return 0;\n"
    "  int best = 1;\n"
    "  uint16_t bestDiff = value > LETTER_SPACING_THRESHOLDS[1]\n"
    "                          ? value - LETTER_SPACING_THRESHOLDS[1]\n"
    "                          : LETTER_SPACING_THRESHOLDS[1] - value;\n"
    "  for (int i = 2; i < static_cast<int>(std::size(LETTER_SPACING_THRESHOLDS)); ++i) {\n"
    "    const uint16_t threshold = LETTER_SPACING_THRESHOLDS[i];\n"
    "    const uint16_t diff = value > threshold ? value - threshold : threshold - value;\n"
    "    if (diff < bestDiff) {\n"
    "      best = i;\n"
    "      bestDiff = diff;\n"
    "    }\n"
    "  }\n"
    "  return best;\n"
    "}\n",
)

replace_once(
    settings_ui,
    "const int cur = v == 0 ? 0 : std::clamp<int>((575 - std::clamp<int>(v, 400, 550)) / 25, 1, 7);",
    "const int cur = letterSpacingUiIndex(v);",
)

replace_once(
    settings_ui,
    "SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint16_t>(575 - idx * 25);",
    "SETTINGS.letterSpacingLimitPercent = LETTER_SPACING_THRESHOLDS[std::clamp(idx, 0, 7)];",
)

replace_once(
    settings_ui,
    "const int displayPercent = ((575 - std::clamp<int>(v, 400, 550)) / 25) * 10;",
    "const int displayPercent = letterSpacingUiIndex(v) * 10;",
)

settings_header = Path("src/CrossPointSettings.h")
replace_once(
    settings_header,
    "// value is the word-space stretch threshold in percent (400..550).",
    "// value is the word-space stretch threshold in percent (280..550), using a non-linear UI scale.",
)

print("CPHUN-117 applied: 10..70% -> 550,530,500,460,410,350,280 thresholds")
