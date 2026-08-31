from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Expected anchor not found in {path}: {old!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# New build identity.
replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260830-36"',
    '#define CPHUN_BUILD_ID "CPHUN-260831-37"',
)

# The 12-slot ReaderButtonProfileStore already exists on the CPHUN-36 branch,
# but was deliberately not loaded during the gesture-prototype phase. CPHUN-37
# promotes it into the normal boot lifecycle so menu edits can persist.
replace_once(
    "src/main.cpp",
    '#include "RecentBooksStore.h"\n',
    '#include "RecentBooksStore.h"\n#include "ReaderButtonProfileStore.h"\n',
)
replace_once(
    "src/main.cpp",
    '  RECENT_BOOKS.loadFromFile();\n  I18N.setLanguage(static_cast<Language>(SETTINGS.language));\n',
    '  RECENT_BOOKS.loadFromFile();\n  READER_BUTTONS.loadFromFile();\n  I18N.setLanguage(static_cast<Language>(SETTINGS.language));\n',
)

# Guard the persistence contract: persisted ReaderAction values and 12 slots
# must remain stable while the configurable-menu work is built on top.
action = Path("src/ReaderAction.h").read_text(encoding="utf-8")
profile = Path("src/ReaderButtonProfile.h").read_text(encoding="utf-8")
store = Path("src/ReaderButtonProfileStore.h").read_text(encoding="utf-8")
main = Path("src/main.cpp").read_text(encoding="utf-8")

required = {
    "ReaderAction append-only contract": "must never be reordered or reused" in action,
    "ReaderAction count": "COUNT" in action,
    "12-slot profile": "READER_BUTTON_ACTION_SLOT_COUNT" in profile,
    "profile store path": "/.crosspoint/reader-buttons.json" in store,
    "profile boot load": "READER_BUTTONS.loadFromFile();" in main,
}
for name, ok in required.items():
    if not ok:
        raise SystemExit(f"CPHUN-37 foundation check failed: {name}")

print("Applied CPHUN-37 configurable button-functions foundation")
