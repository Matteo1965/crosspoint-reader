from pathlib import Path
import re

path = Path('lib/Epub/Epub/ParsedText.cpp')
s = path.read_text(encoding='utf-8')

pattern = re.compile(
    r"\n  // CPHUN-260827-(?:22|25) diagnostic: force .*?\n"
    r"  // normal justified LTR non-last lines\. This intentionally bypasses the\n"
    r"  // 120/240% activation threshold so we can verify the layout->TextBlock->render path\.\n"
    r"  if \(effectiveAlignment == CssTextAlign::Justify.*?\n"
    r"  \} else if \(letterSpacingLimitPercent > 0 && effectiveAlignment == CssTextAlign::Justify",
    re.DOTALL,
)

replacement = (
    "\n  // CPHUN-260827-26: production tracking path. Apply at most +1 px only when\n"
    "  // the configured 120-240% inter-word-gap threshold is exceeded.\n"
    "  if (letterSpacingLimitPercent > 0 && effectiveAlignment == CssTextAlign::Justify"
)

s2, count = pattern.subn(replacement, s, count=1)
if count != 1:
    raise SystemExit(f'Expected exactly one forced tracking diagnostic block, found {count}')

path.write_text(s2, encoding='utf-8')
print('Applied CPHUN-260827-26 threshold-gated +1 px tracking')
