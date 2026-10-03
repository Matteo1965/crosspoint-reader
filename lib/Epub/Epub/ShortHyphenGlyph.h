#pragma once

#include <GfxRenderer.h>

namespace short_hyphen {

struct Glyph {
  const char* utf8;
  uint32_t codepoint;
};

inline Glyph select(const GfxRenderer& renderer, const int fontId,
                    const EpdFontFamily::Style style) {
  const auto it = renderer.getFontMap().find(fontId);
  if (it != renderer.getFontMap().end()) {
    if (it->second.getGlyph(0x2011, style)) return {"\xE2\x80\x91", 0x2011};
    if (it->second.getGlyph(0x2010, style)) return {"\xE2\x80\x90", 0x2010};
  }
  return {"-", 0x002D};
}

}  // namespace short_hyphen
