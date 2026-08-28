from pathlib import Path


def replace_all(path: str, old: str, new: str, expected: int) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"Expected {expected} matches in {path}, found {count}")
    p.write_text(text.replace(old, new), encoding="utf-8")


replace_all(
    "src/activities/settings/TextSettingsActivity.cpp",
    "360, 330, 300, 270, 240, 210, 180",
    "500, 450, 400, 350, 300, 250, 200",
    3,
)

replace_all(
    "src/activities/settings/TextSettingsActivity.cpp",
    "decreases monotonically from 360% to 180%.",
    "decreases monotonically from 500% to 200%.",
    1,
)

p = Path("src/CrossPointSettings.cpp")
text = p.read_text(encoding="utf-8")
old = '''  if (letterSpacingLimitPercent != 0 && letterSpacingLimitPercent != 180 && letterSpacingLimitPercent != 210 &&
      letterSpacingLimitPercent != 240 && letterSpacingLimitPercent != 270 && letterSpacingLimitPercent != 300 &&
      letterSpacingLimitPercent != 330 && letterSpacingLimitPercent != 360) {'''
new = '''  if (letterSpacingLimitPercent != 0 && letterSpacingLimitPercent != 200 && letterSpacingLimitPercent != 250 &&
      letterSpacingLimitPercent != 300 && letterSpacingLimitPercent != 350 && letterSpacingLimitPercent != 400 &&
      letterSpacingLimitPercent != 450 && letterSpacingLimitPercent != 500) {'''
if text.count(old) != 1:
    raise SystemExit("Expected old CPHUN-31 validation block exactly once")
p.write_text(text.replace(old, new, 1), encoding="utf-8")

print("CPHUN-260828-31 agreed 500-200 tracking scale applied")
