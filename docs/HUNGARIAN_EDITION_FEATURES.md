# Hungarian Edition feature audit v2

Strict feature-specific audit against the checked-out production source. Equivalent implementations are accepted only where explicitly encoded in the audit.

## Summary

- Active features: **23**
- Present: **11**
- Partial: **2**
- Missing: **10**
- Retired features unexpectedly present: **0**

## Dictionary

### ✅ PRESENT — Hungarian dictionary stemming v16 + case folding

- ✅ v16 implementation marker — `Dictionary.cpp`
- ✅ HU case fold — `Dictionary.cpp`
- ✅ stemming regression suite — `run_hungarian_stemming_regression_v2.py`
- ✅ false-positive regression suite — `run_hungarian_cpp_false_positive_regression.py`

## Hyphenation

### ✅ PRESENT — Hungarian hyphenation core

- ✅ generated Hungarian trie — `hyph-hu.trie.h`
- ✅ Hungarian registry entry — `LanguageRegistry.cpp`
- ✅ Hungarian patterns compiled — `hyph-hu.trie.h`

### ✅ PRESENT — Extended Hungarian hyphenation toggle and render/cache wiring

- ✅ persistent setting — `CrossPointSettings.h`
- ✅ Text Settings exposure — `TextSettingsActivity.cpp`
- ✅ render spec field — `ReaderRenderSpec.h`
- ✅ Section cache compares setting — `Section.cpp`

### ❌ MISSING — Short foreign/proper-name guard (<=5 chars; no vowelless remainder)

Historical reference: `typography round 2`

- ❌ short-Hungarian automatic-break filter — `Hyphenator.cpp`
- ❌ regression test — `HungarianTypographyRegressionTest.cpp`

### ❌ MISSING — Compound breakpoint priority / replacement ordering

Historical reference: `2bc5c26b`

- ❌ approved replacement priority — `Hyphenator.cpp`
- ❌ compound regression test — `HungarianTypographyRegressionTest.cpp`

### ❌ MISSING — Quoted compound hyphenation

Historical reference: `fb115087 verification`

- ❌ closing quote before hyphen handling — `Hyphenator.cpp`

### ❌ MISSING — Paragraph-final remainder guard: block 1-2 letters, allow 3+

Historical reference: `be05a1ea`

- ❌ paragraph-final lexical-word detection — `ParsedText.cpp`
- ❌ exact <=2 rule — `ParsedText.cpp`

## Reflow/performance

### ⚠️ PARTIAL — Visible Indexing feedback before rebuild

Historical reference: `fb115087 / b1e53180`

- ✅ popup helper exists — `EpubReaderActivity::showBuildPopup`
- ❌ popup physically flushed before long work — `EpubReaderActivity::showBuildPopup`

### ❌ MISSING — Text Settings avoids Section rebuild when layout unchanged

Historical reference: `b1e53180`

- ❌ before/after ReaderRenderSpec comparison — `EpubReaderActivity.cpp`
- ❌ layoutChanged guard — `EpubReaderActivity.cpp`

### ⚠️ PARTIAL — Responsive font-size/family reflow state machine

Historical reference: `b821f63c / c85efc1d`

- ❌ pending state — `EpubReaderActivity.h`
- ❌ font-change activation — `EpubReaderActivity.cpp`
- ✅ saved visible-text target retained — `EpubReaderActivity.cpp`

### ❌ MISSING — Parser-level time-sliced target reflow

Historical reference: `a3c45269`

- ❌ Section target-build method — `Section.cpp`
- ❌ 12ms parser budget — `EpubReaderActivity.h`
- ❌ target-reached API — `Section.cpp`

### ❌ MISSING — Font-change Section lifecycle safety

Historical reference: `0a303680`

- ❌ font-reflow activation context — `EpubReaderActivity.cpp`
- ❌ old-spec build explicitly abandoned before reset — `EpubReaderActivity.cpp`

## Retired/diagnostic

### 🟦 RETIRED (correctly absent) — USB-free performance logger

Diagnostic firmware only; must remain absent from production.

- ✅ /performance.log absent — `production reader`
- ✅ PerformanceDiagnostic absent — `production reader`

## Retired/experimental

### 🟦 RETIRED (correctly absent) — Picture filter / Hungarian image brightness experiment

- ✅ picture-filter setting absent — `SettingsListBase.h`
- ✅ brightness hook absent — `ImageBlock.cpp`

### 🟦 RETIRED (correctly absent) — Long-down screenshot experiment

- ✅ feature absent — `production source`

## Stability

### ✅ PRESENT — ParsedText fragmented-heap visible-offset protection

Historical reference: `63655eb2 + 27886404`

- ✅ deque-backed visible offsets — `ParsedText.h`
- ✅ reserve compatibility is safe — `ParsedText.h / ParsedText.cpp`

## Typography

### ❌ MISSING — Minimum word spacing 50-100%

Historical reference: `fb115087 / b1e53180`

User-visible regression: menu option disappeared.

- ❌ persistent setting + default 100 — `CrossPointSettings.h`
- ❌ Text Settings control — `TextSettingsActivity.cpp`
- ❌ render spec field — `ReaderRenderSpec.h`
- ❌ Section cache field/compare — `Section.cpp`
- ❌ layout scales natural word space — `ParsedText.cpp`

### ❌ MISSING — Minimum-space vs natural final-line rehyphenation repair

Historical reference: `b821f63c`

- ❌ natural 100% final-line pass — `ParsedText.cpp`
- ❌ retry final-word hyphenation before whole-word move — `ParsedText.cpp`

### ✅ PRESENT — Dialogue correction + fixed opening gap

- ✅ persistent setting — `CrossPointSettings.h`
- ✅ Text Settings Layout control — `TextSettingsActivity.cpp`
- ✅ render spec — `ReaderRenderSpec.h`
- ✅ Section cache parameter — `Section.cpp`
- ✅ ParsedText behavior — `ParsedText.cpp`

### ✅ PRESENT — Optical margin / hanging punctuation base feature

- ✅ persistent percentage — `CrossPointSettings.h`
- ✅ Text Settings control — `TextSettingsActivity.cpp`
- ✅ render spec pixel limit — `ReaderRenderSpec.h`
- ✅ layout allowance — `ParsedText.cpp`

### ❌ MISSING — Per-character optical-margin ratios

Historical reference: `97a83230`

- ❌ hyphen ratio 50% — `ParsedText.cpp`
- ❌ question/exclamation ratio 10% — `ParsedText.cpp`
- ❌ default supported punctuation ratio 25% — `ParsedText.cpp`

### ✅ PRESENT — Exact justified-line remainder-pixel distribution

Historical reference: `57151fd6`

- ✅ normal/LTR remainder distribution — `ParsedText.cpp`
- ✅ reordered/RTL remainder distribution — `ParsedText.cpp`

## UI

### ✅ PRESENT — Hungarian Edition identity/version page

- ✅ boot label — `BootActivity.cpp`
- ✅ version activity — `CrossPointVersionActivity.cpp`
- ✅ Hungarian stemming summary — `CrossPointVersionActivity.cpp`

### ✅ PRESENT — RoundedRaff Hungarian Edition dimensions

- ✅ cover height 376 — `RoundedRaffTheme.h`
- ✅ tile height 400 — `RoundedRaffTheme.h`

### ✅ PRESENT — English/Hungarian translation-key parity

- ✅ key sets match — `EN=466, HU=466, missingHU=0, extraHU=0`

## UI/input

### ✅ PRESENT — Version-page side buttons follow mapped controls

- ✅ PageForward mapping used — `CrossPointVersionActivity.cpp`

## Next-build restoration candidates

- **Short foreign/proper-name guard (<=5 chars; no vowelless remainder)** — MISSING
- **Compound breakpoint priority / replacement ordering** — MISSING
- **Quoted compound hyphenation** — MISSING
- **Paragraph-final remainder guard: block 1-2 letters, allow 3+** — MISSING
- **Minimum word spacing 50-100%** — MISSING
- **Minimum-space vs natural final-line rehyphenation repair** — MISSING
- **Per-character optical-margin ratios** — MISSING
- **Text Settings avoids Section rebuild when layout unchanged** — MISSING
- **Parser-level time-sliced target reflow** — MISSING
- **Font-change Section lifecycle safety** — MISSING
- **Visible Indexing feedback before rebuild** — PARTIAL
- **Responsive font-size/family reflow state machine** — PARTIAL

## Planned, intentionally not yet integrated

- SMALL CAPS support — postponed until the audited stable typography/reflow baseline is restored.

## Build policy

Before a future Hungarian production firmware build, this audit should be run as a blocking validation. Any MISSING or PARTIAL active feature must be explicitly restored, replaced by an equivalent implementation, or deliberately retired with a documented decision.
