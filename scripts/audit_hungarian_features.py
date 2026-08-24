#!/usr/bin/env python3
from pathlib import Path
from dataclasses import dataclass
import sys

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    p = ROOT / path
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def has(path: str, needle: str) -> bool:
    return needle in text(path)


def exists(path: str) -> bool:
    p = ROOT / path
    return p.exists() and p.stat().st_size > 0


@dataclass
class Check:
    label: str
    ok: bool
    evidence: str


@dataclass
class Feature:
    name: str
    category: str
    checks: list[Check]
    historical: str = ""
    note: str = ""
    expected: bool = True

    @property
    def status(self) -> str:
        if not self.expected:
            return "RETIRED_OK" if all(c.ok for c in self.checks) else "RETIRED_PRESENT"
        passed = sum(c.ok for c in self.checks)
        if passed == len(self.checks):
            return "PRESENT"
        if passed == 0:
            return "MISSING"
        return "PARTIAL"


def C(label: str, ok: bool, evidence: str) -> Check:
    return Check(label, ok, evidence)


features: list[Feature] = []

features += [
    Feature(
        "Hungarian hyphenation core",
        "Hyphenation",
        [
            C("generated Hungarian trie", exists("lib/Epub/Epub/hyphenation/generated/hyph-hu.trie.h"), "hyph-hu.trie.h"),
            C("Hungarian language registered", has("lib/Epub/Epub/hyphenation/LanguageRegistry.cpp", '"hungarian", "hu"'), "LanguageRegistry.cpp"),
            C("Hungarian pattern symbol present", has("lib/Epub/Epub/hyphenation/generated/hyph-hu.trie.h", "hu_patterns"), "hyph-hu.trie.h: hu_patterns"),
        ],
    ),
    Feature(
        "Extended Hungarian hyphenation toggle/wiring",
        "Hyphenation",
        [
            C("setting field", has("src/CrossPointSettings.h", "hungarianHyphenationExtended"), "CrossPointSettings.h"),
            C("reader settings entry", has("src/SettingsListBase.h", "hungarianHyphenationExtended"), "SettingsListBase.h"),
            C("render spec carries flag", has("lib/Epub/Epub/ReaderRenderSpec.h", "hungarianHyphenationExtended"), "ReaderRenderSpec.h"),
            C("section/cache compares flag", has("lib/Epub/Epub/Section.cpp", "hungarianHyphenationExtended"), "Section.cpp"),
        ],
    ),
    Feature(
        "Short foreign/proper-name guard (<=5 chars, no vowelless remainder)",
        "Hyphenation",
        [
            C("short-word filter", has("lib/Epub/Epub/hyphenation/Hyphenator.cpp", "filterShortHungarianAutomaticBreaks"), "Hyphenator.cpp"),
            C("regression test", has("test/hyphenation_eval/HungarianTypographyRegressionTest.cpp", "ShortForeignNamesDoNotLeaveVowellessRemainders"), "HungarianTypographyRegressionTest.cpp"),
        ],
        historical="typography round 2",
    ),
    Feature(
        "Hungarian compound breakpoint priority / replacement ordering",
        "Hyphenation",
        [
            C("replacement tie-break ordering", has("lib/Epub/Epub/hyphenation/Hyphenator.cpp", "a.replacement < b.replacement"), "Hyphenator.cpp"),
            C("compound regression", has("test/hyphenation_eval/HungarianTypographyRegressionTest.cpp", "CompoundBoundaryBeatsFalseExtendedReplacement"), "HungarianTypographyRegressionTest.cpp"),
        ],
        historical="typography round 2",
    ),
    Feature(
        "Quoted compound hyphenation",
        "Hyphenation",
        [C("closing quote before hyphen handling", has("lib/Epub/Epub/hyphenation/Hyphenator.cpp", "isClosingQuoteBeforeHyphen"), "Hyphenator.cpp")],
    ),
    Feature(
        "Paragraph-final hyphenation remainder: block 1-2 letters, allow 3+",
        "Hyphenation",
        [
            C("paragraph-final lexical-word guard", has("lib/Epub/Epub/ParsedText.cpp", "isParagraphFinalLexicalWord"), "ParsedText.cpp"),
            C("1-2 letter remainder rule", has("lib/Epub/Epub/ParsedText.cpp", "remainderLetterCount <= 2"), "ParsedText.cpp"),
        ],
        historical="be05a1ea",
    ),
    Feature(
        "Minimum word spacing 50-100%",
        "Typography",
        [
            C("persistent setting field", has("src/CrossPointSettings.h", "minimumSpacePercent"), "CrossPointSettings.h"),
            C("default 100%", has("src/CrossPointSettings.h", "minimumSpacePercent = 100"), "CrossPointSettings.h"),
            C("Text Settings UI", has("src/activities/settings/TextSettingsActivity.cpp", "Min. szóköz") or has("src/SettingsListBase.h", "minimumSpacePercent"), "TextSettingsActivity.cpp / SettingsListBase.h"),
            C("render spec wiring", has("lib/Epub/Epub/ReaderRenderSpec.h", "minimumSpacePercent"), "ReaderRenderSpec.h"),
            C("section cache parameter", has("lib/Epub/Epub/Section.cpp", "fileMinimumSpacePercent"), "Section.cpp"),
            C("layout scaling", has("lib/Epub/Epub/ParsedText.cpp", "scaledNormalSpaceAdvance"), "ParsedText.cpp"),
        ],
        historical="fb115087 / b1e53180",
        note="This is the user-observed missing menu feature.",
    ),
    Feature(
        "Minimum-space / natural final-line rehyphenation interaction",
        "Typography",
        [
            C("natural final-line width pass", has("lib/Epub/Epub/ParsedText.cpp", "naturalLineWidth"), "ParsedText.cpp"),
            C("retry final-word hyphenation", has("lib/Epub/Epub/ParsedText.cpp", "availableForFinalPrefix") or has("lib/Epub/Epub/ParsedText.cpp", "repairedByHyphenation"), "ParsedText.cpp"),
        ],
        historical="b821f63c",
    ),
    Feature(
        "Dialogue correction + fixed opening gap",
        "Typography",
        [
            C("persistent setting", has("src/CrossPointSettings.h", "fixedDialogueSpacing"), "CrossPointSettings.h"),
            C("settings UI wiring", has("src/SettingsListBase.h", "fixedDialogueSpacing"), "SettingsListBase.h"),
            C("render spec wiring", has("lib/Epub/Epub/ReaderRenderSpec.h", "fixedDialogueSpacing"), "ReaderRenderSpec.h"),
            C("cache invalidation", has("lib/Epub/Epub/Section.cpp", "fileFixedDialogueSpacing") or has("lib/Epub/Epub/Section.cpp", "fixedDialogueSpacing"), "Section.cpp"),
            C("parser/layout behavior", has("lib/Epub/Epub/ParsedText.cpp", "fixedDialogueSpacing"), "ParsedText.cpp"),
        ],
    ),
    Feature(
        "Optical margin / hanging punctuation",
        "Typography",
        [
            C("persistent percentage setting", has("src/CrossPointSettings.h", "hangingPunctuation"), "CrossPointSettings.h"),
            C("render spec limit", has("lib/Epub/Epub/ReaderRenderSpec.h", "hangingPunctuationLimitPx"), "ReaderRenderSpec.h"),
            C("layout allowance", has("lib/Epub/Epub/ParsedText.cpp", "hangingPunctuationAllowance"), "ParsedText.cpp"),
            C("hyphen 50% ratio", has("lib/Epub/Epub/ParsedText.cpp", "hangingPercent = 50"), "ParsedText.cpp"),
            C("?! 10% ratio", has("lib/Epub/Epub/ParsedText.cpp", "hangingPercent = 10"), "ParsedText.cpp"),
        ],
        historical="97a83230",
    ),
    Feature(
        "Exact justified-line remainder-pixel distribution",
        "Typography",
        [
            C("LTR/normal remainder distribution", has("lib/Epub/Epub/ParsedText.cpp", "justifyRemainder"), "ParsedText.cpp"),
            C("reordered/RTL remainder distribution", has("lib/Epub/Epub/ParsedText.cpp", "reorderedJustifyRemainder"), "ParsedText.cpp"),
        ],
    ),
    Feature(
        "Visible Indexing feedback before rebuild",
        "Reflow/performance",
        [
            C("Indexing popup", has("src/activities/reader/EpubReaderActivity.cpp", "STR_INDEXING"), "EpubReaderActivity.cpp"),
            C("physical display flush", has("src/activities/reader/EpubReaderActivity.cpp", "renderer.displayBuffer();"), "EpubReaderActivity.cpp"),
        ],
        historical="fb115087 / b1e53180",
    ),
    Feature(
        "Text Settings only invalidates Section on layout change",
        "Reflow/performance",
        [
            C("before/after render spec", has("src/activities/reader/EpubReaderActivity.cpp", "beforeSpec") and has("src/activities/reader/EpubReaderActivity.cpp", "afterSpec"), "EpubReaderActivity.cpp"),
            C("layoutChanged guard", has("src/activities/reader/EpubReaderActivity.cpp", "layoutChanged"), "EpubReaderActivity.cpp"),
        ],
        historical="b1e53180",
    ),
    Feature(
        "Responsive font-size/family reflow",
        "Reflow/performance",
        [
            C("pending-state flag", has("src/activities/reader/EpubReaderActivity.h", "responsiveFontReflowPending"), "EpubReaderActivity.h"),
            C("font-change activation", has("src/activities/reader/EpubReaderActivity.cpp", "responsiveFontReflowPending"), "EpubReaderActivity.cpp"),
            C("saved visible-text target", has("src/activities/reader/EpubReaderActivity.cpp", "cachedVisibleTextOffset"), "EpubReaderActivity.cpp"),
        ],
        historical="b821f63c / c85efc1d",
    ),
    Feature(
        "Parser-level time-sliced target reflow",
        "Reflow/performance",
        [
            C("Section target-build API", has("lib/Epub/Epub/Section.cpp", "buildTowardVisibleTextOffset"), "Section.cpp"),
            C("parser time budget", has("src/activities/reader/EpubReaderActivity.h", "RESPONSIVE_REFLOW_PARSE_BUDGET_MS"), "EpubReaderActivity.h"),
            C("target reached query", has("lib/Epub/Epub/Section.cpp", "buildReachedVisibleTextOffset"), "Section.cpp"),
        ],
        historical="a3c45269",
    ),
    Feature(
        "Font-reflow Section lifecycle safety",
        "Reflow/performance",
        [
            C("abandon old-spec active build", has("src/activities/reader/EpubReaderActivity.cpp", "section->abandonBuild()"), "EpubReaderActivity.cpp"),
            C("lifecycle diagnostic marker", has("src/activities/reader/EpubReaderActivity.cpp", "abandoning old-spec active build"), "EpubReaderActivity.cpp"),
        ],
        historical="0a303680",
    ),
    Feature(
        "ParsedText fragmented-heap crash protection",
        "Stability",
        [
            C("visible-offset deltas use deque", has("lib/Epub/Epub/ParsedText.h", "std::deque<uint16_t> wordVisibleOffsetDeltas"), "ParsedText.h"),
            C("no invalid deque reserve", not has("lib/Epub/Epub/ParsedText.cpp", "wordVisibleOffsetDeltas.reserve"), "ParsedText.cpp"),
        ],
        historical="63655eb2 + 27886404",
    ),
    Feature(
        "Hungarian dictionary stemming v16 + case folding",
        "Dictionary",
        [
            C("v16 implementation marker", has("src/util/Dictionary.cpp", "Hungarian dictionary stemming v16"), "Dictionary.cpp"),
            C("Hungarian case-fold table", has("src/util/Dictionary.cpp", "HU_CASE_FOLD"), "Dictionary.cpp"),
            C("stemming regression runner", exists("scripts/run_hungarian_stemming_regression_v2.py"), "scripts/run_hungarian_stemming_regression_v2.py"),
            C("false-positive regression runner", exists("scripts/run_hungarian_cpp_false_positive_regression.py"), "scripts/run_hungarian_cpp_false_positive_regression.py"),
        ],
    ),
    Feature(
        "Hungarian Edition identity/version page",
        "UI",
        [
            C("boot label", has("src/activities/boot_sleep/BootActivity.cpp", "Hungarian Edition"), "BootActivity.cpp"),
            C("version activity", exists("src/activities/settings/CrossPointVersionActivity.cpp"), "CrossPointVersionActivity.cpp"),
            C("stemming count displayed", has("src/activities/settings/CrossPointVersionActivity.cpp", "Magyar szótövezés"), "CrossPointVersionActivity.cpp"),
        ],
    ),
    Feature(
        "RoundedRaff Hungarian Edition dimensions",
        "UI",
        [
            C("cover height 376", has("src/components/themes/roundedraff/RoundedRaffTheme.h", "homeCoverHeight = 376"), "RoundedRaffTheme.h"),
            C("tile height 400", has("src/components/themes/roundedraff/RoundedRaffTheme.h", "homeCoverTileHeight = 400"), "RoundedRaffTheme.h"),
        ],
    ),
    Feature(
        "Version-page side-button mapping follows mapped controls",
        "UI/input",
        [C("mapped page-forward button used", has("src/activities/settings/CrossPointVersionActivity.cpp", "MappedInputManager::Button::PageForward"), "CrossPointVersionActivity.cpp")],
    ),
]

# Translation key parity is a semantic invariant rather than a string marker.
try:
    sys.path.insert(0, str(ROOT / "scripts"))
    from gen_i18n import parse_yaml_file
    en = parse_yaml_file(ROOT / "lib/I18n/translations/english.yaml")
    hu = parse_yaml_file(ROOT / "lib/I18n/translations/hungarian.yaml")
    parity = set(en) == set(hu)
    parity_evidence = f"EN={len(en)}, HU={len(hu)}, missingHU={len(set(en)-set(hu))}, extraHU={len(set(hu)-set(en))}"
except Exception as exc:
    parity = False
    parity_evidence = f"translation parser failed: {exc}"
features.append(Feature("English/Hungarian translation-key parity", "UI", [C("key sets match", parity, parity_evidence)]))

# Historical experiments/features that are intentionally absent from the production RC.
features += [
    Feature(
        "USB-free performance diagnostic logger",
        "Retired/diagnostic",
        [
            C("/performance.log absent", "/performance.log" not in text("src/activities/reader/EpubReaderActivity.cpp"), "production source"),
            C("PerformanceDiagnostic absent", "PerformanceDiagnostic" not in text("src/activities/reader/EpubReaderActivity.cpp"), "production source"),
        ],
        expected=False,
        note="Diagnostic-only firmware; intentionally excluded from normal builds.",
    ),
    Feature(
        "Picture-filter / Hungarian image-brightness experiment",
        "Retired/experimental",
        [
            C("picture filter removed from settings", "STR_PICTURE_FILTER" not in text("src/SettingsList.h") and "STR_PICTURE_FILTER" not in text("src/SettingsListBase.h"), "settings"),
            C("picture brightness hook removed", "brightnessPercentForPicture" not in text("lib/Epub/Epub/blocks/ImageBlock.cpp"), "ImageBlock.cpp"),
        ],
        expected=False,
        note="Current production build explicitly validates that these experimental hooks are absent.",
    ),
    Feature(
        "Long-down screenshot experiment",
        "Retired/experimental",
        [C("longDownScreenshot absent", "longDownScreenshot" not in text("src/main.cpp") and "STR_LONG_DOWN_SCREENSHOT" not in text("src/SettingsListBase.h"), "production source")],
        expected=False,
        note="Current production build explicitly validates removal.",
    ),
]

status_icon = {
    "PRESENT": "✅ PRESENT",
    "PARTIAL": "⚠️ PARTIAL",
    "MISSING": "❌ MISSING",
    "RETIRED_OK": "🟦 RETIRED (correctly absent)",
    "RETIRED_PRESENT": "🟥 RETIRED FEATURE LEAKED BACK",
}

lines = [
    "# Hungarian Edition feature audit",
    "",
    "Generated by `scripts/audit_hungarian_features.py` against the checked-out source tree.",
    "This file is the canonical inventory for custom Hungarian Edition features and regression guards.",
    "",
]

active = [f for f in features if f.expected]
missing = [f for f in active if f.status == "MISSING"]
partial = [f for f in active if f.status == "PARTIAL"]
present = [f for f in active if f.status == "PRESENT"]
retired_bad = [f for f in features if not f.expected and f.status == "RETIRED_PRESENT"]

lines += [
    "## Summary",
    "",
    f"- Active features: **{len(active)}**",
    f"- Present: **{len(present)}**",
    f"- Partial: **{len(partial)}**",
    f"- Missing: **{len(missing)}**",
    f"- Retired features unexpectedly present: **{len(retired_bad)}**",
    "",
]

for category in sorted({f.category for f in features}):
    lines += [f"## {category}", ""]
    for f in [x for x in features if x.category == category]:
        lines += [f"### {status_icon[f.status]} — {f.name}", ""]
        if f.historical:
            lines.append(f"Historical reference: `{f.historical}`")
            lines.append("")
        if f.note:
            lines.append(f.note)
            lines.append("")
        for c in f.checks:
            lines.append(f"- {'✅' if c.ok else '❌'} {c.label} — `{c.evidence}`")
        lines.append("")

lines += ["## Next-build restoration candidates", ""]
if not missing and not partial and not retired_bad:
    lines.append("No missing/partial active feature detected by the current marker set.")
else:
    for f in missing + partial:
        lines.append(f"- **{f.name}** — {f.status}")
    for f in retired_bad:
        lines.append(f"- **Remove leaked retired feature:** {f.name}")
lines.append("")
lines += [
    "## Planned but not yet integrated",
    "",
    "- SMALL CAPS support — deliberately postponed until the stable typography/reflow baseline is restored and audited.",
    "",
    "## Audit policy",
    "",
    "A production Hungarian firmware build should run this audit before compilation. Missing or partial active features must be reviewed explicitly; they must not disappear silently during rebases, upstream integrations, or patch-chain rebuilds.",
]

out = ROOT / "docs/HUNGARIAN_EDITION_FEATURES.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[:20]))
print(f"Wrote {out}")

# Do not fail here: the audit branch must publish the report even when it finds regressions.
