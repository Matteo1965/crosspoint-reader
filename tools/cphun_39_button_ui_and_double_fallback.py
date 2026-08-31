from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"CPHUN-39 anchor missing in {path}: {old!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Bottom-button mapping screen: device-photo based alignment corrections.
p = Path("src/activities/settings/ButtonFunctionsActivity.cpp")
text = p.read_text(encoding="utf-8")
text = text.replace("constexpr int kButtonX = 145;", "constexpr int kButtonX = 105;", 1)
text = text.replace("constexpr int kActionX = 285;", "constexpr int kActionX = 235;", 1)
text = text.replace(
    'return I18N.getLanguage() == Language::HU ? "Alsó gombok" : "Bottom buttons";',
    'return I18N.getLanguage() == Language::HU ? "Alsó gombkiosztás" : "Bottom button mapping";',
    1,
)
text = text.replace(
    'const int textY = rowTop + std::max(0, (rowHeight - textHeight) / 2);',
    '// FreeInk selection pill sits about 10 px below the custom fixed-column text baseline on X4.\n'
    '    // Match the custom labels to the visual centre of the selection pill.\n'
    '    const int textY = rowTop + std::max(0, (rowHeight - textHeight) / 2) + 10;',
    1,
)
text = text.replace(
    '(I18N.getLanguage() == Language::HU ? "Tart:" : "Hold:")',
    '(I18N.getLanguage() == Language::HU ? "Hosszan:" : "Hold:")',
    1,
)
p.write_text(text, encoding="utf-8")

# Restore the four device-confirmed CPHUN-36 v2 hard-wired 2x actions as a
# compatibility fallback only while the corresponding configurable 2x slot is None.
# Once a user assigns a concrete 2x action, the saved profile takes precedence.
p = Path("tools/cphun_36_double_click_v2.py")
text = p.read_text(encoding="utf-8")
old = '''    const ReaderAction configured = READER_BUTTONS.get(physical, ReaderButtonGesture::Double);\n    if (configured == ReaderAction::None) return;\n'''
new = '''    const ReaderAction configured = READER_BUTTONS.get(physical, ReaderButtonGesture::Double);\n    if (configured == ReaderAction::None) {\n      // Compatibility fallback: preserve the four device-confirmed CPHUN-36 v2\n      // double-click shortcuts until the user assigns an explicit 2x mapping.\n      if (raw == HalGPIO::BTN_BACK) { cphun36OpenSettings(); return; }\n      if (raw == HalGPIO::BTN_CONFIRM) { cphun36OpenLayout(); return; }\n      if (raw == HalGPIO::BTN_LEFT) {\n        if (SETTINGS.screenMargin > CrossPointSettings::SCREEN_MARGIN_MIN) {\n          SETTINGS.screenMargin = std::max<int>(CrossPointSettings::SCREEN_MARGIN_MIN,\n                                                SETTINGS.screenMargin - CrossPointSettings::SCREEN_MARGIN_STEP);\n          SETTINGS.saveToFile(); cphun36RebuildReader();\n        }\n        return;\n      }\n      if (raw == HalGPIO::BTN_RIGHT && SETTINGS.screenMargin < CrossPointSettings::SCREEN_MARGIN_MAX) {\n        SETTINGS.screenMargin = std::min<int>(CrossPointSettings::SCREEN_MARGIN_MAX,\n                                              SETTINGS.screenMargin + CrossPointSettings::SCREEN_MARGIN_STEP);\n        SETTINGS.saveToFile(); cphun36RebuildReader();\n      }\n      return;\n    }\n'''
if old not in text:
    raise SystemExit("CPHUN-39 configurable-double anchor missing after CPHUN-37 preparation")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")

# Static guards for the device-requested layout and safe 2x fallback.
ui = Path("src/activities/settings/ButtonFunctionsActivity.cpp").read_text(encoding="utf-8")
for needle in (
    "constexpr int kButtonX = 105;",
    "constexpr int kActionX = 235;",
    '"Alsó gombkiosztás"',
    '"Hosszan:"',
    "+ 10;",
):
    if needle not in ui:
        raise SystemExit(f"CPHUN-39 UI correction missing: {needle}")

v2 = Path("tools/cphun_36_double_click_v2.py").read_text(encoding="utf-8")
for needle in (
    "Compatibility fallback",
    "cphun36OpenSettings(); return;",
    "cphun36OpenLayout(); return;",
    "SCREEN_MARGIN_STEP",
):
    if needle not in v2:
        raise SystemExit(f"CPHUN-39 2x fallback missing: {needle}")

print("Applied CPHUN-39 bottom-button UI alignment and safe 2x compatibility fallback")
