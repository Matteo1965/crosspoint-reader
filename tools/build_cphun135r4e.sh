#!/usr/bin/env bash
set -euo pipefail

python3 tools/cphun110_cover_dither_clean_patch.py
python3 tools/cphun111_cover_4gray_floyd_patch.py
python3 tools/cphun112_cover_grayscale_pass_patch.py
python3 tools/cphun113_letter_spacing_scale_patch.py
python3 tools/cphun114_letter_spacing_scale_patch.py
python3 tools/cphun116_letter_spacing_scale_patch.py
python3 tools/cphun117_non_linear_scale_patch.py 2>/dev/null || python3 tools/cphun117_letter_spacing_scale_patch.py
python3 tools/cphun118_fixedpoint_optimization_patch.py
python3 tools/cphun119_fixedpoint_pair_tuning_patch.py
python3 tools/cphun120_fixedpoint_intensity_patch.py
python3 tools/cphun121_native_pair_advance_patch.py
python3 tools/cphun123_ink_edge_right_margin_patch.py
python3 tools/cphun124_dark_ink_edge_patch.py
python3 tools/cphun125_roundedraff_text_settings_layout_patch.py
python3 tools/cphun126_new_dogear_patch.py
python3 tools/cphun127_roundedraff_list_fit_patch.py
python3 tools/cphun128_letter_spacing_profiles_patch.py
python3 tools/cphun129_dictionary_bookinfo_ui_patch.py
python3 tools/cphun130_notoserif16_spacing_optimization_patch.py
python3 tools/cphun131_hyphenation_threshold_patch.py

sed -i 's/SECTION_FILE_VERSION = 57/SECTION_FILE_VERSION = 56/' lib/Epub/Epub/Section.cpp
python3 tools/cphun132_word_highlights_patch.py
python3 tools/cphun132r2_highlight_visibility_lookup_fix.py
python3 tools/cphun132r3_toggle_notfound_fix.py
python3 tools/cphun132r4_bookmarks_export_ui_lookup_fix.py
python3 tools/cphun133_button_action_categories_patch.py

python3 - <<'PY'
from pathlib import Path
import re
p = Path('src/activities/reader/DictionaryWordSelectActivity.cpp')
s = p.read_text()
pattern = re.compile(
    r'  bool found = ok && dict\.lookup\(words\[selected\]\.text, definition, headword, &result\);\n'
    r'  if \(!found && ok && result == Dictionary::LookupResult::ReadError\) \{\n'
    r'    vTaskDelay\(1\);\n'
    r'    definition\.clear\(\);\n'
    r'    headword\.clear\(\);\n'
    r'    result = Dictionary::LookupResult::NotFound;\n'
    r'    found = dict\.lookup\(words\[selected\]\.text, definition, headword, &result\);\n'
    r'  \}\n')
replacement = ('  // CPHUN-89: selected word first. Exact context headwords are alternatives.\n'
               '  const bool found = ok && dict.lookup(words[selected].text, definition, headword, &result);\n')
s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'r2 lookup block not found for r5 normalization: {n}')
p.write_text(s2)
PY

python3 tools/cphun132r5_review_fixes.py

python3 - <<'PY'
from pathlib import Path
import re
p = Path('src/activities/reader/DictionaryWordSelectActivity.cpp')
s = p.read_text()
pattern = re.compile(r'(?m)^\s*const bool found = ok && dict\.lookup\(lookupWord\.c_str\(\), definition, headword, &result\);$')
replacement = '''  bool found = ok && dict.lookup(lookupWord.c_str(), definition, headword, &result);
  if (!found && ok && result == Dictionary::LookupResult::ReadError) {
    vTaskDelay(1);
    definition.clear();
    headword.clear();
    result = Dictionary::LookupResult::NotFound;
    found = dict.lookup(lookupWord.c_str(), definition, headword, &result);
  }'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'r5 logical lookup line not found for retry restore: {n}')
p.write_text(s2)
PY

python3 tools/cphun132r6_dictionary_guard_ui_fix.py
python3 tools/cphun132r7_dictionary_index32_lookup_fix.py
python3 tools/cphun132r8_page_boundary_dictionary_fix.py
python3 tools/cphun132r9_lookup_hard_deadline_fix.py
python3 tools/cphun134_deferred_notfound_prompt_fix.py
python3 tools/cphun135r1_patch_driver.py
python3 tools/cphun135r2_keyboard_delete_patch.py
python3 tools/cphun135r3_ui_hu_hyphen_selection_patch.py
python3 tools/cphun128b_bitter60_multisize_experiment.py
python3 tools/cphun135r4a_selection_keyboard_patch.py
python3 tools/cphun135r4b_patch_driver_v2.py

# R4E: make the Footnotes Reader-menu row visible, but only within
# openReaderMenu(). Do not restore the old synchronous whole-book scan.
python3 - <<'PY'
from pathlib import Path
import re
p = Path('src/activities/reader/EpubReaderActivity.cpp')
s = p.read_text(encoding='utf-8')
m = re.search(r'void EpubReaderActivity::openReaderMenu\(const bool startOnBookTab\)\s*\{(.*?)\n\}', s, re.S)
if not m:
    raise SystemExit('R4E prepatch: openReaderMenu body not found')
body = m.group(1)
body2, n = re.subn(r'!currentPageFootnotes\.empty\(\)', 'true', body, count=1)
if n == 0 and 'SETTINGS.orientation, true,' not in body:
    raise SystemExit('R4E prepatch: current-page Footnotes visibility guard not found')
s = s[:m.start(1)] + body2 + s[m.end(1):]
p.write_text(s, encoding='utf-8')
PY

python3 tools/cphun135r4e_footnote_resolver_patch.py

python3 - <<'PY'
from pathlib import Path
import re
p = Path('src/activities/reader/EpubReaderActivity.cpp')
s = p.read_text(encoding='utf-8')
if '#include <cctype>' not in s:
    if '#include <algorithm>' in s:
        s = s.replace('#include <algorithm>', '#include <algorithm>\n#include <cctype>', 1)
    else:
        s = '#include <cctype>\n' + s
p.write_text(s, encoding='utf-8')
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"', '#define CPHUN_BUILD_ID "CPHUN-260917-135R4E-EXP"', b, count=1)
if n != 1:
    raise SystemExit('R4E build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

sed -i -E 's/SECTION_FILE_VERSION = [0-9]+/SECTION_FILE_VERSION = 61/' lib/Epub/Epub/Section.cpp

git diff --check
grep -F 'CPHUN-260917-135R4E-EXP' src/CPHUNBuildId.h
grep -F 'readItemContentsToStream(targetHref' src/activities/reader/EpubReaderActivity.cpp
grep -F 'FOOTNOTE_ANCHOR_NOT_FOUND' src/activities/reader/EpubReaderActivity.cpp
grep -F 'CrossPoint Footnote Diagnostic' src/activities/reader/EpubReaderActivity.cpp
grep -F 'A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.' src/activities/reader/EpubReaderActivity.cpp
grep -F 'openFootnotesList(false, true);' src/activities/reader/EpubReaderActivity.cpp
grep -F 'SECTION_FILE_VERSION = 61' lib/Epub/Epub/Section.cpp

python3 - <<'PY'
from pathlib import Path
s = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
if 'ensureBookFootnotes();\n      openFootnotesList(true, true);' in s:
    raise SystemExit('R4E synchronous whole-book scan is still reachable from Reader menu')
if 'extractFootnoteText(const FootnoteEntry& footnote' not in s:
    raise SystemExit('R4E resolver signature missing')
if 'readItemContentsToStream(targetHref' not in s:
    raise SystemExit('R4E direct href target resolver missing')
if 'CrossPoint Footnote Diagnostic' not in s:
    raise SystemExit('R4E diagnostic logging missing')
print('R4E semantic verification passed')
PY
