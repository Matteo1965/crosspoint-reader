from pathlib import Path
import re


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 marker, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Optikai margó: KI = 0 px; BE = screenMargin - 1, leaving exactly
# one physical pixel as the right-side safety strip.
replace_once(
    "src/CrossPointSettings.cpp",
    "spec.hangingPunctuationLimitPx = hangingPunctuation ? static_cast<uint8_t>(std::min<int>(31, screenMargin)) : 0;",
    "spec.hangingPunctuationLimitPx = hangingPunctuation && screenMargin > 0 ? static_cast<uint8_t>(screenMargin - 1) : 0;",
    "optical margin render spec",
)

p = Path("lib/Epub/Epub/ParsedText.cpp")
s = p.read_text(encoding="utf-8")

old_head = """int hangingPunctuationAllowance(const GfxRenderer& renderer, const int fontId, const std::string& word,
                                const EpdFontFamily::Style style, const uint8_t packedSetting) {
  const uint8_t percentStep = packedSetting >> 5;
  const uint8_t pixelLimit = static_cast<uint8_t>(packedSetting & 0x1F);
  if (percentStep == 0 || pixelLimit == 0 || word.empty()) return 0;
"""
new_head = """int hangingPunctuationAllowance(const GfxRenderer& renderer, const int fontId, const std::string& word,
                                const EpdFontFamily::Style style, const uint8_t pixelLimit) {
  if (pixelLimit == 0 || word.empty()) return 0;
"""
if s.count(old_head) != 1:
    raise SystemExit(f"hanging allowance header: expected 1 marker, found {s.count(old_head)}")
s = s.replace(old_head, new_head, 1)

old_tail = """  const int proportionalAdvance = (punctuationAdvance * std::min<int>(percentStep, 5) + 4) / 5;
  return std::min<int>(pixelLimit, proportionalAdvance);
"""
new_tail = """  // Optikai margó is a simple OFF/ON control. ON allows 100% of the
  // punctuation contribution to hang, capped by screenMargin - 1.
  return std::min<int>(pixelLimit, punctuationAdvance);
"""
if s.count(old_tail) != 1:
    raise SystemExit(f"hanging allowance tail: expected 1 marker, found {s.count(old_tail)}")
s = s.replace(old_tail, new_tail, 1)

# Fixed dialogue spacing must use the font's natural 100% space. General
# Min. word spacing uses a different second argument and is deliberately untouched.
pattern = re.compile(
    r"scaledNormalSpaceAdvance\(\s*"
    r"(renderer\.getSpaceAdvance\((?:[^()]|\([^()]*\))*\))\s*,\s*"
    r"minimumSpacePercent_\s*\)",
    re.MULTILINE,
)
s, count = pattern.subn(r"\1", s)
if count < 3:
    raise SystemExit(f"fixed dialogue natural-space replacements: expected at least 3, found {count}")

p.write_text(s, encoding="utf-8")

# Keep the dictionary HTML parser call synchronized with the CPHUN-19
# ChapterHtmlSlimParser constructor. Dictionary pages inherit the user's
# embedded soft-hyphen and letter-spacing settings just like normal EPUB text.
replace_once(
    "src/util/DictHtmlPages.cpp",
    """        SETTINGS.hyphenationEnabled, SETTINGS.focusReadingEnabled, /*hangingPunctuationLimitPx=*/0,
        SETTINGS.fixedDialogueSpacing != 0,
""",
    """        SETTINGS.hyphenationEnabled, SETTINGS.softHyphenEnabled != 0, SETTINGS.focusReadingEnabled,
        /*hangingPunctuationLimitPx=*/0, SETTINGS.fixedDialogueSpacing != 0, SETTINGS.letterSpacingLimitPercent,
""",
    "dictionary ChapterHtmlSlimParser constructor",
)

print(f"CPHUN-19 margin/dialogue/dictionary sync fix applied; fixed-dialogue replacements={count}")
