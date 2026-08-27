from pathlib import Path

p = Path('lib/Epub/Epub/Section.cpp')
s = p.read_text(encoding='utf-8')

repls = [
    ('constexpr uint8_t SECTION_FILE_VERSION = 49;', 'constexpr uint8_t SECTION_FILE_VERSION = 50;'),
    ('sizeof(bool) + sizeof(uint8_t) + sizeof(bool) + sizeof(uint8_t) +\n                                 sizeof(uint32_t)',
     'sizeof(bool) + sizeof(uint8_t) + sizeof(bool) + sizeof(uint8_t) + sizeof(uint8_t) +\n                                 sizeof(uint32_t)'),
    ('sizeof(spec.minimumSpacePercent) + sizeof(spec.embeddedStyle)',
     'sizeof(spec.minimumSpacePercent) + sizeof(spec.letterSpacingLimitPercent) + sizeof(spec.embeddedStyle)'),
    ('serialization::writePod(file, spec.minimumSpacePercent);\n  serialization::writePod(file, spec.embeddedStyle);',
     'serialization::writePod(file, spec.minimumSpacePercent);\n  serialization::writePod(file, spec.letterSpacingLimitPercent);\n  serialization::writePod(file, spec.embeddedStyle);'),
    ('uint8_t fileMinimumSpacePercent;\n    bool fileEmbeddedStyle;',
     'uint8_t fileMinimumSpacePercent;\n    uint8_t fileLetterSpacingLimitPercent;\n    bool fileEmbeddedStyle;'),
    ('serialization::readPod(file, fileMinimumSpacePercent);\n    serialization::readPod(file, fileEmbeddedStyle);',
     'serialization::readPod(file, fileMinimumSpacePercent);\n    serialization::readPod(file, fileLetterSpacingLimitPercent);\n    serialization::readPod(file, fileEmbeddedStyle);'),
    ('spec.fixedDialogueSpacing != fileFixedDialogueSpacing || spec.minimumSpacePercent != fileMinimumSpacePercent ||\n        spec.embeddedStyle != fileEmbeddedStyle ||',
     'spec.fixedDialogueSpacing != fileFixedDialogueSpacing || spec.minimumSpacePercent != fileMinimumSpacePercent ||\n        spec.letterSpacingLimitPercent != fileLetterSpacingLimitPercent || spec.embeddedStyle != fileEmbeddedStyle ||'),
]

for old, new in repls:
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'Expected 1 occurrence, found {count}: {old[:80]!r}')
    s = s.replace(old, new, 1)

marker = '// v43: TextBlock arena stores one cached BidiBaseDir byte per word. This avoids\n//      repeating Unicode direction detection on every page redraw.\n'
if marker not in s:
    raise SystemExit('Version comment marker not found')
s = s.replace(marker, marker + '// v50: Section cache header now includes letterSpacingLimitPercent, so changing\n//      Betűköz korrekció invalidates cached layout and rebuilds affected sections.\n', 1)

p.write_text(s, encoding='utf-8')
print('Patched Section.cpp for letter-spacing cache invalidation (v50)')
