from pathlib import Path

path = Path("lib/Epub/Epub/ParsedText.cpp")
text = path.read_text(encoding="utf-8")

old = '''    // 2-bit font packing is MSB-first, 4 pixels per byte:\n    // 0=white, 1=light gray, 2=dark gray, 3=black.\n'''
new = '''    // 2-bit font packing is MSB-first, 4 pixels per byte:\n    // 0=white, 1=light gray, 2=dark gray, 3=black.\n    // CPHUN-124: for optical right-edge purposes, dark gray (2) and\n    // black (3) count equally as visible ink; light gray (1) is treated\n    // as white. This keeps the calculation binary and ignores faint\n    // anti-aliased fringe pixels.\n'''
if text.count(old) != 1:
    raise SystemExit(f"CPHUN-124: 2-bit comment anchor matches={text.count(old)}")
text = text.replace(old, new, 1)

old_cond = '        if (value == 3 && x > rightmostStrong) rightmostStrong = x;'
new_cond = '        if (value >= 2 && x > rightmostStrong) rightmostStrong = x;'
if text.count(old_cond) != 1:
    raise SystemExit(f"CPHUN-124: strong-ink condition matches={text.count(old_cond)}")
text = text.replace(old_cond, new_cond, 1)

# The #123 guard must remain intact: hanging punctuation, including synthetic
# short hyphen U+2011, is handled by the existing hangingAllowance path and must
# not receive this ordinary final-glyph ink-edge compensation.
required = 'effectiveAlignment == CssTextAlign::Justify && !isLastLine && !blockStyle.isRtl && hangingAllowance == 0'
if required not in text:
    raise SystemExit("CPHUN-124: hanging-punctuation exclusion guard missing")

if 'value >= 2' not in text:
    raise SystemExit("CPHUN-124: dark-gray ink threshold missing")

path.write_text(text, encoding="utf-8")
