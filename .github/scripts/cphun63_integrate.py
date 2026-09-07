from pathlib import Path


def patch_once(path: str, old: str, new: str, marker: str) -> None:
    p = Path(path)
    s = p.read_text()
    if marker in s:
        return
    if old not in s:
        raise SystemExit(f"{path}: missing patch anchor for {marker}")
    p.write_text(s.replace(old, new, 1))


# 57c692f: port only the memory-gate logic while preserving CPHUN parser arguments.
p = Path("src/util/DictHtmlPages.cpp")
s = p.read_text()
if "MIN_STYLED_RETAIN_HEAP" not in s:
    old = """// Keep enough contiguous heap for the parser's 16KB SD-font advance scratch
// plus page/layout allocations. Falling back to plain text is cheaper than
// entering a throwing allocation path under pressure.
constexpr size_t MIN_STYLED_FREE_HEAP = 40 * 1024;
constexpr size_t MIN_STYLED_MAX_ALLOC = 20 * 1024;
"""
    new = """// ENTRY gate: is there room to start a styled layout at all? Keeps enough
// contiguous heap for the parser's 16KB SD-font advance scratch plus
// page/layout allocations. Falling back to plain text is cheaper than entering
// a throwing allocation path under pressure.
constexpr size_t MIN_STYLED_FREE_HEAP = 40 * 1024;
constexpr size_t MIN_STYLED_MAX_ALLOC = 20 * 1024;

// RETAIN gate: the parser is already alive here, so use a lower floor than the
// entry gate. The retained page count/element caps below still bound memory use.
constexpr size_t MIN_STYLED_RETAIN_HEAP = 16 * 1024;
constexpr size_t MIN_STYLED_RETAIN_ALLOC = 8 * 1024;
"""
    if old not in s:
        raise SystemExit("DictHtmlPages.cpp: missing entry-gate block")
    s = s.replace(old, new, 1)
    s = s.replace(
        "  bool resourceLimitHit = false;\n  size_t retainedElements = 0;",
        "  bool resourceLimitHit = false;\n  const char* limitReason = nullptr;\n  size_t retainedElements = 0;",
        1,
    )
    old_lambda = """        [&pagesOut, &resourceLimitHit, &retainedElements](std::unique_ptr<Page> page, uint16_t, uint16_t, uint32_t) {
          if (resourceLimitHit) return;
          const size_t pageElements = page->elements.size();
          if (pagesOut.size() >= MAX_STYLED_PAGES || pageElements > MAX_STYLED_PAGE_ELEMENTS - retainedElements ||
              ESP.getFreeHeap() < MIN_STYLED_FREE_HEAP || ESP.getMaxAllocHeap() < MIN_STYLED_MAX_ALLOC) {
            resourceLimitHit = true;
            pagesOut.clear();
            return;
          }
          retainedElements += pageElements;
          pagesOut.push_back(std::move(page));
        },
"""
    new_lambda = """        [&pagesOut, &resourceLimitHit, &retainedElements, &limitReason](std::unique_ptr<Page> page, uint16_t, uint16_t,
                                                                        uint32_t) {
          if (resourceLimitHit) return;
          const size_t pageElements = page->elements.size();
          if (pagesOut.size() >= MAX_STYLED_PAGES) {
            limitReason = \"page count\";
          } else if (pageElements > MAX_STYLED_PAGE_ELEMENTS - retainedElements) {
            limitReason = \"element count\";
          } else if (ESP.getFreeHeap() < MIN_STYLED_RETAIN_HEAP || ESP.getMaxAllocHeap() < MIN_STYLED_RETAIN_ALLOC) {
            limitReason = \"free heap\";
          }
          if (limitReason != nullptr) {
            LOG_ERR(\"DHTML\", \"Styled definition stopped on %s (pages=%u elements=%u free=%u contig=%u)\", limitReason,
                    static_cast<unsigned>(pagesOut.size()), static_cast<unsigned>(retainedElements + pageElements),
                    ESP.getFreeHeap(), ESP.getMaxAllocHeap());
            resourceLimitHit = true;
            pagesOut.clear();
            return;
          }
          retainedElements += pageElements;
          pagesOut.push_back(std::move(page));
        },
"""
    if old_lambda not in s:
        raise SystemExit("DictHtmlPages.cpp: missing retain lambda block")
    s = s.replace(old_lambda, new_lambda, 1)
    p.write_text(s)


# 84fcff8: release dictionary SD-font caches on exit.
patch_once(
    "src/activities/reader/DictionaryDefinitionActivity.h",
    "  void onEnter() override;\n  void loop() override;",
    "  void onEnter() override;\n  void onExit() override;\n  void loop() override;",
    "void onExit() override;",
)

patch_once(
    "src/activities/reader/DictionaryDefinitionActivity.cpp",
    "  requestUpdate();\n}\n\nDictionaryDefinitionActivity::BodyArea DictionaryDefinitionActivity::bodyArea() const {",
    "  requestUpdate();\n}\n\nvoid DictionaryDefinitionActivity::onExit() {\n  Activity::onExit();\n  if (auto* fcm = renderer.getFontCacheManager()) {\n    fcm->releaseSdFontCaches();\n  }\n}\n\nDictionaryDefinitionActivity::BodyArea DictionaryDefinitionActivity::bodyArea() const {",
    "void DictionaryDefinitionActivity::onExit()",
)


# Dictionary-only part of 8cb0a39: hold Left/Right for repeated word navigation.
p = Path("src/activities/reader/DictionaryWordSelectActivity.cpp")
s = p.read_text()
if "WORD_REPEAT_START_MS" not in s:
    s = s.replace(
        "constexpr unsigned long POPUP_DURATION_MS = 1500;\n",
        "constexpr unsigned long POPUP_DURATION_MS = 1500;\nconstexpr unsigned long WORD_REPEAT_START_MS = 500;\nconstexpr unsigned long WORD_REPEAT_INTERVAL_MS = 500;\n",
        1,
    )
    old = (
        "  const bool hasNextWord = selected + 1 < static_cast<int>(words.size());\n"
        "  if (mappedInput.wasPressed(MappedInputManager::Button::ScreenLeft) && selected > 0) {\n"
        "    selected--;\n"
        "    requestUpdate();\n"
        "  } else if (mappedInput.wasPressed(MappedInputManager::Button::ScreenRight) && hasNextWord) {\n"
        "    selected++;\n"
        "    requestUpdate();\n"
    )
    new = (
        "  const bool hasNextWord = selected + 1 < static_cast<int>(words.size());\n"
        "  const unsigned long now = millis();\n"
        "  const bool repeat =\n"
        "      mappedInput.getHeldTime() >= WORD_REPEAT_START_MS && now - lastHorizontalMoveTime >= WORD_REPEAT_INTERVAL_MS;\n"
        "  const bool moveLeft = mappedInput.wasPressed(MappedInputManager::Button::ScreenLeft) ||\n"
        "                        (repeat && mappedInput.isPressed(MappedInputManager::Button::ScreenLeft));\n"
        "  const bool moveRight = mappedInput.wasPressed(MappedInputManager::Button::ScreenRight) ||\n"
        "                         (repeat && mappedInput.isPressed(MappedInputManager::Button::ScreenRight));\n"
        "  if (moveLeft && selected > 0) {\n"
        "    selected--;\n"
        "    lastHorizontalMoveTime = now;\n"
        "    requestUpdate();\n"
        "  } else if (moveRight && hasNextWord) {\n"
        "    selected++;\n"
        "    lastHorizontalMoveTime = now;\n"
        "    requestUpdate();\n"
    )
    if old not in s:
        raise SystemExit("DictionaryWordSelectActivity.cpp: missing horizontal navigation block")
    p.write_text(s.replace(old, new, 1))

patch_once(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    "  int selected = 0;\n  uint16_t rowCount = 0;\n",
    "  int selected = 0;\n  uint16_t rowCount = 0;\n  unsigned long lastHorizontalMoveTime = 0;\n",
    "lastHorizontalMoveTime = 0;",
)

# 5182d27 was already integrated earlier; verify only.
if "std::isalnum" not in Path("src/util/HtmlToPlainText.cpp").read_text():
    raise SystemExit("5182d27 regression: heading tag scan fix is missing")

Path("src/CPHUNBuildId.h").write_text('#pragma once\n\n#define CPHUN_BUILD_ID "CPHUN-260907-63"\n')
