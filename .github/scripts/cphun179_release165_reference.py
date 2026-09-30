#!/usr/bin/env python3
"""CPHUN-179: make B a CrossPoint 1.6.5 Release X4 cover reference.
A/C remain the CPHUN-178 paths. Apply after CPHUN-178 on regenerated tree.
"""
from pathlib import Path

def rep(path,old,new,expected=1):
    p=Path(path)
    t=p.read_text(encoding="utf-8")
    n=t.count(old)
    if n!=expected: raise SystemExit(f"179: {path}: expected {expected}, got {n}: {old[:90]!r}")
    p.write_text(t.replace(old,new),encoding="utf-8")

# Preserve the existing A Atkinson tuning. The Release's original thresholds
# are selected only for B, and no downstream changes affect C's Floyd path.
rep("lib/GfxRenderer/BitmapHelpers.h",
    "explicit AtkinsonDitherer(int width) : width(width) {",
    "explicit AtkinsonDitherer(int width, bool originalThresholds = false) : width(width), originalThresholds(originalThresholds) {")
p=Path("lib/GfxRenderer/BitmapHelpers.h")
t=p.read_text(encoding="utf-8")
start=t.index("class AtkinsonDitherer")
end=t.index("class FloydSteinbergDitherer")
section=t[start:end]
old="if (false) {  // original thresholds"
if section.count(old)!=1:raise SystemExit("179: Atkinson threshold anchor missing")
p.write_text(t[:start]+section.replace(old,"if (originalThresholds) {  // CrossPoint 1.6.5 original thresholds",1)+t[end:],encoding="utf-8")
rep("lib/GfxRenderer/BitmapHelpers.h",
    "class AtkinsonDitherer {\n public:",
    "class AtkinsonDitherer {\n  const bool originalThresholds;\n public:")

# Add opt-in original thresholds to both JPEG and PNG cover converters. The
# default remains false so A and the original non-cover call sites are intact.
for kind,cls in (("Jpeg","JpegToBmpConverter"),("Png","PngToBmpConverter")):
    base=f"lib/{cls}/{cls}"
    h=Path(base+".h")
    s=h.read_text(encoding="utf-8")
    old="bool oneBit, bool crop = true, bool forceFloyd = false);"
    new="bool oneBit, bool crop = true, bool forceFloyd = false, bool originalThresholds = false);"
    if s.count(old)!=1:raise SystemExit(f"{h}: converter internal declaration missing")
    s=s.replace(old,new,1)
    prefix=kind.lower()
    old=f"static bool {prefix}FileToBmpStream(HalFile& {prefix}File, Print& bmpOut, bool crop = true);"
    new=f"static bool {prefix}FileToBmpStream(HalFile& {prefix}File, Print& bmpOut, bool crop = true, bool originalThresholds = false);"
    if s.count(old)!=1:raise SystemExit(f"{h}: converter public declaration missing")
    h.write_text(s.replace(old,new,1),encoding="utf-8")
    cpp=Path(base+".cpp")
    s=cpp.read_text(encoding="utf-8")
    old="bool oneBit, bool crop, bool forceFloyd) {"
    new="bool oneBit, bool crop, bool forceFloyd, bool originalThresholds) {"
    if s.count(old)!=1:raise SystemExit(f"{cpp}: converter internal implementation missing")
    s=s.replace(old,new,1)
    old="AtkinsonDitherer>(outWidth)" if kind=="Jpeg" else "new AtkinsonDitherer(outWidth)"
    new="AtkinsonDitherer>(outWidth, originalThresholds)" if kind=="Jpeg" else "new AtkinsonDitherer(outWidth, originalThresholds)"
    if s.count(old)!=1:raise SystemExit(f"{cpp}: ditherer ctor missing")
    s=s.replace(old,new,1)
    old=f"bool {cls}::{prefix}FileToBmpStream(HalFile& {prefix}File, Print& bmpOut, bool crop) {{"
    new=f"bool {cls}::{prefix}FileToBmpStream(HalFile& {prefix}File, Print& bmpOut, bool crop, bool originalThresholds) {{"
    if s.count(old)!=1:raise SystemExit(f"{cpp}: converter public implementation missing")
    s=s.replace(old,new,1)
    old=f"return {prefix}FileToBmpStreamInternal({prefix}File, bmpOut, targetWidth, targetHeight, false, crop);"
    new=f"return {prefix}FileToBmpStreamInternal({prefix}File, bmpOut, targetWidth, targetHeight, false, crop, false, originalThresholds);"
    if s.count(old)!=1:raise SystemExit(f"{cpp}: converter call missing")
    cpp.write_text(s.replace(old,new,1),encoding="utf-8")

# A and B must NEVER share an already-cached BMP. The B path uses the source
# EPUB cover, its existing crop option, and the official original thresholds.
rep("lib/Epub/Epub.h",
    "std::string getCoverBmpPath(bool cropped = false) const;\n  bool generateCoverBmp(bool cropped = false) const;",
    "std::string getCoverBmpPath(bool cropped = false, bool release165 = false) const;\n  bool generateCoverBmp(bool cropped = false, bool release165 = false) const;")
rep("lib/Epub/Epub.cpp",
    '''std::string Epub::getCoverBmpPath(bool cropped) const {
  const auto coverFileName = std::string("cover") + (cropped ? "_crop" : "");
  return cachePath + "/" + coverFileName + ".bmp";
}

bool Epub::generateCoverBmp(bool cropped) const {''',
    '''std::string Epub::getCoverBmpPath(bool cropped, bool release165) const {
  const auto coverFileName = std::string(release165 ? "cover_release165" : "cover") +
                             (cropped ? "_crop" : "");
  return cachePath + "/" + coverFileName + ".bmp";
}

bool Epub::generateCoverBmp(bool cropped, bool release165) const {''')
rep("lib/Epub/Epub.cpp","getCoverBmpPath(cropped)", "getCoverBmpPath(cropped, release165)",5)
rep("lib/Epub/Epub.cpp",
    "JpegToBmpConverter::jpegFileToBmpStream(coverJpg, coverBmp, cropped)",
    "JpegToBmpConverter::jpegFileToBmpStream(coverJpg, coverBmp, cropped, release165)")
rep("lib/Epub/Epub.cpp",
    "PngToBmpConverter::pngFileToBmpStream(coverPng, coverBmp, cropped)",
    "PngToBmpConverter::pngFileToBmpStream(coverPng, coverBmp, cropped, release165)")

# B: official image source and driver activation (SDK pinned by release sync).
p=Path("src/activities/boot_sleep/SleepActivity.cpp")
s=p.read_text(encoding="utf-8")
old='''    if (coverBmpPath.empty()) {
      if (!lastEpub.generateCoverBmp(cropped)) {
        LOG_ERR("SLP", "Failed to generate cover bmp");
        return (this->*renderNoCoverSleepScreen)();
      }
      coverBmpPath = lastEpub.getCoverBmpPath(cropped);
    }'''
new='''    if (coverBmpPath.empty()) {
      const bool release165 = SETTINGS.coverTestMode == CrossPointSettings::COVER_TEST_ABSOLUTE &&
                              renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported() &&
                              display.getController() == HalDisplay::Controller::SSD1677 &&
                              SETTINGS.sleepScreenCoverFilter == CrossPointSettings::NO_FILTER;
      if (!lastEpub.generateCoverBmp(cropped, release165)) {
        LOG_ERR("SLP", "Failed to generate cover bmp");
        return (this->*renderNoCoverSleepScreen)();
      }
      coverBmpPath = lastEpub.getCoverBmpPath(cropped, release165);
    }'''
if s.count(old)!=1:raise SystemExit("179: CPHUN-178 cover branch missing")
s=s.replace(old,new,1)
old='''    // CPHUN-177D experimental B: HALF precondition + swapped planes and
    // the original C7 factory activation. Only B can enter Absolute.
    renderer.displayBuffer(HalDisplay::HALF_REFRESH);
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return;'''
new='''    // CPHUN-179 B: official 1.6.5 Absolute path, no HALF preclean,
    // original LSB/MSB RAM assignment and SDK factory 0xCC activation.
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return;'''
if s.count(old)!=1:raise SystemExit("179: experimental B block missing")
p.write_text(s.replace(old,new,1),encoding="utf-8")

for lang,label in (("hungarian","B - Atkinson Absolute"),
                   ("english","B - Atkinson Absolute")):
    p=Path(f"lib/I18n/translations/{lang}.yaml")
    s=p.read_text(encoding="utf-8")
    old='STR_CPHUN_COVER_TEST_B: "B – Absolute (177D)"'
    if s.count(old)!=1:raise SystemExit("179: B label missing")
    p.write_text(s.replace(old,'STR_CPHUN_COVER_TEST_B: "'+label+'"',1),encoding="utf-8")

# CPHUN-180: the default for new installs is set by CPHUN-178's field
# initializer. Existing settings.json values are read without migration.
assert "coverTestMode = COVER_TEST_ABSOLUTE;" in Path("src/CrossPointSettings.h").read_text(encoding="utf-8")
for lang in ("hungarian", "english"):
    labels = Path(f"lib/I18n/translations/{lang}.yaml").read_text(encoding="utf-8")
    for label in ("A - Atkinson Overlay", "B - Atkinson Absolute", "C - Floyd-Steinberg"):
        assert label in labels
print("CPHUN-180: B new-install default; existing A/B/C choices preserved")

# The two experimental driver probes are NOT applied by this workflow.
driver=Path("freeink-sdk/libs/display/FreeInkDisplay/src/driver/Ssd1677Driver.cpp").read_text(encoding="utf-8")
assert 'bus.data(0xCC);  // CLOCK_ON|ANALOG_ON|MODE_SELECT|DISPLAY_START' in driver
assert 'writeGrayRam(bus, CMD_WRITE_RAM_BW, lsb, _bufferSize);' in driver
assert 'writeGrayRam(bus, CMD_WRITE_RAM_RED, msb, _bufferSize);' in driver
assert 'bus.data(0xC7);' not in driver
assert 'COVER_TEST_ABSOLUTE' in s or 'release165' in Path("src/activities/boot_sleep/SleepActivity.cpp").read_text(encoding="utf-8")
print("CPHUN-179: official 1.6.5 B source thresholds/cache/Absolute driver verified")
