#!/usr/bin/env python3
from pathlib import Path

p = Path("src/activities/boot_sleep/SleepActivity.cpp")
s = p.read_text(encoding="utf-8")

def rep(old, new, count=1):
    global s
    if old not in s:
        raise SystemExit("CPHUN-169 sleepdiag anchor missing: " + old[:120].replace("\n","\\n"))
    s = s.replace(old, new, count)

rep("""constexpr uint8_t MIN_VISIBLE_ALPHA = 8;

struct BitmapPlacement {""",
"""constexpr uint8_t MIN_VISIBLE_ALPHA = 8;

// CPHUN-169 Experimental: exact sleep-screen framebuffer diagnostics.
// These dumps do not alter rendering; they copy the already prepared 1-bit
// framebuffers immediately before they are handed to the grayscale pipeline.
bool dumpSleepDiagPlane(const char* path, const GfxRenderer& renderer) {
  if (!Storage.ensureDirectoryExists("/sleepdiag")) {
    LOG_ERR("SLP", "sleepdiag: failed to create /sleepdiag");
    return false;
  }
  const uint8_t* data = renderer.getWriteTarget();
  const size_t size = renderer.getBufferSize();
  if (!data || size == 0) {
    LOG_ERR("SLP", "sleepdiag: framebuffer unavailable");
    return false;
  }
  HalFile out;
  if (!Storage.openFileForWrite("SLP", path, out)) {
    LOG_ERR("SLP", "sleepdiag: cannot open %s", path);
    return false;
  }
  const bool ok = out.write(data, size) == size;
  out.close();
  if (!ok) LOG_ERR("SLP", "sleepdiag: short write %s", path);
  return ok;
}

void writeSleepDiagMeta(const GfxRenderer& renderer) {
  if (!Storage.ensureDirectoryExists("/sleepdiag")) return;
  HalFile out;
  if (!Storage.openFileForWrite("SLP", "/sleepdiag/cphun169_info.txt", out)) return;
  out.print("build=CPHUN-169-EXPERIMENTAL-SLEEPDIAG\\n");
  out.print("width="); out.print(renderer.getDisplayWidth()); out.print("\\n");
  out.print("height="); out.print(renderer.getDisplayHeight()); out.print("\\n");
  out.print("width_bytes="); out.print(renderer.getDisplayWidthBytes()); out.print("\\n");
  out.print("buffer_bytes="); out.print(renderer.getBufferSize()); out.print("\\n");
  out.print("format=raw 1bpp physical framebuffer, three stages: bw/lsb/msb\\n");
  out.close();
}

struct BitmapPlacement {""")

# Transparent alpha BMP
rep("""  if (!renderTransparentOverlayPass(file, info, placement, renderer, row.get(), TransparentOverlayPass::BW))
    return AlphaOverlayResult::Error;
  renderer.displayGrayscaleBase(HalDisplay::HALF_REFRESH);
""",
"""  if (!renderTransparentOverlayPass(file, info, placement, renderer, row.get(), TransparentOverlayPass::BW))
    return AlphaOverlayResult::Error;
  writeSleepDiagMeta(renderer);
  dumpSleepDiagPlane("/sleepdiag/cphun169_overlaybmp_bw.bin", renderer);
  renderer.displayGrayscaleBase(HalDisplay::HALF_REFRESH);
""")
rep("""  renderer.copyGrayscaleLsbBuffers();

  renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
  if (!renderTransparentOverlayPass(file, info, placement, renderer, row.get(), TransparentOverlayPass::GrayscaleMsb)) {""",
"""  dumpSleepDiagPlane("/sleepdiag/cphun169_overlaybmp_lsb.bin", renderer);
  renderer.copyGrayscaleLsbBuffers();

  renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
  if (!renderTransparentOverlayPass(file, info, placement, renderer, row.get(), TransparentOverlayPass::GrayscaleMsb)) {""")
rep("""  renderer.copyGrayscaleMsbBuffers();

  renderer.displayGrayBuffer();
  renderer.setRenderMode(GfxRenderer::BW);
  return AlphaOverlayResult::Rendered;
}""",
"""  dumpSleepDiagPlane("/sleepdiag/cphun169_overlaybmp_msb.bin", renderer);
  renderer.copyGrayscaleMsbBuffers();

  renderer.displayGrayBuffer();
  renderer.setRenderMode(GfxRenderer::BW);
  return AlphaOverlayResult::Rendered;
}""", 1)

# Standard/cover/regular BMP sleep image
rep("""  if (hasGreyscale) {
    // OEM grayscale pipeline base. Must stay HALF: the gray nudge LUT is""",
"""  // Always dump the prepared BW framebuffer for regular/cover/custom bitmap sleep screens,
  // even when the image will not enter the grayscale-plane path.
  writeSleepDiagMeta(renderer, &bitmap, preserveBackground, hasGreyscale);
  dumpSleepDiagPlane("/sleepdiag/cphun169_bitmap_bw.bin", renderer);

  if (hasGreyscale) {
    // OEM grayscale pipeline base. Must stay HALF: the gray nudge LUT is""")
rep("""      renderer.setRenderMode(plane);
      renderer.drawBitmap(bitmap, x, y, pageWidth, pageHeight, cropX, cropY);
      if (plane == GfxRenderer::GRAYSCALE_LSB)
        renderer.copyGrayscaleLsbBuffers();
      else
        renderer.copyGrayscaleMsbBuffers();
""",
"""      renderer.setRenderMode(plane);
      renderer.drawBitmap(bitmap, x, y, pageWidth, pageHeight, cropX, cropY);
      if (plane == GfxRenderer::GRAYSCALE_LSB) {
        dumpSleepDiagPlane("/sleepdiag/cphun169_bitmap_lsb.bin", renderer);
        renderer.copyGrayscaleLsbBuffers();
      } else {
        dumpSleepDiagPlane("/sleepdiag/cphun169_bitmap_msb.bin", renderer);
        renderer.copyGrayscaleMsbBuffers();
      }
""")

# Transparent PNG overlay
rep("""  if (!converter.decodeToFramebuffer(path, renderer, config)) return false;
  renderer.displayGrayscaleBase(HalDisplay::HALF_REFRESH);
""",
"""  if (!converter.decodeToFramebuffer(path, renderer, config)) return false;
  writeSleepDiagMeta(renderer);
  dumpSleepDiagPlane("/sleepdiag/cphun169_overlaypng_bw.bin", renderer);
  renderer.displayGrayscaleBase(HalDisplay::HALF_REFRESH);
""")
# Scope remaining two PNG copy anchors by working from PNG function.
start = s.index("bool SleepActivity::renderTransparentOverlayPng")
head, tail = s[:start], s[start:]
old = """  renderer.copyGrayscaleLsbBuffers();

  renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
"""
if old not in tail:
    raise SystemExit("CPHUN-169 sleepdiag PNG LSB anchor missing")
tail = tail.replace(old,
"""  dumpSleepDiagPlane("/sleepdiag/cphun169_overlaypng_lsb.bin", renderer);
  renderer.copyGrayscaleLsbBuffers();

  renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
""", 1)
old2 = """  renderer.copyGrayscaleMsbBuffers();

  renderer.displayGrayBuffer();
  renderer.setRenderMode(GfxRenderer::BW);
  return true;
}"""
if old2 not in tail:
    raise SystemExit("CPHUN-169 sleepdiag PNG MSB anchor missing")
tail = tail.replace(old2,
"""  dumpSleepDiagPlane("/sleepdiag/cphun169_overlaypng_msb.bin", renderer);
  renderer.copyGrayscaleMsbBuffers();

  renderer.displayGrayBuffer();
  renderer.setRenderMode(GfxRenderer::BW);
  return true;
}""", 1)
s = head + tail

p.write_text(s, encoding="utf-8")
print("CPHUN-169 Experimental sleep grayscale diagnostics applied")
