from pathlib import Path

def replace_once(path, old, new):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count} for {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

SAFE_PAIRS = ['bó', 'bő', 'bö', 'óö', 'öd', 'öé', 'öó', 'öö', 'öő', 'őö', 'bc', 'be', 'bo', 'bq', 'oc', 'od', 'oe', 'oo', 'oq', 'oé', 'oó', 'oö', 'oő', 'pc', 'pd', 'pe', 'po', 'pé', 'pó', 'pö', 'pő', 'óc', 'óe', 'óo', 'óq', 'öc', 'öe', 'öo', 'öq', 'őc', 'őe', 'őo', 'őq', 'zz', 'gp', 'jx', 'bd', 'ód', 'óó', 'óő', 'őd', 'őó', 'őő', 'bé', 'éb', 'őb', 'lá', 'áö', 'öb', 'ba', 'ád', 'ká', 'jw', 'wg', 'zm', 'zn', 'zr', 'ka', 'bb', 'jd', 'jq', 'jé', 'jó', 'jő', 'qq', 'áó', 'áő', 'ób', 'jv', 'xz', 'zx', 'gf', 'gi', 'gm', 'gn', 'gr', 'gí', 'jö', 'sw', 'bg', 'ec', 'ed', 'ee', 'eg', 'eo', 'eq', 'eé', 'eó', 'eö', 'eő', 'oa', 'og', 'oá', 'éc', 'ée', 'ég', 'éo', 'éq', 'óa', 'óg', 'öa', 'ög', 'őa', 'őg', 'ac', 'ad', 'ae', 'ao', 'aq', 'aé', 'aó', 'aö', 'aő', 'eb', 'es', 'jc', 'je', 'jo', 'ob', 'pb', 'qc', 'qd', 'qe', 'qo', 'qé', 'qó', 'qö', 'qő', 'ác', 'áe', 'áo', 'áq', 'és', 'pw', 'sx', 'ks', 'wa', 'ws', 'wá', 'za', 'zá', 'la', 'nc', 'nd', 'ne', 'no', 'nq', 'né', 'nó', 'nö', 'nő', 'pv', 'vo', 'vó', 'vö', 'vő', 'wc', 'wd', 'we', 'wo', 'wq', 'wé', 'wó', 'wö', 'wő', 'pq', 'óé', 'őé', 'bá', 'kz', 'sv', 'yo', 'yó', 'yö', 'yő', 'jz', 'qz', 'sz', 'zb', 'aa', 'ag', 'aá', 'gc', 'gd', 'ge', 'go', 'gé', 'gó', 'gö', 'gő', 'pa', 'pá', 'áa', 'ág']
packed = sorted((ord(p[0]) << 16) | ord(p[1]) for p in SAFE_PAIRS)
if len(packed) != 204 or len(set(packed)) != 204:
    raise SystemExit("Expected exactly 204 unique safe pairs")
array_lines = []
for i in range(0, len(packed), 8):
    array_lines.append("    " + ", ".join(f"0x{v:08X}u" for v in packed[i:i+8]) + ",")
header = '''#pragma once
#include <EpdFontFamily.h>
#include <Utf8.h>
#include <cstddef>
#include <cstdint>
namespace LetterSpacingOptimization {
constexpr uint32_t SAFE_PAIRS[] = {
%s
};
static_assert(sizeof(SAFE_PAIRS) / sizeof(SAFE_PAIRS[0]) == 204, "Safe pair table must contain 204 entries");
constexpr uint8_t STEP_FP4 = 4;
constexpr uint8_t ONE_PX_FP4 = 16;
constexpr uint8_t MAX_EXTRA_PX_PER_LINE = 4;
struct Accumulator { uint8_t fp4 = 0; uint8_t usedPx = 0; };
inline bool isSafePair(uint32_t left, uint32_t right) {
  if (left > 0xFFFFu || right > 0xFFFFu) return false;
  const uint32_t key = (left << 16) | right;
  size_t lo = 0, hi = sizeof(SAFE_PAIRS) / sizeof(SAFE_PAIRS[0]);
  while (lo < hi) {
    const size_t mid = lo + (hi - lo) / 2;
    if (SAFE_PAIRS[mid] < key) lo = mid + 1; else hi = mid;
  }
  return lo < sizeof(SAFE_PAIRS) / sizeof(SAFE_PAIRS[0]) && SAFE_PAIRS[lo] == key;
}
inline uint8_t consumePair(uint32_t left, uint32_t right, EpdFontFamily::Style style, Accumulator& acc) {
  if (style != EpdFontFamily::REGULAR || acc.usedPx >= MAX_EXTRA_PX_PER_LINE || !isSafePair(left, right)) return 0;
  acc.fp4 = static_cast<uint8_t>(acc.fp4 + STEP_FP4);
  if (acc.fp4 < ONE_PX_FP4) return 0;
  acc.fp4 = static_cast<uint8_t>(acc.fp4 - ONE_PX_FP4);
  ++acc.usedPx;
  return 1;
}
inline uint8_t consumeWord(const char* text, EpdFontFamily::Style style, Accumulator& acc) {
  if (!text || !*text || style != EpdFontFamily::REGULAR || acc.usedPx >= MAX_EXTRA_PX_PER_LINE) return 0;
  const auto* cursor = reinterpret_cast<const uint8_t*>(text);
  uint32_t prev = 0; uint8_t extra = 0;
  while (*cursor) {
    const uint32_t cp = utf8NextCodepoint(&cursor);
    if (!cp) break;
    if (prev) extra = static_cast<uint8_t>(extra + consumePair(prev, cp, style, acc));
    prev = cp;
  }
  return extra;
}
}  // namespace LetterSpacingOptimization
''' % "\n".join(array_lines)
Path("lib/Epub/Epub/LetterSpacingOptimization.h").write_text(header, encoding="utf-8")

replace_once("src/CrossPointSettings.h",
'''  uint16_t letterSpacingLimitPercent = 0;
  // Minimum natural word-space width''',
'''  uint16_t letterSpacingLimitPercent = 0;
  uint8_t letterSpacingOptimization = 0;
  // Minimum natural word-space width''')

replace_once("src/CrossPointSettings.cpp",
'''  doc["letterSpacingLimitPercent"] = letterSpacingLimitPercent;
  doc["softHyphenEnabled"] = softHyphenEnabled;''',
'''  doc["letterSpacingLimitPercent"] = letterSpacingLimitPercent;
  doc["letterSpacingOptimization"] = letterSpacingOptimization;
  doc["softHyphenEnabled"] = softHyphenEnabled;''')

p=Path("src/CrossPointSettings.cpp")
t=p.read_text(encoding="utf-8")
s='  letterSpacingLimitPercent = doc["letterSpacingLimitPercent"] | (uint16_t)0;\n'
a=t.index(s)
b=t.index('  minimumSpacePercent = doc["minimumSpacePercent"] | (uint8_t)100;',a)
t=t[:a]+'''  letterSpacingLimitPercent = doc["letterSpacingLimitPercent"] | (uint16_t)0;
  constexpr uint16_t validLetterSpacingThresholds[] = {0, 550, 530, 500, 460, 410, 350, 280};
  if (std::find(std::begin(validLetterSpacingThresholds), std::end(validLetterSpacingThresholds),
                letterSpacingLimitPercent) == std::end(validLetterSpacingThresholds)) {
    letterSpacingLimitPercent = 0;
    needsResave = true;
  }
  letterSpacingOptimization = (doc["letterSpacingOptimization"] | (uint8_t)0) ? 1 : 0;
'''+t[b:]
p.write_text(t,encoding="utf-8")

replace_once("src/CrossPointSettings.cpp",
'''  spec.letterSpacingLimitPercent = letterSpacingLimitPercent;
  spec.minimumSpacePercent = minimumSpacePercent;''',
'''  const bool bitter16Optimization = letterSpacingOptimization && letterSpacingLimitPercent > 0 &&
                                    fontPointSize == 16 && strcmp(sdFontFamilyName, "Bitter") == 0;
  spec.letterSpacingLimitPercent =
      static_cast<uint16_t>(letterSpacingLimitPercent | (bitter16Optimization ? 0x8000u : 0u));
  spec.minimumSpacePercent = minimumSpacePercent;''')

replace_once("src/activities/settings/TextSettingsActivity.h",
'''    LetterSpacingCorrection,
    ScreenMargin,''',
'''    LetterSpacingCorrection,
    LetterSpacingOptimization,
    ScreenMargin,''')

replace_once("src/activities/settings/TextSettingsActivity.cpp",
'''        } else if (i == static_cast<int>(LayoutRow::ScreenMargin)) {''',
'''        } else if (i == static_cast<int>(LayoutRow::LetterSpacingOptimization)) {
          item.label = I18N.getLanguage() == Language::HU ? "Betűköz optimalizálás" : "Letter spacing optimization";
        } else if (i == static_cast<int>(LayoutRow::ScreenMargin)) {''')

p=Path("src/activities/settings/TextSettingsActivity.cpp")
t=p.read_text(encoding="utf-8")
corr=t.index("case LayoutRow::LetterSpacingCorrection:")
needle='''      requestUpdate();
      break;
    }
    case LayoutRow::ShortHyphen:'''
pos=t.index(needle,corr)
replacement='''      requestUpdate();
      break;
    }
    case LayoutRow::LetterSpacingOptimization:
      if (SETTINGS.letterSpacingLimitPercent == 0) {
        requestUpdate();
        break;
      }
      SETTINGS.letterSpacingOptimization = !SETTINGS.letterSpacingOptimization;
      SETTINGS.saveToFile();
      requestUpdate();
      break;
    case LayoutRow::ShortHyphen:'''
t=t[:pos]+t[pos:].replace(needle,replacement,1)
p.write_text(t,encoding="utf-8")

replace_once("src/activities/settings/TextSettingsActivity.cpp",
'''    case LayoutRow::ScreenMargin:
      return std::to_string(SETTINGS.screenMargin);''',
'''    case LayoutRow::LetterSpacingOptimization:
      return SETTINGS.letterSpacingOptimization ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);
    case LayoutRow::ScreenMargin:
      return std::to_string(SETTINGS.screenMargin);''')

replace_once("lib/Epub/Epub/ParsedText.h",
'''  uint16_t letterSpacingLimitPercent;
  bool isNaturalAlign;''',
'''  uint16_t letterSpacingLimitPercent;
  bool letterSpacingOptimization;
  bool isNaturalAlign;''')
replace_once("lib/Epub/Epub/ParsedText.h",
'''        fixedDialogueSpacing(fixedDialogueSpacing),
        letterSpacingLimitPercent(letterSpacingLimitPercent),
        isNaturalAlign(false),''',
'''        fixedDialogueSpacing(fixedDialogueSpacing),
        letterSpacingLimitPercent(static_cast<uint16_t>(letterSpacingLimitPercent & 0x7FFFu)),
        letterSpacingOptimization((letterSpacingLimitPercent & 0x8000u) != 0),
        isNaturalAlign(false),''')

p=Path("lib/Epub/Epub/ParsedText.cpp")
t=p.read_text(encoding="utf-8")
t=t.replace('#include "ParsedText.h"\n','#include "ParsedText.h"\n#include "LetterSpacingOptimization.h"\n',1)
old='''        for (const auto& w : lineWords) {
          const uint32_t cps = countCodepoints(w);
          if (cps > 1) trackingExtraTotal += static_cast<int>(cps - 1);
        }
        if (trackingExtraTotal > 0 && trackingExtraTotal < spareSpace) letterSpacingPx = 1;'''
new='''        if (letterSpacingOptimization) {
          LetterSpacingOptimization::Accumulator optAcc;
          for (size_t i = 0; i < lineWords.size(); ++i) {
            trackingExtraTotal += LetterSpacingOptimization::consumeWord(lineWords[i].c_str(), lineWordStyles[i], optAcc);
          }
          if (trackingExtraTotal > 0 && trackingExtraTotal < spareSpace) letterSpacingPx = 2;
        } else {
          for (const auto& w : lineWords) {
            const uint32_t cps = countCodepoints(w);
            if (cps > 1) trackingExtraTotal += static_cast<int>(cps - 1);
          }
          if (trackingExtraTotal > 0 && trackingExtraTotal < spareSpace) letterSpacingPx = 1;
        }'''
if t.count(old)!=1: raise SystemExit(f"tracking block matches={t.count(old)}")
t=t.replace(old,new,1)
loop='''      size_t justifyGapIndex = 0;
      int hyphenMicroRemaining = hyphenMicroTotal;
      int punctuationMicroRemaining = punctuationMicroTotal;
      for (size_t wordIdx = 0; wordIdx < lineWordCount; wordIdx++) {'''
loopnew='''      size_t justifyGapIndex = 0;
      int hyphenMicroRemaining = hyphenMicroTotal;
      int punctuationMicroRemaining = punctuationMicroTotal;
      LetterSpacingOptimization::Accumulator optPositionAcc;
      for (size_t wordIdx = 0; wordIdx < lineWordCount; wordIdx++) {
        const int wordTrackingExtra = letterSpacingPx == 2
            ? LetterSpacingOptimization::consumeWord(lineWords[wordIdx].c_str(), lineWordStyles[wordIdx], optPositionAcc)
            : (letterSpacingPx ? static_cast<int>(std::max<uint32_t>(1, countCodepoints(lineWords[wordIdx])) - 1) * letterSpacingPx : 0);'''
if t.count(loop)!=1: raise SystemExit(f"LTR loop matches={t.count(loop)}")
t=t.replace(loop,loopnew,1)
expr='wordWidths[lastBreakAt + wordIdx] + (letterSpacingPx ? static_cast<int>(std::max<uint32_t>(1, countCodepoints(lineWords[wordIdx])) - 1) * letterSpacingPx : 0)'
if t.count(expr)!=2: raise SystemExit(f"position expr matches={t.count(expr)}")
t=t.replace(expr,'wordWidths[lastBreakAt + wordIdx] + wordTrackingExtra',2)
p.write_text(t,encoding="utf-8")

p=Path("lib/Epub/Epub/blocks/TextBlock.cpp")
t=p.read_text(encoding="utf-8")
t=t.replace('#include "../ParsedText.h"\n','#include "../ParsedText.h"\n#include "../LetterSpacingOptimization.h"\n',1)
sig='''                     const uint8_t letterSpacingPx, const bool alignTrailingShortHyphenInk) {'''
newsig='''                     const uint8_t letterSpacingPx, const bool alignTrailingShortHyphenInk,
                     LetterSpacingOptimization::Accumulator* optimizationAcc) {'''
if t.count(sig)!=1: raise SystemExit("signature not found")
t=t.replace(sig,newsig,1)
oldkern='''    if (previous != 0) {
      penX += renderer.getKerning(fontId, previous, cp, style) + letterSpacingPx;
    }'''
newkern='''    if (previous != 0) {
      int trackingExtra = letterSpacingPx == 1 ? 1 : 0;
      if (letterSpacingPx == 2 && optimizationAcc) {
        trackingExtra = LetterSpacingOptimization::consumePair(previous, cp, style, *optimizationAcc);
      }
      penX += renderer.getKerning(fontId, previous, cp, style) + trackingExtra;
    }'''
if t.count(oldkern)!=1: raise SystemExit("kern block not found")
t=t.replace(oldkern,newkern,1)
t=t.replace('''  if (simpleRender) {
    for (uint16_t i = 0; i < numWords; ++i) {''','''  if (simpleRender) {
    LetterSpacingOptimization::Accumulator optimizationAcc;
    for (uint16_t i = 0; i < numWords; ++i) {''',1)
t=t.replace('''      drawTrackedText(renderer, fontId, xposArr[i] + x, y, wordText(i), wordStyle(i), baseDir, letterSpacingPx,
                      alignTrailingShortHyphenInk);''','''      drawTrackedText(renderer, fontId, xposArr[i] + x, y, wordText(i), wordStyle(i), baseDir, letterSpacingPx,
                      alignTrailingShortHyphenInk, &optimizationAcc);''',1)
t=t.replace('''  for (uint16_t i = 0; i < numWords; i++) {
    const char* word = wordText(i);''','''  LetterSpacingOptimization::Accumulator optimizationAcc;
  for (uint16_t i = 0; i < numWords; i++) {
    const char* word = wordText(i);''',1)
t=t.replace('''      drawTrackedText(renderer, fontId, drawX, wordY, word, currentStyle, baseDir, letterSpacingPx,
                      alignTrailingShortHyphenInk);''','''      drawTrackedText(renderer, fontId, drawX, wordY, word, currentStyle, baseDir, letterSpacingPx,
                      alignTrailingShortHyphenInk, &optimizationAcc);''',1)
t=t.replace('if (letterSpacingPx != 0 && cps > 1) {','if (letterSpacingPx == 1 && cps > 1) {')
t=t.replace('if (letterSpacingPx != 0 && visibleCps > 1) {','if (letterSpacingPx == 1 && visibleCps > 1) {')
p.write_text(t,encoding="utf-8")

print("CPHUN-118 Experimental fixed-point optimizer patch applied")
