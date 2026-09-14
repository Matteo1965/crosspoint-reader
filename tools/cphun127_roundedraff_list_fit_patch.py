from pathlib import Path

path = Path("src/activities/settings/TextSettingsActivity.cpp")
text = path.read_text(encoding="utf-8")

old_preview = (
    "  if (SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF) "
    "previewHeight -= 10;"
)
new_preview = (
    "  if (SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF) "
    "previewHeight -= 16;"
)
if text.count(old_preview) != 1:
    raise SystemExit(
        f"CPHUN-127: RoundedRaff preview anchor matches={text.count(old_preview)}"
    )
text = text.replace(old_preview, new_preview, 1)

old_rows = """  const int16_t textSettingsRowHeight = compactLyraLayout ? 36 : 40;
"""
new_rows = """  const bool compactRoundedRaffRows =
      SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF;
  const int16_t textSettingsRowHeight =
      (compactLyraLayout || compactRoundedRaffRows) ? 36 : 40;
"""
if text.count(old_rows) != 1:
    raise SystemExit(
        f"CPHUN-127: row-height anchor matches={text.count(old_rows)}"
    )
text = text.replace(old_rows, new_rows, 1)

# The same computed height must drive both painting and viewport/navigation
# calculations, otherwise the final row can remain outside the visible range.
if text.count("props.rowHeight = textSettingsRowHeight;") != 1:
    raise SystemExit("CPHUN-127: list painter does not use the shared row height")
if text.count(
    "syncTabListViewport(screen, props, false, textSettingsRowHeight);"
) != 1:
    raise SystemExit("CPHUN-127: viewport does not use the shared row height")

path.write_text(text, encoding="utf-8")

build_id_path = Path("src/CPHUNBuildId.h")
build_id = build_id_path.read_text(encoding="utf-8")
old_id = '#define CPHUN_BUILD_ID "CPHUN-260914-126"'
new_id = '#define CPHUN_BUILD_ID "CPHUN-260914-127"'
if build_id.count(old_id) != 1:
    raise SystemExit(f"CPHUN-127: build-id anchor matches={build_id.count(old_id)}")
build_id_path.write_text(build_id.replace(old_id, new_id, 1), encoding="utf-8")
