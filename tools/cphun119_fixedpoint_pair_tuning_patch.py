from pathlib import Path

ELIGIBLE_PAIRS = ['bó', 'bő', 'bö', 'óö', 'öd', 'öé', 'öó', 'öö', 'öő', 'őö', 'bc', 'be', 'bo', 'bq', 'oc', 'od', 'oe', 'oo', 'oq', 'oé', 'oó', 'oö', 'oő', 'pc', 'pd', 'pe', 'po', 'pé', 'pó', 'pö', 'pő', 'óc', 'óe', 'óo', 'óq', 'öc', 'öe', 'öo', 'öq', 'őc', 'őe', 'őo', 'őq', 'zz', 'gp', 'jx', 'bd', 'ód', 'óó', 'óő', 'őd', 'őó', 'őő', 'bé', 'éb', 'őb', 'lá', 'áö', 'öb', 'ba', 'ád', 'ká', 'jw', 'wg', 'zm', 'zn', 'zr', 'ka', 'bb', 'jd', 'jq', 'jé', 'jó', 'jő', 'qq', 'áó', 'áő', 'ób', 'jv', 'xz', 'zx', 'gf', 'gi', 'gm', 'gn', 'gr', 'gí', 'jö', 'sw', 'bg', 'ec', 'ed', 'ee', 'eg', 'eo', 'eq', 'eé', 'eó', 'eö', 'eő', 'oa', 'og', 'oá', 'éc', 'ée', 'ég', 'éo', 'éq', 'óa', 'óg', 'öa', 'ög', 'őa', 'őg', 'ac', 'ad', 'ae', 'ao', 'aq', 'aé', 'aó', 'aö', 'aő', 'eb', 'es', 'gg', 'jc', 'je', 'jo', 'ob', 'pb', 'qc', 'qd', 'qe', 'qo', 'qé', 'qó', 'qö', 'qő', 'ác', 'áe', 'áo', 'áq', 'és', 'pw', 'sx', 'ks', 'wa', 'ws', 'wá', 'za', 'zá', 'la', 'nc', 'nd', 'ne', 'no', 'nq', 'né', 'nó', 'nö', 'nő', 'pv', 'vo', 'vó', 'vö', 'vő', 'wc', 'wd', 'we', 'wo', 'wq', 'wé', 'wó', 'wö', 'wő', 'pq', 'óé', 'őé', 'cw', 'bá', 'gx', 'kz', 'sv', 'yo', 'yó', 'yö', 'yő', 'jz', 'qz', 'sz', 'zb', 'aa', 'ag', 'aá', 'gc', 'gd', 'ge', 'go', 'gé', 'gó', 'gö', 'gő', 'pa', 'pá', 'áa', 'ág', 'ex', 'éx', 'cx', 'va', 'vá', 'zf', 'zi', 'zí', 'sy', 'gh', 'gk', 'gl', 'jg', 'jm', 'jn', 'jr', 'na', 'ng', 'ná', 'vg', 'zs', 'dx', 'lx', 'xf', 'xm', 'xn', 'xr', 'gb', 'sa', 'sá', 'ya', 'yá', 'cv', 'vz', 'cz', 'cm', 'cn', 'cr', 'tz', 'xb', 'éö', 'já', 'áá', 'áé', 'km', 'kn', 'kr', 'cf', 'jí', 'as', 'ga', 'gá', 'jb', 'qy', 'sc', 'sd', 'so', 'sq', 'st', 'só', 'sö', 'ső', 'áb', 'ás', 'ab', 'bu', 'ja', 'qa', 'qá', 'sb', 'cb', 'ez', 'kp', 'éz', 'dw', 'lw', 'ns', 'qw', 'uw', 'wb', 'úw', 'üw', 'űw', 'ci', 'cí', 'ef', 'em', 'en', 'er', 'nb', 'vc', 'vd', 've', 'vq', 'vé', 'ém', 'én', 'ér', 'jy', 'kj', 'xi', 'xj', 'xp', 'xí', 'cg', 'ts', 'kg', 'xa', 'xá', 'az', 'iz', 'nw', 'nz', 'zt', 'áz', 'íz', 'yc', 'yd', 'ye', 'yé', 'bw', 'ew', 'ow', 'zg', 'éw', 'ów', 'öw', 'őw', 'kx', 'bf', 'bh', 'bj', 'bk', 'bl', 'bú', 'bű', 'hé', 'hó', 'hő', 'pj', 'pp', 'éf', 'éh', 'ék', 'él', 'éí', 'íé', 'íó', 'íő', 'óf', 'óh', 'ój', 'ók', 'ól', 'óí', 'óú', 'óű', 'őf', 'őh', 'őj', 'ők', 'ől', 'őí', 'őú', 'őű', 'bs', 'by', 'ej', 'et', 'eu', 'ey', 'eú', 'eü', 'eű', 'os', 'ps', 'se', 'sj', 'sp', 'su', 'sé', 'sú', 'sü', 'sű', 'éu', 'éy', 'ós', 'ös', 'ős', 'bx', 'bi', 'bt', 'bí', 'bü', 'dv', 'dz', 'dö', 'fz', 'id', 'iá', 'ié', 'ió', 'iő', 'lv', 'lz', 'qv', 'uv', 'uz', 'wz', 'zh', 'zj', 'zk', 'zl', 'zp', 'éi', 'éü', 'íd', 'ói', 'óü', 'öj', 'öú', 'öü', 'öű', 'úv', 'úz', 'úö', 'üd', 'üv', 'üz', 'üá', 'üé', 'üó', 'üö', 'üő', 'ői', 'őü', 'űv', 'űz', 'űö', 'bp', 'js', 'nv', 'oj', 'ot', 'ou', 'oú', 'oü', 'oű', 'qb', 'qs', 'óu', 'öu', 'őu', 'hö', 'iö', 'lö', 'íö', 'öf', 'öh', 'öi', 'ök', 'öl', 'öí', 'bv', 'bz', 'ck', 'ev', 'ha', 'hg', 'ia', 'ig', 'ma', 'mg', 'má', 'ov', 'oz', 'sf', 'sm', 'sn', 'sr', 'év', 'ía', 'íg', 'óv', 'óz', 'öv', 'öz', 'őv', 'őz', 'ax', 'ay', 'áx', 'áy', 'öt', 'gq', 'pg', 'óá', 'őá', 'bm', 'bn', 'br', 'ei', 'eí', 'hz', 'im', 'in', 'ir', 'zu', 'zú', 'zü', 'zű', 'ét', 'ím', 'ín', 'ír', 'ót', 'öá', 'őt', 'cj', 'cp', 'dy', 'ta', 'tg', 'uy', 'yb', 'úy', 'üy', 'űy', 'ca', 'cá', 'hv', 'hw', 'ké', 'kó', 'kő', 'mv', 'mw', 'ny', 'dá', 'hd', 'lé', 'ló', 'lő', 'éj', 'íá', 'úd', 'űd', 'dm', 'dn', 'dr', 'lm', 'ln', 'lr', 'ly', 'mz', 'qx', 'um', 'un', 'ur', 'vb', 'úm', 'ún', 'úr', 'üm', 'ün', 'ür', 'űm', 'űn', 'űr', 'ek', 'kö', 'of', 'om', 'on', 'or', 'tá', 'óm', 'ón', 'ór', 'öm', 'ön', 'ör', 'őm', 'őn', 'őr', 'ox', 'px', 'óx', 'öx', 'őx', 'pz', 'yq', 'zd', 'zq', 'nx', 'da', 'dc', 'de', 'dg', 'do', 'dq', 'ep', 'op', 'oy', 'pt', 'pu', 'py', 'pú', 'pü', 'pű', 'tb', 'ua', 'uc', 'ud', 'ue', 'ug', 'uo', 'uq', 'uá', 'ué', 'uó', 'uö', 'uő', 'ép', 'óp', 'óy', 'öp', 'öy', 'úa', 'úc', 'úe', 'úg', 'úo', 'úq', 'üa', 'üc', 'üe', 'üg', 'üo', 'üq', 'őp', 'őy', 'űa', 'űc', 'űe', 'űg', 'űo', 'űq']

packed = sorted((ord(p[0]) << 16) | ord(p[1]) for p in ELIGIBLE_PAIRS)
if len(packed) != 655 or len(set(packed)) != 655:
    raise SystemExit("Expected exactly 655 unique optimizable pairs")
array_lines = []
for i in range(0, len(packed), 8):
    array_lines.append("    " + ", ".join(f"0x{v:08X}u" for v in packed[i:i+8]) + ",")
header = '''#pragma once
#include <EpdFontFamily.h>
#include <Utf8.h>
#include <cstddef>
#include <cstdint>
namespace LetterSpacingOptimization {
constexpr uint32_t OPTIMIZABLE_PAIRS[] = {
%s
};
static_assert(sizeof(OPTIMIZABLE_PAIRS) / sizeof(OPTIMIZABLE_PAIRS[0]) == 655,
              "Optimizable pair table must contain 655 entries");
constexpr uint8_t STEP_FP4 = 4;
constexpr uint8_t ONE_PX_FP4 = 16;
constexpr uint8_t MAX_EXTRA_PX_PER_LINE = 4;
struct Accumulator { uint8_t fp4 = 0; uint8_t usedPx = 0; };
inline bool isOptimizablePair(uint32_t left, uint32_t right) {
  if (left > 0xFFFFu || right > 0xFFFFu) return false;
  const uint32_t key = (left << 16) | right;
  size_t lo = 0, hi = sizeof(OPTIMIZABLE_PAIRS) / sizeof(OPTIMIZABLE_PAIRS[0]);
  while (lo < hi) {
    const size_t mid = lo + (hi - lo) / 2;
    if (OPTIMIZABLE_PAIRS[mid] < key) lo = mid + 1; else hi = mid;
  }
  return lo < sizeof(OPTIMIZABLE_PAIRS) / sizeof(OPTIMIZABLE_PAIRS[0]) && OPTIMIZABLE_PAIRS[lo] == key;
}
inline uint8_t consumePair(uint32_t left, uint32_t right, EpdFontFamily::Style style, Accumulator& acc) {
  if (style != EpdFontFamily::REGULAR || acc.usedPx >= MAX_EXTRA_PX_PER_LINE || !isOptimizablePair(left, right)) return 0;
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

p = Path("lib/Epub/Epub/blocks/TextBlock.cpp")
t = p.read_text(encoding="utf-8")
start = t.index("void drawTrackedText(")
end = t.index("\n}\n\n}  // namespace", start) + 2
new_function = r'''void drawTrackedText(const GfxRenderer& renderer, const int fontId, const int x, const int y, const char* text,
                     const EpdFontFamily::Style style, const BidiUtils::BidiBaseDir baseDir,
                     const uint8_t letterSpacingPx, const bool alignTrailingShortHyphenInk,
                     LetterSpacingOptimization::Accumulator* optimizationAcc) {
  if (text == nullptr || *text == '\0') return;

  const bool adjustTrailingHyphen = alignTrailingShortHyphenInk && endsWithShortHyphen(text);
  if (letterSpacingPx == 0) {
    if (!adjustTrailingHyphen) {
      renderer.drawText(fontId, x, y, text, true, style, baseDir);
      return;
    }
    const size_t len = strlen(text);
    const std::string prefix(text, len - SHORT_HYPHEN_BYTES);
    if (!prefix.empty()) renderer.drawText(fontId, x, y, prefix.c_str(), true, style, baseDir);
    const int fullAdvance = renderer.getTextAdvanceX(fontId, text, style);
    const int hyphenAdvance = renderer.getTextAdvanceX(fontId, SHORT_HYPHEN_UTF8, style);
    const int hyphenPenX = x + fullAdvance - hyphenAdvance;
    renderer.drawText(fontId, hyphenPenX + trailingShortHyphenInkShift(renderer, fontId, style), y,
                      SHORT_HYPHEN_UTF8, true, style, baseDir);
    return;
  }

  if (letterSpacingPx == 2 && optimizationAcc) {
    const auto* cursor = reinterpret_cast<const uint8_t*>(text);
    std::string nativePrefix;
    uint32_t previous = 0;
    int optimizationOffset = 0;
    while (*cursor) {
      const auto* glyphStart = cursor;
      const uint32_t cp = utf8NextCodepoint(&cursor);
      if (cp == 0) break;
      const size_t glyphBytes = static_cast<size_t>(cursor - glyphStart);
      char glyphText[5];
      memcpy(glyphText, glyphStart, glyphBytes);
      glyphText[glyphBytes] = '\0';
      if (previous != 0) {
        optimizationOffset += LetterSpacingOptimization::consumePair(previous, cp, style, *optimizationAcc);
      }
      nativePrefix.append(reinterpret_cast<const char*>(glyphStart), glyphBytes);
      const int prefixAdvance = renderer.getTextAdvanceX(fontId, nativePrefix.c_str(), style);
      const int glyphAdvance = renderer.getTextAdvanceX(fontId, glyphText, style);
      int glyphX = x + prefixAdvance - glyphAdvance + optimizationOffset;
      if (adjustTrailingHyphen && cp == 0x2011 && *cursor == 0) {
        glyphX += trailingShortHyphenInkShift(renderer, fontId, style);
      }
      renderer.drawText(fontId, glyphX, y, glyphText, true, style, baseDir);
      previous = cp;
    }
    return;
  }

  const auto* cursor = reinterpret_cast<const uint8_t*>(text);
  int penX = x;
  uint32_t previous = 0;
  while (*cursor) {
    const auto* glyphStart = cursor;
    const uint32_t cp = utf8NextCodepoint(&cursor);
    if (cp == 0) break;
    if (previous != 0) {
      penX += renderer.getKerning(fontId, previous, cp, style) + letterSpacingPx;
    }
    const size_t glyphBytes = static_cast<size_t>(cursor - glyphStart);
    char glyphText[5];
    memcpy(glyphText, glyphStart, glyphBytes);
    glyphText[glyphBytes] = '\0';
    int glyphX = penX;
    if (adjustTrailingHyphen && cp == 0x2011 && *cursor == 0) {
      glyphX += trailingShortHyphenInkShift(renderer, fontId, style);
    }
    renderer.drawText(fontId, glyphX, y, glyphText, true, style, baseDir);
    penX += renderer.getTextAdvanceX(fontId, glyphText, style);
    previous = cp;
  }
}'''
t = t[:start] + new_function + t[end:]
p.write_text(t, encoding="utf-8")
