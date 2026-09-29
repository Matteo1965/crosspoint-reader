#!/usr/bin/env python3
from pathlib import Path

def rep(path, old, new, n=1, require_unique=True):
    p=Path(path); s=p.read_text(encoding="utf-8")
    if old not in s:
        raise SystemExit(f"CPHUN-177 anchor missing: {path}: {old[:100]!r}")
    if require_unique and s.count(old)!=1:
        raise SystemExit(f"CPHUN-177 anchor not unique: {path}: {old[:100]!r}")
    p.write_text(s.replace(old,new,n),encoding="utf-8")

# ---- HAL capability bridge -------------------------------------------------
rep("lib/hal/HalDisplay.h",
"""#include <Arduino.h>
#include <EInkDisplay.h>
""",
"""#include <Arduino.h>
#include <BoardConfig.h>
#include <EInkDisplay.h>
""")
rep("lib/hal/HalDisplay.h",
"""class HalDisplay {
 public:
  // Constructor with pin configuration
""",
"""class HalDisplay {
 public:
  using Controller = BoardConfig::DisplayController;
  using GrayscaleMode = freeink::GrayscaleMode;
  using GrayscaleCapabilities = freeink::GrayscaleCapabilities;
  using GrayscaleBase = freeink::GrayscaleBase;
  using GrayscaleEncoding = freeink::GrayscaleEncoding;

  Controller getController() const;
  GrayscaleCapabilities grayscaleCapabilities(GrayscaleMode mode = GrayscaleMode::Overlay) const;

  // Constructor with pin configuration
""")
rep("lib/hal/HalDisplay.h",
"""  void displayGrayscaleBase(RefreshMode fallback = HALF_REFRESH, bool turnOffScreen = false);

  void copyGrayscaleBuffers""",
"""  void displayGrayscaleBase(RefreshMode fallback = HALF_REFRESH, bool turnOffScreen = false);
  bool displayGrayscaleBase(GrayscaleMode mode, RefreshMode fallback = HALF_REFRESH, bool turnOffScreen = false);

  void copyGrayscaleBuffers""")
rep("lib/hal/HalDisplay.cpp",
"""HalDisplay::~HalDisplay() {}

void HalDisplay::begin""",
"""HalDisplay::~HalDisplay() {}

HalDisplay::Controller HalDisplay::getController() const { return BoardConfig::ACTIVE.displayController; }

HalDisplay::GrayscaleCapabilities HalDisplay::grayscaleCapabilities(GrayscaleMode mode) const {
  return einkDisplay.grayscaleCapabilities(mode);
}

void HalDisplay::begin""")
rep("lib/hal/HalDisplay.cpp",
"""void HalDisplay::displayGrayscaleBase(RefreshMode fallback, bool turnOffScreen) {
""",
"""bool HalDisplay::displayGrayscaleBase(GrayscaleMode mode, RefreshMode fallback, bool turnOffScreen) {
  if (gpio.deviceIsX3() && fallback == RefreshMode::HALF_REFRESH) einkDisplay.requestResync(1);
  return einkDisplay.displayGrayscaleBase(mode, convertRefreshMode(fallback), turnOffScreen);
}

void HalDisplay::displayGrayscaleBase(RefreshMode fallback, bool turnOffScreen) {
""")
rep("lib/hal/HalDisplay.cpp",
"""bool HalDisplay::supportsStripGrayscale() const { return einkDisplay.supportsStripGrayscale(); }

bool HalDisplay::combinesGrayscaleBase() const { return einkDisplay.combinesGrayscaleBase(); }
""",
"""bool HalDisplay::supportsStripGrayscale() const { return grayscaleCapabilities().stripUploads; }

bool HalDisplay::combinesGrayscaleBase() const {
  return grayscaleCapabilities().base == GrayscaleBase::Combined;
}
""")

# ---- Plane encoding helper -------------------------------------------------
rep("lib/GfxRenderer/BitmapHelpers.h",
"""int adjustPixel(int gray);

enum class BmpRowOrder""",
"""int adjustPixel(int gray);

struct GrayPlanePixel {
  bool write;
  bool black;
};

// level: 0 black, 1 dark, 2 light, 3 white.
constexpr GrayPlanePixel grayPlanePixel(uint8_t level, bool msb, bool absolute) {
  if (absolute) return {true, !(level == 3 || level == (msb ? 2 : 1))};
  return {msb ? (level == 1 || level == 2) : level == 1, false};
}

enum class BmpRowOrder""")

# ---- Renderer absolute-plane state ----------------------------------------
rep("lib/GfxRenderer/GfxRenderer.h",
"""  RenderMode renderMode;
  Orientation orientation;
""",
"""  RenderMode renderMode;
  mutable bool absoluteGrayPlanes = false;
  Orientation orientation;
""")
rep("lib/GfxRenderer/GfxRenderer.h",
"""  bool supportsAsyncRefresh() const;
""",
"""  bool supportsAsyncRefresh() const;
  HalDisplay::GrayscaleCapabilities grayscaleCapabilities(
      HalDisplay::GrayscaleMode mode = HalDisplay::GrayscaleMode::Overlay) const;
""")
rep("lib/GfxRenderer/GfxRenderer.h",
"""  void setRenderMode(const RenderMode mode) { this->renderMode = mode; }
  RenderMode getRenderMode() const { return renderMode; }
""",
"""  void setRenderMode(RenderMode mode);
  RenderMode getRenderMode() const { return renderMode; }
""")
rep("lib/GfxRenderer/GfxRenderer.h",
"""  void displayGrayscaleBase(HalDisplay::RefreshMode fallback = HalDisplay::HALF_REFRESH) const;
  void copyGrayscaleLsbBuffers() const;
""",
"""  void displayGrayscaleBase(HalDisplay::RefreshMode fallback = HalDisplay::HALF_REFRESH) const;
  bool displayGrayscaleBase(HalDisplay::GrayscaleMode mode,
                            HalDisplay::RefreshMode fallback = HalDisplay::HALF_REFRESH) const;
  void copyGrayscaleLsbBuffers() const;
""")
rep("lib/GfxRenderer/GfxRenderer.h",
"""  void displayGrayBuffer() const;

  // Tiled grayscale""",
"""  void displayGrayBuffer() const;
  bool grayPlanesAreAbsolute() const { return absoluteGrayPlanes; }

  // Tiled grayscale""")

rep("lib/GfxRenderer/GfxRenderer.cpp",
"""bool GfxRenderer::supportsAsyncRefresh() const { return !fadingFix && display.supportsAsyncRefresh(); }
""",
"""bool GfxRenderer::supportsAsyncRefresh() const { return !fadingFix && display.supportsAsyncRefresh(); }

HalDisplay::GrayscaleCapabilities GfxRenderer::grayscaleCapabilities(HalDisplay::GrayscaleMode mode) const {
  auto caps = display.grayscaleCapabilities(mode);
  if (fadingFix) caps.asyncBase = false;
  return caps;
}
""")
rep("lib/GfxRenderer/GfxRenderer.cpp",
"""      if (renderMode == BW && val < 3) {
        drawPixel(screenX, screenY);
      } else if (renderMode == GRAYSCALE_MSB && (val == 1 || val == 2)) {
        drawPixel(screenX, screenY, false);
      } else if (renderMode == GRAYSCALE_LSB && val == 1) {
        drawPixel(screenX, screenY, false);
      }
""",
"""      if (renderMode == BW && val < 3) {
        drawPixel(screenX, screenY);
      } else if (renderMode == GRAYSCALE_LSB || renderMode == GRAYSCALE_MSB) {
        const auto pixel = grayPlanePixel(val, renderMode == GRAYSCALE_MSB, absoluteGrayPlanes);
        if (pixel.write) drawPixel(screenX, screenY, pixel.black);
      }
""")
rep("lib/GfxRenderer/GfxRenderer.cpp",
"""void GfxRenderer::displayGrayscaleBase(HalDisplay::RefreshMode fallback) const {
  display.displayGrayscaleBase(fallback, fadingFix);
}
""",
"""void GfxRenderer::displayGrayscaleBase(HalDisplay::RefreshMode fallback) const {
  absoluteGrayPlanes = false;
  display.displayGrayscaleBase(fallback, fadingFix);
}

bool GfxRenderer::displayGrayscaleBase(HalDisplay::GrayscaleMode mode, HalDisplay::RefreshMode fallback) const {
  absoluteGrayPlanes = false;
  if (!display.displayGrayscaleBase(mode, fallback, fadingFix)) return false;
  absoluteGrayPlanes = mode == HalDisplay::GrayscaleMode::Absolute;
  return true;
}
""")
rep("lib/GfxRenderer/GfxRenderer.cpp",
"""void GfxRenderer::displayGrayBuffer() const { display.displayGrayBuffer(fadingFix); }
""",
"""void GfxRenderer::displayGrayBuffer() const {
  display.displayGrayBuffer(fadingFix);
  absoluteGrayPlanes = false;
}

void GfxRenderer::setRenderMode(RenderMode mode) {
  if (mode == BW && absoluteGrayPlanes) {
    display.cleanupGrayscaleBuffers(nullptr);
    absoluteGrayPlanes = false;
  }
  renderMode = mode;
}
""")

# ---- Direct PNG/JPEG framebuffer writer -----------------------------------
rep("lib/Epub/Epub/converters/DirectPixelWriter.h",
"""#pragma once

#include <GfxRenderer.h>
""",
"""#pragma once

#include <BitmapHelpers.h>
#include <GfxRenderer.h>
""")
rep("lib/Epub/Epub/converters/DirectPixelWriter.h",
"""  GfxRenderer::RenderMode mode;
  uint16_t displayWidthBytes;""",
"""  GfxRenderer::RenderMode mode;
  bool absolute = false;
  uint16_t displayWidthBytes;""")
rep("lib/Epub/Epub/converters/DirectPixelWriter.h",
"""    mode = renderer.getRenderMode();
    displayWidthBytes""",
"""    mode = renderer.getRenderMode();
    absolute = renderer.grayPlanesAreAbsolute();
    displayWidthBytes""")
rep("lib/Epub/Epub/converters/DirectPixelWriter.h",
"""      case GfxRenderer::GRAYSCALE_MSB:
        draw = (pixelValue == 1 || pixelValue == 2);
        state = false;
        break;
      case GfxRenderer::GRAYSCALE_LSB:
        draw = (pixelValue == 1);
        state = false;
        break;
""",
"""      case GfxRenderer::GRAYSCALE_MSB:
      case GfxRenderer::GRAYSCALE_LSB: {
        const auto pixel = grayPlanePixel(pixelValue, mode == GfxRenderer::GRAYSCALE_MSB, absolute);
        draw = pixel.write;
        state = pixel.black;
        break;
      }
""")

# ---- Sleep screen: enable absolute mode on X4 SSD1677 ----------------------
rep("src/activities/boot_sleep/SleepActivity.cpp",
"""#include <Epub.h>
""",
"""#include <BitmapHelpers.h>
#include <Epub.h>
""")
rep("src/activities/boot_sleep/SleepActivity.cpp",
"""        case TransparentOverlayPass::GrayscaleLsb:
          if (level == 1) renderer.drawPixel(screenX, screenY, false);
          break;
        case TransparentOverlayPass::GrayscaleMsb:
          if (level == 1 || level == 2) renderer.drawPixel(screenX, screenY, false);
          break;
""",
"""        case TransparentOverlayPass::GrayscaleLsb:
        case TransparentOverlayPass::GrayscaleMsb: {
          const auto planePixel =
              grayPlanePixel(level, pass == TransparentOverlayPass::GrayscaleMsb, renderer.grayPlanesAreAbsolute());
          if (planePixel.write) renderer.drawPixel(screenX, screenY, planePixel.black);
          break;
        }
""")
rep("src/activities/boot_sleep/SleepActivity.cpp",
"""  renderer.displayGrayscaleBase(HalDisplay::HALF_REFRESH);

  renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_LSB);
""",
"""  const bool absolute = renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();
  if (absolute) {
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return AlphaOverlayResult::Error;
  } else {
    renderer.displayGrayscaleBase(HalDisplay::HALF_REFRESH);
  }

  if (!absolute) renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_LSB);
""",1,False)
rep("src/activities/boot_sleep/SleepActivity.cpp",
"""  renderer.copyGrayscaleLsbBuffers();

  renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
""",
"""  renderer.copyGrayscaleLsbBuffers();

  if (!absolute) renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
""",1)

# Bitmap sleep screen: absolute base and absolute plane buffers.
old_comment="""// CPHUN-176: upstream #3541's Direct/Absolute grayscale branch depends on
// the capability consolidation introduced by #3478. The independent #3541
// quantization/transparency fixes are backported now; this existing HALF-base
// pipeline is intentionally retained until #3478 is integrated next.
"""
rep("src/activities/boot_sleep/SleepActivity.cpp", old_comment, "")
rep("src/activities/boot_sleep/SleepActivity.cpp",
"""  if (hasGreyscale) {
    // OEM grayscale pipeline base. Must stay HALF: the gray nudge LUT is
""",
"""  const bool absolute =
      hasGreyscale && renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();
  if (absolute) {
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return;
  } else if (hasGreyscale) {
    // OEM grayscale pipeline base. Must stay HALF: the gray nudge LUT is
""")
rep("src/activities/boot_sleep/SleepActivity.cpp",
"""      renderer.clearScreen(0x00);
      renderer.setRenderMode(plane);
""",
"""      renderer.clearScreen(absolute ? 0xFF : 0x00);
      renderer.setRenderMode(plane);
""",1)

# PNG transparent overlay: second absolute-base site.
needle="""  if (!converter.decodeToFramebuffer(path, renderer, config)) return false;
  renderer.displayGrayscaleBase(HalDisplay::HALF_REFRESH);

  renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_LSB);
"""
rep("src/activities/boot_sleep/SleepActivity.cpp",needle,
"""  if (!converter.decodeToFramebuffer(path, renderer, config)) return false;
  const bool absolute = renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();
  if (absolute) {
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return false;
  } else {
    renderer.displayGrayscaleBase(HalDisplay::HALF_REFRESH);
  }

  if (!absolute) renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_LSB);
""")
# Replace only following PNG MSB clear remaining after this area; last occurrence.
p=Path("src/activities/boot_sleep/SleepActivity.cpp"); s=p.read_text(encoding="utf-8")
marker="bool SleepActivity::renderTransparentOverlayPng"
pos=s.index(marker)
tail=s[pos:]
old="""  renderer.copyGrayscaleLsbBuffers();

  renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
"""
if old not in tail: raise SystemExit("CPHUN-177 PNG MSB clear anchor missing")
tail=tail.replace(old,
"""  renderer.copyGrayscaleLsbBuffers();

  if (!absolute) renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
""",1)
p.write_text(s[:pos]+tail,encoding="utf-8")

print("CPHUN-177 application-side absolute grayscale core applied")
