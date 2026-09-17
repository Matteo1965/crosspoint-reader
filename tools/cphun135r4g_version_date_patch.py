from pathlib import Path
import re

# Keep the user-visible CrossPoint Version date tied to the build identity
# instead of a stale hard-coded literal in CrossPointVersionActivity.cpp.
bid = Path("src/CPHUNBuildId.h")
b = bid.read_text(encoding="utf-8")

# Remove/replace an older build-date macro if a previous experimental stage
# already created one.
if re.search(r'^#define CPHUN_BUILD_DATE ', b, re.M):
    b = re.sub(r'^#define CPHUN_BUILD_DATE .*$', '#define CPHUN_BUILD_DATE "Sep-17 2026"', b, count=1, flags=re.M)
else:
    if not b.endswith("\n"):
        b += "\n"
    b += '#define CPHUN_BUILD_DATE "Sep-17 2026"\n'
bid.write_text(b, encoding="utf-8")

page = Path("src/activities/settings/CrossPointVersionActivity.cpp")
s = page.read_text(encoding="utf-8")
old = 'drawLabelValue(hu ? "Dátum" : "Date", "Sep-8 2026");'
new = 'drawLabelValue(hu ? "Dátum" : "Date", CPHUN_BUILD_DATE);'
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    # Accept any older hard-coded Sep-* 2026 value, but only on the Date row.
    s2, n = re.subn(r'drawLabelValue\(hu \? "Dátum" : "Date", "[A-Za-z]{3}-\d{1,2} 2026"\);', new, s, count=1)
    if n != 1:
        raise SystemExit("CPHUN-135r4g: CrossPoint Version hard-coded date row not found")
    s = s2
page.write_text(s, encoding="utf-8")

print("CPHUN-135r4g version date synchronized: CPHUN_BUILD_DATE=Sep-17 2026")
