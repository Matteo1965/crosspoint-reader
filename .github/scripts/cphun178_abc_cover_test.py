#!/usr/bin/env python3
"""CPHUN-178: A/B/C sleep-cover comparison, without SD framebuffer dumps."""
from pathlib import Path

def once(path, old, new):
    p=Path(path)
    s=p.read_text(encoding="utf-8")
    n=s.count(old)
    if n != 1:
        raise SystemExit(f"CPHUN-178: {path}: expected one anchor, got {n}: {old[:100]!r}")
    p.write_text(s.replace(old,new,1),encoding="utf-8")

once("src/CrossPointSettings.h",
     "  enum SLEEP_SCREEN_COVER_MODE { FIT = 0, CROP = 1, SLEEP_SCREEN_COVER_MODE_COUNT };",
     """  enum SLEEP_SCREEN_COVER_MODE { FIT = 0, CROP = 1, SLEEP_SCREEN_COVER_MODE_COUNT };
  // A/B/C physical-panel test; B (official Atkinson Absolute) is the default.
  enum COVER_TEST_MODE : uint8_t { COVER_TEST_OVERLAY = 0, COVER_TEST_ABSOLUTE = 1,
                                   COVER_TEST_FLOYD_OVERLAY = 2, COVER_TEST_MODE_COUNT };""")
once("src/CrossPointSettings.h",
     "  uint8_t sleepScreenCoverMode = FIT;",
     "  uint8_t sleepScreenCoverMode = FIT;\n  uint8_t coverTestMode = COVER_TEST_ABSOLUTE;")
once("src/SettingsListBase.h",
     """        SettingInfo::Enum(StrId::STR_SLEEP_COVER_FILTER, &CrossPointSettings::sleepScreenCoverFilter,""",
     """        SettingInfo::Enum(StrId::STR_CPHUN_COVER_TEST_MODE, &CrossPointSettings::coverTestMode,
                          {StrId::STR_CPHUN_COVER_TEST_A, StrId::STR_CPHUN_COVER_TEST_B,
                           StrId::STR_CPHUN_COVER_TEST_C},
                          "coverTestMode", StrId::STR_CAT_DISPLAY),
        SettingInfo::Enum(StrId::STR_SLEEP_COVER_FILTER, &CrossPointSettings::sleepScreenCoverFilter,""")

for path,labels in [
  ("lib/I18n/translations/hungarian.yaml", """STR_CPHUN_COVER_TEST_MODE: "Borító mód"
STR_CPHUN_COVER_TEST_A: "A - Atkinson Overlay"
STR_CPHUN_COVER_TEST_B: "B – Absolute (177D)"
STR_CPHUN_COVER_TEST_C: "C - Floyd-Steinberg"
"""),
  ("lib/I18n/translations/english.yaml", """STR_CPHUN_COVER_TEST_MODE: "Cover test mode"
STR_CPHUN_COVER_TEST_A: "A - Atkinson Overlay"
STR_CPHUN_COVER_TEST_B: "B – Absolute (177D)"
STR_CPHUN_COVER_TEST_C: "C - Floyd-Steinberg"
"""),
]:
    p=Path(path)
    s=p.read_text(encoding="utf-8")
    if "STR_CPHUN_COVER_TEST_MODE:" in s: raise SystemExit("duplicate labels "+path)
    p.write_text(s.rstrip()+"\n"+labels,encoding="utf-8")

# The C path reuses EXACTLY the dedicated book-menu Floyd–Steinberg BMP cache,
# rather than reprocessing the standard sleeping-cover BMP.
p=Path("src/activities/boot_sleep/SleepActivity.cpp")
s=p.read_text(encoding="utf-8")
old='''    if (!lastEpub.generateCoverBmp(cropped)) {
      LOG_ERR("SLP", "Failed to generate cover bmp");
      return (this->*renderNoCoverSleepScreen)();
    }

    coverBmpPath = lastEpub.getCoverBmpPath(cropped);
'''
new='''    // CPHUN-178 mode C: the same cached 2-bit Floyd–Steinberg bitmap used
    // by Book -> Show Cover. Only EPUB offers this dedicated cache.
    if (SETTINGS.coverTestMode == CrossPointSettings::COVER_TEST_FLOYD_OVERLAY) {
      const std::string fsPath = lastEpub.getBookCoverViewBmpPath();
      if (Storage.exists(fsPath.c_str()) || lastEpub.generateBookCoverViewBmp()) {
        coverBmpPath = fsPath;
      } else {
        LOG_ERR("SLP", "Floyd book-cover generation failed; using standard cover");
      }
    }
    if (coverBmpPath.empty()) {
      if (!lastEpub.generateCoverBmp(cropped)) {
        LOG_ERR("SLP", "Failed to generate cover bmp");
        return (this->*renderNoCoverSleepScreen)();
      }
      coverBmpPath = lastEpub.getCoverBmpPath(cropped);
    }
'''
if s.count(old)!=1:raise SystemExit("EPUB cover cache anchor missing")
s=s.replace(old,new,1)

# Apply the mode exclusively to the standard bitmap/cover path; unrelated
# transparent custom overlays keep the existing legacy behavior.
old='''  const bool absolute =
      hasGreyscale && renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();
  if (absolute) {
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return;
  } else if (hasGreyscale) {'''
new='''  const bool absolute =
      hasGreyscale && SETTINGS.coverTestMode == CrossPointSettings::COVER_TEST_ABSOLUTE &&
      renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();
  if (absolute) {
    // CPHUN-177D experimental B: HALF precondition + swapped planes and
    // the original C7 factory activation. Only B can enter Absolute.
    renderer.displayBuffer(HalDisplay::HALF_REFRESH);
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return;
  } else if (hasGreyscale) {'''
if s.count(old)!=1:raise SystemExit("bitmap grayscale mode anchor missing")
s=s.replace(old,new,1)
p.write_text(s,encoding="utf-8")

# Check the post-core render hooks and default settings wiring.
settings=Path("src/SettingsListBase.h").read_text(encoding="utf-8")
assert '"coverTestMode", StrId::STR_CAT_DISPLAY' in settings
assert "coverTestMode = COVER_TEST_ABSOLUTE;" in Path("src/CrossPointSettings.h").read_text(encoding="utf-8")
assert "getBookCoverViewBmpPath()" in s
assert "dumpSleepDiagPlane177" not in s
print("CPHUN-178: A/B/C menu, persistent enum, C Floyd cache, B HALF preclean; no sleepdiag")
