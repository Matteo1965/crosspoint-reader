from pathlib import Path

# CPHUN-47: small follow-up on top of CPHUN-46.
# - home cover: another +4 px down (+10 -> +14 inside tile)
# - two-line centered home title: another +4 px down
# - CrossPoint Version page 3: requested Soft hyphen title wording

p = Path('src/components/themes/roundedraff/RoundedRaffTheme.cpp')
s = p.read_text(encoding='utf-8')

old_cover = 'const int imgY = tileY + (tileHeight - RoundedRaffMetrics::values.homeCoverHeight) / 2 + 10;'
new_cover = 'const int imgY = tileY + (tileHeight - RoundedRaffMetrics::values.homeCoverHeight) / 2 + 14;'
if old_cover not in s:
    raise SystemExit('CPHUN-47 cover offset anchor missing')
s = s.replace(old_cover, new_cover, 1)

old_title = 'int textY = rect.y + std::max(0, (rect.height - lines * lineHeight) / 2);'
new_title = 'int textY = rect.y + std::max(0, (rect.height - lines * lineHeight) / 2) + 4;'
if old_title not in s:
    raise SystemExit('CPHUN-47 title offset anchor missing')
s = s.replace(old_title, new_title, 1)
p.write_text(s, encoding='utf-8')

p = Path('src/activities/settings/CrossPointVersionActivity.cpp')
v = p.read_text(encoding='utf-8')
old = 'hu ? "Beágyazott elválasztás (Soft hyphen)" : "Embedded hyphenation (Soft hyphen)"'
new = 'hu ? "Beágyazott elválasztás - Soft hyphen" : "Embedded hyphenation (Soft hyphen)"'
if old not in v:
    raise SystemExit('CPHUN-47 version page 3 title anchor missing')
v = v.replace(old, new, 1)
p.write_text(v, encoding='utf-8')

# Verification.
rr = Path('src/components/themes/roundedraff/RoundedRaffTheme.cpp').read_text(encoding='utf-8')
assert 'homeCoverHeight) / 2 + 14;' in rr
assert '(rect.height - lines * lineHeight) / 2) + 4;' in rr
version = Path('src/activities/settings/CrossPointVersionActivity.cpp').read_text(encoding='utf-8')
assert 'Beágyazott elválasztás - Soft hyphen' in version
print('Applied CPHUN-47 home +4/+4 offsets and version page 3 title')
