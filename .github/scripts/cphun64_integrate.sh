#!/usr/bin/env bash
set -euo pipefail

UPSTREAM=https://github.com/crosspoint-reader/crosspoint-reader.git

git remote add upstream "$UPSTREAM" 2>/dev/null || true
for c in \
  c6fe67d48d8b65f5dfdefae31f06d0bc9826f267 \
  7e42d070774e75f250c8ffefe5e9357dacd39eb2 \
  da3d50c245334155daccb85058f3645637fd6db4 \
  52444a0c973ef9ffe4dd719c92d2dccca9a4d778 \
  30992315663dfd181476880b873fa91a49ac8d87 \
  ce6c6cbce473e34a9271c34d374e5d7eb1c7695f; do
  git fetch upstream "$c"
done

# Port small, low-conflict fixes directly from their upstream commits.
# Keep CPHUN's newer Section.cpp/cache format and custom parser extensions.
git checkout c6fe67d48d8b65f5dfdefae31f06d0bc9826f267 -- lib/Epub/Epub/ParsedText.cpp

git checkout 30992315663dfd181476880b873fa91a49ac8d87 -- lib/EpdFont/EpdFont.cpp

python3 - <<'PY'
from pathlib import Path

cpp = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp')
hdr = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h')
css = Path('lib/Epub/Epub/css/CssParser.cpp')
cssh = Path('lib/Epub/Epub/css/CssParser.h')

s = cpp.read_text()
h = hdr.read_text()
c = css.read_text()
ch = cssh.read_text()

# c6fe67d: don't soft-flush in a ruby group.
s = s.replace('if (blockWordCount > softFlushThreshold) {',
              'if (blockWordCount > softFlushThreshold && !self->inRuby) {', 1)

# 7e42d07: tolerate junk after a completed </html> document.
if 'bool htmlEnded_ = false;' not in h:
    h = h.replace('  bool insideBody = false;\n', '  bool insideBody = false;\n  bool htmlEnded_ = false;\n', 1)
if 'self->htmlEnded_ = true;' not in s:
    s = s.replace('  if (strcmp(name, "body") == 0) {\n    self->insideBody = false;\n  }\n}',
                  '  if (strcmp(name, "body") == 0) {\n    self->insideBody = false;\n  }\n  if (strcmp(name, "html") == 0) {\n    self->htmlEnded_ = true;\n  }\n}', 1)
if 'htmlEnded_ = false;' not in s:
    s = s.replace('bool ChapterHtmlSlimParser::beginParse() {\n',
                  'bool ChapterHtmlSlimParser::beginParse() {\n  htmlEnded_ = false;\n', 1)
err_anchor = '  if (XML_ParseBuffer(xmlParser_, static_cast<int>(len), done) == XML_STATUS_ERROR) {\n'
if 'Ignoring trailing data after </html>' not in s:
    if err_anchor not in s:
        raise SystemExit('parse error anchor missing')
    s = s.replace(err_anchor, err_anchor +
                  '    if (htmlEnded_) {\n'
                  '      LOG_DBG("EHP", "Ignoring trailing data after </html>: %s", XML_ErrorString(XML_GetErrorCode(xmlParser_)));\n'
                  '      return ParseStatus::Done;\n'
                  '    }\n', 1)

# 52444a0: strip !important for all supported declarations.
if 'std::string_view value = trimCssWhitespace(decl.substr(colonPos + 1));' not in c:
    c = c.replace('const std::string_view value = trimCssWhitespace(decl.substr(colonPos + 1));',
                  'std::string_view value = trimCssWhitespace(decl.substr(colonPos + 1));', 1)
if 'value = stripTrailingImportant(value);' not in c:
    c = c.replace('  if (name.empty() || value.empty()) return;\n',
                  '  if (name.empty() || value.empty()) return;\n\n  value = stripTrailingImportant(value);\n', 1)
c = c.replace('    const std::string_view displayValue = stripTrailingImportant(value);\n    style.display = iequalsAscii(displayValue, "none") ? CssDisplay::None : CssDisplay::Block;',
              '    style.display = iequalsAscii(value, "none") ? CssDisplay::None : CssDisplay::Block;')
c = c.replace('    const std::string_view directionValue = stripTrailingImportant(value);\n    if (iequalsAscii(directionValue, "rtl")) {',
              '    if (iequalsAscii(value, "rtl")) {')
c = c.replace('    } else if (iequalsAscii(directionValue, "ltr")) {',
              '    } else if (iequalsAscii(value, "ltr")) {')
if 'CSS_CACHE_VERSION = 11' not in ch:
    ch = ch.replace('CSS_CACHE_VERSION = 10', 'CSS_CACHE_VERSION = 11')

# 52444a0: strip inherited vertical spacing when a block closes.
s = s.replace('      self->startNewTextBlock(self->blockStyleStack.back());',
              '      self->startNewTextBlock(self->blockStyleStack.back().withoutTop().withoutBottom());', 1)

# ce6c6cb: paragraph base direction must not be replaced by inline direction.
if 'bool setsParagraphDirection = false;' not in h:
    h = h.replace('    CssTextDirection direction = CssTextDirection::Ltr;\n',
                  '    CssTextDirection direction = CssTextDirection::Ltr;\n    bool setsParagraphDirection = false;\n', 1)

# badfa95: preserve superscript/subscript on internal EPUB links.
if 'applyVerticalAlignToEntry' not in s:
    anchor = '''void ChapterHtmlSlimParser::applyTextDecorationToEntry(StyleStackEntry& entry, const CssStyle& css) {\n  if (css.hasTextDecoration()) {\n    entry.hasTextDecoration = true;\n    entry.textDecoration = css.textDecoration;\n  }\n}\n'''
    addition = anchor + '''\nvoid ChapterHtmlSlimParser::applyVerticalAlignToEntry(StyleStackEntry& entry, const CssStyle& css) {\n  if (!css.hasVerticalAlign()) return;\n  if (css.verticalAlign == CssVerticalAlign::Super) {\n    entry.hasSup = true;\n    entry.sup = true;\n  } else if (css.verticalAlign == CssVerticalAlign::Sub) {\n    entry.hasSub = true;\n    entry.sub = true;\n  }\n}\n'''
    if anchor not in s:
        raise SystemExit('missing applyTextDecorationToEntry anchor')
    s = s.replace(anchor, addition, 1)
    link_anchor = '      applyDirectionToEntry(entry, cssStyle);\n      self->inlineStyleStack.push_back(entry);'
    if link_anchor in s:
        s = s.replace(link_anchor,
                      '      applyDirectionToEntry(entry, cssStyle);\n      applyVerticalAlignToEntry(entry, cssStyle);\n      self->inlineStyleStack.push_back(entry);', 1)
    old = '''      if (cssStyle.hasVerticalAlign()) {\n        if (cssStyle.verticalAlign == CssVerticalAlign::Super) {\n          entry.hasSup = true;\n          entry.sup = true;\n        } else if (cssStyle.verticalAlign == CssVerticalAlign::Sub) {\n          entry.hasSub = true;\n          entry.sub = true;\n        }\n      }\n'''
    if old in s:
        s = s.replace(old, '      applyVerticalAlignToEntry(entry, cssStyle);\n', 1)
if 'applyVerticalAlignToEntry' not in h:
    h = h.replace('  static void applyTextDecorationToEntry(StyleStackEntry& entry, const CssStyle& css);\n',
                  '  static void applyTextDecorationToEntry(StyleStackEntry& entry, const CssStyle& css);\n  static void applyVerticalAlignToEntry(StyleStackEntry& entry, const CssStyle& css);\n', 1)

cpp.write_text(s)
hdr.write_text(h)
css.write_text(c)
cssh.write_text(ch)
Path('src/CPHUNBuildId.h').write_text('#pragma once\n\n#define CPHUN_BUILD_ID "CPHUN-260907-64"\n')
PY

# Guard imported fixes.
grep -F 'htmlEnded_' lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h
grep -F '!self->inRuby' lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp
grep -F 'stripTrailingImportant(value)' lib/Epub/Epub/css/CssParser.cpp
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
