from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-128B: {path}: expected one match, found {count}: {old[:160]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Experimental transfer test: keep the already measured Bitter 16 pt score>=60
# / guardrail-filtered 655-pair table unchanged, but allow that exact table at
# 12, 14, 16 and 18 pt. This isolates size transfer from pair-list changes.
replace_once(
    "src/CrossPointSettings.cpp",
    '''  const bool isBitter16 =
      fontPointSize == 16 && strcmp(sdFontFamilyName, "Bitter") == 0;
  const bool isNotoSerif16 =
      fontPointSize == 16 && sdFontFamilyName[0] == '\\0' && fontFamily == NOTOSERIF;
  const uint8_t bitter16OptimizationProfile =
      letterSpacingLimitPercent > 0 && (isBitter16 || isNotoSerif16)
          ? std::min<uint8_t>(letterSpacingOptimization, 4)
          : 0;''',
    '''  const bool isBitterExperimentalSize =
      (fontPointSize == 12 || fontPointSize == 14 || fontPointSize == 16 ||
       fontPointSize == 18) &&
      strcmp(sdFontFamilyName, "Bitter") == 0;
  const bool isNotoSerif16 =
      fontPointSize == 16 && sdFontFamilyName[0] == '\\0' && fontFamily == NOTOSERIF;
  const uint8_t bitter16OptimizationProfile =
      letterSpacingLimitPercent > 0 && (isBitterExperimentalSize || isNotoSerif16)
          ? std::min<uint8_t>(letterSpacingOptimization, 4)
          : 0;''',
)

replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260916-135-EXP-r3"',
    '#define CPHUN_BUILD_ID "CPHUN-260916-128B-EXP"',
)

print("CPHUN-128B applied: unchanged Bitter score>=60 655-pair table enabled at 12/14/16/18 pt")
