from pathlib import Path
import re

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, s):
    Path(path).write_text(s, encoding="utf-8")

# ---------------------------------------------------------------------------
# Persisted word-selector mode: 0=Dictionary, 1=Highlight, 2=Edit
# ---------------------------------------------------------------------------
p = "src/CrossPointSettings.h"
s = read(p)
anchor = '  char dictionaryName[32] = "";\n'
if s.count(anchor) != 1:
    raise SystemExit(f"CPHUN-136R3: dictionaryName header anchor matches={s.count(anchor)}")
s = s.replace(
    anchor,
    anchor + '  // Word selector mode used by the hardware OpenDictionary action: 0=Dictionary, 1=Highlight, 2=Edit.\n'
             '  uint8_t wordSelectionMode = 0;\n',
    1,
)
write(p, s)

p = "src/CrossPointSettings.cpp"
s = read(p)
save_anchor = '''  if (dictionaryName[0] != '\\0') {
    doc["dictionaryName"] = dictionaryName;
  }
'''
if s.count(save_anchor) != 1:
    raise SystemExit(f"CPHUN-136R3: dictionary save anchor matches={s.count(save_anchor)}")
s = s.replace(save_anchor, save_anchor + '  doc["wordSelectionMode"] = wordSelectionMode;\n', 1)

load_anchor = '''  // Dictionary folder name — uses dynamic getter/setter in SettingsList, load manually
  copyToField(dictionaryName, doc["dictionaryName"] | "", sizeof(dictionaryName));
'''
if s.count(load_anchor) != 1:
    raise SystemExit(f"CPHUN-136R3: dictionary load anchor matches={s.count(load_anchor)}")
s = s.replace(
    load_anchor,
    load_anchor +
    '''  const uint8_t storedWordSelectionMode = doc["wordSelectionMode"] | (uint8_t)0;
  if (storedWordSelectionMode <= 2) {
    wordSelectionMode = storedWordSelectionMode;
  } else {
    wordSelectionMode = 0;
    needsResave = true;
  }
''',
    1,
)
write(p, s)

# ---------------------------------------------------------------------------
# Reader menu: add in-place "Mód választó" option.
# ---------------------------------------------------------------------------
hp = "src/activities/reader/EpubReaderMenuActivity.h"
h = read(hp)
enum_anchor = "    DICTIONARY,\n"
if h.count(enum_anchor) != 1:
    raise SystemExit(f"CPHUN-136R3: DICTIONARY enum anchor matches={h.count(enum_anchor)}")
h = h.replace(enum_anchor, "    WORD_SELECTION_MODE,\n" + enum_anchor, 1)
h = re.sub(r'static constexpr size_t MAX_MENU_ITEMS = \d+;',
           'static constexpr size_t MAX_MENU_ITEMS = 16;', h, count=1)
write(hp, h)

mp = "src/activities/reader/EpubReaderMenuActivity.cpp"
m = read(mp)
row_anchor = '  items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótár"});\n'
if m.count(row_anchor) != 1:
    raise SystemExit(f"CPHUN-136R3: dictionary Reader-menu row matches={m.count(row_anchor)}")
m = m.replace(
    row_anchor,
    '  items.push_back({MenuAction::WORD_SELECTION_MODE, StrId::STR_LOOKUP, "Mód választó"});\n' + row_anchor,
    1,
)

activate_anchor = '  if (selectedAction == MenuAction::DICTIONARY_SETTINGS) {\n'
if m.count(activate_anchor) != 1:
    raise SystemExit(f"CPHUN-136R3: dictionary settings activation anchor matches={m.count(activate_anchor)}")
mode_handler = '''  if (selectedAction == MenuAction::WORD_SELECTION_MODE) {
    static const char* modeLabels[] = {"Szótár", "Megjelölés", "Szerkesztés"};
    const uint8_t selected = SETTINGS.wordSelectionMode <= 2 ? SETTINGS.wordSelectionMode : 0;
    optionPopup.show("Mód választó", modeLabels, 3, selected, [this](int idx) {
      SETTINGS.wordSelectionMode = static_cast<uint8_t>(idx);
      SETTINGS.saveToFile();
      requestUpdate();
    });
    requestUpdate();
    return;
  }

'''
m = m.replace(activate_anchor, mode_handler + activate_anchor, 1)

build_anchor = '''    if (action == MenuAction::ROTATE_SCREEN) {
'''
if m.count(build_anchor) != 1:
    raise SystemExit(f"CPHUN-136R3: buildScreen action anchor matches={m.count(build_anchor)}")
m = m.replace(
    build_anchor,
    '''    if (action == MenuAction::WORD_SELECTION_MODE) {
      static const char* modeLabels[] = {"Szótár", "Megjelölés", "Szerkesztés"};
      menuRowItems[i].value = modeLabels[SETTINGS.wordSelectionMode <= 2 ? SETTINGS.wordSelectionMode : 0];
    } else if (action == MenuAction::ROTATE_SCREEN) {
''',
    1,
)
write(mp, m)

# ---------------------------------------------------------------------------
# Hardware OpenDictionary action follows the persisted mode.
# ---------------------------------------------------------------------------
rp = "src/activities/reader/EpubReaderActivity.cpp"
r = read(rp)
hardware_old = '''    if (configured == ReaderAction::OpenDictionary) { openDictionaryWordSelect(); return true; }'''
hardware_new = '''    if (configured == ReaderAction::OpenDictionary) {
      WordSelectionMode mode = WordSelectionMode::Dictionary;
      if (SETTINGS.wordSelectionMode == 1) mode = WordSelectionMode::Highlight;
      else if (SETTINGS.wordSelectionMode == 2) mode = WordSelectionMode::Edit;
      openDictionaryWordSelect(mode);
      return true;
    }'''
if r.count(hardware_old) != 1:
    raise SystemExit(f"CPHUN-136R3: hardware OpenDictionary anchor matches={r.count(hardware_old)}")
r = r.replace(hardware_old, hardware_new, 1)
write(rp, r)

# ---------------------------------------------------------------------------
# Semantic verification
# ---------------------------------------------------------------------------
for token in [
    'MenuAction::WORD_SELECTION_MODE',
    '"Mód választó"',
    '{"Szótár", "Megjelölés", "Szerkesztés"}',
]:
    if token not in read(mp):
        raise SystemExit(f"CPHUN-136R3: Reader-menu mode selector missing: {token}")

settings_h = read("src/CrossPointSettings.h")
settings_cpp = read("src/CrossPointSettings.cpp")
reader = read(rp)
for token in ['uint8_t wordSelectionMode = 0;', 'doc["wordSelectionMode"] = wordSelectionMode;',
              'storedWordSelectionMode']:
    if token not in settings_h + settings_cpp:
        raise SystemExit(f"CPHUN-136R3: persisted mode missing: {token}")

for token in [
    'SETTINGS.wordSelectionMode == 1',
    'SETTINGS.wordSelectionMode == 2',
    'openDictionaryWordSelect(mode)',
]:
    if token not in reader:
        raise SystemExit(f"CPHUN-136R3: hardware mode dispatch missing: {token}")

print("CPHUN-136R3 applied: persisted Mód választó controls the common hardware word selector")
