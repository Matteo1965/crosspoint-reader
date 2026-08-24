#!/usr/bin/env python3
from pathlib import Path
from dataclasses import dataclass
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    p = ROOT / path
    return p.read_text(encoding='utf-8', errors='replace') if p.exists() else ''

def has(path, needle): return needle in read(path)
def all_has(path, *needles):
    s = read(path)
    return all(n in s for n in needles)
def exists(path):
    p = ROOT / path
    return p.exists() and p.stat().st_size > 0

@dataclass
class Feature:
    category: str
    name: str
    checks: list[tuple[str,bool,str]]
    history: str = ''
    note: str = ''
    expected: bool = True
    @property
    def status(self):
        vals=[x[1] for x in self.checks]
        if not self.expected:
            return 'RETIRED_OK' if all(vals) else 'RETIRED_PRESENT'
        if all(vals): return 'PRESENT'
        if any(vals): return 'PARTIAL'
        return 'MISSING'

F=[]
def add(category,name,checks,history='',note='',expected=True):
    F.append(Feature(category,name,checks,history,note,expected))

def c(label,ok,evidence): return (label,ok,evidence)

# --- Hyphenation ---
add('Hyphenation','Hungarian hyphenation core',[
 c('generated Hungarian trie',exists('lib/Epub/Epub/hyphenation/generated/hyph-hu.trie.h'),'hyph-hu.trie.h'),
 c('Hungarian registry entry',has('lib/Epub/Epub/hyphenation/LanguageRegistry.cpp','"hungarian", "hu"'),'LanguageRegistry.cpp'),
 c('Hungarian patterns compiled',has('lib/Epub/Epub/hyphenation/generated/hyph-hu.trie.h','hu_patterns'),'hyph-hu.trie.h')])
add('Hyphenation','Extended Hungarian hyphenation toggle and render/cache wiring',[
 c('persistent setting',has('src/CrossPointSettings.h','hungarianHyphenationExtended'),'CrossPointSettings.h'),
 c('Text Settings exposure',has('src/activities/settings/TextSettingsActivity.cpp','HungarianHyphenation'),'TextSettingsActivity.cpp'),
 c('render spec field',has('lib/Epub/Epub/ReaderRenderSpec.h','hungarianHyphenationExtended'),'ReaderRenderSpec.h'),
 c('Section cache compares setting',has('lib/Epub/Epub/Section.cpp','fileHungarianHyphenationExtended'),'Section.cpp')])
add('Hyphenation','Short foreign/proper-name guard (<=5 chars; no vowelless remainder)',[
 c('short-Hungarian automatic-break filter',has('lib/Epub/Epub/hyphenation/Hyphenator.cpp','filterShortHungarianAutomaticBreaks'),'Hyphenator.cpp'),
 c('regression test',has('test/hyphenation_eval/HungarianTypographyRegressionTest.cpp','ShortForeignNamesDoNotLeaveVowellessRemainders'),'HungarianTypographyRegressionTest.cpp')],history='typography round 2')
add('Hyphenation','Compound breakpoint priority / replacement ordering',[
 c('approved replacement priority',has('lib/Epub/Epub/hyphenation/Hyphenator.cpp','a.replacement < b.replacement'),'Hyphenator.cpp'),
 c('compound regression test',has('test/hyphenation_eval/HungarianTypographyRegressionTest.cpp','CompoundBoundaryBeatsFalseExtendedReplacement'),'HungarianTypographyRegressionTest.cpp')],history='2bc5c26b')
add('Hyphenation','Quoted compound hyphenation',[
 c('closing quote before hyphen handling',has('lib/Epub/Epub/hyphenation/Hyphenator.cpp','isClosingQuoteBeforeHyphen'),'Hyphenator.cpp')],history='fb115087 verification')
add('Hyphenation','Paragraph-final remainder guard: block 1-2 letters, allow 3+',[
 c('paragraph-final lexical-word detection',has('lib/Epub/Epub/ParsedText.cpp','isParagraphFinalLexicalWord'),'ParsedText.cpp'),
 c('exact <=2 rule',has('lib/Epub/Epub/ParsedText.cpp','remainderLetterCount <= 2'),'ParsedText.cpp')],history='be05a1ea')

# --- Typography ---
add('Typography','Minimum word spacing 50-100%',[
 c('persistent setting + default 100',all_has('src/CrossPointSettings.h','minimumSpacePercent','minimumSpacePercent = 100'),'CrossPointSettings.h'),
 c('Text Settings control',has('src/activities/settings/TextSettingsActivity.cpp','Min. szóköz'),'TextSettingsActivity.cpp'),
 c('render spec field',has('lib/Epub/Epub/ReaderRenderSpec.h','minimumSpacePercent'),'ReaderRenderSpec.h'),
 c('Section cache field/compare',has('lib/Epub/Epub/Section.cpp','fileMinimumSpacePercent'),'Section.cpp'),
 c('layout scales natural word space',has('lib/Epub/Epub/ParsedText.cpp','scaledNormalSpaceAdvance'),'ParsedText.cpp')],history='fb115087 / b1e53180',note='User-visible regression: menu option disappeared.')
add('Typography','Minimum-space vs natural final-line rehyphenation repair',[
 c('natural 100% final-line pass',has('lib/Epub/Epub/ParsedText.cpp','naturalLineWidth'),'ParsedText.cpp'),
 c('retry final-word hyphenation before whole-word move',has('lib/Epub/Epub/ParsedText.cpp','availableForFinalPrefix') and has('lib/Epub/Epub/ParsedText.cpp','repairedByHyphenation'),'ParsedText.cpp')],history='b821f63c')
add('Typography','Dialogue correction + fixed opening gap',[
 c('persistent setting',has('src/CrossPointSettings.h','fixedDialogueSpacing'),'CrossPointSettings.h'),
 c('Text Settings Layout control',has('src/activities/settings/TextSettingsActivity.cpp','LayoutRow::FixedDialogueSpacing'),'TextSettingsActivity.cpp'),
 c('render spec',has('lib/Epub/Epub/ReaderRenderSpec.h','fixedDialogueSpacing'),'ReaderRenderSpec.h'),
 c('Section cache parameter',has('lib/Epub/Epub/Section.cpp','fileFixedDialogueSpacing'),'Section.cpp'),
 c('ParsedText behavior',has('lib/Epub/Epub/ParsedText.cpp','fixedDialogueSpacing'),'ParsedText.cpp')])
add('Typography','Optical margin / hanging punctuation base feature',[
 c('persistent percentage',has('src/CrossPointSettings.h','hangingPunctuation'),'CrossPointSettings.h'),
 c('Text Settings control',has('src/activities/settings/TextSettingsActivity.cpp','HangingPunctuation'),'TextSettingsActivity.cpp'),
 c('render spec pixel limit',has('lib/Epub/Epub/ReaderRenderSpec.h','hangingPunctuationLimitPx'),'ReaderRenderSpec.h'),
 c('layout allowance',has('lib/Epub/Epub/ParsedText.cpp','hangingPunctuationAllowance'),'ParsedText.cpp')])
add('Typography','Per-character optical-margin ratios',[
 c('hyphen ratio 50%',has('lib/Epub/Epub/ParsedText.cpp','hangingPercent = 50'),'ParsedText.cpp'),
 c('question/exclamation ratio 10%',has('lib/Epub/Epub/ParsedText.cpp','hangingPercent = 10'),'ParsedText.cpp'),
 c('default supported punctuation ratio 25%',has('lib/Epub/Epub/ParsedText.cpp','hangingPercent = 25'),'ParsedText.cpp')],history='97a83230')
add('Typography','Exact justified-line remainder-pixel distribution',[
 c('normal/LTR remainder distribution',has('lib/Epub/Epub/ParsedText.cpp','justifyRemainder'),'ParsedText.cpp'),
 c('reordered/RTL remainder distribution',has('lib/Epub/Epub/ParsedText.cpp','reorderedJustifyRemainder'),'ParsedText.cpp')],history='57151fd6')

# --- Reflow/performance ---
# The strict popup-flush check requires both actions in showBuildPopup(), not a displayBuffer elsewhere.
reader=read('src/activities/reader/EpubReaderActivity.cpp')
show_start=reader.find('void EpubReaderActivity::showBuildPopup')
show_end=reader.find('\n}',show_start)+2 if show_start>=0 else 0
show_body=reader[show_start:show_end] if show_start>=0 and show_end>show_start else ''
add('Reflow/performance','Visible Indexing feedback before rebuild',[
 c('popup helper exists','STR_INDEXING' in show_body,'EpubReaderActivity::showBuildPopup'),
 c('popup physically flushed before long work','renderer.displayBuffer();' in show_body,'EpubReaderActivity::showBuildPopup')],history='fb115087 / b1e53180')
add('Reflow/performance','Text Settings avoids Section rebuild when layout unchanged',[
 c('before/after ReaderRenderSpec comparison',all_has('src/activities/reader/EpubReaderActivity.cpp','beforeSpec','afterSpec'),'EpubReaderActivity.cpp'),
 c('layoutChanged guard',has('src/activities/reader/EpubReaderActivity.cpp','layoutChanged'),'EpubReaderActivity.cpp')],history='b1e53180')
add('Reflow/performance','Responsive font-size/family reflow state machine',[
 c('pending state',has('src/activities/reader/EpubReaderActivity.h','responsiveFontReflowPending'),'EpubReaderActivity.h'),
 c('font-change activation',has('src/activities/reader/EpubReaderActivity.cpp','responsiveFontReflowPending = beforeSpec.fontId != afterSpec.fontId'),'EpubReaderActivity.cpp'),
 c('saved visible-text target retained',has('src/activities/reader/EpubReaderActivity.cpp','cachedVisibleTextOffset'),'EpubReaderActivity.cpp')],history='b821f63c / c85efc1d')
add('Reflow/performance','Parser-level time-sliced target reflow',[
 c('Section target-build method',has('lib/Epub/Epub/Section.cpp','buildTowardVisibleTextOffset'),'Section.cpp'),
 c('12ms parser budget',has('src/activities/reader/EpubReaderActivity.h','RESPONSIVE_REFLOW_PARSE_BUDGET_MS'),'EpubReaderActivity.h'),
 c('target-reached API',has('lib/Epub/Epub/Section.cpp','buildReachedVisibleTextOffset'),'Section.cpp')],history='a3c45269')
# Specific lifecycle fix, not generic abandonBuild used for page-load errors.
add('Reflow/performance','Font-change Section lifecycle safety',[
 c('font-reflow activation context',has('src/activities/reader/EpubReaderActivity.cpp','responsiveFontReflowPending'),'EpubReaderActivity.cpp'),
 c('old-spec build explicitly abandoned before reset',has('src/activities/reader/EpubReaderActivity.cpp','Font reflow: abandoning old-spec active build'),'EpubReaderActivity.cpp')],history='0a303680')

# --- Stability ---
ph=read('lib/Epub/Epub/ParsedText.h')
add('Stability','ParsedText fragmented-heap visible-offset protection',[
 c('deque-backed visible offsets',('VisibleOffsetDeque : std::deque<uint16_t>' in ph) or ('std::deque<uint16_t> wordVisibleOffsetDeltas' in ph),'ParsedText.h'),
 c('reserve compatibility is safe',('void reserve(size_t) noexcept {}' in ph) or ('wordVisibleOffsetDeltas.reserve' not in read('lib/Epub/Epub/ParsedText.cpp')),'ParsedText.h / ParsedText.cpp')],history='63655eb2 + 27886404')

# --- Dictionary ---
add('Dictionary','Hungarian dictionary stemming v16 + case folding',[
 c('v16 implementation marker',has('src/util/Dictionary.cpp','Hungarian dictionary stemming v16'),'Dictionary.cpp'),
 c('HU case fold',has('src/util/Dictionary.cpp','HU_CASE_FOLD'),'Dictionary.cpp'),
 c('stemming regression suite',exists('scripts/run_hungarian_stemming_regression_v2.py'),'run_hungarian_stemming_regression_v2.py'),
 c('false-positive regression suite',exists('scripts/run_hungarian_cpp_false_positive_regression.py'),'run_hungarian_cpp_false_positive_regression.py')])

# --- UI/input ---
add('UI','Hungarian Edition identity/version page',[
 c('boot label',has('src/activities/boot_sleep/BootActivity.cpp','Hungarian Edition'),'BootActivity.cpp'),
 c('version activity',exists('src/activities/settings/CrossPointVersionActivity.cpp'),'CrossPointVersionActivity.cpp'),
 c('Hungarian stemming summary',has('src/activities/settings/CrossPointVersionActivity.cpp','Magyar szótövezés'),'CrossPointVersionActivity.cpp')])
add('UI','RoundedRaff Hungarian Edition dimensions',[
 c('cover height 376',has('src/components/themes/roundedraff/RoundedRaffTheme.h','homeCoverHeight = 376'),'RoundedRaffTheme.h'),
 c('tile height 400',has('src/components/themes/roundedraff/RoundedRaffTheme.h','homeCoverTileHeight = 400'),'RoundedRaffTheme.h')])
add('UI/input','Version-page side buttons follow mapped controls',[
 c('PageForward mapping used',has('src/activities/settings/CrossPointVersionActivity.cpp','MappedInputManager::Button::PageForward'),'CrossPointVersionActivity.cpp')])

try:
    sys.path.insert(0,str(ROOT/'scripts'))
    from gen_i18n import parse_yaml_file
    en=parse_yaml_file(ROOT/'lib/I18n/translations/english.yaml'); hu=parse_yaml_file(ROOT/'lib/I18n/translations/hungarian.yaml')
    parity=set(en)==set(hu); ev=f'EN={len(en)}, HU={len(hu)}, missingHU={len(set(en)-set(hu))}, extraHU={len(set(hu)-set(en))}'
except Exception as e:
    parity=False; ev=str(e)
add('UI','English/Hungarian translation-key parity',[c('key sets match',parity,ev)])

# --- Explicitly retired experiments ---
add('Retired/diagnostic','USB-free performance logger',[
 c('/performance.log absent','/performance.log' not in reader,'production reader'),
 c('PerformanceDiagnostic absent','PerformanceDiagnostic' not in reader,'production reader')],expected=False,note='Diagnostic firmware only; must remain absent from production.')
add('Retired/experimental','Picture filter / Hungarian image brightness experiment',[
 c('picture-filter setting absent','STR_PICTURE_FILTER' not in read('src/SettingsListBase.h'),'SettingsListBase.h'),
 c('brightness hook absent','brightnessPercentForPicture' not in read('lib/Epub/Epub/blocks/ImageBlock.cpp'),'ImageBlock.cpp')],expected=False)
add('Retired/experimental','Long-down screenshot experiment',[
 c('feature absent','longDownScreenshot' not in read('src/main.cpp') and 'STR_LONG_DOWN_SCREENSHOT' not in read('src/SettingsListBase.h'),'production source')],expected=False)

icons={'PRESENT':'✅ PRESENT','PARTIAL':'⚠️ PARTIAL','MISSING':'❌ MISSING','RETIRED_OK':'🟦 RETIRED (correctly absent)','RETIRED_PRESENT':'🟥 RETIRED FEATURE LEAKED BACK'}
active=[f for f in F if f.expected]
present=[f for f in active if f.status=='PRESENT']; partial=[f for f in active if f.status=='PARTIAL']; missing=[f for f in active if f.status=='MISSING']; leaked=[f for f in F if not f.expected and f.status=='RETIRED_PRESENT']

out=['# Hungarian Edition feature audit v2','',
     'Strict feature-specific audit against the checked-out production source. Equivalent implementations are accepted only where explicitly encoded in the audit.', '',
     '## Summary','',f'- Active features: **{len(active)}**',f'- Present: **{len(present)}**',f'- Partial: **{len(partial)}**',f'- Missing: **{len(missing)}**',f'- Retired features unexpectedly present: **{len(leaked)}**','']
for cat in sorted(set(f.category for f in F)):
    out += [f'## {cat}','']
    for f in [x for x in F if x.category==cat]:
        out += [f'### {icons[f.status]} — {f.name}','']
        if f.history: out += [f'Historical reference: `{f.history}`','']
        if f.note: out += [f.note,'']
        for label,ok,evd in f.checks: out.append(f"- {'✅' if ok else '❌'} {label} — `{evd}`")
        out.append('')
out += ['## Next-build restoration candidates','']
for f in missing+partial: out.append(f'- **{f.name}** — {f.status}')
if not missing and not partial: out.append('No active restoration candidate detected.')
out += ['', '## Planned, intentionally not yet integrated','', '- SMALL CAPS support — postponed until the audited stable typography/reflow baseline is restored.', '',
        '## Build policy','', 'Before a future Hungarian production firmware build, this audit should be run as a blocking validation. Any MISSING or PARTIAL active feature must be explicitly restored, replaced by an equivalent implementation, or deliberately retired with a documented decision.','']
(ROOT/'docs/HUNGARIAN_EDITION_FEATURES.md').write_text('\n'.join(out),encoding='utf-8')
print(f'Present={len(present)} Partial={len(partial)} Missing={len(missing)} Leaked={len(leaked)}')
print('Restoration candidates:')
for f in missing+partial: print(f' - {f.status}: {f.name}')
