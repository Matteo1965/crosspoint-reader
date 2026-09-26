#pragma once

#include <cstdint>

// Only use a visually equivalent character from the CURRENT font when its
// Unicode counterpart is missing. The original EPUB codepoint is never changed.
namespace ReaderGlyphFallback {
template <typename HasGlyph>
uint32_t localSubstitute(const uint32_t cp, const HasGlyph& hasGlyph) {
  // Mathematical minus (U+2212): Bitter's own en dash is a suitable display
  // fallback. Preserve true minus whenever the font contains it.
  if (cp == 0x2212 && !hasGlyph(cp) && hasGlyph(0x2013)) return 0x2013;
  return cp;
}
}  // namespace ReaderGlyphFallback
