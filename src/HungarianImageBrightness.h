#pragma once

#include <GfxRenderer.h>

#include <algorithm>

#include <cstdint>

namespace HungarianImageBrightness {
inline void apply(GfxRenderer& renderer, int x, int y, int width, int height, uint8_t percent) {
  if (percent == 0 || width <= 0 || height <= 0) return;
  const int threshold = percent >= 20 ? 2 : 1;
  const int x0 = x < 0 ? 0 : x;
  const int y0 = y < 0 ? 0 : y;
  const int x1 = std::min(x + width, renderer.getScreenWidth());
  const int y1 = std::min(y + height, renderer.getScreenHeight());

  // Spatially mix each rendered gray level with white. Existing white pixels
  // stay white; dark/mid pixels are whitened on 10% or 20% of the lattice.
  // This approximates gray' = gray + (white-gray)*p without needing an 8-bit
  // framebuffer and works in BW plus both grayscale planes/strip targets.
  for (int py = y0; py < y1; ++py) {
    for (int px = x0; px < x1; ++px) {
      if (((px * 3 + py * 7) % 10) < threshold) renderer.drawPixel(px, py, false);
    }
  }
}
}  // namespace HungarianImageBrightness
