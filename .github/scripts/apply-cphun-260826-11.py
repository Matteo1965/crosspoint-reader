from pathlib import Path

# CPHUN-260826-11 / item 3: normalize legacy Hungarian õ/û forms only in
# hyphenation processing. The EPUB source string is left untouched and UTF-8
# byte offsets remain based on the original word.
p = Path('lib/Epub/Epub/hyphenation/Hyphenator.cpp')
s = p.read_text(encoding='utf-8')
needle = '''  auto cps = collectCodepoints(word);\n  trimSurroundingPunctuationAndFootnote(cps);'''
replacement = '''  auto cps = collectCodepoints(word);\n  // Hungarian processing normalization: preserve original source bytes/offsets.\n  if (preferredLanguageIsHungarian_) {\n    for (auto& cp : cps) {\n      switch (cp.value) {\n        case 0x00F5: cp.value = 0x0151; break;  // õ -> ő\n        case 0x00FB: cp.value = 0x0171; break;  // û -> ű\n        case 0x00D5: cp.value = 0x0150; break;  // Õ -> Ő\n        case 0x00DB: cp.value = 0x0170; break;  // Û -> Ű\n        default: break;\n      }\n    }\n  }\n  trimSurroundingPunctuationAndFootnote(cps);'''
if needle not in s:
    raise SystemExit('Hyphenator insertion point not found')
s = s.replace(needle, replacement, 1)
p.write_text(s, encoding='utf-8')

# Items 1-2 are applied by the existing dialogue/min-space patch layer inherited
# from the 260825 test series. This build keeps the suspended hyphen-position task untouched.
print('CPHUN-260826-11 patch applied')
