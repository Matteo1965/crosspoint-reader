from pathlib import Path

def once(path: str, old: str, new: str, label: str):
    p = Path(path)
    source = p.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-150 {label}: expected one anchor, got {count}")
    p.write_text(source.replace(old, new, 1), encoding="utf-8")

reader = "src/activities/reader/EpubReaderActivity.cpp"

# ReaderRenderSpec contains the serialization-relevant fields. Compare them
# explicitly (never memcmp: compiler-inserted padding is not meaningful).
helper = r'''
struct Cphun150LayoutSnapshot {
  ReaderRenderSpec spec;
  uint8_t orientation;
  uint8_t screenMargin;
  uint8_t statusBarHeight;
};

Cphun150LayoutSnapshot captureReaderLayout(const uint16_t width, const uint16_t height) {
  return {SETTINGS.readerRenderSpec(width, height), SETTINGS.orientation, SETTINGS.screenMargin,
          UITheme::getInstance().getStatusBarHeight()};
}

bool readerLayoutMatches(const Cphun150LayoutSnapshot& saved,
                         const uint16_t width, const uint16_t height) {
  if (saved.orientation != SETTINGS.orientation || saved.screenMargin != SETTINGS.screenMargin ||
      saved.statusBarHeight != UITheme::getInstance().getStatusBarHeight()) {
    return false;
  }
  const ReaderRenderSpec current = SETTINGS.readerRenderSpec(width, height);
  const ReaderRenderSpec& old = saved.spec;
  return old.fontId == current.fontId &&
         old.lineCompression == current.lineCompression &&
         old.extraParagraphSpacing == current.extraParagraphSpacing &&
         old.paragraphAlignment == current.paragraphAlignment &&
         old.viewportWidth == current.viewportWidth &&
         old.viewportHeight == current.viewportHeight &&
         old.hyphenationEnabled == current.hyphenationEnabled &&
         old.hungarianHyphenationExtended == current.hungarianHyphenationExtended &&
         old.hangingPunctuationLimitPx == current.hangingPunctuationLimitPx &&
         old.shortHyphen == current.shortHyphen &&
         old.fixedDialogueSpacing == current.fixedDialogueSpacing &&
         old.minimumSpacePercent == current.minimumSpacePercent &&
         old.letterSpacingLimitPercent == current.letterSpacingLimitPercent &&
         old.embeddedStyle == current.embeddedStyle &&
         old.imageRendering == current.imageRendering &&
         old.focusReadingEnabled == current.focusReadingEnabled;
}

'''
once(reader,
     'namespace {\nconstexpr int PAGE_TURN_RATES[]',
     'namespace {\n' + helper + 'constexpr int PAGE_TURN_RATES[]',
     "layout snapshot helpers")

# The generic Settings screen can change appearance/frontlight/etc. Only
# invalidate the reader's section if effective layout parameters changed.
once(reader,
'''  const auto cphun36OpenSettings = [this]() {
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
  };''',
'''  const auto cphun36OpenSettings = [this]() {
    const auto before = captureReaderLayout(buildViewportWidth, buildViewportHeight);
    startActivityForResult(std::make_unique<SettingsActivity>(renderer, mappedInput),
                           [this, before](const ActivityResult&) {
                             if (!readerLayoutMatches(before, buildViewportWidth, buildViewportHeight)) {
                               RenderLock lock;
                               if (section) {
                                 rememberCurrentContentOffset();
                                 cachedSpineIndex = currentSpineIndex;
                                 cachedChapterTotalPageCount = section->pageCount;
                                 nextPageNumber = section->currentPage;
                               }
                               section.reset();
                               LOG_INF("ERS", "CPHUN-150: settings changed layout; refreshing section");
                             } else {
                               LOG_DBG("ERS", "CPHUN-150: settings unchanged; retaining section");
                             }
                             requestUpdate();
                           });
  };''',
"button shortcut to general settings")

once(reader,
'''  const auto cphun36OpenLayout = [this]() {
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
  };''',
'''  const auto cphun36OpenLayout = [this]() {
    const auto before = captureReaderLayout(buildViewportWidth, buildViewportHeight);
    startActivityForResult(
        std::make_unique<TextSettingsActivity>(renderer, mappedInput, &sdFontSystem.registry(),
                                               TextSettingsActivity::Tab::Layout),
        [this, before](const ActivityResult&) {
          if (!readerLayoutMatches(before, buildViewportWidth, buildViewportHeight)) {
            RenderLock lock;
            if (section) {
              rememberCurrentContentOffset();
              cachedSpineIndex = currentSpineIndex;
              cachedChapterTotalPageCount = section->pageCount;
              nextPageNumber = section->currentPage;
            }
            section.reset();
            LOG_INF("ERS", "CPHUN-150: layout changed; refreshing section");
          } else {
            LOG_DBG("ERS", "CPHUN-150: layout unchanged; retaining section");
          }
          requestUpdate();
        });
  };''',
"button shortcut to layout")

once(reader,
'''    case EpubReaderMenuActivity::MenuAction::TEXT_SETTINGS: {
      startActivityForResult(std::make_unique<TextSettingsActivity>(renderer, mappedInput, &sdFontSystem.registry(),
                                                                    TextSettingsActivity::Tab::Family),
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
                               openReaderMenu();
                             });
      break;
    }''',
'''    case EpubReaderMenuActivity::MenuAction::TEXT_SETTINGS: {
      const auto before = captureReaderLayout(buildViewportWidth, buildViewportHeight);
      startActivityForResult(std::make_unique<TextSettingsActivity>(renderer, mappedInput, &sdFontSystem.registry(),
                                                                    TextSettingsActivity::Tab::Family),
                             [this, before](const ActivityResult&) {
                               if (!readerLayoutMatches(before, buildViewportWidth, buildViewportHeight)) {
                                 RenderLock lock;
                                 if (section) {
                                   rememberCurrentContentOffset();
                                   cachedSpineIndex = currentSpineIndex;
                                   cachedChapterTotalPageCount = section->pageCount;
                                   nextPageNumber = section->currentPage;
                                 }
                                 section.reset();
                                 LOG_INF("ERS", "CPHUN-150: text settings changed; refreshing section");
                               } else {
                                 LOG_DBG("ERS", "CPHUN-150: text settings unchanged; retaining section");
                               }
                               openReaderMenu();
                             });
      break;
    }''',
"reader menu text settings")

# Sleep/wake path: ActivityManager::goToSleep REPLACES the activity (the ESP32
# may enter deep sleep). In-progress Section::~Section() already persists a
# partial .bin; complete .bin is read by renderBook() after wake. Never
# bypass cache parameter validation. Add field-specific diagnostics for the
# remaining observed rebuilds to separate genuine layout changes from bad
# cached metadata on the device.
section = "lib/Epub/Epub/Section.cpp"
once(section,
'''      LOG_ERR("SCT", "Deserialization failed: Parameters do not match");
      clearCache();''',
'''      LOG_ERR("SCT",
              "CPHUN-150 cache mismatch: font=%d/%d viewport=%ux%u/%ux%u "
              "tracking=%u/%u margins=%u/%u line=%u/%u",
              fileFontId, spec.fontId,
              static_cast<unsigned>(fileViewportWidth), static_cast<unsigned>(fileViewportHeight),
              static_cast<unsigned>(spec.viewportWidth), static_cast<unsigned>(spec.viewportHeight),
              static_cast<unsigned>(fileLetterSpacingLimitPercent),
              static_cast<unsigned>(spec.letterSpacingLimitPercent),
              static_cast<unsigned>(fileHangingPunctuationLimitPx),
              static_cast<unsigned>(spec.hangingPunctuationLimitPx),
              static_cast<unsigned>(fileExtraParagraphSpacing),
              static_cast<unsigned>(spec.extraParagraphSpacing));
      clearCache();''',
"reason-coded cache mismatch logging")

# No cache format change: the stored representation remains backward-compatible.
once("src/CPHUNBuildId.h",
     '#define CPHUN_BUILD_ID "CPHUN-260925-149-EXP"',
     '#define CPHUN_BUILD_ID "CPHUN-260925-150-EXP"',
     "build identifier")

print("CPHUN-150: 3 no-op menu return paths preserve section; sleep cache diagnostics enabled")
