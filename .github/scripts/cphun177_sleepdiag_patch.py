#!/usr/bin/env python3
from pathlib import Path

p = Path("src/activities/boot_sleep/SleepActivity.cpp")
s = p.read_text(encoding="utf-8")

def rep(old, new, count=1):
    global s
    if old not in s:
        raise SystemExit("CPHUN-177 sleepdiag anchor missing: " + old[:140].replace("\n","\\n"))
    s = s.replace(old, new, count)

rep("""constexpr uint8_t MIN_VISIBLE_ALPHA = 8;

struct BitmapPlacement {""",
"""constexpr uint8_t MIN_VISIBLE_ALPHA = 8;

// CPHUN-177 Experimental: exact sleep-screen framebuffer diagnostics.
// Dumps are observational only: they copy the prepared 1-bit work buffers.
bool dumpSleepDiagPlane177(const char* path, const GfxRenderer& renderer) {
  if (!Storage.ensureDirectoryExists("/sleepdiag")) {
    LOG_ERR("SLP", "sleepdiag177: failed to create /sleepdiag");
    return false;
  }
  const uint8_t* data = renderer.getWriteTarget();
  const size_t size = renderer.getBufferSize();
  if (!data || size == 0) {
    LOG_ERR("SLP", "sleepdiag177: framebuffer unavailable");
    return false;
  }
  HalFile out;
  if (!Storage.openFileForWrite("SLP", path, out)) {
    LOG_ERR("SLP", "sleepdiag177: cannot open %s", path);
    return false;
  }
  const bool ok = out.write(data, size) == size;
  out.close();
  if (!ok) LOG_ERR("SLP", "sleepdiag177: short write %s", path);
  return ok;
}

void writeSleepDiagMeta177(const GfxRenderer& renderer, const Bitmap* bitmap = nullptr,
                           const bool preserveBackground = false, const bool hasGreyscale = false,
                           const bool absolute = false) {
  if (!Storage.ensureDirectoryExists("/sleepdiag")) return;
  HalFile out;
  if (!Storage.openFileForWrite("SLP", "/sleepdiag/cphun177_info.txt", out)) return;
  out.print("build=CPHUN-260929-177-GRAY-SLEEPDIAG\\n");
  out.print("width="); out.print(renderer.getDisplayWidth()); out.print("\\n");
  out.print("height="); out.print(renderer.getDisplayHeight()); out.print("\\n");
  out.print("width_bytes="); out.print(renderer.getDisplayWidthBytes()); out.print("\\n");
  out.print("buffer_bytes="); out.print(renderer.getBufferSize()); out.print("\\n");
  if (bitmap) {
    out.print("bpp="); out.print(bitmap->getBpp()); out.print("\\n");
    out.print("bitmap_hasGreyscale="); out.print(hasGreyscale ? 1 : 0); out.print("\\n");
    out.print("preserveBackground="); out.print(preserveBackground ? 1 : 0); out.print("\\n");
    out.print("coverFilter="); out.print(static_cast<int>(SETTINGS.sleepScreenCoverFilter)); out.print("\\n");
  }
  out.print("absolute="); out.print(absolute ? 1 : 0); out.print("\\n");
  out.print("format=raw 1bpp physical framebuffer stages: bw/lsb/msb\\n");
  out.close();
}

struct BitmapPlacement {""")

# Standard/cover/custom bitmap: dump BW after Absolute capability is selected,
# but before the display base waveform is sent.
rep("""  const bool absolute =
      hasGreyscale && renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();
  if (absolute) {""",
"""  const bool absolute =
      hasGreyscale && renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();
  writeSleepDiagMeta177(renderer, &bitmap, preserveBackground, hasGreyscale, absolute);
  dumpSleepDiagPlane177("/sleepdiag/cphun177_bitmap_bw.bin", renderer);
  if (absolute) {""", 1)

rep("""      renderer.clearScreen(absolute ? 0xFF : 0x00);
      renderer.setRenderMode(plane);
      renderer.drawBitmap(bitmap, x, y, pageWidth, pageHeight, cropX, cropY);
      if (plane == GfxRenderer::GRAYSCALE_LSB)
        renderer.copyGrayscaleLsbBuffers();
      else
        renderer.copyGrayscaleMsbBuffers();
""",
"""      renderer.clearScreen(absolute ? 0xFF : 0x00);
      renderer.setRenderMode(plane);
      renderer.drawBitmap(bitmap, x, y, pageWidth, pageHeight, cropX, cropY);
      if (plane == GfxRenderer::GRAYSCALE_LSB) {
        dumpSleepDiagPlane177("/sleepdiag/cphun177_bitmap_lsb.bin", renderer);
        renderer.copyGrayscaleLsbBuffers();
      } else {
        dumpSleepDiagPlane177("/sleepdiag/cphun177_bitmap_msb.bin", renderer);
        renderer.copyGrayscaleMsbBuffers();
      }
""", 1)

# Transparent alpha BMP: dump all three stages as well.
rep("""  const bool absolute = renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();
  if (absolute) {
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return AlphaOverlayResult::Error;
""",
"""  const bool absolute = renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();
  writeSleepDiagMeta177(renderer, nullptr, true, true, absolute);
  dumpSleepDiagPlane177("/sleepdiag/cphun177_overlaybmp_bw.bin", renderer);
  if (absolute) {
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return AlphaOverlayResult::Error;
""", 1)

rep("""  renderer.copyGrayscaleLsbBuffers();

  if (!absolute) renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
""",
"""  dumpSleepDiagPlane177("/sleepdiag/cphun177_overlaybmp_lsb.bin", renderer);
  renderer.copyGrayscaleLsbBuffers();

  if (!absolute) renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
""", 1)

# First matching MSB copy after alpha-BMP function.
rep("""  renderer.copyGrayscaleMsbBuffers();

  renderer.displayGrayBuffer();
  renderer.setRenderMode(GfxRenderer::BW);
  return AlphaOverlayResult::Rendered;
}""",
"""  dumpSleepDiagPlane177("/sleepdiag/cphun177_overlaybmp_msb.bin", renderer);
  renderer.copyGrayscaleMsbBuffers();

  renderer.displayGrayBuffer();
  renderer.setRenderMode(GfxRenderer::BW);
  return AlphaOverlayResult::Rendered;
}""", 1)

# Transparent PNG: scope replacements to its function to avoid touching BMP.
marker = "bool SleepActivity::renderTransparentOverlayPng"
pos = s.index(marker)
head, tail = s[:pos], s[pos:]

old = """  const bool absolute = renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();
  if (absolute) {
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return false;
"""
if old not in tail:
    raise SystemExit("CPHUN-177 sleepdiag PNG base anchor missing")
tail = tail.replace(old,
"""  const bool absolute = renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();
  writeSleepDiagMeta177(renderer, nullptr, true, true, absolute);
  dumpSleepDiagPlane177("/sleepdiag/cphun177_overlaypng_bw.bin", renderer);
  if (absolute) {
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return false;
""", 1)

old = """  renderer.copyGrayscaleLsbBuffers();

  if (!absolute) renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
"""
if old not in tail:
    raise SystemExit("CPHUN-177 sleepdiag PNG LSB anchor missing")
tail = tail.replace(old,
"""  dumpSleepDiagPlane177("/sleepdiag/cphun177_overlaypng_lsb.bin", renderer);
  renderer.copyGrayscaleLsbBuffers();

  if (!absolute) renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
""", 1)

old = """  renderer.copyGrayscaleMsbBuffers();

  renderer.displayGrayBuffer();
  renderer.setRenderMode(GfxRenderer::BW);
  return true;
}"""
if old not in tail:
    raise SystemExit("CPHUN-177 sleepdiag PNG MSB anchor missing")
tail = tail.replace(old,
"""  dumpSleepDiagPlane177("/sleepdiag/cphun177_overlaypng_msb.bin", renderer);
  renderer.copyGrayscaleMsbBuffers();

  renderer.displayGrayBuffer();
  renderer.setRenderMode(GfxRenderer::BW);
  return true;
}""", 1)

s = head + tail
p.write_text(s, encoding="utf-8")
print("CPHUN-177 sleep framebuffer diagnostics applied")
