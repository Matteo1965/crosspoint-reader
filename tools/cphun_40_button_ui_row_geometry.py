from pathlib import Path

p = Path("src/activities/settings/ButtonFunctionsActivity.cpp")
text = p.read_text(encoding="utf-8")

replacements = [
    ("constexpr int kButtonX = 105;", "constexpr int kButtonX = 115;"),
    ('(I18N.getLanguage() == Language::HU ? "Hosszan:" : "Hold:")',
     '(I18N.getLanguage() == Language::HU ? "Hosszú:" : "Hold:")'),
    ("  const int rowHeight = metrics.listRowHeight;\n",
     "  const int rowHeight = metrics.listRowHeight;\n  const int rowGap = metrics.listRowGap;\n  const int rowStep = rowHeight + rowGap;\n"),
    ("    const int rowTop = listTop + visualRow * rowHeight;",
     "    // Use the exact same vertical stride as FreeInk's List: row height + theme gap.\n"
     "    // Using rowHeight alone caused cumulative drift of the selection pill on RoundedRaff\n"
     "    // (42 px row + 6 px gap): the pill moved 48 px while custom text moved only 42 px.\n"
     "    const int rowTop = listTop + visualRow * rowStep;"),
    ("    // FreeInk selection pill sits about 10 px below the custom fixed-column text baseline on X4.\n"
     "    // Match the custom labels to the visual centre of the selection pill.\n"
     "    const int textY = rowTop + std::max(0, (rowHeight - textHeight) / 2) + 10;",
     "    // Centre custom text inside the same row rectangle used by the FreeInk selection pill.\n"
     "    const int textY = rowTop + std::max(0, (rowHeight - textHeight) / 2);")
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"CPHUN-40 anchor missing: {old!r}")
    text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")

ui = p.read_text(encoding="utf-8")
for needle in (
    "constexpr int kButtonX = 115;",
    '"Hosszú:"',
    "const int rowGap = metrics.listRowGap;",
    "const int rowStep = rowHeight + rowGap;",
    "visualRow * rowStep",
):
    if needle not in ui:
        raise SystemExit(f"CPHUN-40 UI invariant missing: {needle}")

if "+ 10;" in ui:
    raise SystemExit("Old fixed +10 px vertical correction still present")

print("Applied CPHUN-40 bottom-button exact row geometry correction")
