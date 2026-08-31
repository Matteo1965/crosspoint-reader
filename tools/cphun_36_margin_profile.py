from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Expected patch anchor not found in {path}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Refine the user-facing horizontal margin range to the requested values:
# 10, 12, 14, 16, 18, 20, 22, 24 px.
replace_once(
    "src/CrossPointSettings.h",
    "  static constexpr uint8_t SCREEN_MARGIN_MIN = 8;\n"
    "  static constexpr uint8_t SCREEN_MARGIN_MAX = 36;\n"
    "  static constexpr uint8_t SCREEN_MARGIN_STEP = 4;\n",
    "  static constexpr uint8_t SCREEN_MARGIN_MIN = 10;\n"
    "  static constexpr uint8_t SCREEN_MARGIN_MAX = 24;\n"
    "  static constexpr uint8_t SCREEN_MARGIN_STEP = 2;\n",
)

reader_path = Path("src/activities/reader/EpubReaderActivity.cpp")
text = reader_path.read_text(encoding="utf-8")

# Dictionary word-selection coordinates must use the same asymmetric margins as
# the rendered page so the selection overlay remains aligned with the text.
old = (
    "  orientedMarginTop += SETTINGS.screenMargin;\n"
    "  orientedMarginLeft += SETTINGS.screenMargin;\n\n"
    "  startActivityForResult(std::make_unique<DictionaryWordSelectActivity>"
)
new = (
    "  const int verticalScreenMargin = std::max(0, static_cast<int>(SETTINGS.screenMargin) - 4);\n"
    "  orientedMarginTop += verticalScreenMargin;\n"
    "  orientedMarginLeft += SETTINGS.screenMargin;\n\n"
    "  startActivityForResult(std::make_unique<DictionaryWordSelectActivity>"
)
if new not in text:
    if old not in text:
        raise SystemExit("Dictionary margin anchor not found")
    text = text.replace(old, new, 1)

# Reader viewport: left/right use the selected margin unchanged, while top and
# bottom use selected margin - 4 px.
old = (
    "  orientedMarginTop += SETTINGS.screenMargin;\n"
    "  orientedMarginLeft += SETTINGS.screenMargin;\n"
    "  orientedMarginRight += SETTINGS.screenMargin;\n\n"
    "  const uint8_t statusBarHeight = UITheme::getInstance().getStatusBarHeight();\n"
)
new = (
    "  const int verticalScreenMargin = std::max(0, static_cast<int>(SETTINGS.screenMargin) - 4);\n"
    "  orientedMarginTop += verticalScreenMargin;\n"
    "  orientedMarginLeft += SETTINGS.screenMargin;\n"
    "  orientedMarginRight += SETTINGS.screenMargin;\n\n"
    "  const uint8_t statusBarHeight = UITheme::getInstance().getStatusBarHeight();\n"
)
if new not in text:
    if old not in text:
        raise SystemExit("Reader viewport margin anchor not found")
    text = text.replace(old, new, 1)

text = text.replace(
    "        std::max(SETTINGS.screenMargin,\n                 static_cast<uint8_t>(statusBarHeight + UITheme::getInstance().getMetrics().statusBarVerticalMargin));",
    "        std::max(verticalScreenMargin,\n                 static_cast<int>(statusBarHeight + UITheme::getInstance().getMetrics().statusBarVerticalMargin));",
    1,
)
text = text.replace(
    "    orientedMarginBottom += std::max(SETTINGS.screenMargin, statusBarHeight);",
    "    orientedMarginBottom += std::max(verticalScreenMargin, static_cast<int>(statusBarHeight));",
    1,
)

reader_path.write_text(text, encoding="utf-8")

# Safety/intent checks.
settings = Path("src/CrossPointSettings.h").read_text(encoding="utf-8")
reader = reader_path.read_text(encoding="utf-8")
for needle in [
    "SCREEN_MARGIN_MIN = 10",
    "SCREEN_MARGIN_MAX = 24",
    "SCREEN_MARGIN_STEP = 2",
]:
    if needle not in settings:
        raise SystemExit(f"Missing margin setting marker: {needle}")
if reader.count("verticalScreenMargin") < 4:
    raise SystemExit("Asymmetric vertical margin was not applied to all expected reader paths")
if "static_cast<int>(SETTINGS.screenMargin) - 4" not in reader:
    raise SystemExit("Vertical -4 px rule missing")

print("Applied CPHUN-36 refined 10..24 margin profile with vertical -4 px")
