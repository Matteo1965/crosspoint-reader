from pathlib import Path

BRANCH_MARKER = "CPHUN-36 2x front-button test"


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Expected patch anchor not found in {path}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Expose the raw physical front-button release edge, matching the existing
# getPressedFrontButton() helper. This keeps 2x gestures attached to hardware
# buttons instead of logical remaps/orientation.
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

replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '#include "ProgressMapper.h"\n',
    '#include "ProgressMapper.h"\n#include "ReaderButtonGestureDetector.h"\n',
)

anchor = "  const auto touch = ReaderUtils::detectTouchPageTurn(renderer, mappedInput);\n\n"
block = r'''  const auto touch = ReaderUtils::detectTouchPageTurn(renderer, mappedInput);

  // CPHUN-36 2x front-button test. Only short physical front-button contacts
  // enter this detector. Existing long/hold releases fall through unchanged to
  // the legacy reader code below.
  static ReaderButtonGestureDetector cphun36Gestures(400, ReaderUtils::SKIP_HOLD_MS);

  const auto asPhysicalButton = [](const int raw) -> std::optional<ReaderPhysicalButton> {
    switch (raw) {
      case HalGPIO::BTN_BACK:
        return ReaderPhysicalButton::Back;
      case HalGPIO::BTN_CONFIRM:
        return ReaderPhysicalButton::Confirm;
      case HalGPIO::BTN_LEFT:
        return ReaderPhysicalButton::Left;
      case HalGPIO::BTN_RIGHT:
        return ReaderPhysicalButton::Right;
      default:
        return std::nullopt;
    }
  };

  const auto openTextSettingsTab = [this](const TextSettingsActivity::Tab tab) {
    startActivityForResult(
        std::make_unique<TextSettingsActivity>(renderer, mappedInput, &sdFontSystem.registry(), tab),
        [this](const ActivityResult&) {
          {
            RenderLock lock;
            if (section) {
              rememberCurrentContentOffset();
              cachedSpineIndex = currentSpineIndex;
              cachedChapterTotalPageCount = section->pageCount;
              nextPageNumber = section->currentPage;
            }
            section.reset();
          }
          requestUpdate();
        });
  };

  const auto runDoubleAction = [this, &openTextSettingsTab](const ReaderPhysicalButton button) {
    switch (button) {
      case ReaderPhysicalButton::Back:
        openReaderMenu();
        break;
      case ReaderPhysicalButton::Confirm:
        openTextSettingsTab(TextSettingsActivity::Tab::Family);
        break;
      case ReaderPhysicalButton::Left:
        openTextSettingsTab(TextSettingsActivity::Tab::Layout);
        break;
      case ReaderPhysicalButton::Right:
        openTextSettingsTab(TextSettingsActivity::Tab::Style);
        break;
      case ReaderPhysicalButton::Count:
        break;
    }
  };

  const auto runLegacyShortAction = [this](const ReaderPhysicalButton button) {
    int raw = -1;
    switch (button) {
      case ReaderPhysicalButton::Back:
        raw = HalGPIO::BTN_BACK;
        break;
      case ReaderPhysicalButton::Confirm:
        raw = HalGPIO::BTN_CONFIRM;
        break;
      case ReaderPhysicalButton::Left:
        raw = HalGPIO::BTN_LEFT;
        break;
      case ReaderPhysicalButton::Right:
        raw = HalGPIO::BTN_RIGHT;
        break;
      case ReaderPhysicalButton::Count:
        return;
    }

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
    constexpr unsigned long kMinManualTurnGapMs = 200;
    if (RenderLock::peek() || (millis() - lastPageTurnTime) < kMinManualTurnGapMs) {
      pendingManualTurn = previous ? -1 : 1;
      return;
    }
    pageTurn(next);
    requestUpdate();
  };

  const auto dispatchGesture = [&runDoubleAction, &runLegacyShortAction](
                                   const std::optional<ReaderButtonGestureEvent>& event) {
    if (!event.has_value()) return false;
    if (event->gesture == ReaderButtonGesture::Double) {
      runDoubleAction(event->button);
      return true;
    }
    if (event->gesture == ReaderButtonGesture::Single) {
      runLegacyShortAction(event->button);
      return true;
    }
    return false;
  };

  if (const auto pressed = asPhysicalButton(mappedInput.getPressedFrontButton())) {
    cphun36Gestures.onPressed(*pressed, millis());
    // Suppress the legacy press path. If this remains a single click its
    // original action is replayed after the double-click window expires.
    return;
  }

  if (const int rawReleased = mappedInput.getReleasedFrontButton(); rawReleased >= 0) {
    if (const auto released = asPhysicalButton(rawReleased)) {
      const unsigned long heldMs = mappedInput.getHeldTime();
      bool legacyHold = false;

      if (rawReleased == SETTINGS.frontButtonBack) {
        legacyHold = heldMs >= ReaderUtils::GO_BACK_OR_HOME_MS;
      } else if (rawReleased == SETTINGS.frontButtonConfirm) {
        switch (SETTINGS.longPressMenuFunction) {
          case CrossPointSettings::LP_MENU_BOOKMARK:
          case CrossPointSettings::LP_MENU_DICTIONARY:
            legacyHold = heldMs >= ReaderUtils::BOOKMARK_HOLD_MS;
            break;
          case CrossPointSettings::LP_MENU_KOSYNC:
            legacyHold = heldMs >= ReaderUtils::GO_HOME_MS;
            break;
          case CrossPointSettings::LP_MENU_READER_MENU:
          case CrossPointSettings::LP_MENU_DISABLED:
          default:
            legacyHold = false;
            break;
        }
      } else if ((rawReleased == SETTINGS.frontButtonLeft || rawReleased == SETTINGS.frontButtonRight) &&
                 SETTINGS.longPressButtonBehavior != SETTINGS.OFF) {
        legacyHold = heldMs > ReaderUtils::SKIP_HOLD_MS;
      }

      if (legacyHold) {
        // Mark/cancel any pending short gesture, but deliberately do not run a
        // CPHUN-36 Hold action. The existing code below receives this release.
        cphun36Gestures.onHeld(*released, millis());
        cphun36Gestures.onReleased(*released, millis());
      } else {
        const auto event = cphun36Gestures.onReleased(*released, millis());
        dispatchGesture(event);
        return;
      }
    }
  }

  if (dispatchGesture(cphun36Gestures.poll(millis()))) return;

'''
replace_once("src/activities/reader/EpubReaderActivity.cpp", anchor, block)

# Lightweight source checks make CI fail loudly if the test patch drifts.
checks = {
    "src/MappedInputManager.h": "getReleasedFrontButton",
    "src/MappedInputManager.cpp": "MappedInputManager::getReleasedFrontButton",
    "src/activities/reader/EpubReaderActivity.cpp": BRANCH_MARKER,
}
for filename, needle in checks.items():
    if needle not in Path(filename).read_text(encoding="utf-8"):
        raise SystemExit(f"CPHUN-36 test patch verification failed: {filename}: {needle}")

print("Applied CPHUN-36 2x front-button test integration")
