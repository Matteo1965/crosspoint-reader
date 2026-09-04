from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Expected patch anchor not found in {path}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Raw physical release edge. The baseline already exposes raw press.
replace_once(
    "src/MappedInputManager.h",
    "  // Returns the raw front button index that was pressed this frame (or -1 if none).\n"
    "  int getPressedFrontButton() const;\n",
    "  // Returns the raw front button index that was pressed this frame (or -1 if none).\n"
    "  int getPressedFrontButton() const;\n"
    "  // Returns the raw front button index that was released this frame (or -1 if none).\n"
    "  int getReleasedFrontButton() const;\n",
)
replace_once(
    "src/MappedInputManager.cpp",
    "int MappedInputManager::getPressedFrontButton() const {\n"
    "  // Scan the raw front buttons in hardware order.\n"
    "  // This bypasses remapping so the remap activity can capture physical presses.\n"
    "  if (gpio.wasPressed(HalGPIO::BTN_BACK)) {\n"
    "    return HalGPIO::BTN_BACK;\n"
    "  }\n"
    "  if (gpio.wasPressed(HalGPIO::BTN_CONFIRM)) {\n"
    "    return HalGPIO::BTN_CONFIRM;\n"
    "  }\n"
    "  if (gpio.wasPressed(HalGPIO::BTN_LEFT)) {\n"
    "    return HalGPIO::BTN_LEFT;\n"
    "  }\n"
    "  if (gpio.wasPressed(HalGPIO::BTN_RIGHT)) {\n"
    "    return HalGPIO::BTN_RIGHT;\n"
    "  }\n"
    "  return -1;\n"
    "}\n",
    "int MappedInputManager::getPressedFrontButton() const {\n"
    "  // Scan the raw front buttons in hardware order.\n"
    "  // This bypasses remapping so the remap activity can capture physical presses.\n"
    "  if (gpio.wasPressed(HalGPIO::BTN_BACK)) {\n"
    "    return HalGPIO::BTN_BACK;\n"
    "  }\n"
    "  if (gpio.wasPressed(HalGPIO::BTN_CONFIRM)) {\n"
    "    return HalGPIO::BTN_CONFIRM;\n"
    "  }\n"
    "  if (gpio.wasPressed(HalGPIO::BTN_LEFT)) {\n"
    "    return HalGPIO::BTN_LEFT;\n"
    "  }\n"
    "  if (gpio.wasPressed(HalGPIO::BTN_RIGHT)) {\n"
    "    return HalGPIO::BTN_RIGHT;\n"
    "  }\n"
    "  return -1;\n"
    "}\n\n"
    "int MappedInputManager::getReleasedFrontButton() const {\n"
    "  if (gpio.wasReleased(HalGPIO::BTN_BACK)) return HalGPIO::BTN_BACK;\n"
    "  if (gpio.wasReleased(HalGPIO::BTN_CONFIRM)) return HalGPIO::BTN_CONFIRM;\n"
    "  if (gpio.wasReleased(HalGPIO::BTN_LEFT)) return HalGPIO::BTN_LEFT;\n"
    "  if (gpio.wasReleased(HalGPIO::BTN_RIGHT)) return HalGPIO::BTN_RIGHT;\n"
    "  return -1;\n"
    "}\n",
)

# v2 deliberately does NOT return from the reader loop on a front-button press.
# It consumes only the legacy front short-action conditions locally.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '#include "activities/settings/TextSettingsActivity.h"\n',
    '#include "ReaderButtonProfileStore.h"\n#include "activities/settings/SettingsActivity.h"\n#include "activities/settings/TextSettingsActivity.h"\n',
)

anchor = "  const auto touch = ReaderUtils::detectTouchPageTurn(renderer, mappedInput);\n\n"
block = r'''  const auto touch = ReaderUtils::detectTouchPageTurn(renderer, mappedInput);

  // CPHUN-36 2x front-button test v2.
  // IMPORTANT: never return merely because a front button was pressed. Side
  // buttons, Power and all legacy hold processing must continue through this
  // reader loop. Only the four front buttons' SHORT actions are deferred.
  struct Cphun36DoubleState {
    int raw = -1;
    unsigned long firstReleaseMs = 0;
    bool waitingSecond = false;
  };
  static Cphun36DoubleState cphun36;
  constexpr unsigned long CPHUN36_DOUBLE_MS = 400;

  const int cphun36PressedRaw = mappedInput.getPressedFrontButton();
  const int cphun36ReleasedRaw = mappedInput.getReleasedFrontButton();
  const unsigned long cphun36HeldMs = mappedInput.getHeldTime();

  const auto cphun36RebuildReader = [this]() {
    RenderLock lock;
    if (section) {
      rememberCurrentContentOffset();
      cachedSpineIndex = currentSpineIndex;
      cachedChapterTotalPageCount = section->pageCount;
      nextPageNumber = section->currentPage;
    }
    section.reset();
    requestUpdate();
  };

  const auto cphun36OpenSettings = [this]() {
    startActivityForResult(std::make_unique<SettingsActivity>(renderer, mappedInput),
                           [this](const ActivityResult&) {
                             RenderLock lock;
                             if (section) {
                               rememberCurrentContentOffset();
                               cachedSpineIndex = currentSpineIndex;
                               cachedChapterTotalPageCount = section->pageCount;
                               nextPageNumber = section->currentPage;
                             }
                             section.reset();
                             requestUpdate();
                           });
  };

  const auto cphun36OpenLayout = [this]() {
    startActivityForResult(
        std::make_unique<TextSettingsActivity>(renderer, mappedInput, &sdFontSystem.registry(),
                                               TextSettingsActivity::Tab::Layout),
        [this](const ActivityResult&) {
          RenderLock lock;
          if (section) {
            rememberCurrentContentOffset();
            cachedSpineIndex = currentSpineIndex;
            cachedChapterTotalPageCount = section->pageCount;
            nextPageNumber = section->currentPage;
          }
          section.reset();
          requestUpdate();
        });
  };

  const auto cphun36DoubleAction = [this, &cphun36OpenSettings, &cphun36OpenLayout, &cphun36RebuildReader](
                                      const int raw) {
    ReaderPhysicalButton physical = ReaderPhysicalButton::Back;
    if (raw == HalGPIO::BTN_CONFIRM) physical = ReaderPhysicalButton::Confirm;
    else if (raw == HalGPIO::BTN_LEFT) physical = ReaderPhysicalButton::Left;
    else if (raw == HalGPIO::BTN_RIGHT) physical = ReaderPhysicalButton::Right;
    const ReaderAction configured = READER_BUTTONS.get(physical, ReaderButtonGesture::Double);
    if (configured == ReaderAction::None) {
      // Compatibility fallback: preserve the four device-confirmed CPHUN-36 v2
      // double-click shortcuts until the user assigns an explicit 2x mapping.
      if (raw == HalGPIO::BTN_BACK) { cphun36OpenSettings(); return; }
      if (raw == HalGPIO::BTN_CONFIRM) { cphun36OpenLayout(); return; }
      if (raw == HalGPIO::BTN_LEFT) {
        if (SETTINGS.screenMargin > CrossPointSettings::SCREEN_MARGIN_MIN) {
          SETTINGS.screenMargin = std::max<int>(CrossPointSettings::SCREEN_MARGIN_MIN,
                                                SETTINGS.screenMargin - CrossPointSettings::SCREEN_MARGIN_STEP);
          SETTINGS.saveToFile(); cphun36RebuildReader();
        }
        return;
      }
      if (raw == HalGPIO::BTN_RIGHT && SETTINGS.screenMargin < CrossPointSettings::SCREEN_MARGIN_MAX) {
        SETTINGS.screenMargin = std::min<int>(CrossPointSettings::SCREEN_MARGIN_MAX,
                                              SETTINGS.screenMargin + CrossPointSettings::SCREEN_MARGIN_STEP);
        SETTINGS.saveToFile(); cphun36RebuildReader();
      }
      return;
    }
    if (configured == ReaderAction::OpenTextSettings) { cphun36OpenLayout(); return; }
    if (configured == ReaderAction::OpenLayoutMenu) { cphun36OpenLayout(); return; }
    if (configured == ReaderAction::ScreenMarginDown) {
      if (SETTINGS.screenMargin > CrossPointSettings::SCREEN_MARGIN_MIN) {
        SETTINGS.screenMargin = std::max<int>(CrossPointSettings::SCREEN_MARGIN_MIN, SETTINGS.screenMargin - CrossPointSettings::SCREEN_MARGIN_STEP);
        SETTINGS.saveToFile(); cphun36RebuildReader();
      }
      return;
    }
    if (configured == ReaderAction::ScreenMarginUp) {
      if (SETTINGS.screenMargin < CrossPointSettings::SCREEN_MARGIN_MAX) {
        SETTINGS.screenMargin = std::min<int>(CrossPointSettings::SCREEN_MARGIN_MAX, SETTINGS.screenMargin + CrossPointSettings::SCREEN_MARGIN_STEP);
        SETTINGS.saveToFile(); cphun36RebuildReader();
      }
      return;
    }
    if (configured == ReaderAction::GoHome) { onGoHome(); return; }
    if (configured == ReaderAction::OpenReaderMenu) { openReaderMenu(); return; }
    if (configured == ReaderAction::ToggleNightMode) { SETTINGS.screenInverted = !SETTINGS.screenInverted; SETTINGS.saveToFile(); requestUpdate(); return; }
    if (configured == ReaderAction::ToggleHyphenation) { SETTINGS.hyphenationEnabled = !SETTINGS.hyphenationEnabled; SETTINGS.saveToFile(); cphun36RebuildReader(); return; }
    if (configured == ReaderAction::ToggleSoftHyphen) { SETTINGS.softHyphenEnabled = !SETTINGS.softHyphenEnabled; SETTINGS.saveToFile(); cphun36RebuildReader(); return; }
    // Temporary fallback for actions not yet specialized in this integration: preserve known v2 test behavior.

    if (raw == HalGPIO::BTN_BACK) {
      cphun36OpenSettings();
      return;
    }
    if (raw == HalGPIO::BTN_CONFIRM) {
      cphun36OpenLayout();
      return;
    }
    if (raw == HalGPIO::BTN_LEFT) {
      if (SETTINGS.screenMargin > CrossPointSettings::SCREEN_MARGIN_MIN) {
        SETTINGS.screenMargin = std::max<int>(CrossPointSettings::SCREEN_MARGIN_MIN,
                                              SETTINGS.screenMargin - CrossPointSettings::SCREEN_MARGIN_STEP);
        SETTINGS.saveToFile();
        cphun36RebuildReader();
      }
      return;
    }
    if (raw == HalGPIO::BTN_RIGHT && SETTINGS.screenMargin < CrossPointSettings::SCREEN_MARGIN_MAX) {
      SETTINGS.screenMargin = std::min<int>(CrossPointSettings::SCREEN_MARGIN_MAX,
                                            SETTINGS.screenMargin + CrossPointSettings::SCREEN_MARGIN_STEP);
      SETTINGS.saveToFile();
      cphun36RebuildReader();
    }
  };

  const auto cphun36LegacyShort = [this](const int raw) {
    if (raw == SETTINGS.frontButtonBack) {
      if (footnoteDepth > 0) {
        restoreSavedPosition();
      } else if (SETTINGS.backShortToFileBrowser) {
        activityManager.goToFileBrowser(bookPath);
      } else {
        onGoHome();
      }
      return;
    }
    if (raw == SETTINGS.frontButtonConfirm) {
      openReaderMenu();
      return;
    }

    bool previous = raw == SETTINGS.frontButtonLeft;
    bool next = raw == SETTINGS.frontButtonRight;
    if (!previous && !next) return;
    if (mappedInput.isNavDirectionSwapped()) std::swap(previous, next);
    if (handleEndOfBookPageTurn(previous, next)) return;
    constexpr unsigned long kCphun36MinTurnGapMs = 200;
    if (RenderLock::peek() || (millis() - lastPageTurnTime) < kCphun36MinTurnGapMs) {
      pendingManualTurn = previous ? -1 : 1;
      return;
    }
    if (!section) {
      requestUpdate();
      return;
    }
    pageTurn(next);
    requestUpdate();
  };

  // A completed first short release is held for 400 ms. A matching second
  // short release runs the 2x action. Long releases are never consumed here.
  bool cphun36ConsumeFrontShort = false;
  if (cphun36ReleasedRaw >= 0) {
    bool legacyHold = false;
    if (cphun36ReleasedRaw == SETTINGS.frontButtonBack) {
      legacyHold = cphun36HeldMs >= ReaderUtils::GO_BACK_OR_HOME_MS;
    } else if (cphun36ReleasedRaw == SETTINGS.frontButtonConfirm) {
      switch (SETTINGS.longPressMenuFunction) {
        case CrossPointSettings::LP_MENU_BOOKMARK:
        case CrossPointSettings::LP_MENU_DICTIONARY:
          legacyHold = cphun36HeldMs >= ReaderUtils::BOOKMARK_HOLD_MS;
          break;
        case CrossPointSettings::LP_MENU_KOSYNC:
          legacyHold = cphun36HeldMs >= ReaderUtils::GO_HOME_MS;
          break;
        default:
          break;
      }
    } else if ((cphun36ReleasedRaw == SETTINGS.frontButtonLeft ||
                cphun36ReleasedRaw == SETTINGS.frontButtonRight) &&
               SETTINGS.longPressButtonBehavior != SETTINGS.OFF) {
      legacyHold = cphun36HeldMs > ReaderUtils::SKIP_HOLD_MS;
    }

    if (!legacyHold) {
      cphun36ConsumeFrontShort = true;
      if (cphun36.waitingSecond && cphun36.raw == cphun36ReleasedRaw &&
          millis() - cphun36.firstReleaseMs <= CPHUN36_DOUBLE_MS) {
        cphun36.waitingSecond = false;
        cphun36DoubleAction(cphun36ReleasedRaw);
      } else {
        if (cphun36.waitingSecond) cphun36LegacyShort(cphun36.raw);
        cphun36.raw = cphun36ReleasedRaw;
        cphun36.firstReleaseMs = millis();
        cphun36.waitingSecond = true;
      }
    } else if (cphun36.waitingSecond && cphun36.raw == cphun36ReleasedRaw) {
      cphun36.waitingSecond = false;
    }
  }

  if (cphun36.waitingSecond && millis() - cphun36.firstReleaseMs > CPHUN36_DOUBLE_MS) {
    const int raw = cphun36.raw;
    cphun36.waitingSecond = false;
    cphun36LegacyShort(raw);
  }

'''
replace_once("src/activities/reader/EpubReaderActivity.cpp", anchor, block)

# Suppress only legacy front short-action conditions. No global return and no
# side/Power condition is changed.
p = Path("src/activities/reader/EpubReaderActivity.cpp")
text = p.read_text(encoding="utf-8")
text = text.replace(
    "  const bool confirmReleased = mappedInput.wasReleased(MappedInputManager::Button::Confirm);\n",
    "  const bool confirmReleased = !cphun36ConsumeFrontShort && mappedInput.wasReleased(MappedInputManager::Button::Confirm);\n",
    1,
)
text = text.replace(
    "  if (footnoteDepth > 0 && mappedInput.wasReleased(MappedInputManager::Button::Back) &&\n",
    "  if (!cphun36ConsumeFrontShort && footnoteDepth > 0 && mappedInput.wasReleased(MappedInputManager::Button::Back) &&\n",
    1,
)
# Back navigation itself is release based; skip it only for a deferred short release.
text = text.replace(
    "  if (handleBackNavigation()) {\n",
    "  if (!cphun36ConsumeFrontShort && handleBackNavigation()) {\n",
    1,
)
# ReaderUtils::detectPageTurn may use front press when long-press behavior is OFF,
# or front release when it is enabled. Mask the result only if the trigger came
# from a physical front event currently owned by the 2x detector. Side buttons
# and tilt remain untouched.
old = "  auto [prevTriggered, nextTriggered, fromTilt] = ReaderUtils::detectPageTurn(mappedInput);\n  prevTriggered = prevTriggered || touch.prev;\n"
new = "  auto [prevTriggered, nextTriggered, fromTilt] = ReaderUtils::detectPageTurn(mappedInput);\n  if (!fromTilt && (cphun36PressedRaw >= 0 || cphun36ConsumeFrontShort)) {\n    const bool sidePrev = mappedInput.wasReleased(MappedInputManager::Button::PageBack) ||\n                          mappedInput.wasPressed(MappedInputManager::Button::PageBack);\n    const bool sideNext = mappedInput.wasReleased(MappedInputManager::Button::PageForward) ||\n                          mappedInput.wasPressed(MappedInputManager::Button::PageForward);\n    prevTriggered = sidePrev;\n    nextTriggered = sideNext;\n  }\n  prevTriggered = prevTriggered || touch.prev;\n"
if old not in text:
    raise SystemExit("Page-turn anchor not found")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")

# CI safety checks: the previous bad integration's press-frame early-return must
# never reappear, and v2 must keep side/Power code in the reader loop.
reader = p.read_text(encoding="utf-8")
required = [
    "CPHUN-36 2x front-button test v2",
    "cphun36OpenSettings",
    "TextSettingsActivity::Tab::Layout",
    "SCREEN_MARGIN_STEP",
    "cphun36ConsumeFrontShort",
    "Button::Power",
    "Button::PageBack",
    "Button::PageForward",
]
for needle in required:
    if needle not in reader:
        raise SystemExit(f"Missing v2 safety marker: {needle}")
if "Suppress the legacy press path" in reader:
    raise SystemExit("Unsafe v1 early-return integration detected")

print("Applied safe CPHUN-36 2x button test v2 integration")
