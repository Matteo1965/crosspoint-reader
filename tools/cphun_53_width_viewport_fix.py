from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"Expected pattern not found in {path}: {old[:120]!r}")
    p.write_text(s.replace(old, new, 1))

# 1) Width bookkeeping: in Optical margin mode the line-break decision intentionally
#    measures a synthetic break with U+002D, but rendering may substitute U+2011.
#    After the breakpoint has been selected, store the width of the ACTUAL rendered
#    prefix so justification / hanging punctuation use the real glyph width.
replace_once(
    'lib/Epub/Epub/ParsedText.cpp',
    '''  // Update cached widths to reflect the new prefix/remainder pairing.\n  wordWidths[wordIndex] = static_cast<uint16_t>(chosenWidth);\n  const uint16_t remainderWidth =\n      measureFocusWordWidth(renderer, fontId, remainder, style, wordFocusBoundary[wordIndex + 1]);''',
    '''  // Update cached widths to reflect the new prefix/remainder pairing.\n  // With Optical margin ON, breakpoint selection may have used U+002D deliberately\n  // even though Short Hyphen renders U+2011. Once the break is fixed, bookkeeping\n  // must switch to the actual rendered prefix width or justification will reserve\n  // space for the wrong glyph and the short hyphens will not start on one margin line.\n  if (shortHyphenEnabled_ && opticalMarginEnabled_ && chosenNeedsHyphen) {\n    wordWidths[wordIndex] = measureFocusWordWidth(renderer, fontId, words[wordIndex], wordStyles[wordIndex],\n                                                  wordFocusBoundary[wordIndex]);\n  } else {\n    wordWidths[wordIndex] = static_cast<uint16_t>(chosenWidth);\n  }\n  const uint16_t remainderWidth =\n      measureFocusWordWidth(renderer, fontId, remainder, style, wordFocusBoundary[wordIndex + 1]);''')

# 2) Verify the REAL EPUB viewport construction. This is the renderBook() path that
#    determines both pagination viewportHeight and the draw origin. Do not apply a
#    second -4: the desired vertical profile is already present here.
epub = Path('src/activities/reader/EpubReaderActivity.cpp').read_text()
viewport_block = '''  renderer.getOrientedViewableTRBL(&orientedMarginTop, &orientedMarginRight, &orientedMarginBottom,\n                                   &orientedMarginLeft);\n  const int verticalScreenMargin = std::max(0, static_cast<int>(SETTINGS.screenMargin) - 4);\n  orientedMarginTop += verticalScreenMargin;\n  orientedMarginLeft += SETTINGS.screenMargin;\n  orientedMarginRight += SETTINGS.screenMargin;'''
if viewport_block not in epub:
    raise SystemExit('CPHUN-53: renderBook viewport does not apply screenMargin - 4 at top')
if 'orientedMarginBottom += std::max(verticalScreenMargin, static_cast<int>(statusBarHeight));' not in epub:
    raise SystemExit('CPHUN-53: renderBook viewport does not apply verticalScreenMargin at bottom')
if 'const uint16_t viewportHeight = renderer.getScreenHeight() - orientedMarginTop - orientedMarginBottom;' not in epub:
    raise SystemExit('CPHUN-53: actual viewportHeight construction not found')

# Build identity.
p = Path('src/CPHUNBuildId.h')
s = p.read_text()
if 'CPHUN-260904-52' not in s:
    raise SystemExit('CPHUN-53: expected CPHUN-52 build id not found')
p.write_text(s.replace('CPHUN-260904-52', 'CPHUN-260904-53', 1))
