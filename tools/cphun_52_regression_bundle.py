from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"Expected pattern not found in {path}: {old[:80]!r}")
    s2 = s.replace(old, new, 1)
    p.write_text(s2)

# 1) Vertical EPUB margins: preserve the already recovered CPHUN margin profile.
#    Horizontal = selected margin; top/bottom = selected margin - 4 px.
epub = Path('src/activities/reader/EpubReaderActivity.cpp').read_text()
needle = 'const int verticalScreenMargin = std::max(0, static_cast<int>(SETTINGS.screenMargin) - 4);'
if epub.count(needle) < 2:
    raise SystemExit('CPHUN-52: vertical screen-margin profile is missing')

# 2) Optical margin is a simple OFF/ON setting, while accepting legacy percentage values as ON.
replace_once(
    'src/CrossPointSettings.cpp',
    '''  const uint8_t storedHangingPunctuation = doc["hangingPunctuation"] | (uint8_t)75;\n  if (storedHangingPunctuation == 1) {\n    // Migrate the previous On/Off implementation: On meant 50%.\n    hangingPunctuation = 50;\n    needsResave = true;\n  } else if (storedHangingPunctuation == 0 || storedHangingPunctuation == 25 || storedHangingPunctuation == 50 ||\n             storedHangingPunctuation == 75 || storedHangingPunctuation == 100) {\n    hangingPunctuation = storedHangingPunctuation;\n  } else {\n    hangingPunctuation = 75;\n    needsResave = true;\n  }''',
    '''  const uint8_t storedHangingPunctuation = doc["hangingPunctuation"] | (uint8_t)1;\n  hangingPunctuation = storedHangingPunctuation ? 1 : 0;\n  if (storedHangingPunctuation > 1) needsResave = true;''')

replace_once(
    'src/CrossPointSettings.cpp',
    '''  // High nibble: percentage step (1=25% .. 4=100%). Low nibble: overhang cap in 4-pixel units.\n  // The physical cap is 80% of the selected margin: 5->4, 10->8, ... 40->32 px.\n  const uint8_t hangingLimitUnits = static_cast<uint8_t>((screenMargin * 4 / 5) / 4);\n  spec.hangingPunctuationLimitPx =\n      static_cast<uint8_t>(((SETTINGS.hangingPunctuation / 20) << 5) | (SETTINGS.screenMargin > 2 ? SETTINGS.screenMargin - 2 : 0));''',
    '''  // Optical margin is OFF/ON. ON permits the eligible end punctuation to hang\n  // into the physical right margin, capped just inside the selected screen margin.\n  spec.hangingPunctuationLimitPx =\n      hangingPunctuation ? static_cast<uint8_t>(screenMargin > 1 ? screenMargin - 1 : 0) : 0;''')

replace_once(
    'src/activities/settings/TextSettingsActivity.cpp',
    'SETTINGS.hangingPunctuation = SETTINGS.hangingPunctuation ? 0 : 100;',
    'SETTINGS.hangingPunctuation = SETTINGS.hangingPunctuation ? 0 : 1;')
replace_once(
    'src/activities/settings/TextSettingsActivity.cpp',
    'return SETTINGS.hangingPunctuation ? std::to_string(SETTINGS.hangingPunctuation) + "%" : tr(STR_STATE_OFF);',
    'return SETTINGS.hangingPunctuation ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);')

# 3+4) Short hyphen interaction + restore the approved optical-margin punctuation set.
replace_once(
    'lib/Epub/Epub/ParsedText.h',
    '  static bool shortHyphenEnabled_;',
    '  static bool shortHyphenEnabled_;\n  static bool opticalMarginEnabled_;')
replace_once(
    'lib/Epub/Epub/ParsedText.h',
    '  static bool isShortHyphenEnabled() { return shortHyphenEnabled_; }',
    '  static bool isShortHyphenEnabled() { return shortHyphenEnabled_; }\n  static void setOpticalMarginEnabled(bool enabled) { opticalMarginEnabled_ = enabled; }\n  static bool isOpticalMarginEnabled() { return opticalMarginEnabled_; }')

replace_once(
    'lib/Epub/Epub/ParsedText.cpp',
    'bool ParsedText::shortHyphenEnabled_ = false;',
    'bool ParsedText::shortHyphenEnabled_ = false;\nbool ParsedText::opticalMarginEnabled_ = false;')
replace_once(
    'lib/Epub/Epub/ParsedText.cpp',
    '''bool isHangingPunctuation(const uint32_t cp) {\n  return cp == '-' || (ParsedText::isShortHyphenEnabled() && cp == 0x2011);\n}''',
    '''bool isHangingPunctuation(const uint32_t cp) {\n  // CPHUN approved optical-margin set: hyphen, period, comma, colon, semicolon.\n  // U+2011 participates only when Short Hyphen is enabled.\n  return cp == '-' || cp == '.' || cp == ',' || cp == ':' || cp == ';' ||\n         (ParsedText::isShortHyphenEnabled() && cp == 0x2011);\n}''')
replace_once(
    'lib/Epub/Epub/ParsedText.cpp',
    '''  if (appendHyphen) {\n    if (ParsedText::isShortHyphenEnabled()) {\n      sanitized += SHORT_HYPHEN_UTF8;\n    } else {\n      sanitized.push_back('-');\n    }\n  }''',
    '''  if (appendHyphen) {\n    // With Optical margin ON, choose line breaks using the normal U+002D width,\n    // then substitute U+2011 only for rendering. This keeps Short Hyphen from\n    // changing pagination in optical-margin mode. With Optical margin OFF the\n    // shorter U+2011 width is intentionally allowed to affect line breaking.\n    if (ParsedText::isShortHyphenEnabled() && !ParsedText::isOpticalMarginEnabled()) {\n      sanitized += SHORT_HYPHEN_UTF8;\n    } else {\n      sanitized.push_back('-');\n    }\n  }''')

replace_once(
    'lib/Epub/Epub/Section.cpp',
    '  ParsedText::setShortHyphenEnabled(spec.shortHyphen);',
    '  ParsedText::setShortHyphenEnabled(spec.shortHyphen);\n  ParsedText::setOpticalMarginEnabled(spec.hangingPunctuationLimitPx > 0);')

# Build identity.
p = Path('src/CPHUNBuildId.h')
s = p.read_text()
import re
s2, n = re.subn(r'CPHUN-\d{6}-\d+', 'CPHUN-260904-52', s, count=1)
if n != 1:
    raise SystemExit('CPHUN-52: build ID pattern not found')
p.write_text(s2)
