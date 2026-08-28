from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one match in {path}, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# With CPHUN-30 the whole threshold path is uint16_t, so the original
# 360..180 production scale can finally be tested without 8-bit truncation.
replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    '''      // CPHUN-260828-29: widen the low-strength range for font-sensitive faces.
      // Higher UI percentage means stronger/more frequent correction; the internal
      // activation threshold therefore decreases monotonically from 600% to 180%.
      const char* options[] = {tr(STR_STATE_OFF), "10%", "20%", "30%", "40%", "50%", "60%", "70%"};
      constexpr uint16_t thresholds[] = {0, 600, 500, 420, 360, 300, 240, 180};''',
    '''      // CPHUN-260828-31: production scale after the parser threshold was widened
      // to uint16_t end-to-end. Higher UI percentage means stronger/more frequent
      // correction; the internal threshold decreases monotonically from 360% to 180%.
      const char* options[] = {tr(STR_STATE_OFF), "10%", "20%", "30%", "40%", "50%", "60%", "70%"};
      constexpr uint16_t thresholds[] = {0, 360, 330, 300, 270, 240, 210, 180};''',
)

replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    '''                          constexpr uint16_t thresholds[] = {0, 600, 500, 420, 360, 300, 240, 180};''',
    '''                          constexpr uint16_t thresholds[] = {0, 360, 330, 300, 270, 240, 210, 180};''',
)

replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    '''      constexpr uint16_t thresholds[] = {600, 500, 420, 360, 300, 240, 180};''',
    '''      constexpr uint16_t thresholds[] = {360, 330, 300, 270, 240, 210, 180};''',
)

replace_once(
    "src/CrossPointSettings.cpp",
    '''  if (letterSpacingLimitPercent != 0 && letterSpacingLimitPercent != 180 && letterSpacingLimitPercent != 240 &&
      letterSpacingLimitPercent != 300 && letterSpacingLimitPercent != 360 && letterSpacingLimitPercent != 420 &&
      letterSpacingLimitPercent != 500 && letterSpacingLimitPercent != 600) {''',
    '''  if (letterSpacingLimitPercent != 0 && letterSpacingLimitPercent != 180 && letterSpacingLimitPercent != 210 &&
      letterSpacingLimitPercent != 240 && letterSpacingLimitPercent != 270 && letterSpacingLimitPercent != 300 &&
      letterSpacingLimitPercent != 330 && letterSpacingLimitPercent != 360) {''',
)

# Document the existing Soft hyphen support in the version information only.
# No hyphenation parsing/rendering logic is changed by this build.
replace_once(
    "src/activities/settings/CrossPointVersionActivity.cpp",
    '''        hu ? "Kiterjesztett magyar elválasztás" : "Extended Hungarian hyphenation",
        hu ? "Javított sorkizárt szedés" : "Improved justified text layout",''',
    '''        hu ? "Kiterjesztett magyar elválasztás" : "Extended Hungarian hyphenation",
        hu ? "Beágyazott elválasztás (Soft hyphen)" : "Embedded hyphenation (Soft hyphen)",
        hu ? "Javított sorkizárt szedés" : "Improved justified text layout",''',
)

replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260827-19"',
    '#define CPHUN_BUILD_ID "CPHUN-260828-31"',
)

print("CPHUN-260828-31 tracking scale + version info patch applied")
