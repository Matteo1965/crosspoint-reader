from pathlib import Path

# CPHUN-44: test stronger explicit-hyphen justification microspacing.
# Increase the CPHUN-43 cap from +2/+2 px to +4/+4 px.

p = Path('lib/Epub/Epub/ParsedText.cpp')
s = p.read_text(encoding='utf-8')

replacements = [
    ('// CPHUN-43: up to +2 px before and +2 px after each explicit ASCII hyphen.',
     '// CPHUN-44: up to +4 px before and +4 px after each explicit ASCII hyphen.'),
    ('static_cast<int>(hyphenMicroOpportunityCount) * 2',
     'static_cast<int>(hyphenMicroOpportunityCount) * 4'),
    ('const int micro = std::min(2, hyphenMicroRemaining);',
     'const int micro = std::min(4, hyphenMicroRemaining);'),
]
for old, new in replacements:
    if old not in s:
        raise SystemExit(f'CPHUN-44 anchor missing: {old}')
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')

parsed = p.read_text(encoding='utf-8')
for needle in [
    'CPHUN-44: up to +4 px before and +4 px after each explicit ASCII hyphen.',
    'static_cast<int>(hyphenMicroOpportunityCount) * 4',
    'std::min(4, hyphenMicroRemaining)',
]:
    assert needle in parsed, needle

print('Applied CPHUN-44 explicit-hyphen justification microspacing +4/+4 px')
