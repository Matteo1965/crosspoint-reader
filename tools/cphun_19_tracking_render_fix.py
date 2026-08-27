from pathlib import Path

p = Path('lib/Epub/Epub/blocks/TextBlock.cpp')
s = p.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected 1 marker, found {n}')
    s = s.replace(old, new, 1)

replace_once(
    '#include <Serialization.h>\n\n#include <cstring>\n',
    '#include <Serialization.h>\n#include <Utf8.h>\n\n#include <cstring>\n',
    'Utf8 include',
)

replace_once(
    '#include "../../../../src/fontIds.h"\n\nsize_t TextBlock::arenaSize',
    '''#include "../../../../src/fontIds.h"\n\nnamespace {\n\nuint32_t countCodepoints(const char* text) {\n  if (text == nullptr) return 0;\n  const auto* cursor = reinterpret_cast<const uint8_t*>(text);\n  uint32_t count = 0;\n  while (*cursor) {\n    if (utf8NextCodepoint(&cursor) == 0) break;\n    ++count;\n  }\n  return count;\n}\n\nvoid drawTrackedText(const GfxRenderer& renderer, const int fontId, const int x, const int y, const char* text,\n                     const EpdFontFamily::Style style, const BidiUtils::BidiBaseDir baseDir,\n                     const uint8_t letterSpacingPx) {\n  if (letterSpacingPx == 0 || text == nullptr || *text == '\\0') {\n    renderer.drawText(fontId, x, y, text, true, style, baseDir);\n    return;\n  }\n\n  // ParsedText enables tracking only on pure-LTR justified lines. Render one\n  // codepoint at a time so the physical glyph positions match the +1 px per\n  // internal pair already reserved by layout, while preserving pair kerning.\n  const auto* cursor = reinterpret_cast<const uint8_t*>(text);\n  int penX = x;\n  uint32_t previous = 0;\n  while (*cursor) {\n    const auto* glyphStart = cursor;\n    const uint32_t cp = utf8NextCodepoint(&cursor);\n    if (cp == 0) break;\n\n    if (previous != 0) {\n      penX += renderer.getKerning(fontId, previous, cp, style) + letterSpacingPx;\n    }\n\n    const size_t glyphBytes = static_cast<size_t>(cursor - glyphStart);\n    char glyphText[5];\n    memcpy(glyphText, glyphStart, glyphBytes);\n    glyphText[glyphBytes] = '\\0';\n    renderer.drawText(fontId, penX, y, glyphText, true, style, baseDir);\n    penX += renderer.getTextAdvanceX(fontId, glyphText, style);\n    previous = cp;\n  }\n}\n\n}  // namespace\n\nsize_t TextBlock::arenaSize''',
    'tracking helper',
)

replace_once(
    '''    bidiDir[i] = static_cast<uint8_t>(BidiUtils::detectParagraphLevel(words[i].c_str(), blockStyle.isRtl ? 1 : 0));\n    memcpy(text + off, words[i].data(), words[i].size());''',
    '''    bidiDir[i] = static_cast<uint8_t>(BidiUtils::detectParagraphLevel(words[i].c_str(), blockStyle.isRtl ? 1 : 0));\n    if (letterSpacingPx != 0) bidiDir[i] |= 0x80;\n    memcpy(text + off, words[i].data(), words[i].size());''',
    'cache tracking flag',
)

replace_once(
    '''      renderer.drawText(fontId, xposArr[i] + x, y, wordText(i), true, wordStyle(i), baseDir);''',
    '''      drawTrackedText(renderer, fontId, xposArr[i] + x, y, wordText(i), wordStyle(i), baseDir, letterSpacingPx);''',
    'simple render tracking',
)

replace_once(
    '''    } else {\n      renderer.drawText(fontId, drawX, wordY, word, true, currentStyle, baseDir);\n    }''',
    '''    } else {\n      drawTrackedText(renderer, fontId, drawX, wordY, word, currentStyle, baseDir, letterSpacingPx);\n    }''',
    'complex render tracking',
)

replace_once(
    '''      int lineWidth = renderer.getTextWidth(fontId, word, currentStyle, baseDir);\n\n      if ((currentStyle & (EpdFontFamily::SUP | EpdFontFamily::SUB)) != 0) {''',
    '''      int lineWidth = renderer.getTextWidth(fontId, word, currentStyle, baseDir);\n      const uint32_t cps = countCodepoints(word);\n      if (letterSpacingPx != 0 && cps > 1) {\n        lineWidth += static_cast<int>(cps - 1) * letterSpacingPx;\n      }\n\n      if ((currentStyle & (EpdFontFamily::SUP | EpdFontFamily::SUB)) != 0) {''',
    'decoration tracking width',
)

replace_once(
    '''        lineWidth = renderer.getTextWidth(fontId, visibleText, currentStyle, baseDir);\n        if ((currentStyle & (EpdFontFamily::SUP | EpdFontFamily::SUB)) != 0) {''',
    '''        lineWidth = renderer.getTextWidth(fontId, visibleText, currentStyle, baseDir);\n        const uint32_t visibleCps = countCodepoints(visibleText);\n        if (letterSpacingPx != 0 && visibleCps > 1) {\n          lineWidth += static_cast<int>(visibleCps - 1) * letterSpacingPx;\n        }\n        if ((currentStyle & (EpdFontFamily::SUP | EpdFontFamily::SUB)) != 0) {''',
    'visible decoration tracking width',
)

replace_once(
    '''    block->bindArenaPointers();\n\n    // Validate offsets before anything dereferences wordText():''',
    '''    block->bindArenaPointers();\n    // Backward-compatible cache packing: old caches have only 0/1 here, new\n    // caches use the high bit to persist the line's 1 px tracking flag.\n    block->letterSpacingPx = (block->bidiDirArr[0] & 0x80) != 0 ? 1 : 0;\n\n    // Validate offsets before anything dereferences wordText():''',
    'deserialize tracking flag',
)

p.write_text(s, encoding='utf-8')
print('Applied CPHUN-260827-19 tracking render/cache fix')
