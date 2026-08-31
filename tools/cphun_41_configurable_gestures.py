from pathlib import Path

# Final requested bottom-button geometry and wording.
p = Path('src/activities/settings/ButtonFunctionsActivity.cpp')
t = p.read_text(encoding='utf-8')
t = t.replace('constexpr int kButtonX = 115;', 'constexpr int kButtonX = 125;')
t = t.replace('constexpr int kButtonX = 105;', 'constexpr int kButtonX = 125;')
t = t.replace('constexpr int kButtonX = 145;', 'constexpr int kButtonX = 125;')
t = t.replace('"Hosszan:"', '"Hosszú:"').replace('"Tart:"', '"Hosszú:"')
t = t.replace('return hu ? "Alsó gombok" : "Bottom buttons";',
              'return hu ? "Alsó gombkiosztás" : "Bottom button layout";')
t = t.replace('case ReaderAction::ToggleSoftHyphen: return "Soft Hyphen";',
              'case ReaderAction::ToggleSoftHyphen: return hu ? "Kiterjesztett elválasztás" : "Extended hyphenation";')
p.write_text(t, encoding='utf-8')

# Turn the safe CPHUN-38/39 dispatcher into a gesture dispatcher. Single and Hold
# use the same saved 12-slot profile as Double. None preserves legacy behaviour.
p = Path('src/activities/reader/EpubReaderActivity.cpp')
t = p.read_text(encoding='utf-8')
old = '''  const auto cphun36DoubleAction = [this, &cphun36OpenSettings, &cphun36OpenLayout, &cphun36RebuildReader](\n                                      const int raw) {\n    ReaderPhysicalButton physical = ReaderPhysicalButton::Back;'''
new = '''  const auto cphun36GestureAction = [this, &cphun36OpenSettings, &cphun36OpenLayout, &cphun36RebuildReader](\n                                      const int raw, const ReaderButtonGesture gesture) -> bool {\n    ReaderPhysicalButton physical = ReaderPhysicalButton::Back;'''
if old not in t:
    raise SystemExit('CPHUN-41 dispatcher anchor missing')
t = t.replace(old, new, 1)
t = t.replace(
    'const ReaderAction configured = READER_BUTTONS.get(physical, ReaderButtonGesture::Double);\n    if (configured == ReaderAction::None) return;',
    'const ReaderAction configured = READER_BUTTONS.get(physical, gesture);\n    if (configured == ReaderAction::None) return false;', 1)

# The dispatcher has an explicit bool return type. Every legacy/configured action
# inside this block consumes the gesture, so all no-value returns must become true.
start = t.index('  const auto cphun36GestureAction')
end = t.index('  const auto cphun36LegacyShort', start)
block = t[start:end]
block = block.replace('return;', 'return true;')
# Defensive final return for the retained compatibility fallback.
last = block.rfind('\n  };')
if last < 0:
    raise SystemExit('CPHUN-41 dispatcher end missing')
if not block[:last].rstrip().endswith('return true;'):
    block = block[:last] + '\n    return true;' + block[last:]
t = t[:start] + block + t[end:]

# Single: configured action overrides legacy single; None keeps the proven legacy path.
needle = '''  const auto cphun36LegacyShort = [this](const int raw) {'''
repl = '''  const auto cphun36LegacyShort = [this, &cphun36GestureAction](const int raw) {\n    if (cphun36GestureAction(raw, ReaderButtonGesture::Single)) return;'''
if needle not in t:
    raise SystemExit('CPHUN-41 single anchor missing')
t = t.replace(needle, repl, 1)
# Double now uses the same generic dispatcher.
if 'cphun36DoubleAction(cphun36ReleasedRaw);' not in t:
    raise SystemExit('CPHUN-41 double anchor missing')
t = t.replace('cphun36DoubleAction(cphun36ReleasedRaw);',
              'cphun36GestureAction(cphun36ReleasedRaw, ReaderButtonGesture::Double);', 1)
# Hold: if a configured Hold exists consume it; otherwise preserve legacy hold processing.
needle = '''    } else if (cphun36.waitingSecond && cphun36.raw == cphun36ReleasedRaw) {\n      cphun36.waitingSecond = false;\n    }'''
repl = '''    } else {\n      if (cphun36.waitingSecond && cphun36.raw == cphun36ReleasedRaw) cphun36.waitingSecond = false;\n      if (cphun36GestureAction(cphun36ReleasedRaw, ReaderButtonGesture::Hold)) {\n        cphun36ConsumeFrontShort = true;\n      }\n    }'''
if needle not in t:
    raise SystemExit('CPHUN-41 hold anchor missing')
t = t.replace(needle, repl, 1)
p.write_text(t, encoding='utf-8')

# Paragraph mode encoding for the renderer:
#   255 = KI: preserve book/CSS spacing and first-line indentation
#     0 = enabled 0%: no added paragraph spacing and force non-negative indent to zero
# 25..100 = enabled extra spacing, likewise suppress positive/default indentation.
p = Path('src/CrossPointSettings.cpp')
t = p.read_text(encoding='utf-8')
old = '  spec.extraParagraphSpacing = extraParagraphSpacing;'
new = '  spec.extraParagraphSpacing = extraParagraphSpacingEnabled ? extraParagraphSpacing : static_cast<uint8_t>(255);'
if old not in t:
    raise SystemExit('CPHUN-41 render-spec paragraph anchor missing')
t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')

p = Path('lib/Epub/Epub/ParsedText.cpp')
t = p.read_text(encoding='utf-8')
old = '''int ParsedText::resolveFirstLineIndent(const bool isFirstLine, const GfxRenderer& renderer, const int fontId) const {\n  if (!isFirstLine || !isNaturalAlign) {\n    return 0;\n  }\n  if (blockStyle.textIndentDefined) {\n    if (blockStyle.textIndent < 0 || !extraParagraphSpacing) {\n      return blockStyle.textIndent;\n    }\n    return 0;\n  }\n  if (!extraParagraphSpacing) {\n    return renderer.getSpaceWidth(fontId, EpdFontFamily::REGULAR) * 3;\n  }\n  return 0;\n}'''
new = '''int ParsedText::resolveFirstLineIndent(const bool isFirstLine, const GfxRenderer& renderer, const int fontId) const {\n  if (!isFirstLine || !isNaturalAlign) {\n    return 0;\n  }\n  // CPHUN-41: 255 is the renderer-only sentinel for KI. Enabled 0% is a\n  // real override state and therefore suppresses the book/default indent.\n  const bool paragraphOverrideEnabled = extraParagraphSpacing != 255;\n  if (blockStyle.textIndentDefined) {\n    if (blockStyle.textIndent < 0 || !paragraphOverrideEnabled) {\n      return blockStyle.textIndent;\n    }\n    return 0;\n  }\n  if (!paragraphOverrideEnabled) {\n    return renderer.getSpaceWidth(fontId, EpdFontFamily::REGULAR) * 3;\n  }\n  return 0;\n}'''
if old not in t:
    raise SystemExit('CPHUN-41 first-line indent anchor missing')
t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')

p = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp')
t = p.read_text(encoding='utf-8')
old = '''  // Extra paragraph spacing: 100% equals the legacy lineHeight/2 behavior.\n  if (extraParagraphSpacing) {\n    const int extraBase = lineHeight / 2;\n    currentPageNextY += (extraBase * extraParagraphSpacing + 50) / 100;\n  }'''
new = '''  // Extra paragraph spacing: 100% equals the legacy lineHeight/2 behavior.\n  // 255 is CPHUN-41's renderer-only KI sentinel: preserve CSS margins/indent and add nothing.\n  if (extraParagraphSpacing > 0 && extraParagraphSpacing <= 100) {\n    const int extraBase = lineHeight / 2;\n    currentPageNextY += (extraBase * extraParagraphSpacing + 50) / 100;\n  }'''
if old not in t:
    raise SystemExit('CPHUN-41 paragraph-spacing anchor missing')
t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')

# Verify requested UI/profile integration without touching Power/side paths.
ui = Path('src/activities/settings/ButtonFunctionsActivity.cpp').read_text(encoding='utf-8')
for s in ['constexpr int kButtonX = 125;', '"Hosszú:"', 'Kiterjesztett elválasztás']:
    assert s in ui, s
r = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
for s in ['ReaderButtonGesture::Single', 'ReaderButtonGesture::Double', 'ReaderButtonGesture::Hold',
          'Button::Power', 'Button::PageBack', 'Button::PageForward']:
    assert s in r, s
gesture_start = r.index('  const auto cphun36GestureAction')
gesture_end = r.index('  const auto cphun36LegacyShort', gesture_start)
gesture_block = r[gesture_start:gesture_end]
assert '-> bool' in gesture_block
assert 'return;' not in gesture_block, 'no-value return survived inside bool gesture dispatcher'

settings = Path('src/CrossPointSettings.cpp').read_text(encoding='utf-8')
assert 'extraParagraphSpacingEnabled ? extraParagraphSpacing : static_cast<uint8_t>(255)' in settings
parsed = Path('lib/Epub/Epub/ParsedText.cpp').read_text(encoding='utf-8')
assert 'paragraphOverrideEnabled = extraParagraphSpacing != 255' in parsed
parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text(encoding='utf-8')
assert 'extraParagraphSpacing > 0 && extraParagraphSpacing <= 100' in parser

# The current Hyphenator already merges explicit-hyphen breakpoints with Liang
# pattern breaks computed independently for every component. Keep this invariant
# in the CPHUN-41 build so ASCII-hyphenated Hungarian compounds can split both at
# the original '-' and inside either component without duplicating the hyphen.
hyphenator = Path('lib/Epub/Epub/hyphenation/Hyphenator.cpp').read_text(encoding='utf-8')
for s in ['buildExplicitBreakInfos', 'appendSegmentPatternBreaks',
          'appendSegmentPatternBreaks(cps, *hyphenator, /*includeFallback=*/false, explicitBreakInfos)']:
    assert s in hyphenator, s

print('Applied CPHUN-41 bool fix, button geometry, 0% paragraph mode, and compound-hyphen invariants')
