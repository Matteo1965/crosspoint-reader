from pathlib import Path

p = Path("src/activities/settings/TextSettingsPreview.cpp")
s = p.read_text(encoding="utf-8")
old = """  ParsedText parsed(SETTINGS.extraParagraphSpacing != 0, SETTINGS.hyphenationEnabled != 0,
                    SETTINGS.focusReadingEnabled != 0, 0, SETTINGS.fixedDialogueSpacing != 0, style);
"""
new = """  ParsedText parsed(SETTINGS.extraParagraphSpacing != 0, SETTINGS.hyphenationEnabled != 0,
                    SETTINGS.softHyphenEnabled != 0, SETTINGS.focusReadingEnabled != 0, 0,
                    SETTINGS.fixedDialogueSpacing != 0, SETTINGS.letterSpacingLimitPercent, style);
"""
count = s.count(old)
if count != 1:
    raise SystemExit(f"TextSettingsPreview ParsedText marker: expected 1, found {count}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("TextSettingsPreview ParsedText wiring updated")
