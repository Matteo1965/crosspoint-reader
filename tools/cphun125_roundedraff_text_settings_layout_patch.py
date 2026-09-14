from pathlib import Path

path = Path("src/activities/settings/TextSettingsActivity.cpp")
text = path.read_text(encoding="utf-8")

old = """  previewHeight = usableHeight * metrics_.previewHeightPercent / 100;
"""
new = """  previewHeight = usableHeight * metrics_.previewHeightPercent / 100;
  // CPHUN-125: RoundedRaff needs more vertical room for the Layout list.
  // Shorten only the preview pane; its caption, the tabs, and every following
  // control consequently move up by 10 px while row sizes stay unchanged.
  if (SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF) previewHeight -= 10;
"""
if text.count(old) != 1:
    raise SystemExit(f"CPHUN-125: preview-height anchor matches={text.count(old)}")
text = text.replace(old, new, 1)

if text.count("previewHeight -= 10") != 1:
    raise SystemExit("CPHUN-125: RoundedRaff preview compression missing")
if "compactLyraLayout ? 36 : 40" not in text:
    raise SystemExit("CPHUN-125: text-settings row heights changed unexpectedly")

path.write_text(text, encoding="utf-8")

build_id_path = Path("src/CPHUNBuildId.h")
build_id = build_id_path.read_text(encoding="utf-8")
old_id = '#define CPHUN_BUILD_ID "CPHUN-260914-124-EXP"'
new_id = '#define CPHUN_BUILD_ID "CPHUN-260914-125"'
if build_id.count(old_id) != 1:
    raise SystemExit(f"CPHUN-125: build-id anchor matches={build_id.count(old_id)}")
build_id_path.write_text(build_id.replace(old_id, new_id, 1), encoding="utf-8")
