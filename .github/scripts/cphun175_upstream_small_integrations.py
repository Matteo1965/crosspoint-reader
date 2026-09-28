#!/usr/bin/env python3
from pathlib import Path

def replace_once(path, old, new):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    if old not in s:
        raise SystemExit(f"CPHUN-175 anchor missing in {path}: {old[:100]!r}")
    if s.count(old) != 1:
        raise SystemExit(f"CPHUN-175 anchor not unique in {path}: {old[:100]!r}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

# Move Sleep timeout from System to Display, immediately after Cover filter.
replace_once(
    "src/SettingsListBase.h",
    """        SettingInfo::Enum(StrId::STR_SLEEP_COVER_FILTER, &CrossPointSettings::sleepScreenCoverFilter,
                          {StrId::STR_NONE_OPT, StrId::STR_FILTER_CONTRAST, StrId::STR_INVERTED},
                          "sleepScreenCoverFilter", StrId::STR_CAT_DISPLAY),
        SettingInfo::Enum(StrId::STR_QUICK_RESUME_TIMEOUT, &CrossPointSettings::quickResumeSleepScreen,
""",
    """        SettingInfo::Enum(StrId::STR_SLEEP_COVER_FILTER, &CrossPointSettings::sleepScreenCoverFilter,
                          {StrId::STR_NONE_OPT, StrId::STR_FILTER_CONTRAST, StrId::STR_INVERTED},
                          "sleepScreenCoverFilter", StrId::STR_CAT_DISPLAY),
        SettingInfo::Value(
            StrId::STR_TIME_TO_SLEEP, &CrossPointSettings::sleepTimeoutMinutes,
            {CrossPointSettings::MIN_SLEEP_TIMEOUT_MINUTES, CrossPointSettings::MAX_SLEEP_TIMEOUT_MINUTES, 1},
            "sleepTimeoutMinutes", StrId::STR_CAT_DISPLAY),
        SettingInfo::Enum(StrId::STR_QUICK_RESUME_TIMEOUT, &CrossPointSettings::quickResumeSleepScreen,
"""
)
replace_once(
    "src/SettingsListBase.h",
    """        // --- System ---
        SettingInfo::Value(
            StrId::STR_TIME_TO_SLEEP, &CrossPointSettings::sleepTimeoutMinutes,
            {CrossPointSettings::MIN_SLEEP_TIMEOUT_MINUTES, CrossPointSettings::MAX_SLEEP_TIMEOUT_MINUTES, 1},
            "sleepTimeoutMinutes", StrId::STR_CAT_SYSTEM),
        SettingInfo::Toggle(StrId::STR_SHOW_HIDDEN_FILES, &CrossPointSettings::showHiddenFiles, "showHiddenFiles",
""",
    """        // --- System ---
        SettingInfo::Toggle(StrId::STR_SHOW_HIDDEN_FILES, &CrossPointSettings::showHiddenFiles, "showHiddenFiles",
"""
)

# Upstream #3569 intent: construct optional controls in the initial vector and
# erase unavailable entries, avoiding insert-triggered reallocation.
replace_once(
    "src/SettingsListBase.h",
    """        SettingInfo::Enum(StrId::STR_LONG_PRESS_MENU, &CrossPointSettings::longPressMenuFunction,
                          buildLongPressMenuValues(), "longPressMenuFunction", StrId::STR_CAT_CONTROLS),
#if FREEINK_CAP_TOUCH
""",
    """        SettingInfo::Enum(StrId::STR_LONG_PRESS_MENU, &CrossPointSettings::longPressMenuFunction,
                          buildLongPressMenuValues(), "longPressMenuFunction", StrId::STR_CAT_CONTROLS),
        // Upstream #3569: include optional entry in the initial allocation and
        // erase it below when unavailable, instead of inserting later.
        SettingInfo::Enum(StrId::STR_TILT_PAGE_TURN, &CrossPointSettings::tiltPageTurn,
                          {StrId::STR_STATE_OFF, StrId::STR_NORMAL, StrId::STR_INVERTED}, "tiltPageTurn",
                          StrId::STR_CAT_CONTROLS),
#if FREEINK_CAP_TOUCH
"""
)
replace_once(
    "src/SettingsListBase.h",
    """    // Only show tilt page turn setting when the QMI8658 IMU is present (X3)
    if (halTiltSensor.isAvailable()) {
      // Insert after the short power button setting (end of Controls section)
      for (auto it = v.begin(); it != v.end(); ++it) {
        if (it->nameId == StrId::STR_SHORT_PWR_BTN) {
          v.insert(it + 1, SettingInfo::Enum(StrId::STR_TILT_PAGE_TURN, &CrossPointSettings::tiltPageTurn,
                                             {StrId::STR_STATE_OFF, StrId::STR_NORMAL, StrId::STR_INVERTED},
                                             "tiltPageTurn", StrId::STR_CAT_CONTROLS));
          break;
        }
      }
    }
    return v;
""",
    """    // Upstream #3569: erasing keeps the vector at its initial allocation.
    if (!halTiltSensor.isAvailable()) {
      v.erase(std::find_if(v.begin(), v.end(),
                           [](const SettingInfo& s) { return s.nameId == StrId::STR_TILT_PAGE_TURN; }));
    }
    return v;
"""
)

print("CPHUN-175 upstream #3569 + Sleep timeout relocation applied")
