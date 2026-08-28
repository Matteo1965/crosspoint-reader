from pathlib import Path


def replace_exact(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Expected source block not found in {path}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Settings storage must hold thresholds above 255.
replace_exact(
    "src/CrossPointSettings.h",
    "  // 0 disables the post-layout +1 px letter-spacing correction; otherwise the\n"
    "  // value is the word-space stretch threshold in percent (120..240).\n"
    "  uint8_t letterSpacingLimitPercent = 0;",
    "  // 0 disables the post-layout +1 px letter-spacing correction; otherwise the\n"
    "  // value is the word-space stretch threshold in percent (180..360).\n"
    "  uint16_t letterSpacingLimitPercent = 0;",
)

replace_exact(
    "src/CrossPointSettings.cpp",
    "  letterSpacingLimitPercent = doc[\"letterSpacingLimitPercent\"] | (uint8_t)0;\n"
    "  if (letterSpacingLimitPercent != 0 &&\n"
    "      (letterSpacingLimitPercent < 120 || letterSpacingLimitPercent > 240 || letterSpacingLimitPercent % 20 != 0)) {",
    "  letterSpacingLimitPercent = doc[\"letterSpacingLimitPercent\"] | (uint16_t)0;\n"
    "  if (letterSpacingLimitPercent != 0 &&\n"
    "      (letterSpacingLimitPercent < 180 || letterSpacingLimitPercent > 360 || letterSpacingLimitPercent % 30 != 0)) {",
)

# Propagate 16-bit threshold through render specification and layout object.
replace_exact(
    "lib/Epub/Epub/ReaderRenderSpec.h",
    "  uint8_t letterSpacingLimitPercent = 0;",
    "  uint16_t letterSpacingLimitPercent = 0;",
)

replace_exact(
    "lib/Epub/Epub/ParsedText.h",
    "  uint8_t letterSpacingLimitPercent;",
    "  uint16_t letterSpacingLimitPercent;",
)
replace_exact(
    "lib/Epub/Epub/ParsedText.h",
    "                      const uint8_t letterSpacingLimitPercent = 0, const BlockStyle& blockStyle = BlockStyle())",
    "                      const uint16_t letterSpacingLimitPercent = 0, const BlockStyle& blockStyle = BlockStyle())",
)

# Cache header layout changes because the threshold field grows from 1 to 2 bytes.
replace_exact(
    "lib/Epub/Epub/Section.cpp",
    "// v52: TextBlock serialization stores the exact letterSpacingPx value instead of\n"
    "//      reducing every non-zero tracking value to a one-bit +1 px flag.\n"
    "constexpr uint8_t SECTION_FILE_VERSION = 52;",
    "// v52: TextBlock serialization stores the exact letterSpacingPx value instead of\n"
    "//      reducing every non-zero tracking value to a one-bit +1 px flag.\n"
    "// v53: letterSpacingLimitPercent widened from uint8_t to uint16_t so the\n"
    "//      production correction scale can use thresholds above 255%.\n"
    "constexpr uint8_t SECTION_FILE_VERSION = 53;",
)
replace_exact(
    "lib/Epub/Epub/Section.cpp",
    "sizeof(uint8_t) + sizeof(bool) + sizeof(uint8_t) + sizeof(bool) + sizeof(uint8_t) + sizeof(uint8_t) +\n",
    "sizeof(uint8_t) + sizeof(bool) + sizeof(uint8_t) + sizeof(bool) + sizeof(uint8_t) + sizeof(uint16_t) +\n",
)
replace_exact(
    "lib/Epub/Epub/Section.cpp",
    "    uint8_t fileLetterSpacingLimitPercent;",
    "    uint16_t fileLetterSpacingLimitPercent;",
)

# CPHUN-28 UI scale: 10..70% maps to 360..180% internal threshold.
replace_exact(
    "src/activities/settings/TextSettingsActivity.cpp",
    "      // CPHUN-260827-27: expose correction strength in the intuitive direction:\n"
    "      // higher UI percentage means more lines are eligible for +1 px tracking.\n"
    "      // Internally we keep the proven CPHUN-26 activation thresholds unchanged.\n"
    "      const char* options[] = {tr(STR_STATE_OFF), \"10%\", \"20%\", \"30%\", \"40%\", \"50%\", \"60%\", \"70%\"};\n"
    "      int cur = 0;\n"
    "      if (SETTINGS.letterSpacingLimitPercent >= 120 && SETTINGS.letterSpacingLimitPercent <= 240) {\n"
    "        cur = 1 + (240 - SETTINGS.letterSpacingLimitPercent) / 20;\n"
    "      }",
    "      // CPHUN-260828-28: gentler production scale. Higher UI percentage still\n"
    "      // means more lines are eligible, but thresholds now span 360% down to 180%.\n"
    "      const char* options[] = {tr(STR_STATE_OFF), \"10%\", \"20%\", \"30%\", \"40%\", \"50%\", \"60%\", \"70%\"};\n"
    "      int cur = 0;\n"
    "      if (SETTINGS.letterSpacingLimitPercent >= 180 && SETTINGS.letterSpacingLimitPercent <= 360 &&\n"
    "          SETTINGS.letterSpacingLimitPercent % 30 == 0) {\n"
    "        cur = 1 + (360 - SETTINGS.letterSpacingLimitPercent) / 30;\n"
    "      }",
)
replace_exact(
    "src/activities/settings/TextSettingsActivity.cpp",
    "                          SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint8_t>(260 - idx * 20);",
    "                          SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint16_t>(390 - idx * 30);",
)
replace_exact(
    "src/activities/settings/TextSettingsActivity.cpp",
    "    case LayoutRow::LetterSpacingCorrection:\n"
    "      if (SETTINGS.letterSpacingLimitPercent >= 120 && SETTINGS.letterSpacingLimitPercent <= 240) {\n"
    "        return std::to_string((260 - SETTINGS.letterSpacingLimitPercent) / 2) + \"%\";\n"
    "      }\n"
    "      return tr(STR_STATE_OFF);",
    "    case LayoutRow::LetterSpacingCorrection:\n"
    "      if (SETTINGS.letterSpacingLimitPercent >= 180 && SETTINGS.letterSpacingLimitPercent <= 360 &&\n"
    "          SETTINGS.letterSpacingLimitPercent % 30 == 0) {\n"
    "        return std::to_string((390 - SETTINGS.letterSpacingLimitPercent) / 3) + \"%\";\n"
    "      }\n"
    "      return tr(STR_STATE_OFF);",
)

print("CPHUN-260828-28 tracking threshold scale patch applied")
