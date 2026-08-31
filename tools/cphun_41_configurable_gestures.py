from pathlib import Path

p=Path('src/activities/settings/ButtonFunctionsActivity.cpp')
t=p.read_text(encoding='utf-8')
# Final requested UI position and wording.
t=t.replace('constexpr int kButtonX = 115;', 'constexpr int kButtonX = 125;')
t=t.replace('constexpr int kButtonX = 105;', 'constexpr int kButtonX = 125;')
t=t.replace('constexpr int kButtonX = 145;', 'constexpr int kButtonX = 125;')
t=t.replace('"Hosszan:"', '"Hosszú:"').replace('"Tart:"', '"Hosszú:"')
t=t.replace('return hu ? "Alsó gombok" : "Bottom buttons";', 'return hu ? "Alsó gombkiosztás" : "Bottom button layout";')
# User-facing name for the existing extended/soft-hyphen toggle.
t=t.replace('case ReaderAction::ToggleSoftHyphen: return "Soft Hyphen";', 'case ReaderAction::ToggleSoftHyphen: return hu ? "Kiterjesztett elválasztás" : "Extended hyphenation";')
p.write_text(t,encoding='utf-8')

# Turn the safe CPHUN-38/39 dispatcher into a gesture dispatcher. Single and Hold
# use the same saved 12-slot profile as Double. None preserves legacy behaviour.
p=Path('src/activities/reader/EpubReaderActivity.cpp')
t=p.read_text(encoding='utf-8')
old='''  const auto cphun36DoubleAction = [this, &cphun36OpenSettings, &cphun36OpenLayout, &cphun36RebuildReader](\n                                      const int raw) {\n    ReaderPhysicalButton physical = ReaderPhysicalButton::Back;'''
new='''  const auto cphun36GestureAction = [this, &cphun36OpenSettings, &cphun36OpenLayout, &cphun36RebuildReader](\n                                      const int raw, const ReaderButtonGesture gesture) -> bool {\n    ReaderPhysicalButton physical = ReaderPhysicalButton::Back;'''
if old not in t: raise SystemExit('CPHUN-41 dispatcher anchor missing')
t=t.replace(old,new,1)
t=t.replace('const ReaderAction configured = READER_BUTTONS.get(physical, ReaderButtonGesture::Double);\n    if (configured == ReaderAction::None) return;', 'const ReaderAction configured = READER_BUTTONS.get(physical, gesture);\n    if (configured == ReaderAction::None) return false;',1)
# Make specialized action returns report consumption.
start=t.index('  const auto cphun36GestureAction')
end=t.index('  const auto cphun36LegacyShort', start)
block=t[start:end]
block=block.replace('{ cphun36OpenLayout(); return; }','{ cphun36OpenLayout(); return true; }')
block=block.replace('{ onGoHome(); return; }','{ onGoHome(); return true; }')
block=block.replace('{ openReaderMenu(); return; }','{ openReaderMenu(); return true; }')
block=block.replace('requestUpdate(); return; }','requestUpdate(); return true; }')
block=block.replace('cphun36RebuildReader(); return; }','cphun36RebuildReader(); return true; }')
block=block.replace('      return;\n    }','      return true;\n    }')
# Existing fallback body is retained for currently supported actions; it must consume.
last=block.rfind('\n  };')
block=block[:last]+'\n    return true;'+block[last:]
t=t[:start]+block+t[end:]
# Single: configured action overrides legacy single; None keeps the proven legacy path.
needle='''  const auto cphun36LegacyShort = [this](const int raw) {'''
repl='''  const auto cphun36LegacyShort = [this, &cphun36GestureAction](const int raw) {\n    if (cphun36GestureAction(raw, ReaderButtonGesture::Single)) return;'''
t=t.replace(needle,repl,1)
# Double now uses the same generic dispatcher.
t=t.replace('cphun36DoubleAction(cphun36ReleasedRaw);','cphun36GestureAction(cphun36ReleasedRaw, ReaderButtonGesture::Double);',1)
# Hold: if a configured Hold exists consume it; otherwise preserve legacy hold processing.
needle='''    } else if (cphun36.waitingSecond && cphun36.raw == cphun36ReleasedRaw) {\n      cphun36.waitingSecond = false;\n    }'''
repl='''    } else {\n      if (cphun36.waitingSecond && cphun36.raw == cphun36ReleasedRaw) cphun36.waitingSecond = false;\n      if (cphun36GestureAction(cphun36ReleasedRaw, ReaderButtonGesture::Hold)) {\n        cphun36ConsumeFrontShort = true;\n      }\n    }'''
if needle not in t: raise SystemExit('CPHUN-41 hold anchor missing')
t=t.replace(needle,repl,1)
p.write_text(t,encoding='utf-8')

# Verify requested UI/profile integration without touching Power/side paths.
assert 'constexpr int kButtonX = 125;' in Path('src/activities/settings/ButtonFunctionsActivity.cpp').read_text(encoding='utf-8')
assert '"Hosszú:"' in Path('src/activities/settings/ButtonFunctionsActivity.cpp').read_text(encoding='utf-8')
assert 'Kiterjesztett elválasztás' in Path('src/activities/settings/ButtonFunctionsActivity.cpp').read_text(encoding='utf-8')
r=Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
for s in ['ReaderButtonGesture::Single','ReaderButtonGesture::Double','ReaderButtonGesture::Hold','Button::Power','Button::PageBack','Button::PageForward']:
    assert s in r, s
print('Applied CPHUN-41 configurable 1x/2x/Hosszú gesture integration')
