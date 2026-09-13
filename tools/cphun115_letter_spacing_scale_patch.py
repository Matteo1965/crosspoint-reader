from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


settings_ui = Path("src/activities/settings/TextSettingsActivity.cpp")
replace_once(
    settings_ui,
    "const int cur = v == 0 ? 0 : std::clamp<int>((525 - std::clamp<int>(v, 350, 500)) / 25, 1, 7);",
    "const int cur = v == 0 ? 0 : std::clamp<int>((575 - std::clamp<int>(v, 400, 550)) / 25, 1, 7);",
)
replace_once(
    settings_ui,
    "SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint16_t>(525 - idx * 25);",
    "SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint16_t>(575 - idx * 25);",
)
replace_once(
    settings_ui,
    "const int displayPercent = ((525 - std::clamp<int>(v, 350, 500)) / 25) * 10;",
    "const int displayPercent = ((575 - std::clamp<int>(v, 400, 550)) / 25) * 10;",
)

settings_header = Path("src/CrossPointSettings.h")
replace_once(
    settings_header,
    "// value is the word-space stretch threshold in percent (350..500).",
    "// value is the word-space stretch threshold in percent (400..550).",
)

print("CPHUN-115 letter-spacing scale patch applied: 10..70% -> 550..400% thresholds")
