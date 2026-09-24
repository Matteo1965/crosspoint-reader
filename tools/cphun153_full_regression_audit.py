#!/usr/bin/env python3
"""Fail CPHUN-153 build if any approved historical feature or persistence pair vanished."""
from pathlib import Path
import re
def content(p):
    q=Path(p)
    if not q.is_file():raise AssertionError(f"MISSING FILE: {p}")
    return q.read_text(encoding="utf-8")
def expect(p,*tokens):
    s=content(p)
    for token in tokens:
        if token not in s:raise AssertionError(f"MISSING FEATURE {p}: {token}")
    return s
ui=expect("src/activities/settings/TextSettingsActivity.cpp",
          "LETTER_SPACING_THRESHOLDS", "LetterSpacingOptimization",
          "HyphenationThreshold", "MinimumSpace", "FixedDialogueSpacing")
settings=expect("src/CrossPointSettings.cpp",
                'doc["letterSpacingLimitPercent"] = letterSpacingLimitPercent;',
                'letterSpacingLimitPercent = doc["letterSpacingLimitPercent"] | (uint16_t)0;',
                'doc["letterSpacingOptimization"]', 'doc["hyphenationThreshold"]')
m=re.search(r'constexpr uint16_t LETTER_SPACING_THRESHOLDS\[\] = \{([^}]+)\};',ui)
assert m,"correction menu missing"
values=[int(v.strip()) for v in m.group(1).split(",")]
assert values==[0,550,520,480,430,370,300,220],values
for val in values:
    assert f"letterSpacingLimitPercent != {val}" in settings,f"loader rejects {val}"
expect("src/activities/reader/EpubReaderActivity.cpp",
       "highlightStore", "textEditStore", "openDictionaryWordSelect",
       "FootnotePopupActivity", "EXPORT_EDITS")
expect("src/activities/reader/EpubReaderMenuActivity.cpp",
       "Szerkesztés", "Megjelölés", "Szótár", "EXPORT_EDITS")
expect("src/activities/reader/DictionaryWordSelectActivity.cpp",
       "WordSelectionMode::Edit", "WordSelectionMode::Highlight")
expect("src/activities/reader/EpubReaderBookmarksActivity.cpp",
       "Megjelölt", "Highlight")
expect("src/highlights/HighlightStore.cpp", "/.crosspoint/highlights/")
expect("src/highlights/TextEditStore.cpp", "/.crosspoint/edits/")
expect("src/highlights/HighlightRenderer.cpp", "HighlightRenderer::render")
expect("src/highlights/TextEditRenderer.cpp", "TextEditRenderer::renderBackground")
expect("src/activities/reader/FootnotePopupActivity.cpp","FootnotePopupActivity")
expect("src/activities/reader/EpubReaderFootnotesActivity.cpp","Footnotes")
expect("lib/Epub/Epub/LetterSpacingOptimization.h",
       "consumeGuardedPair", "left == right")
expect("lib/Epub/Epub/blocks/TextBlock.cpp", "consumeGuardedPair")
expect("lib/GfxRenderer/GfxRenderer.cpp", "previousAdvanceFP + font.getKerning")
expect("lib/Epub/Epub/hyphenation/Hyphenator.cpp", "kHungarianPrefixFamilies")
expect("src/network/OtaUpdater.cpp",
       "parseCphunBuildId(CPHUN_BUILD_ID)", "latestBuild > currentBuild")
for field in ("shortHyphen","fixedDialogueSpacing","minimumSpacePercent",
              "extraParagraphSpacingEnabled","hangingPunctuation","softHyphenEnabled",
              "letterSpacingLimitPercent"):
    assert f'doc["{field}"] = {field};' in settings,f"not saved: {field}"
    assert f'doc["{field}"]' in settings.split("bool CrossPointSettings::fromJson(",1)[1],f"not loaded: {field}"
# generic settings use the exact same settings list for read/write.
assert settings.count("for (const auto& info : getSettingsList())")>=2
for field in ("hyphenationThreshold","letterSpacingOptimization","letterSpacingOptimizationThreshold",
              "wordSelectionMode"):
    assert f'doc["{field}"]' in settings, f"missing custom setting: {field}"
expect("src/CPHUNBuildId.h","CPHUN-260924-153-FULL")
print("CPHUN-153 feature audit PASSED: highlights, edits, export, dictionary, typography, footnotes, OTA, persistence")
