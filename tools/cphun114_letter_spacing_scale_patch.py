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
    "const int cur = v == 0 ? 0 : std::clamp<int>((380 - std::clamp<int>(v, 240, 360)) / 20, 1, 7);",
    "const int cur = v == 0 ? 0 : std::clamp<int>((525 - std::clamp<int>(v, 350, 500)) / 25, 1, 7);",
)
replace_once(
    settings_ui,
    "SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint16_t>(380 - idx * 20);",
    "SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint16_t>(525 - idx * 25);",
)
replace_once(
    settings_ui,
    "const int displayPercent = (380 - std::clamp<int>(v, 240, 360)) / 2;",
    "const int displayPercent = ((525 - std::clamp<int>(v, 350, 500)) / 25) * 10;",
)

settings_header = Path("src/CrossPointSettings.h")
replace_once(
    settings_header,
    "// value is the word-space stretch threshold in percent (240..360).",
    "// value is the word-space stretch threshold in percent (350..500).",
)

print("CPHUN-114 letter-spacing scale patch applied: 10..70% -> 500..350% thresholds")
