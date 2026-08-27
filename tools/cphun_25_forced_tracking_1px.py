from pathlib import Path

path = Path('lib/Epub/Epub/ParsedText.cpp')
s = path.read_text(encoding='utf-8')

old_total = "trackingExtraTotal += static_cast<int>(cps - 1) * 2;"
new_total = "trackingExtraTotal += static_cast<int>(cps - 1);"
old_value = "if (trackingExtraTotal > 0 && trackingExtraTotal < spareSpace) letterSpacingPx = 2;"
new_value = "if (trackingExtraTotal > 0 && trackingExtraTotal < spareSpace) letterSpacingPx = 1;"

if s.count(old_total) != 1:
    raise SystemExit(f'Expected exactly one forced +2px tracking total marker, found {s.count(old_total)}')
if s.count(old_value) != 1:
    raise SystemExit(f'Expected exactly one forced +2px tracking value marker, found {s.count(old_value)}')

s = s.replace(old_total, new_total, 1)
s = s.replace(old_value, new_value, 1)
s = s.replace('CPHUN-260827-22 diagnostic: force clearly visible +2 px tracking on',
              'CPHUN-260827-25 diagnostic: force realistic +1 px tracking on', 1)

path.write_text(s, encoding='utf-8')
print('Applied CPHUN-260827-25 forced +1 px tracking diagnostic')
