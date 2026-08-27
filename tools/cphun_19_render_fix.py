from pathlib import Path

p = Path('lib/Epub/Epub/blocks/TextBlock.cpp')
s = p.read_text(encoding='utf-8')
old = '''namespace {
void drawTrackedLtrWord(const GfxRenderer& renderer, const int fontId, int x, const int y, const char* text,
                        const EpdFontFamily::Style style, const BidiUtils::BidiBaseDir baseDir,
                        const uint8_t letterSpacingPx) {
  const auto* ptr = reinterpret_cast<const unsigned char*>(text);
  while (*ptr) {
    const auto* start = ptr;
    const uint32_t cp = utf8NextCodepoint(&ptr);
    const size_t len = static_cast<size_t>(ptr - start);
    char glyph[5] = {};
    memcpy(glyph, start, std::min<size_t>(len, 4));
    renderer.drawText(fontId, x, y, glyph, true, style, baseDir);
    if (*ptr) {
      const auto* peek = ptr;
      const uint32_t nextCp = utf8NextCodepoint(&peek);
      x += renderer.getTextAdvanceX(fontId, glyph, style);
      x += renderer.getKerning(fontId, cp, nextCp, style);
      x += letterSpacingPx;
    }
  }
}
}  // namespace
'''
new = '''namespace {
void drawTrackedLtrWord(const GfxRenderer& renderer, const int fontId, int x, const int y, const char* text,
                        const EpdFontFamily::Style style, const BidiUtils::BidiBaseDir baseDir,
                        const uint8_t letterSpacingPx) {
  const char* ptr = text;
  while (*ptr) {
    const char* start = ptr;
    const uint32_t cp = utf8NextCodepoint(&ptr);
    const size_t len = static_cast<size_t>(ptr - start);
    char glyph[5] = {};
    memcpy(glyph, start, std::min<size_t>(len, 4));
    renderer.drawText(fontId, x, y, glyph, true, style, baseDir);
    if (*ptr) {
      const char* peek = ptr;
      const uint32_t nextCp = utf8NextCodepoint(&peek);
      x += renderer.getTextAdvanceX(fontId, glyph, style);
      x += renderer.getKerning(fontId, cp, nextCp, style);
      x += letterSpacingPx;
    }
  }
}
}  // namespace
'''
if s.count(old) != 1:
    raise SystemExit(f'tracked renderer marker: expected 1, found {s.count(old)}')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
