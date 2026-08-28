from pathlib import Path

path = Path("lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h")
text = path.read_text(encoding="utf-8")

old_member = "  uint8_t letterSpacingLimitPercent;\n"
new_member = "  uint16_t letterSpacingLimitPercent;\n"
if text.count(old_member) != 1:
    raise SystemExit(f"Expected one uint8_t member, found {text.count(old_member)}")
text = text.replace(old_member, new_member, 1)

old_param = "      const bool fixedDialogueSpacing, const uint8_t letterSpacingLimitPercent,\n"
new_param = "      const bool fixedDialogueSpacing, const uint16_t letterSpacingLimitPercent,\n"
if text.count(old_param) != 1:
    raise SystemExit(f"Expected one uint8_t constructor parameter, found {text.count(old_param)}")
text = text.replace(old_param, new_param, 1)

path.write_text(text, encoding="utf-8")
print("CPHUN-260828-30 ChapterHtmlSlimParser uint16 threshold fix applied")
