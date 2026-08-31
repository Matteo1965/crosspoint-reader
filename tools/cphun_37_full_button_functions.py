from pathlib import Path


def replace_once(path, old, new):
    p=Path(path); t=p.read_text(encoding='utf-8')
    if new in t: return
    if old not in t: raise SystemExit(f'anchor missing: {path}')
    p.write_text(t.replace(old,new,1),encoding='utf-8')

# Settings: expose compact bottom-button activity; hide legacy bottom-button hold controls on X4.
p=Path('src/activities/settings/SettingsActivity.cpp'); t=p.read_text(encoding='utf-8')
t=t.replace('#include "ButtonRemapActivity.h"\n', '#include "ButtonFunctionsActivity.h"\n#include "ButtonRemapActivity.h"\n',1)
t=t.replace('''    } else if (setting.category == StrId::STR_CAT_CONTROLS) {\n      if (setting.valuePtr == &CrossPointSettings::pwrBtnFootnoteBack &&''','''    } else if (setting.category == StrId::STR_CAT_CONTROLS) {\n      if (!BoardConfig::hasTouch() &&\n          (setting.valuePtr == &CrossPointSettings::longPressButtonBehavior ||\n           setting.valuePtr == &CrossPointSettings::longPressMenuFunction ||\n           setting.valuePtr == &CrossPointSettings::backShortToFileBrowser)) {\n        continue;\n      }\n      if (setting.valuePtr == &CrossPointSettings::pwrBtnFootnoteBack &&''',1)
t=t.replace('''    controlsSettings.insert(controlsSettings.begin(),\n                            SettingInfo::Action(StrId::STR_REMAP_FRONT_BUTTONS, SettingAction::RemapFrontButtons));''','''    controlsSettings.insert(controlsSettings.begin(),\n                            SettingInfo::Action(StrId::STR_REMAP_FRONT_BUTTONS, SettingAction::RemapFrontButtons));\n    controlsSettings.insert(controlsSettings.begin(),\n                            SettingInfo::Action(StrId::STR_REMAP_FRONT_BUTTONS, SettingAction::ButtonFunctions));''',1)
t=t.replace('''      case SettingAction::RemapFrontButtons:\n        startActivityForResult(std::make_unique<ButtonRemapActivity>(renderer, mappedInput), resultHandler);\n        break;''','''      case SettingAction::RemapFrontButtons:\n        startActivityForResult(std::make_unique<ButtonRemapActivity>(renderer, mappedInput), resultHandler);\n        break;\n      case SettingAction::ButtonFunctions:\n        startActivityForResult(std::make_unique<ButtonFunctionsActivity>(renderer, mappedInput), resultHandler);\n        break;''',1)
p.write_text(t,encoding='utf-8')

# Hungarian labels: menu row and shorter remap prompt.
p=Path('lib/I18n/translations/hungarian.yaml'); t=p.read_text(encoding='utf-8')
t=t.replace('STR_REMAP_PROMPT: "Nyomj meg egy alsó gombot a cseréhez"','STR_REMAP_PROMPT: "Nyomd meg a cserélendő gombot."')
# The first occurrence is used by the new action too; keep legacy remap wording distinct via activity title later.
t=t.replace('STR_REMAP_FRONT_BUTTONS: "Alsó gombok átállítása"','STR_REMAP_FRONT_BUTTONS: "Alsó gombok"')
p.write_text(t,encoding='utf-8')

# Extra paragraph spacing: preserve legacy 0=Off while adding enabled+0% state.
p=Path('src/CrossPointSettings.h'); t=p.read_text(encoding='utf-8')
t=t.replace('''  // Extra paragraph spacing percentage: 0, 25, 50, 75 or 100.\n  uint8_t extraParagraphSpacing = 100;''','''  // Extra paragraph spacing percentage: 0, 25, 50, 75 or 100.\n  // Enabled is separate so Off and enabled 0% remain distinct across reboot.\n  uint8_t extraParagraphSpacing = 100;\n  uint8_t extraParagraphSpacingEnabled = 1;''',1)
p.write_text(t,encoding='utf-8')
p=Path('src/CrossPointSettings.cpp'); t=p.read_text(encoding='utf-8')
t=t.replace('''  doc["minimumSpacePercent"] = minimumSpacePercent;''','''  doc["minimumSpacePercent"] = minimumSpacePercent;\n  doc["extraParagraphSpacingEnabled"] = extraParagraphSpacingEnabled;''',1)
t=t.replace('''  if (extraParagraphSpacing == 1) {''','''  if (doc["extraParagraphSpacingEnabled"].isNull()) {\n    extraParagraphSpacingEnabled = extraParagraphSpacing == 0 ? 0 : 1;\n    needsResave = true;\n  } else {\n    extraParagraphSpacingEnabled = (doc["extraParagraphSpacingEnabled"] | (uint8_t)0) ? 1 : 0;\n  }\n\n  if (extraParagraphSpacing == 1) {''',1)
p.write_text(t,encoding='utf-8')

p=Path('src/activities/settings/TextSettingsActivity.cpp'); t=p.read_text(encoding='utf-8')
t=t.replace('''      std::vector<std::string> options = {tr(STR_STATE_OFF), "25%", "50%", "75%", "100%"};\n      const int cur =\n          SETTINGS.extraParagraphSpacing == 0 ? 0 : std::clamp<int>(SETTINGS.extraParagraphSpacing / 25, 1, 4);\n      optionPopup_.show(StrId::STR_EXTRA_SPACING, options, cur, [](int idx) {\n        SETTINGS.extraParagraphSpacing = static_cast<uint8_t>(idx * 25);''','''      std::vector<std::string> options = {tr(STR_STATE_OFF), "0%", "25%", "50%", "75%", "100%"};\n      const int cur = !SETTINGS.extraParagraphSpacingEnabled\n                          ? 0\n                          : (SETTINGS.extraParagraphSpacing == 0\n                                 ? 1\n                                 : std::clamp<int>(SETTINGS.extraParagraphSpacing / 25 + 1, 2, 5));\n      optionPopup_.show(StrId::STR_EXTRA_SPACING, options, cur, [](int idx) {\n        SETTINGS.extraParagraphSpacingEnabled = idx == 0 ? 0 : 1;\n        SETTINGS.extraParagraphSpacing = idx <= 1 ? 0 : static_cast<uint8_t>((idx - 1) * 25);''',1)
t=t.replace('''      return SETTINGS.extraParagraphSpacing ? std::to_string(SETTINGS.extraParagraphSpacing) + "%" : tr(STR_STATE_OFF);''','''      return SETTINGS.extraParagraphSpacingEnabled ? std::to_string(SETTINGS.extraParagraphSpacing) + "%"\n                                                   : tr(STR_STATE_OFF);''',1)
p.write_text(t,encoding='utf-8')

# Reader action dispatcher replaces temporary hard-coded double actions while preserving v2 masking.
p=Path('tools/cphun_36_double_click_v2.py'); t=p.read_text(encoding='utf-8')
t=t.replace('#include "activities/settings/SettingsActivity.h"\\n#include "activities/settings/TextSettingsActivity.h"\\n', '#include "ReaderButtonProfileStore.h"\\n#include "activities/settings/SettingsActivity.h"\\n#include "activities/settings/TextSettingsActivity.h"\\n')
# This build keeps the device-confirmed detector but routes double clicks through the saved profile.
t=t.replace('''  const auto cphun36DoubleAction = [this, &cphun36OpenSettings, &cphun36OpenLayout, &cphun36RebuildReader](\n                                      const int raw) {''','''  const auto cphun36DoubleAction = [this, &cphun36OpenSettings, &cphun36OpenLayout, &cphun36RebuildReader](\n                                      const int raw) {\n    ReaderPhysicalButton physical = ReaderPhysicalButton::Back;\n    if (raw == HalGPIO::BTN_CONFIRM) physical = ReaderPhysicalButton::Confirm;\n    else if (raw == HalGPIO::BTN_LEFT) physical = ReaderPhysicalButton::Left;\n    else if (raw == HalGPIO::BTN_RIGHT) physical = ReaderPhysicalButton::Right;\n    const ReaderAction configured = READER_BUTTONS.get(physical, ReaderButtonGesture::Double);\n    if (configured == ReaderAction::None) return;\n    if (configured == ReaderAction::OpenTextSettings) { cphun36OpenLayout(); return; }\n    if (configured == ReaderAction::OpenLayoutMenu) { cphun36OpenLayout(); return; }\n    if (configured == ReaderAction::ScreenMarginDown) {\n      if (SETTINGS.screenMargin > CrossPointSettings::SCREEN_MARGIN_MIN) {\n        SETTINGS.screenMargin = std::max<int>(CrossPointSettings::SCREEN_MARGIN_MIN, SETTINGS.screenMargin - CrossPointSettings::SCREEN_MARGIN_STEP);\n        SETTINGS.saveToFile(); cphun36RebuildReader();\n      }\n      return;\n    }\n    if (configured == ReaderAction::ScreenMarginUp) {\n      if (SETTINGS.screenMargin < CrossPointSettings::SCREEN_MARGIN_MAX) {\n        SETTINGS.screenMargin = std::min<int>(CrossPointSettings::SCREEN_MARGIN_MAX, SETTINGS.screenMargin + CrossPointSettings::SCREEN_MARGIN_STEP);\n        SETTINGS.saveToFile(); cphun36RebuildReader();\n      }\n      return;\n    }\n    if (configured == ReaderAction::GoHome) { onGoHome(); return; }\n    if (configured == ReaderAction::OpenReaderMenu) { openReaderMenu(); return; }\n    if (configured == ReaderAction::ToggleNightMode) { SETTINGS.screenInverted = !SETTINGS.screenInverted; SETTINGS.saveToFile(); requestUpdate(); return; }\n    if (configured == ReaderAction::ToggleHyphenation) { SETTINGS.hyphenationEnabled = !SETTINGS.hyphenationEnabled; SETTINGS.saveToFile(); cphun36RebuildReader(); return; }\n    if (configured == ReaderAction::ToggleSoftHyphen) { SETTINGS.softHyphenEnabled = !SETTINGS.softHyphenEnabled; SETTINGS.saveToFile(); cphun36RebuildReader(); return; }\n    // Temporary fallback for actions not yet specialized in this integration: preserve known v2 test behavior.\n''',1)
p.write_text(t,encoding='utf-8')
print('Applied CPHUN-37 full button functions/menu + paragraph spacing integration')
