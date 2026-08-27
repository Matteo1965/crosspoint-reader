from pathlib import Path

textblock = Path('lib/Epub/Epub/blocks/TextBlock.cpp')
s = textblock.read_text(encoding='utf-8')

old_write = '''  serialization::writePod(file, textBytes);\n  if (numWords > 0) {'''
new_write = '''  serialization::writePod(file, textBytes);\n  // CPHUN-260827-24: persist the actual tracking value. The bidi high bit only\n  // records tracking presence and cannot distinguish +1 px from +2 px.\n  serialization::writePod(file, letterSpacingPx);\n  if (numWords > 0) {'''
if old_write not in s:
    raise SystemExit('TextBlock serialize marker not found')
s = s.replace(old_write, new_write, 1)

old_read = '''  uint16_t textBytes;\n  serialization::readPod(file, wc);\n  serialization::readPod(file, hasFocus);\n  serialization::readPod(file, textBytes);'''
new_read = '''  uint16_t textBytes;\n  uint8_t cachedLetterSpacingPx = 0;\n  serialization::readPod(file, wc);\n  serialization::readPod(file, hasFocus);\n  serialization::readPod(file, textBytes);\n  serialization::readPod(file, cachedLetterSpacingPx);'''
if old_read not in s:
    raise SystemExit('TextBlock deserialize header marker not found')
s = s.replace(old_read, new_read, 1)

old_restore = '''    // Backward-compatible cache packing: old caches have only 0/1 here, new\n    // caches use the high bit to persist the line's 1 px tracking flag.\n    block->letterSpacingPx = (block->bidiDirArr[0] & 0x80) != 0 ? 1 : 0;'''
new_restore = '''    // Cache v52 stores the exact tracking value explicitly, preserving diagnostic\n    // +2 px tracking instead of collapsing every non-zero value to +1 px.\n    block->letterSpacingPx = cachedLetterSpacingPx;'''
if old_restore not in s:
    raise SystemExit('TextBlock tracking restore marker not found')
s = s.replace(old_restore, new_restore, 1)
textblock.write_text(s, encoding='utf-8')

section = Path('lib/Epub/Epub/Section.cpp')
t = section.read_text(encoding='utf-8')
old_version = 'constexpr uint8_t SECTION_FILE_VERSION = 51;'
if old_version not in t:
    raise SystemExit('Expected section cache version 51 marker not found')
t = t.replace('// v50: Section cache header now includes letterSpacingLimitPercent, so changing\n//      Betűköz korrekció invalidates cached layout and rebuilds affected sections.\nconstexpr uint8_t SECTION_FILE_VERSION = 51;',
              '// v50: Section cache header now includes letterSpacingLimitPercent, so changing\n//      Betűköz korrekció invalidates cached layout and rebuilds affected sections.\n// v52: TextBlock serialization stores the exact letterSpacingPx value instead of\n//      reducing every non-zero tracking value to a one-bit +1 px flag.\nconstexpr uint8_t SECTION_FILE_VERSION = 52;', 1)
section.write_text(t, encoding='utf-8')

print('Applied CPHUN-260827-24 exact tracking cache value and cache version 52')
