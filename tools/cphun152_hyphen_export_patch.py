"""CPHUN-152: short-hyphen fallback for SD fonts and export success toast.

Apply after CPHUN-151 and the complete earlier patch chain.
"""
from pathlib import Path


def once(path, old, new, description):
    file = Path(path)
    source = file.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-152 {description}: expected one match, got {count}")
    file.write_text(source.replace(old, new, 1), encoding="utf-8")


# Resolve the same glyph and advance in BOTH layout and rendering. If an SD
# font lacks U+2011, try U+2010 and finally the ordinary hyphen U+002D.
# The metadata check is style-specific, so bold/italic variants can fall back
# independently. All three candidates are prewarmed during paragraph layout.
glyph_helper = r'''#pragma once

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
'''
helper_path = Path("lib/Epub/Epub/ShortHyphenGlyph.h")
if helper_path.exists():
    raise SystemExit("CPHUN-152 unexpected preexisting ShortHyphenGlyph.h")
helper_path.write_text(glyph_helper, encoding="utf-8")

parsed = "lib/Epub/Epub/ParsedText.cpp"
once(parsed, '#include "hyphenation/HyphenationCommon.h"',
     '#include "ShortHyphenGlyph.h"\n#include "hyphenation/HyphenationCommon.h"',
     "shared glyph selection include")
once(parsed,
     'constexpr char SHORT_HYPHEN_UTF8[] = "\\xE2\\x80\\x91";',
     '// CPHUN-152: synthetic glyph is selected per font/style via short_hyphen::select().',
     "remove hardcoded U+2011")
once(parsed,
     '  return cp == \'-\' || cp == \'.\' || cp == \',\' || cp == \':\' || cp == \';\' ||\n'
     '         (ParsedText::isShortHyphenEnabled() && cp == 0x2011);',
     '  return cp == \'-\' || cp == \'.\' || cp == \',\' || cp == \':\' || cp == \';\' ||\n'
     '         (ParsedText::isShortHyphenEnabled() && (cp == 0x2011 || cp == 0x2010));',
     "U+2010 optical overhang")
once(parsed,
     '  if (punctuation == 0x2011 && ParsedText::isShortHyphenEnabled()) {\n'
     '    punctuationAdvance = cachedHangingPunctuationAdvance(renderer, fontId, style, punctuation, SHORT_HYPHEN_UTF8);\n'
     '  }',
     '  if (ParsedText::isShortHyphenEnabled()) {\n'
     '    const auto glyph = short_hyphen::select(renderer, fontId, style);\n'
     '    if (punctuation == glyph.codepoint) {\n'
     '      punctuationAdvance = cachedHangingPunctuationAdvance(renderer, fontId, style, punctuation, glyph.utf8);\n'
     '    }\n'
     '  }',
     "accurate optical overhang for fallback glyph")
once(parsed,
     '      sanitized += SHORT_HYPHEN_UTF8;',
     '      sanitized += short_hyphen::select(renderer, fontId, style).utf8;',
     "width measurement uses selected glyph")
once(parsed,
     '      renderer.ensureSdCardFontReady(fontId, SHORT_HYPHEN_UTF8, styleMask);',
     '      renderer.ensureSdCardFontReady(fontId, "\\xE2\\x80\\x91\\xE2\\x80\\x90-", styleMask);',
     "prewarm all fallback candidates")
once(parsed,
     '      words[wordIndex] += SHORT_HYPHEN_UTF8;',
     '      words[wordIndex] += short_hyphen::select(renderer, fontId, style).utf8;',
     "append selected glyph during word split")

textblock = "lib/Epub/Epub/blocks/TextBlock.cpp"
once(textblock, '#include "../ParsedText.h"',
     '#include "../ParsedText.h"\n#include "../ShortHyphenGlyph.h"',
     "shared glyph in TextBlock")
# Preserve optical-margin placement for U+2011, U+2010, and normal-hyphen
# fallback. The chosen UTF-8 sequence is the one written into page data.
a = Path(textblock)
s = a.read_text(encoding="utf-8")
start = s.find('constexpr char SHORT_HYPHEN_UTF8[]')
end = s.find('void drawTrackedText(', start)
if not (0 <= start < end):
    raise SystemExit("CPHUN-152 TextBlock short-hyphen helper anchors missing")
s = s[:start] + r'''bool endsWithSelectedShortHyphen(const char* text, const short_hyphen::Glyph glyph) {
  if (text == nullptr) return false;
  const size_t len = strlen(text);
  const size_t glyphBytes = strlen(glyph.utf8);
  return len >= glyphBytes &&
         memcmp(text + len - glyphBytes, glyph.utf8, glyphBytes) == 0;
}

int trailingShortHyphenInkShift(const GfxRenderer& renderer, const int fontId,
                               const EpdFontFamily::Style style,
                               const short_hyphen::Glyph glyph) {
  const auto it = renderer.getFontMap().find(fontId);
  if (it == renderer.getFontMap().end()) return 0;
  const EpdGlyph* bitmap = it->second.getGlyph(glyph.codepoint, style);
  if (!bitmap) return 0;
  int renderedLeft = bitmap->left;
  if ((style & (EpdFontFamily::SUP | EpdFontFamily::SUB)) != 0) renderedLeft /= 2;
  return -renderedLeft;
}

''' + s[end:]
s = s.replace(
    '  const bool adjustTrailingHyphen = alignTrailingShortHyphenInk && endsWithShortHyphen(text);',
    '  const auto shortGlyph = short_hyphen::select(renderer, fontId, style);\n'
    '  const bool adjustTrailingHyphen =\n'
    '      alignTrailingShortHyphenInk && endsWithSelectedShortHyphen(text, shortGlyph);',
    1,
)
s = s.replace('const std::string prefix(text, len - SHORT_HYPHEN_BYTES);',
              'const std::string prefix(text, len - strlen(shortGlyph.utf8));',1)
s = s.replace('renderer.getTextAdvanceX(fontId, SHORT_HYPHEN_UTF8, style)',
              'renderer.getTextAdvanceX(fontId, shortGlyph.utf8, style)',1)
s = s.replace('trailingShortHyphenInkShift(renderer, fontId, style), y,\n'
              '                      SHORT_HYPHEN_UTF8, true, style, baseDir);',
              'trailingShortHyphenInkShift(renderer, fontId, style, shortGlyph), y,\n'
              '                      shortGlyph.utf8, true, style, baseDir);',1)
s = s.replace('if (adjustTrailingHyphen && cp == 0x2011 && *cursor == 0) {\n'
              '      glyphX += trailingShortHyphenInkShift(renderer, fontId, style);',
              'if (adjustTrailingHyphen && cp == shortGlyph.codepoint && *cursor == 0) {\n'
              '      glyphX += trailingShortHyphenInkShift(renderer, fontId, style, shortGlyph);',1)
if "SHORT_HYPHEN_UTF8" in s or "SHORT_HYPHEN_BYTES" in s:
    raise SystemExit("CPHUN-152 residual hardcoded glyph: " + "\\n".join(
        line for line in s.splitlines() if "SHORT_HYPHEN_" in line))
a.write_text(s, encoding="utf-8")

reader = "src/activities/reader/EpubReaderActivity.cpp"
reader_h = "src/activities/reader/EpubReaderActivity.h"

# The earlier TSV export returns bool. Show the success toast only on true.
# Mirror existing bookmark/dictionary popup lifetime management, without
# showing a confirmation dialog or requiring user interaction.
once(reader_h,
     "  bool showDictionaryMessage = false;",
     "  bool showDictionaryMessage = false;\n"
     "  bool showExportSuccess = false;\n"
     "  unsigned long exportSuccessTime = 0UL;",
     "export toast state")
once(reader,
     '  if (showDictionaryMessage && (millis() - dictionaryMessageTime) >= ReaderUtils::BOOKMARK_MESSAGE_DURATION_MS) {\n'
     '    showDictionaryMessage = false;\n'
     '    requestUpdate();\n'
     '  }',
     '  if (showDictionaryMessage && (millis() - dictionaryMessageTime) >= ReaderUtils::BOOKMARK_MESSAGE_DURATION_MS) {\n'
     '    showDictionaryMessage = false;\n'
     '    requestUpdate();\n'
     '  }\n'
     '  if (showExportSuccess && millis() - exportSuccessTime >= 2000UL) {\n'
     '    showExportSuccess = false;\n'
     '    requestUpdate();\n'
     '  }',
     "two-second timeout")
once(reader,
     '  if (showDictionaryMessage) {\n'
     '    GUI.drawPopup(renderer, tr(STR_DICT_NO_DICT_SET));\n'
     '  }',
     '  if (showDictionaryMessage) {\n'
     '    GUI.drawPopup(renderer, tr(STR_DICT_NO_DICT_SET));\n'
     '  }\n'
     '  if (showExportSuccess) {\n'
     '    GUI.drawPopup(renderer, "Sikeres exportálás.");\n'
     '  }',
     "success popup")
once(reader,
     '      exportEditsTsv();\n'
     '      openReaderMenu(true);',
     '      if (exportEditsTsv()) {\n'
     '        showExportSuccess = true;\n'
     '        exportSuccessTime = millis();\n'
     '      }\n'
     '      requestUpdate();',
     "only show popup after successful export")

once("src/CPHUNBuildId.h",
     '#define CPHUN_BUILD_ID "CPHUN-260925-151-EXP"',
     '#define CPHUN_BUILD_ID "CPHUN-260925-152-EXP"',
     "new build ID")

print("CPHUN-152: per-font short hyphen fallback + 2s export success toast applied")
