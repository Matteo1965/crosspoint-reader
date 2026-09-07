#!/usr/bin/env bash
set -euo pipefail

UPSTREAM=https://github.com/crosspoint-reader/crosspoint-reader.git
COMMITS=(
  c6fe67d48d8b65f5dfdefae31f06d0bc9826f267
  7e42d070774e75f250c8ffefe5e9357dacd39eb2
  da3d50c245334155daccb85058f3645637fd6db4
  52444a0c973ef9ffe4dd719c92d2dccca9a4d778
  30992315663dfd181476880b873fa91a49ac8d87
  ce6c6cbce473e34a9271c34d374e5d7eb1c7695f
)

git remote add upstream "$UPSTREAM" 2>/dev/null || true
for c in "${COMMITS[@]}"; do
  git fetch upstream "$c"
done

for c in "${COMMITS[@]}"; do
  echo "=== Applying $c ==="
  if git cherry-pick --no-commit "$c"; then
    continue
  fi

  # CPHUN has its own newer section-cache format/version and extra render-spec
  # fields. Upstream commits in this batch only bump Section.cpp's version for
  # their layout change, so keep CPHUN's Section.cpp when it is the sole or one
  # of the conflicts and let the actual parser/rendering changes apply.
  conflicted="$(git diff --name-only --diff-filter=U)"
  echo "Conflicts:"
  echo "$conflicted"
  if grep -qx 'lib/Epub/Epub/Section.cpp' <<<"$conflicted"; then
    git checkout --ours lib/Epub/Epub/Section.cpp
    git add lib/Epub/Epub/Section.cpp
  fi

  remaining="$(git diff --name-only --diff-filter=U)"
  if [[ -n "$remaining" ]]; then
    echo "Unresolved CPHUN-64 conflicts remain:"
    echo "$remaining"
    exit 42
  fi
  git cherry-pick --continue || true
done

# badfa95: port only the EPUB parser superscript/subscript-link fix, not the
# unrelated formatting/test churn bundled in that upstream commit.
python3 - <<'PY'
from pathlib import Path

cpp = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp')
hdr = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h')
s = cpp.read_text()
h = hdr.read_text()

if 'applyVerticalAlignToEntry' not in s:
    anchor = '''void ChapterHtmlSlimParser::applyTextDecorationToEntry(StyleStackEntry& entry, const CssStyle& css) {
  if (css.hasTextDecoration()) {
    entry.hasTextDecoration = true;
    entry.textDecoration = css.textDecoration;
  }
}
'''
    addition = anchor + '''\nvoid ChapterHtmlSlimParser::applyVerticalAlignToEntry(StyleStackEntry& entry, const CssStyle& css) {
  if (!css.hasVerticalAlign()) return;
  if (css.verticalAlign == CssVerticalAlign::Super) {
    entry.hasSup = true;
    entry.sup = true;
  } else if (css.verticalAlign == CssVerticalAlign::Sub) {
    entry.hasSub = true;
    entry.sub = true;
  }
}
'''
    if anchor not in s:
        raise SystemExit('missing applyTextDecorationToEntry anchor')
    s = s.replace(anchor, addition, 1)

    # Internal EPUB link branch: add vertical-align after direction handling.
    link_anchor = '      applyDirectionToEntry(entry, cssStyle);\n      self->inlineStyleStack.push_back(entry);'
    if link_anchor not in s:
        raise SystemExit('missing internal-link style anchor')
    s = s.replace(link_anchor,
                  '      applyDirectionToEntry(entry, cssStyle);\n      applyVerticalAlignToEntry(entry, cssStyle);\n      self->inlineStyleStack.push_back(entry);', 1)

    # Generic inline branch may still contain the open-coded vertical-align block.
    old = '''      if (cssStyle.hasVerticalAlign()) {
        if (cssStyle.verticalAlign == CssVerticalAlign::Super) {
          entry.hasSup = true;
          entry.sup = true;
        } else if (cssStyle.verticalAlign == CssVerticalAlign::Sub) {
          entry.hasSub = true;
          entry.sub = true;
        }
      }
'''
    if old in s:
        s = s.replace(old, '      applyVerticalAlignToEntry(entry, cssStyle);\n', 1)
    cpp.write_text(s)

if 'applyVerticalAlignToEntry' not in h:
    h_anchor = '  static void applyTextDecorationToEntry(StyleStackEntry& entry, const CssStyle& css);\n'
    if h_anchor not in h:
        raise SystemExit('missing parser header style-helper anchor')
    h = h.replace(h_anchor, h_anchor + '  static void applyVerticalAlignToEntry(StyleStackEntry& entry, const CssStyle& css);\n', 1)
    hdr.write_text(h)

Path('src/CPHUNBuildId.h').write_text('#pragma once\n\n#define CPHUN_BUILD_ID "CPHUN-260907-64"\n')
PY

# Guard the imported fixes.
grep -F 'htmlEnded_' lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h
grep -F '!self->inRuby' lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp
grep -F 'fallbackTableRowToStacked' lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp
grep -F 'stripTrailingImportant(value)' lib/Epub/Epub/css/CssParser.cpp
grep -F 'setsParagraphDirection' lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h
grep -F 'isArabicPresentationForm' lib/EpdFont/EpdFont.cpp
grep -F 'applyVerticalAlignToEntry' lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp

# Preserve CPHUN typography/hyphenation and previously validated fixes.
grep -F 'TIGHT = 0' src/CrossPointSettings.h
grep -F 'NORMAL_PLUS = 4' src/CrossPointSettings.h
grep -F 'WIDE_PLUS = 5' src/CrossPointSettings.h
grep -F 'hasHungarianNumericLeft' lib/Epub/Epub/hyphenation/Hyphenator.cpp
grep -F 'AllowsNumericSuffixBreakAfterExistingHyphen' test/hungarian_single_prefix/HungarianSinglePrefixTest.cpp
grep -F 'uppercaseHungarian' src/activities/reader/DictionaryDefinitionActivity.cpp
grep -F 'MIN_STYLED_RETAIN_HEAP = 16 * 1024' src/util/DictHtmlPages.cpp
grep -F 'props.rowHeight = 40;' src/activities/settings/TextSettingsActivity.cpp

# Keep CPHUN's newer section format rather than upstream's intermediate v40-v45.
grep -F 'SECTION_FILE_VERSION = 54' lib/Epub/Epub/Section.cpp

# USB serial regression guard.
python3 - <<'PY'
from pathlib import Path
s = Path('platformio.ini').read_text()
for env in ('gh_release', 'gh_release_rc'):
    start = s.index(f'[env:{env}]')
    end = s.find('\n[', start + 1)
    block = s[start:end if end != -1 else len(s)]
    if block.count('-DCROSSPOINT_WAIT_FOR_USB_SERIAL') != 1:
        raise SystemExit(f'{env}: USB serial wait flag missing or duplicated')
PY

git diff --check
