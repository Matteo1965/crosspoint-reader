from pathlib import Path
import re


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-134: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def regex_replace_once(path, pattern, replacement):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    text2, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"CPHUN-134: {path}: regex expected one match, found {count}: {pattern[:180]!r}")
    p.write_text(text2, encoding="utf-8")


# The #131 -> #132 device regression was isolated to starting the highlight
# prompt synchronously from performLookup() after a genuine dictionary miss.
# Defer that activity transition to the next normal Activity::loop() turn.
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    "  void showHighlightPrompt(bool noDictionary);\n",
    "  void showHighlightPrompt(bool noDictionary);\n  void queueHighlightPrompt(bool noDictionary);\n",
)

replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    "  unsigned long popupTime = 0;\n",
    "  unsigned long popupTime = 0;\n  bool pendingHighlightPrompt = false;\n  bool pendingHighlightPromptNoDictionary = false;\n",
)

# Insert a tiny queue helper immediately before the existing prompt opener.
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    "void DictionaryWordSelectActivity::showHighlightPrompt(const bool noDictionary) {\n",
    "void DictionaryWordSelectActivity::queueHighlightPrompt(const bool noDictionary) {\n"
    "  pendingHighlightPrompt = true;\n"
    "  pendingHighlightPromptNoDictionary = noDictionary;\n"
    "  popup = Popup::None;\n"
    "  snapshotIdx = -1;\n"
    "  requestUpdate();\n"
    "}\n\n"
    "void DictionaryWordSelectActivity::showHighlightPrompt(const bool noDictionary) {\n",
)

# No-dictionary is the same unsafe transition shape, so defer it too.
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    "  if (SETTINGS.dictionaryName[0] == '\\0') {\n    showHighlightPrompt(true);\n    return;\n  }\n",
    "  if (SETTINGS.dictionaryName[0] == '\\0') {\n    queueHighlightPrompt(true);\n    return;\n  }\n",
)

# Genuine NotFound must not start a child Activity while the blocking lookup
# call stack is still unwinding. Queue it and return to the main loop first.
regex_replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    r"(case Dictionary::LookupResult::NotFound:\n\s*default:\n\s*)showHighlightPrompt\(false\);\n\s*return;",
    r"\1queueHighlightPrompt(false);\n        return;",
)

# Consume the queued transition at the very start of the next loop turn.
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    "void DictionaryWordSelectActivity::loop() {\n",
    "void DictionaryWordSelectActivity::loop() {\n"
    "  if (pendingHighlightPrompt) {\n"
    "    const bool noDictionary = pendingHighlightPromptNoDictionary;\n"
    "    pendingHighlightPrompt = false;\n"
    "    pendingHighlightPromptNoDictionary = false;\n"
    "    showHighlightPrompt(noDictionary);\n"
    "    return;\n"
    "  }\n",
)

# Give the diagnostic firmware its own visible build identity.
p = Path("src/CPHUNBuildId.h")
s = p.read_text(encoding="utf-8")
s2, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"', '#define CPHUN_BUILD_ID "CPHUN-260916-134-EXP"', s, count=1)
if n != 1:
    raise SystemExit(f"CPHUN-134: build id replacement failed: {n}")
p.write_text(s2, encoding="utf-8")

print("CPHUN-134 deferred NotFound/highlight prompt fix applied")
