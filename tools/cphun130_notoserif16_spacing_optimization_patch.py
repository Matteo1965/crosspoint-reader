from pathlib import Path


def replace_once(path, old, new):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-130: {path}: expected one match, found {count}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# Noto Serif Regular 16 pt was measured independently at the firmware's native
# 150-DPI raster size. 35 lowercase Hungarian glyphs -> 1225 ordered pairs.
# Measurement/classification is identical to the Bitter run:
#   two ink thresholds; median/Q25/Q10 scanline gap; overlap rows; 4.4 kerning;
#   score = 34% Q25 + 26% median + 16% Q10 + 14% overlap + 10% kerning.
# The same >=60 eligibility threshold and geometry guardrails yield 75 pairs.
NOTO_SERIF_16_PAIRS = """bc be bo bq bs cs es gg gj gs oa oc od oe og oo oq os oá oé oó oö oő pc pd pe po ps pé pó pö pő sa sb sj sp st sá és óa óc ód óe óg óo óq ós óé óó óö óő öa öc öd öe ög öo öq ös öé öó öö öő őa őc őd őe őg őo őq ős őé őó őö őő""".split()
packed = sorted((ord(p[0]) << 16) | ord(p[1]) for p in NOTO_SERIF_16_PAIRS)
if len(packed) != 75 or len(set(packed)) != 75:
    raise SystemExit("CPHUN-130: expected exactly 75 unique Noto Serif 16 pairs")
lines = []
for i in range(0, len(packed), 8):
    lines.append("    " + ", ".join(f"0x{v:08X}u" for v in packed[i:i + 8]) + ",")
noto_array = """constexpr uint32_t NOTOSERIF_16_OPTIMIZABLE_PAIRS[] = {
%s
};
static_assert(sizeof(NOTOSERIF_16_OPTIMIZABLE_PAIRS) /
                  sizeof(NOTOSERIF_16_OPTIMIZABLE_PAIRS[0]) == 75,
              "Noto Serif 16 pair table must contain 75 entries");

enum class PairTable : uint8_t { Bitter16, NotoSerif16 };
constexpr int NOTOSERIF_16_OPTIMIZATION_FONT_ID = 17214534;

inline PairTable tableForFontId(const int fontId) {
  return fontId == NOTOSERIF_16_OPTIMIZATION_FONT_ID
             ? PairTable::NotoSerif16
             : PairTable::Bitter16;
}

""" % "\n".join(lines)

replace_once(
    "lib/Epub/Epub/LetterSpacingOptimization.h",
    "constexpr uint8_t ONE_PX_FP4 = 16;",
    noto_array + "constexpr uint8_t ONE_PX_FP4 = 16;",
)

replace_once(
    "lib/Epub/Epub/LetterSpacingOptimization.h",
    '''  uint8_t budgetPx = 0;

  Accumulator() = default;
  Accumulator(const uint8_t level, const uint8_t budget)
      : profileLevel(clampProfile(level)),
        budgetPx(std::min<uint8_t>(budget, profile(level).maxPxPerLine)) {}
};''',
    '''  uint8_t budgetPx = 0;
  PairTable pairTable = PairTable::Bitter16;

  Accumulator() = default;
  Accumulator(const uint8_t level, const uint8_t budget,
              const PairTable table = PairTable::Bitter16)
      : profileLevel(clampProfile(level)),
        budgetPx(std::min<uint8_t>(budget, profile(level).maxPxPerLine)),
        pairTable(table) {}
};''',
)

replace_once(
    "lib/Epub/Epub/LetterSpacingOptimization.h",
    '''inline bool isOptimizablePair(uint32_t left, uint32_t right) {
  if (left > 0xFFFFu || right > 0xFFFFu) return false;
  const uint32_t key = (left << 16) | right;
  size_t lo = 0, hi = sizeof(OPTIMIZABLE_PAIRS) / sizeof(OPTIMIZABLE_PAIRS[0]);
  while (lo < hi) {
    const size_t mid = lo + (hi - lo) / 2;
    if (OPTIMIZABLE_PAIRS[mid] < key) lo = mid + 1; else hi = mid;
  }
  return lo < sizeof(OPTIMIZABLE_PAIRS) / sizeof(OPTIMIZABLE_PAIRS[0]) &&
         OPTIMIZABLE_PAIRS[lo] == key;
}''',
    '''inline bool isOptimizablePair(const uint32_t left, const uint32_t right,
                              const PairTable table) {
  if (left > 0xFFFFu || right > 0xFFFFu) return false;
  const uint32_t key = (left << 16) | right;
  const uint32_t* pairs = table == PairTable::NotoSerif16
                              ? NOTOSERIF_16_OPTIMIZABLE_PAIRS
                              : OPTIMIZABLE_PAIRS;
  const size_t count = table == PairTable::NotoSerif16
                           ? sizeof(NOTOSERIF_16_OPTIMIZABLE_PAIRS) /
                                 sizeof(NOTOSERIF_16_OPTIMIZABLE_PAIRS[0])
                           : sizeof(OPTIMIZABLE_PAIRS) / sizeof(OPTIMIZABLE_PAIRS[0]);
  size_t lo = 0;
  size_t hi = count;
  while (lo < hi) {
    const size_t mid = lo + (hi - lo) / 2;
    if (pairs[mid] < key)
      lo = mid + 1;
    else
      hi = mid;
  }
  return lo < count && pairs[lo] == key;
}''',
)

replace_once(
    "lib/Epub/Epub/LetterSpacingOptimization.h",
    "      !isOptimizablePair(left, right)) {",
    "      !isOptimizablePair(left, right, acc.pairTable)) {",
)

# The layout measurement and both render paths choose the table from the actual
# resolved font ID, guaranteeing that measurement and emitted pixels agree.
replace_once(
    "lib/Epub/Epub/ParsedText.cpp",
    '''          LetterSpacingOptimization::Accumulator optAcc(
              letterSpacingOptimizationProfile, availableBudget);''',
    '''          LetterSpacingOptimization::Accumulator optAcc(
              letterSpacingOptimizationProfile, availableBudget,
              LetterSpacingOptimization::tableForFontId(fontId));''',
)
replace_once(
    "lib/Epub/Epub/ParsedText.cpp",
    '''      LetterSpacingOptimization::Accumulator optPositionAcc(
          LetterSpacingOptimization::unpackProfile(letterSpacingPx),
          LetterSpacingOptimization::unpackBudget(letterSpacingPx));''',
    '''      LetterSpacingOptimization::Accumulator optPositionAcc(
          LetterSpacingOptimization::unpackProfile(letterSpacingPx),
          LetterSpacingOptimization::unpackBudget(letterSpacingPx),
          LetterSpacingOptimization::tableForFontId(fontId));''',
)
replace_once(
    "lib/Epub/Epub/blocks/TextBlock.cpp",
    '''    LetterSpacingOptimization::Accumulator optimizationAcc(
        LetterSpacingOptimization::unpackProfile(letterSpacingPx),
        LetterSpacingOptimization::unpackBudget(letterSpacingPx));''',
    '''    LetterSpacingOptimization::Accumulator optimizationAcc(
        LetterSpacingOptimization::unpackProfile(letterSpacingPx),
        LetterSpacingOptimization::unpackBudget(letterSpacingPx),
        LetterSpacingOptimization::tableForFontId(fontId));''',
)
replace_once(
    "lib/Epub/Epub/blocks/TextBlock.cpp",
    '''  LetterSpacingOptimization::Accumulator optimizationAcc(
      LetterSpacingOptimization::unpackProfile(letterSpacingPx),
      LetterSpacingOptimization::unpackBudget(letterSpacingPx));''',
    '''  LetterSpacingOptimization::Accumulator optimizationAcc(
      LetterSpacingOptimization::unpackProfile(letterSpacingPx),
      LetterSpacingOptimization::unpackBudget(letterSpacingPx),
      LetterSpacingOptimization::tableForFontId(fontId));''',
)

# Enable profiles for built-in Noto Serif 16 as well as SD-card Bitter 16.
replace_once(
    "src/CrossPointSettings.cpp",
    '''  const uint8_t bitter16OptimizationProfile =
      letterSpacingLimitPercent > 0 && fontPointSize == 16 && strcmp(sdFontFamilyName, "Bitter") == 0
          ? std::min<uint8_t>(letterSpacingOptimization, 4)
          : 0;''',
    '''  const bool isBitter16 =
      fontPointSize == 16 && strcmp(sdFontFamilyName, "Bitter") == 0;
  const bool isNotoSerif16 =
      fontPointSize == 16 && sdFontFamilyName[0] == '\\0' && fontFamily == NOTOSERIF;
  const uint8_t bitter16OptimizationProfile =
      letterSpacingLimitPercent > 0 && (isBitter16 || isNotoSerif16)
          ? std::min<uint8_t>(letterSpacingOptimization, 4)
          : 0;''',
)

replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260914-129-EXP"',
    '#define CPHUN_BUILD_ID "CPHUN-260914-130-EXP"',
)
