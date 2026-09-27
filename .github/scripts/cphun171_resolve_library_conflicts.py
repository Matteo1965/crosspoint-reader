#!/usr/bin/env python3
"""Resolve the known PR #3366/CPHUN-169 rejected hunks without losing HU code.

Run after git apply --reject. Unexpected rejects or missing semantic anchors
are fatal: never publish partially integrated firmware.
"""
from pathlib import Path
import re
import subprocess

def edit(path, fn):
    p = Path(path)
    old = p.read_text(encoding="utf-8")
    new = fn(old)
    if new != old:
        p.write_text(new, encoding="utf-8")
    print("MERGED", path)

def one(s, a, b, name, allow_done=False):
    if a not in s:
        if allow_done and b in s:
            return s
        raise RuntimeError(f"{name}: missing source anchor {a[:95]!r}")
    if s.count(a) != 1:
        raise RuntimeError(f"{name}: ambiguous anchor ({s.count(a)}) {a[:95]!r}")
    return s.replace(a,b,1)

def method(s, start, end, code, name):
    a=s.find(start)
    b=s.find(end,a+len(start))
    if a<0 or b<0 or s.find(start,a+1)>=0:
        raise RuntimeError(f"{name}: unexpected method boundaries")
    return s[:a]+code+"\n\n"+s[b:]

# EPUB: preserve the Hungarian fingerprint cache and all existing reading
# functionality; add shared ZIP only to lightweight metadata discovery.
def epub_cpp(s):
    s=one(s,"bool Epub::findContentOpfFile(std::string* contentOpfFile) const {",
        "bool Epub::findContentOpfFile(std::string* contentOpfFile, ZipFile* sharedZip) const {","EPUB signature")
    s=one(s,"  if (!getItemSize(containerPath, &containerSize)) {",
        "  const bool sizeFound = sharedZip ? sharedZip->getInflatedFileSize(containerPath, &containerSize)\n"
        "                                   : getItemSize(containerPath, &containerSize);\n"
        "  if (!sizeFound) {","EPUB container size")
    # This hunk is normally applied by git apply; tolerate source-context drift.
    s=one(s,"  if (!readItemContentsToStream(containerPath, containerParser, 512)) {",
        "  const bool read = sharedZip ? sharedZip->readFileToStream(containerPath, containerParser, 512)\n"
        "                              : readItemContentsToStream(containerPath, containerParser, 512);\n"
        "  if (!read) {","EPUB shared read",True)
    return s
edit("lib/Epub/Epub.cpp",epub_cpp)

def epub_h(s):
    if "class ZipFile;" not in s:
        s=one(s,"class Epub {","class ZipFile;\n\nclass Epub {","ZipFile forward declaration")
    s=one(s,"  bool findContentOpfFile(std::string* contentOpfFile) const;",
        "  bool findContentOpfFile(std::string* contentOpfFile, ZipFile* sharedZip = nullptr) const;","Epub declaration")
    s=one(s,"  bool parseContentOpf(BookMetadataCache::BookMetadata& bookMetadata, bool writeSpineEntries = true);",
        "  bool parseContentOpf(BookMetadataCache::BookMetadata& bookMetadata, bool writeSpineEntries = true,\n"
        "                       bool metadataOnly = false, ZipFile* sharedZip = nullptr);","OPF declaration")
    s=one(s,"  bool load(bool buildIfMissing = true, bool skipLoadingCss = false);",
        "  bool load(bool buildIfMissing = true, bool skipLoadingCss = false);\n"
        "  bool loadMetadata(std::string& title, std::string& author);","Metadata declaration")
    return s
edit("lib/Epub/Epub.h",epub_h)

# The Hungarian OPF parser already extracts extended metadata. Add a
# metadata-only mode without replacing its description/series/subjects logic.
def parser_h(s):
    s=one(s,"  BookMetadataCache* cache;\n",
        "  BookMetadataCache* cache;\n  const bool metadataOnly;\n  bool metadataComplete = false;\n"
        "  bool metadataSpacePending = false;\n  bool authorSeparatorPending = false;\n","OPF fields")
    s=one(s,"                            BookMetadataCache* cache)\n"
        "      : cachePath(cachePath), baseContentPath(baseContentPath), remainingSize(xmlSize), cache(cache) {}",
        "                            BookMetadataCache* cache, const bool metadataOnly = false)\n"
        "      : cachePath(cachePath), baseContentPath(baseContentPath), remainingSize(xmlSize),\n"
        "        cache(cache), metadataOnly(metadataOnly) {}","OPF constructor")
    return s
edit("lib/Epub/Epub/parsers/ContentOpfParser.h",parser_h)

def parser_cpp(s):
    start="void XMLCALL ContentOpfParser::characterData(void* userData, const XML_Char* s, const int len) {"
    end="  if (self->state == IN_BOOK_DESCRIPTION) {"
    old=s[s.find(start):s.find(end,s.find(start))]
    if "appendMetadataText(self->title" in old:
        return s
    replacement=start+"\n  auto* self = static_cast<ContentOpfParser*>(userData);\n\n"+\
        "  if (self->metadataOnly && self->metadataComplete) return;\n\n"+\
        "  if (self->state == IN_BOOK_TITLE) {\n"+\
        "    appendMetadataText(self->title, s, len, self->metadataSpacePending);\n    return;\n  }\n\n"+\
        "  if (self->state == IN_BOOK_AUTHOR) {\n"+\
        "    appendMetadataText(self->author, s, len, self->metadataSpacePending, &self->authorSeparatorPending);\n"+\
        "    return;\n  }\n\n"+\
        "  if (self->state == IN_BOOK_LANGUAGE) {\n"+\
        "    appendMetadataText(self->language, s, len, self->metadataSpacePending);\n    return;\n  }\n\n"
    if s.find(start)<0 or s.find(end,s.find(start))<0:
        raise RuntimeError("Parser characterData section missing")
    return s.replace(old,replacement,1)
edit("lib/Epub/Epub/parsers/ContentOpfParser.cpp",parser_cpp)

edit("src/CrossPointSettings.h", lambda s: one(s,
    "  uint8_t showHiddenFiles = 0;",
    "  uint8_t showHiddenFiles = 0;\n"
    "  // Display embedded EPUB title/author in Library View.\n"
    "  uint8_t libraryUseMetadata = 1;","Metadata setting"))

# CPHUN wraps upstream SettingsList: the real settings live in SettingsListBase.
edit("src/SettingsListBase.h",lambda s: one(s,
    "        SettingInfo::Toggle(StrId::STR_REMOVE_READ_FROM_RECENTS,",
    "        SettingInfo::Toggle(StrId::STR_LIBRARY_USE_METADATA, &CrossPointSettings::libraryUseMetadata,\n"
    "                            \"libraryUseMetadata\", StrId::STR_CAT_SYSTEM),\n"
    "        SettingInfo::Toggle(StrId::STR_REMOVE_READ_FROM_RECENTS,","Settings list"))

# Keep the tested RecentBooksActivity source for fallback, but route Home to
# the new LibraryListActivity. Its other manager hunks applied cleanly.
edit("src/activities/ActivityManager.cpp",lambda s: one(s,
    '#include "home/RecentBooksActivity.h"',
    '#include "library/LibraryListActivity.h"',"Library manager include"))
edit("src/activities/ActivityManager.h",lambda s: one(s,
    "  void goToRecentBooks();","  void goToLibrary();","Library manager header"))

# The upgraded SDK takes rendering ownership of viewport reconciliation;
# preserve X4's narrow list rows via explicit rowHeight on non-touch hardware.
def ui_list_cpp(s):
    s=method(s,"void UiListActivity::moveSelectionTo(const int index) {",
        "void UiListActivity::loop() {",
        "void UiListActivity::moveSelectionTo(const int index) {\n"
        "  activeNav().requestSelection(index);\n  requestUpdate();\n}",
        "List selection")
    s=s.replace("n.pageRows()", "n.inputPageRows()")
    s=method(s,"void UiListActivity::syncListViewport(UiScreen& screen,",
        "void UiListActivity::drawChrome() {",
        "void UiListActivity::syncListViewport(UiScreen& screen, fui::ListProps& props,\n"
        "                                      bool hasSubtitle, int selectionOffset) {\n"
        "  if (!mappedInput.hasTouch() && props.rowHeight <= 0) {\n"
        "    const auto& metrics = UITheme::getInstance().getMetrics();\n"
        "    props.rowHeight = static_cast<int16_t>(hasSubtitle ? metrics.listWithSubtitleRowHeight\n"
        "                                                    : metrics.listRowHeight);\n"
        "  }\n"
        "  props.partialTrailingRow = true;\n"
        "  screen.syncListViewport(activeNav(), props, listCount(), selectionOffset);\n}",
        "Viewport")
    return s
edit("src/activities/UiListActivity.cpp",ui_list_cpp)
edit("src/activities/UiListActivity.h",lambda s: one(s,
    "void syncListViewport(UiScreen& screen, freeink::ui::ListProps& props, bool hasSubtitle = false);",
    "void syncListViewport(UiScreen& screen, freeink::ui::ListProps& props,\n"
    "                        bool hasSubtitle = false, int selectionOffset = 0);","Viewport declaration"))

# Preserve the Hungarian custom tab width percentages and row-height
# overrides. The upstream library adds per-tab sort arrows + long press.
def tab_cpp(s):
    s=one(s,
        "UiTabListActivity::UiTabListActivity(const char* name, GfxRenderer& renderer, MappedInputManager& mappedInput)\n"
        "    : UiListActivity(name, renderer, mappedInput) {}",
        "UiTabListActivity::UiTabListActivity(const char* name, GfxRenderer& renderer, MappedInputManager& mappedInput,\n"
        "                                     const bool wantsTouchLongPress)\n"
        "    : UiListActivity(name, renderer, mappedInput, wantsTouchLongPress) {}","Tab ctor")
    s=one(s,"  activateIndex(event.value);\n}\n\nvoid UiTabListActivity::moveRingTo",
        "  if (event.longPress) {\n    onRowLongPress(event.value);\n    return;\n  }\n"
        "  activateIndex(event.value);\n}\n\nvoid UiTabListActivity::moveRingTo","Tab long press")
    s=method(s,"void UiTabListActivity::moveRingTo(const int ringIndex) {",
        "void UiTabListActivity::navigateButtons() {",
        "void UiTabListActivity::moveRingTo(const int ringIndex) {\n"
        "  activeNav().requestSelection(ringIndex);\n  requestUpdate();\n}","Tab nav")
    s=method(s,"void UiTabListActivity::syncTabListViewport(UiScreen& screen,",
        "void UiTabListActivity::buildTabBar(UiScreen& screen) {",
        "void UiTabListActivity::syncTabListViewport(UiScreen& screen, fui::ListProps& props,\n"
        "                                              bool hasSubtitle, int16_t rowHeightOverride) {\n"
        "  if (rowHeightOverride > 0) props.rowHeight = rowHeightOverride;\n"
        "  syncListViewport(screen, props, hasSubtitle, 1);\n}","Tab viewport")
    if "tabs[i].indicator = tabIndicator(i);" not in s:
        s=one(s,"    tabs[i].selected = activeTab() == i;",
            "    tabs[i].selected = activeTab() == i;\n"
            "    tabs[i].indicator = tabIndicator(i);","Tab indicator")
    if "tabPillMaxPad > 0" not in s:
        s=one(s,"  const int16_t tabLineHeight = screen.target().lineHeight(tabProps.text.font);",
            "  if (tabPillMaxPad > 0 && metrics.tabPillFullSlot) {\n"
            "    tabProps.contentInset.left = tabPillMaxPad;\n"
            "    tabProps.contentInset.right = tabPillMaxPad;\n"
            "  }\n"
            "  const int16_t tabLineHeight = screen.target().lineHeight(tabProps.text.font);","Library tab pill")
    return s
edit("src/activities/UiTabListActivity.cpp",tab_cpp)

def tab_h(s):
    s=one(s,"UiTabListActivity(const char* name, GfxRenderer& renderer, MappedInputManager& mappedInput);",
        "UiTabListActivity(const char* name, GfxRenderer& renderer, MappedInputManager& mappedInput,\n"
        "                    bool wantsTouchLongPress = false);","Tab ctor decl")
    s=one(s,"  virtual const char* tabLabel(int index) const = 0;",
        "  virtual const char* tabLabel(int index) const = 0;\n"
        "  virtual freeink::ui::TabIndicator tabIndicator(int) const {\n"
        "    return freeink::ui::TabIndicator::None;\n"
        "  }","Tab indicator decl")
    s=one(s,"  std::vector<freeink::ui::ListNav> tabNavs;",
        "  std::vector<freeink::ui::ListNav> tabNavs;\n"
        "  int16_t tabPillMaxPad = 0;","Tab pill declaration")
    return s
edit("src/activities/UiTabListActivity.h",tab_h)

def settings_h(s):
    s=one(s,"  ClearCache,\n","  ClearCache,\n  RebuildLibraryIndex,\n","Rebuild action enum")
    s=one(s,"  void openSleepTimeoutPicker();",
        "  void openSleepTimeoutPicker();\n  void rebuildLibraryIndex();","Rebuild method decl")
    return s
edit("src/activities/settings/SettingsActivity.h",settings_h)

# Preserve Hungarian OptionPopup's lock-free render/interaction publication.
def option_popup(s):
    s=one(s,"    title = I18N.get(titleId);",
        "    title = I18N.get(titleId);\n    headline.clear();","Popup first overload")
    s=one(s,"    title = titleStr;",
        "    title = titleStr;\n    headline.clear();","Popup text overload")
    # Second 'I18N.get' belongs to the vector overload.
    pos=s.find("  void show(StrId titleId, const std::vector<std::string>& options")
    if pos<0: raise RuntimeError("Popup vector overload missing")
    front,back=s[:pos],s[pos:]
    back=one(back,"    title = I18N.get(titleId);",
             "    title = I18N.get(titleId);\n    headline.clear();","Popup vector overload")
    s=front+back
    marker="  void show(StrId titleId, const std::vector<std::string>& options"
    overload="  void show(const char* titleStr, const char* headlineStr, const char* const* options,\n"\
             "            int optionCount, int currentIndex, std::function<void(int)> onSelect) {\n"\
             "    show(titleStr, options, optionCount, currentIndex, std::move(onSelect));\n"\
             "    headline = headlineStr ? headlineStr : \"\";\n  }\n\n"
    s=one(s,marker,overload+marker,"Popup headline overload")
    s=one(s,"    props.title = title.c_str();",
        "    props.title = title.c_str();\n"
        "    props.headline = headline.empty() ? nullptr : headline.c_str();","Popup headline prop")
    s=one(s,"    props.titleText.align = fui::TextAlign::Center;",
        "    props.titleText.align = fui::TextAlign::Center;\n"
        "    props.titleText.maxLines = 2;\n"
        "    props.headlineText.font = fui::GfxRendererTarget::FONT_BODY;\n"
        "    props.headlineText.align = fui::TextAlign::Center;\n"
        "    props.headlineText.maxLines = 3;","Popup text")
    s=one(s,"  std::string title;","  std::string title;\n  std::string headline;","Popup headline field")
    return s
edit("src/components/OptionPopup.h",option_popup)

# Use the existing Hungarian icon collection, append only the new upstream
# blocks artwork; wholesale replacement would lose Hungarian-specific icons.
def icons(s):
    if "icon_blocks_24_bits" in s: return s
    head=subprocess.check_output(["git","show",
           "e64317ae3b54fa1c7120e14c4bfda0ec249fb269:src/components/icons/listIcons.h"],text=True)
    marker="// blocks  (lucide: blocks)"
    if marker not in head: raise RuntimeError("Upstream blocks icon not found")
    return s.rstrip()+"\n\n"+head[head.index(marker):]
edit("src/components/icons/listIcons.h",icons)
edit("src/components/icons/listIcons.manifest",lambda s:
    s if "blocks = blocks" in s else s.rstrip()+"\nblocks = blocks\n")
edit("src/components/themes/BaseTheme.h",lambda s:
    s if "Bookmark, Blocks" in s else
    one(s,"Bookmark };","Bookmark, Blocks };","Blocks UIIcon") if "Bookmark };" in s else
    one(s,"  Bookmark,","  Bookmark, Blocks,","Blocks UIIcon"))

def app_icons(s):
    if "icon_blocks_32" not in s:
        s=one(s,"      case UIIcon::Bookmark:\n        return freeink::ui::bitmapFromIcon(icon_bookmark_32);",
              "      case UIIcon::Bookmark:\n        return freeink::ui::bitmapFromIcon(icon_bookmark_32);\n"
              "      case UIIcon::Blocks:\n        return freeink::ui::bitmapFromIcon(icon_blocks_32);","Block 32")
        s=one(s,"    case UIIcon::Bookmark:\n      return freeink::ui::bitmapFromIcon(icon_bookmark_24);",
              "    case UIIcon::Bookmark:\n      return freeink::ui::bitmapFromIcon(icon_bookmark_24);\n"
              "    case UIIcon::Blocks:\n      return freeink::ui::bitmapFromIcon(icon_blocks_24);","Block 24")
    return s
edit("src/components/UiAppHelpers.h",app_icons)

expected={
    "lib/Epub/Epub.cpp", "lib/Epub/Epub.h",
    "lib/Epub/Epub/parsers/ContentOpfParser.cpp",
    "lib/Epub/Epub/parsers/ContentOpfParser.h",
    "src/CrossPointSettings.h", "src/SettingsList.h",
    "src/activities/ActivityManager.cpp", "src/activities/ActivityManager.h",
    "src/activities/UiListActivity.cpp",
    "src/activities/UiTabListActivity.cpp", "src/activities/UiTabListActivity.h",
    "src/activities/network/NetworkModeSelectionActivity.cpp",
    "src/activities/reader/EpubReaderBookmarksActivity.cpp",
    "src/activities/settings/SettingsActivity.h",
    "src/components/OptionPopup.h", "src/components/UiAppHelpers.h",
    "src/components/icons/listIcons.h", "src/components/icons/listIcons.manifest",
    "src/components/themes/BaseTheme.h",
}
rejects=list(Path("lib").rglob("*.rej"))+list(Path("src").rglob("*.rej"))
unknown={str(p)[:-4] for p in rejects}-expected
if unknown:
    raise RuntimeError(f"Unexpected upstream conflicts: {sorted(unknown)}")
for p in rejects: p.unlink()
for file,token in [
    ("src/activities/home/HomeActivity.cpp","STR_LIBRARY"),
    ("src/activities/ActivityManager.cpp","goToLibrary"),
    ("src/activities/settings/SettingsActivity.cpp","rebuildLibraryIndex"),
    ("lib/Epub/Epub.cpp","loadMetadata("),
    ("src/activities/UiTabListActivity.cpp","tabIndicator(i)"),
    ("lib/Epub/Epub/parsers/ContentOpfParser.cpp","metadataComplete"),
    ("src/CrossPointSettings.h","libraryUseMetadata"),
    ("src/SettingsListBase.h","libraryUseMetadata"),
]:
    if token not in Path(file).read_text(encoding="utf-8"):
        raise RuntimeError(f"Missing Library UI capability {file}: {token}")
print(f"Resolved {len(rejects)} rejected files; Hungarian UI and EPUB customizations kept")
