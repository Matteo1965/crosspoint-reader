from pathlib import Path

parsed = Path('lib/Epub/Epub/ParsedText.cpp')
s = parsed.read_text(encoding='utf-8')
old = "(letterSpacingPx ? static_cast<int>(std::max<uint32_t>(1, countCodepoints(lineWords[wordIdx])) - 1) : 0)"
new = "(letterSpacingPx ? static_cast<int>(std::max<uint32_t>(1, countCodepoints(lineWords[wordIdx])) - 1) * letterSpacingPx : 0)"
count = s.count(old)
if count != 2:
    raise SystemExit(f'Expected 2 tracking layout markers, found {count}')
s = s.replace(old, new)
parsed.write_text(s, encoding='utf-8')

section = Path('lib/Epub/Epub/Section.cpp')
t = section.read_text(encoding='utf-8')
if 'constexpr uint8_t SECTION_FILE_VERSION = 50;' not in t:
    raise SystemExit('Expected section cache version 50 marker not found')
t = t.replace('constexpr uint8_t SECTION_FILE_VERSION = 50;', 'constexpr uint8_t SECTION_FILE_VERSION = 51;', 1)
section.write_text(t, encoding='utf-8')

print('Applied CPHUN-260827-23 tracking layout scale fix and cache version 51')
