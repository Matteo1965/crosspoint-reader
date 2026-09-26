"""CPHUN-163 post-chain safety gates and layout-cache invalidation.

Run after the last tested CPHUN-152 patch chain and the 157/159/160 adapters.
Do not silently ship a firmware that lost the dictionary or glyph changes.
"""
from pathlib import Path
import re

checks = {
    "src/util/Dictionary.cpp": [
        '#include "DictWordEdges.h"',
        "DictWordEdges::trim(word)",
    ],
    "lib/GfxRenderer/GfxRenderer.cpp": [
        "GfxRenderer::ReaderGlyphChoice GfxRenderer::chooseReaderGlyph(",
        "ReaderGlyphFallback::localSubstitute(",
        "if (readerGlyphFallbackEnabled_)",
        "const auto choice = chooseReaderGlyph(resolvedFontId, cp, style);",
        "havePreviousGlyph = true;",
    ],
    "src/activities/reader/EpubReaderActivity.cpp": [
        "renderer.setReaderGlyphFallbackFonts(NOTOSERIF_12_FONT_ID",
        "renderer.clearReaderGlyphFallbackFonts();",
    ],
    "test/cphun163_glyph_dictionary/CPHUN163GlyphDictionaryTest.cpp": [
        "HungarianGuillemetsWithTrailingComma",
        "MathematicalMinusUsesPrimaryEnDashWhenPresent",
    ],
}
for path, tokens in checks.items():
    source = Path(path).read_text(encoding="utf-8")
    for token in tokens:
        if token not in source:
            raise SystemExit(f"CPHUN-163 missing {token!r} in {path}")

# The replacement Noto Serif glyph can change word widths and pagination.
# Invalidate v57 and prior section files as well as their partial-build sentinels.
section = Path("lib/Epub/Epub/Section.cpp")
source = section.read_text(encoding="utf-8")
marker = "// CPHUN-163: glyph fallback changes line widths and pagination."
if marker not in source:
    if "// CPHUN-159: HTML hidden attribute changes section layout." not in source:
        raise SystemExit("CPHUN-159 cache invalidation was lost")
    pattern = r"(?m)^(constexpr uint8_t SECTION_FILE_VERSION = )(\d+)(;.*)$"
    match = re.search(pattern, source)
    if not match:
        raise SystemExit("No section version found")
    version = int(match.group(2))
    if version >= 220:
        raise SystemExit("No safe section-cache version remains")
    source = source[:match.start()] + marker + "\n" + match.group(1) + str(version + 1) + match.group(3) + source[match.end():]
    section.write_text(source, encoding="utf-8")
    print(f"CPHUN-163: section-cache version {version} -> {version + 1}")
print("CPHUN-163: dictionary guillemets and reader glyph fallback verified.")
