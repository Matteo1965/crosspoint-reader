#include "CrossPointSettings.h"

#include <I18n.h>
#include <Logging.h>
#include <ObfuscationUtils.h>

#include <algorithm>
#include <cstring>
#include <iterator>
#include <string>

#include "I18nKeys.h"
#include "ReaderFontSizes.h"
#include "SettingsList.h"
#include "fontIds.h"

namespace {

// Stack buffer for "<key>_obf" key construction — avoids a std::string
// allocation per obfuscated setting on every save and load.
constexpr size_t OBF_KEY_BUF = 64;

// Null-terminated copy into a fixed-size settings field.
void copyToField(char* dest, const char* src, const size_t maxLen) {
  strncpy(dest, src, maxLen - 1);
  dest[maxLen - 1] = '\0';
}

}  // namespace

void CrossPointSettings::validateFrontButtonMapping(CrossPointSettings& settings) {
  const uint8_t mapping[] = {settings.frontButtonBack, settings.frontButtonConfirm, settings.frontButtonLeft,
                             settings.frontButtonRight};
  for (size_t i = 0; i < 4; i++) {
    for (size_t j = i + 1; j < 4; j++) {
      if (mapping[i] == mapping[j]) {
        settings.frontButtonBack = FRONT_HW_BACK;
        settings.frontButtonConfirm = FRONT_HW_CONFIRM;
        settings.frontButtonLeft = FRONT_HW_LEFT;
        settings.frontButtonRight = FRONT_HW_RIGHT;
        return;
      }
    }
  }
}

uint8_t CrossPointSettings::sleepTimeoutEnumToMinutes(const uint8_t legacyValue) {
  switch (legacyValue) {
    case SLEEP_1_MIN:
      return 1;
    case SLEEP_5_MIN:
      return 5;
    case SLEEP_15_MIN:
      return 15;
    case SLEEP_30_MIN:
      return 30;
    case SLEEP_10_MIN:
    default:
      return 10;
  }
}

void CrossPointSettings::toJson(JsonDocument& doc) const {
  const CrossPointSettings& s = *this;

  for (const auto& info : getSettingsList()) {
    if (!info.key) continue;
    // Dynamic entries (KOReader etc.) are stored in their own files — skip.
    if (!info.valuePtr && !info.stringOffset) continue;

    if (info.stringOffset) {
      const char* strPtr = (const char*)&s + info.stringOffset;
      if (info.obfuscated) {
        char obfKey[OBF_KEY_BUF];
        snprintf(obfKey, sizeof(obfKey), "%s_obf", info.key);
        doc[obfKey] = obfuscation::obfuscateToBase64(strPtr);
      } else {
        doc[info.key] = strPtr;
      }
    } else {
      doc[info.key] = s.*(info.valuePtr);
    }
  }

  // Front button remap — managed by RemapFrontButtons sub-activity, not in SettingsList.
  doc["frontButtonBack"] = frontButtonBack;
  doc["frontButtonConfirm"] = frontButtonConfirm;
  doc["frontButtonLeft"] = frontButtonLeft;
  doc["frontButtonRight"] = frontButtonRight;
  // Font family and size — both use dynamic getter/setters in SettingsList (the
  // option lists depend on the SD font registry), so the generic loop skips them.
  doc["fontFamily"] = fontFamily;
  doc["fontSize"] = fontPointSize;
  doc["hangingPunctuation"] = hangingPunctuation;
  doc["shortHyphen"] = shortHyphen;
  doc["fixedDialogueSpacing"] = fixedDialogueSpacing;
  doc["letterSpacingLimitPercent"] = letterSpacingLimitPercent;
  doc["letterSpacingOptimization"] = letterSpacingOptimization;
  doc["letterSpacingOptimizationThreshold"] = letterSpacingOptimizationThreshold;
  doc["hyphenationThreshold"] = hyphenationThreshold;
  doc["softHyphenEnabled"] = softHyphenEnabled;
  doc["minimumSpacePercent"] = minimumSpacePercent;
  doc["extraParagraphSpacingEnabled"] = extraParagraphSpacingEnabled;
  // SD card font family name — not in SettingsList, save manually
  if (sdFontFamilyName[0] != '\0') {
    doc["sdFontFamilyName"] = sdFontFamilyName;
  }
  // Dictionary folder name — uses dynamic getter/setter in SettingsList, save manually
  if (dictionaryName[0] != '\0') {
    doc["dictionaryName"] = dictionaryName;
  }
  doc["wordSelectionMode"] = wordSelectionMode;
  doc["libraryViewMode"] = libraryViewMode;

  // Language -- managed by LanguageSelectActivity, not in SettingsList.
  // Stored as ISO code string ("EN", "DE", ...) for stability across enum reorders.
  doc["language"] = (language < getLanguageCount()) ? LANGUAGE_CODES[language] : "EN";

  // A uint16_t mask, so it does not fit the uint8_t generic loop. Omitted while
  // unconfigured, so the default keeps following the UI language.
  if (keyboardLayouts != 0) {
    doc["keyboardLayouts"] = keyboardLayouts;
  }
}

bool CrossPointSettings::fromJson(JsonVariantConst doc) {
  CrossPointSettings& s = *this;
  bool needsResave = false;

  // CPHUN-181 migration: the first Cover Grid prototype stored it as UI theme
  // value 4. It is now an independent home layout. Preserve the tester's choice
  // while moving styling to RoundedRaff.
  const bool legacyCoverGridTheme = !doc["uiTheme"].isNull() && (doc["uiTheme"] | (uint8_t)0) == 4;

  auto clamp = [](uint8_t val, uint8_t maxVal, uint8_t def) -> uint8_t { return val < maxVal ? val : def; };

  for (const auto& info : getSettingsList()) {
    if (!info.key) continue;
    // Dynamic entries (KOReader etc.) are stored in their own files — skip.
    if (!info.valuePtr && !info.stringOffset) continue;

    if (info.stringOffset) {
      // destPtr starts out holding the struct-initializer default; it stays that
      // way unless the document actually carries a value for this key.
      char* destPtr = (char*)&s + info.stringOffset;
      if (info.stringMaxLen == 0) {
        LOG_ERR("CPS", "Misconfigured SettingInfo: stringMaxLen is 0 for key '%s'", info.key);
        destPtr[0] = '\0';
        needsResave = true;
        continue;
      }

      bool loaded = false;
      if (info.obfuscated) {
        char obfKey[OBF_KEY_BUF];
        snprintf(obfKey, sizeof(obfKey), "%s_obf", info.key);
        bool ok = false;
        bool tooLong = false;
        const std::string decoded =
            obfuscation::deobfuscateFromBase64(doc[obfKey] | "", info.stringMaxLen - 1, &ok, &tooLong);
        if (tooLong) {
          LOG_ERR("CPS", "Oversized obfuscated value for key '%s'", info.key);
          needsResave = true;
        }
        if (ok && !decoded.empty()) {
          copyToField(destPtr, decoded.c_str(), info.stringMaxLen);
          loaded = true;
        }
      }
      if (!loaded) {
        // Read as const char*, never `| std::string(...)`: ArduinoJson's
        // std::string converter drags a per-TU copy of the serializer into
        // flash. See the note in PersistableStore.h.
        const char* raw = doc[info.key].is<const char*>() ? doc[info.key].as<const char*>() : nullptr;
        if (raw) {
          // Obfuscated field recovered from a legacy plaintext value -> resave.
          if (info.obfuscated && strcmp(raw, destPtr) != 0) needsResave = true;
          copyToField(destPtr, raw, info.stringMaxLen);
        }
      }
    } else {
      const uint8_t fieldDefault = s.*(info.valuePtr);  // struct-initializer default, read before we overwrite it
      uint8_t v = doc[info.key] | fieldDefault;
      if (info.type == SettingType::ENUM) {
        v = clamp(v, (uint8_t)info.enumValues.size(), fieldDefault);
      } else if (info.type == SettingType::TOGGLE) {
        v = clamp(v, (uint8_t)2, fieldDefault);
      } else if (info.type == SettingType::VALUE) {
        if (v < info.valueRange.min)
          v = info.valueRange.min;
        else if (v > info.valueRange.max)
          v = info.valueRange.max;
      }
      s.*(info.valuePtr) = v;
    }
  }

  libraryViewMode = clamp(doc["libraryViewMode"] | (uint8_t)LIBRARY_LIST,
                          (uint8_t)LIBRARY_VIEW_MODE_COUNT, (uint8_t)LIBRARY_LIST);

  if (legacyCoverGridTheme && doc["homeLayout"].isNull()) {
    uiTheme = ROUNDEDRAFF;
    homeLayout = HOME_COVER_GRID;
    needsResave = true;
  }

  if (doc["extraParagraphSpacingEnabled"].isNull()) {
    extraParagraphSpacingEnabled = extraParagraphSpacing == 0 ? 0 : 1;
    needsResave = true;
  } else {
    extraParagraphSpacingEnabled = (doc["extraParagraphSpacingEnabled"] | (uint8_t)0) ? 1 : 0;
  }

  if (extraParagraphSpacing == 1) {
    // Legacy toggle: ON meant the old lineHeight/2 spacing, now defined as 100%.
    extraParagraphSpacing = 100;
    needsResave = true;
  } else if (extraParagraphSpacing != 0 && extraParagraphSpacing != 25 && extraParagraphSpacing != 50 &&
             extraParagraphSpacing != 75 && extraParagraphSpacing != 100) {
    extraParagraphSpacing = 100;
    needsResave = true;
  }

  if (doc["sleepTimeoutMinutes"].isNull() && !doc["sleepTimeout"].isNull()) {
    const uint8_t legacyValue =
        clamp(doc["sleepTimeout"] | (uint8_t)SLEEP_10_MIN, SLEEP_TIMEOUT_COUNT, (uint8_t)SLEEP_10_MIN);
    sleepTimeoutMinutes = sleepTimeoutEnumToMinutes(legacyValue);
    needsResave = true;
  }
  // Front button remap — managed by RemapFrontButtons sub-activity, not in SettingsList.
  frontButtonBack = clamp(doc["frontButtonBack"] | (uint8_t)FRONT_HW_BACK, FRONT_BUTTON_HARDWARE_COUNT, FRONT_HW_BACK);
  frontButtonConfirm =
      clamp(doc["frontButtonConfirm"] | (uint8_t)FRONT_HW_CONFIRM, FRONT_BUTTON_HARDWARE_COUNT, FRONT_HW_CONFIRM);
  frontButtonLeft = clamp(doc["frontButtonLeft"] | (uint8_t)FRONT_HW_LEFT, FRONT_BUTTON_HARDWARE_COUNT, FRONT_HW_LEFT);
  frontButtonRight =
      clamp(doc["frontButtonRight"] | (uint8_t)FRONT_HW_RIGHT, FRONT_BUTTON_HARDWARE_COUNT, FRONT_HW_RIGHT);
  validateFrontButtonMapping(s);

  // Reader font size — an actual point size since 1.5. Files written by 1.4 and
  // earlier hold the old SMALL/MEDIUM/LARGE/EXTRA_LARGE slot in 0..3; no font is
  // renderable at those sizes, so the range is unambiguous and folds to the
  // point sizes those slots used to mean. Drop this once 1.4 upgrades are done.
  uint8_t storedFontSize = doc["fontSize"] | DEFAULT_FONT_POINT_SIZE;
  if (storedFontSize <= LEGACY_FONT_SIZE_MAX) {
    storedFontSize = 12 + storedFontSize * 2;  // 0,1,2,3 -> 12,14,16,18
    needsResave = true;
  }
  fontPointSize = storedFontSize;
  shortHyphen = (doc["shortHyphen"] | (uint8_t)0) ? 1 : 0;
  fixedDialogueSpacing = (doc["fixedDialogueSpacing"] | (uint8_t)0) ? 1 : 0;
  hyphenationThreshold = doc["hyphenationThreshold"] | (uint8_t)2;
  if (hyphenationThreshold > 4) {
    hyphenationThreshold = 2;
    needsResave = true;
  }
  softHyphenEnabled = (doc["softHyphenEnabled"] | (uint8_t)0) ? 1 : 0;
  letterSpacingLimitPercent = doc["letterSpacingLimitPercent"] | (uint16_t)0;
  // CPHUN-191: preserve the canonical CPHUN-184 UI values across
  // restart/deep-sleep wake: 0=Off, 10=Weak, 40=Medium, 70=Strong.
  if (letterSpacingLimitPercent == 550) {
    letterSpacingLimitPercent = 10;
    needsResave = true;
  } else if (letterSpacingLimitPercent == 460) {
    letterSpacingLimitPercent = 40;
    needsResave = true;
  } else if (letterSpacingLimitPercent == 280) {
    letterSpacingLimitPercent = 70;
    needsResave = true;
  } else if (letterSpacingLimitPercent != 0 &&
             letterSpacingLimitPercent != 10 &&
             letterSpacingLimitPercent != 40 &&
             letterSpacingLimitPercent != 70) {
    // One-time migration for other historical physical threshold values.
    constexpr uint16_t legacyPhysical[] = {550, 460, 280};
    constexpr uint16_t canonical[] = {10, 40, 70};
    int bestIndex = 0;
    uint16_t bestDiff = letterSpacingLimitPercent > legacyPhysical[0]
                            ? letterSpacingLimitPercent - legacyPhysical[0]
                            : legacyPhysical[0] - letterSpacingLimitPercent;
    for (int i = 1; i < 3; ++i) {
      const uint16_t d = letterSpacingLimitPercent > legacyPhysical[i]
                             ? letterSpacingLimitPercent - legacyPhysical[i]
                             : legacyPhysical[i] - letterSpacingLimitPercent;
      if (d < bestDiff) {
        bestDiff = d;
        bestIndex = i;
      }
    }
    letterSpacingLimitPercent = canonical[bestIndex];
    needsResave = true;
  }

  // Persist optimizer ON/OFF independently from the correction level.
  letterSpacingOptimization =
      (doc["letterSpacingOptimization"] | (uint8_t)0) ? 4 : 0;

  // CPHUN-183/184 semantics: Off / Weak / Medium / Strong = 0/50/60/70.
  letterSpacingOptimizationThreshold =
      doc["letterSpacingOptimizationThreshold"] | (uint8_t)60;
  if (letterSpacingOptimizationThreshold != 0 &&
      letterSpacingOptimizationThreshold != 50 &&
      letterSpacingOptimizationThreshold != 60 &&
      letterSpacingOptimizationThreshold != 70) {
    letterSpacingOptimizationThreshold = 60;
    needsResave = true;
  }

  minimumSpacePercent = doc["minimumSpacePercent"] | (uint8_t)100;
  if (minimumSpacePercent < 50 || minimumSpacePercent > 100 || minimumSpacePercent % 10 != 0) {
    minimumSpacePercent = 100;
    needsResave = true;
  }
  const uint8_t storedHangingPunctuation = doc["hangingPunctuation"] | (uint8_t)1;
  hangingPunctuation = storedHangingPunctuation ? 1 : 0;
  if (storedHangingPunctuation > 1) needsResave = true;

  // Font family — uses dynamic getter/setter in SettingsList so the generic loop skips it.
  const uint8_t storedFontFamily = doc["fontFamily"] | (uint8_t)0;
  fontFamily = clamp(storedFontFamily, BUILTIN_FONT_COUNT, 0);
  // SD card font family name — not in SettingsList, load manually
  const char* sfn = doc["sdFontFamilyName"] | "";
  strncpy(sdFontFamilyName, sfn, sizeof(sdFontFamilyName) - 1);
  sdFontFamilyName[sizeof(sdFontFamilyName) - 1] = '\0';
  if (storedFontFamily == LEGACY_OPENDYSLEXIC && sdFontFamilyName[0] == '\0') {
    fontFamily = NOTOSERIF;
    strncpy(sdFontFamilyName, "OpenDyslexic", sizeof(sdFontFamilyName) - 1);
    sdFontFamilyName[sizeof(sdFontFamilyName) - 1] = '\0';
    needsResave = true;
  } else if (storedFontFamily >= BUILTIN_FONT_COUNT) {
    needsResave = true;
  }
  // Dictionary folder name — uses dynamic getter/setter in SettingsList, load manually
  copyToField(dictionaryName, doc["dictionaryName"] | "", sizeof(dictionaryName));
  const uint8_t storedWordSelectionMode = doc["wordSelectionMode"] | (uint8_t)0;
  if (storedWordSelectionMode <= 2) {
    wordSelectionMode = storedWordSelectionMode;
  } else {
    wordSelectionMode = 0;
    needsResave = true;
  }

  // Language -- stored as code string for stability across enum reorders.
  // Hungarian Edition deliberately exposes only the 12 tested reading/UI
  // languages. Any older saved choice outside this set falls back to Magyar.
  if (doc["language"].is<const char*>()) {
    const Language loadedLanguage = I18n::languageFromCode(doc["language"].as<const char*>());
    switch (loadedLanguage) {
      case Language::HU:
      case Language::EN:
      case Language::DE:
      case Language::ES:
      case Language::IT:
      case Language::FR:
      case Language::P2:
      case Language::PL:
      case Language::FI:
      case Language::RU:
      case Language::SV:
      case Language::UK:
        language = static_cast<uint8_t>(loadedLanguage);
        break;
      default:
        language = static_cast<uint8_t>(Language::HU);
        needsResave = true;
        break;
    }
  }

  // Absent means unconfigured, which is the default.
  if (doc["keyboardLayouts"].is<uint16_t>()) {
    keyboardLayouts = doc["keyboardLayouts"].as<uint16_t>();
  }

  if (needsResave) {
    LOG_DBG("CPS", "Resaving settings to update format");
    requestResave();
  }

  LOG_DBG("CPS", "Settings loaded from file");

  return true;
}

CrossPointSettings::StatusBarSpec CrossPointSettings::statusBarSpec() const {
  StatusBarSpec spec;
  spec.showChapterPageCount = statusBarChapterPageCount != 0;
  spec.showBookProgressPercent = statusBarBookProgressPercentage != 0;
  spec.titleMode = statusBarTitle;
  spec.showBattery = statusBarBattery != 0;
  spec.showBatteryPercent = hideBatteryPercentage == HIDE_NEVER;
  spec.clockMode = statusBarClock;
  spec.clock12h = clockFormat == 1;
  spec.clockUtcOffsetQ = clockUtcOffsetQ;
  spec.progressBarMode = statusBarProgressBar;
  spec.progressBarHeightPx =
      statusBarProgressBar != HIDE_PROGRESS ? static_cast<uint8_t>((statusBarProgressBarThickness + 1) * 2) : 0;
  spec.xtcMode = xtcStatusBarMode;
  return spec;
}

ReaderRenderSpec CrossPointSettings::readerRenderSpec(const uint16_t viewportWidth,
                                                      const uint16_t viewportHeight) const {
  ReaderRenderSpec spec;
  spec.fontId = getReaderFontId();
  spec.lineCompression = getReaderLineCompression();
  spec.extraParagraphSpacing = extraParagraphSpacingEnabled ? extraParagraphSpacing : static_cast<uint8_t>(255);
  spec.paragraphAlignment = paragraphAlignment;
  spec.viewportWidth = viewportWidth;
  spec.viewportHeight = viewportHeight;
  spec.hyphenationEnabled = hyphenationEnabled != 0;
  spec.hungarianHyphenationExtended = hungarianHyphenationExtended != 0;
  static constexpr uint8_t kHyphenMinPrefix[] = {1, 1, 2, 2, 3};
  static constexpr uint8_t kHyphenMinSuffix[] = {1, 2, 2, 3, 3};
  const uint8_t threshold = hyphenationThreshold <= 4 ? hyphenationThreshold : 2;
  spec.hungarianMinPrefix = kHyphenMinPrefix[threshold];
  spec.hungarianMinSuffix = kHyphenMinSuffix[threshold];
  // Optical margin is OFF/ON. ON permits the eligible end punctuation to hang
  // into the physical right margin, capped just inside the selected screen margin.
  spec.hangingPunctuationLimitPx =
      hangingPunctuation ? static_cast<uint8_t>(screenMargin > 1 ? screenMargin - 1 : 0) : 0;
  spec.shortHyphen = shortHyphen != 0;
  spec.fixedDialogueSpacing = fixedDialogueSpacing != 0;
  const bool isBitterExperimentalSize =
      (fontPointSize == 12 || fontPointSize == 14 || fontPointSize == 16 ||
       fontPointSize == 18) &&
      strcmp(sdFontFamilyName, "Bitter") == 0;
  const bool isBuiltinSerif =
      sdFontFamilyName[0] == '\0' && fontFamily == NOTOSERIF;
  const bool isNotoSerif16 = isBuiltinSerif && fontPointSize == 16;
  const bool knownSdSerif =
      sdFontFamilyName[0] != '\0' &&
      (strstr(sdFontFamilyName, "Serif") || strstr(sdFontFamilyName, "Bitter") ||
       strstr(sdFontFamilyName, "Bookerly") || strstr(sdFontFamilyName, "Georgia") ||
       strstr(sdFontFamilyName, "Garamond") || strstr(sdFontFamilyName, "Palatino") ||
       strstr(sdFontFamilyName, "Literata") || strstr(sdFontFamilyName, "Merriweather") ||
       strstr(sdFontFamilyName, "Cambria") || strstr(sdFontFamilyName, "Times")) &&
      !strstr(sdFontFamilyName, "Sans");
  const bool supportedSerifSize =
      fontPointSize == 12 || fontPointSize == 14 ||
      fontPointSize == 16 || fontPointSize == 18;
  const bool useSerifProfile =
      supportedSerifSize && (isBuiltinSerif || knownSdSerif || isBitterExperimentalSize);
  const uint8_t optimizationThresholdCode =
      letterSpacingLimitPercent > 0 && letterSpacingOptimization && useSerifProfile &&
              letterSpacingOptimizationThreshold >= 50
          ? static_cast<uint8_t>((letterSpacingOptimizationThreshold - 45u) / 5u)
          : 0;
  // Bits 13..15 carry 0=off or threshold code 1..6 (50..75) to ParsedText.
  // Noto Serif 16 keeps its dedicated fixed pair table; the score cutoff applies to Bitter.
  spec.letterSpacingLimitPercent = static_cast<uint16_t>(
      (letterSpacingLimitPercent & 0x1FFFu) |
      (static_cast<uint16_t>(optimizationThresholdCode) << 13));
  spec.minimumSpacePercent = minimumSpacePercent;
  spec.embeddedStyle = embeddedStyle != 0;
  // Updated and Standard differ only in the panel refresh pipeline. Both use
  // the normal embedded-image layout/cache representation.
  spec.imageRendering = imageRendering == IMAGES_STANDARD ? IMAGES_DISPLAY : imageRendering;
  spec.focusReadingEnabled = focusReadingEnabled != 0;
  return spec;
}

float CrossPointSettings::getReaderLineCompression() const {
  // SD card fonts use same compression as Bookerly (the most neutral values)
  if (sdFontFamilyName[0] != '\0') {
    switch (lineSpacing) {
      case TIGHT:
        return 0.95f;
      case NORMAL:
      default:
        return 1.0f;
      case NORMAL_PLUS:
        return 1.05f;
      case WIDE:
        return 1.1f;
      case WIDE_PLUS:
        return 1.15f;
      case EXTRA_WIDE:
        return 1.2f;
    }
  }

  switch (fontFamily) {
    case NOTOSERIF:
    default:
      switch (lineSpacing) {
        case TIGHT:
          return 0.95f;
        case NORMAL:
        default:
          return 1.0f;
        case NORMAL_PLUS:
          return 1.05f;
        case WIDE:
          return 1.1f;
        case WIDE_PLUS:
          return 1.15f;
        case EXTRA_WIDE:
          return 1.2f;
      }
    case NOTOSANS:
      switch (lineSpacing) {
        case TIGHT:
          return 0.90f;
        case NORMAL:
        default:
          return 0.95f;
        case NORMAL_PLUS:
          return 0.975f;
        case WIDE:
          return 1.0f;
        case WIDE_PLUS:
          return 1.025f;
        case EXTRA_WIDE:
          return 1.05f;
      }
  }
}

unsigned long CrossPointSettings::getSleepTimeoutMs() const {
  if (sleepTimeoutMinutes >= SLEEP_TIMEOUT_NEVER_MINUTES) return 0UL;
  const uint8_t minutes =
      std::clamp(sleepTimeoutMinutes, MIN_SLEEP_TIMEOUT_MINUTES, static_cast<uint8_t>(SLEEP_TIMEOUT_NEVER_MINUTES - 1));
  return static_cast<unsigned long>(minutes) * 60UL * 1000UL;
}

int CrossPointSettings::getRefreshFrequency() const {
  switch (refreshFrequency) {
    case REFRESH_1:
      return 1;
    case REFRESH_5:
      return 5;
    case REFRESH_10:
      return 10;
    case REFRESH_15:
    default:
      return 15;
    case REFRESH_30:
      return 30;
  }
}

void CrossPointSettings::clearSdFontFamily() {
  sdFontFamilyName[0] = '\0';
  fontPointSize =
      snapToNearestPointSize(BUILTIN_READER_POINT_SIZES, std::size(BUILTIN_READER_POINT_SIZES), fontPointSize);
  saveToFile();
}

int CrossPointSettings::getReaderFontId() const {
  // Check SD card font first
  if (sdFontFamilyName[0] != '\0' && sdFontIdResolver) {
    int id = sdFontIdResolver(sdFontResolverCtx, sdFontFamilyName, fontPointSize);
    if (id != 0) return id;
    // Fall through to built-in if SD font not found
  }

  // A built-in family only exists at BUILTIN_READER_POINT_SIZES, so a size
  // carried over from an SD family may not be one of them. ensureLoaded()
  // normally persists the snap; snap again here (without allocating — this runs
  // in the page render loop) so rendering is correct even before it has run.
  const uint8_t pt =
      snapToNearestPointSize(BUILTIN_READER_POINT_SIZES, std::size(BUILTIN_READER_POINT_SIZES), fontPointSize);
  const bool sans = (fontFamily == NOTOSANS);
  switch (pt) {
    case 12:
      return sans ? NOTOSANS_12_FONT_ID : NOTOSERIF_12_FONT_ID;
    case 16:
      return sans ? NOTOSANS_16_FONT_ID : NOTOSERIF_16_FONT_ID;
    case 18:
      return sans ? NOTOSANS_18_FONT_ID : NOTOSERIF_18_FONT_ID;
    case 14:
    default:
      return sans ? NOTOSANS_14_FONT_ID : NOTOSERIF_14_FONT_ID;
  }
}
