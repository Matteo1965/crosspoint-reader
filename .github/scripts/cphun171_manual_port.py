#!/usr/bin/env python3
"""Manually port the CPHUN-171 Library UI changes that conflict with tested
Hungarian customizations. Called only after exact non-conflicting hunks have
been applied by cphun171_resolve_library_hunks.py.
Every replacement checks its anchor; do not quietly discard code.
"""
from pathlib import Path
import re

def load(p):
    return Path(p).read_text(encoding="utf-8")

def save(p,s):
    Path(p).write_text(s,encoding="utf-8")
    reject=Path(p+".rej")
    if reject.exists(): reject.unlink()
    print("CPHUN-171 manual port:",p)

def once(s,old,new,path):
    n=s.count(old)
    if n != 1:
        raise RuntimeError(f"{path}: expected one anchor, found {n}: {old[:100]!r}")
    return s.replace(old,new,1)

def method(s,start,end,replacement,path):
    a=s.find(start)
    if a<0: raise RuntimeError(f"{path}: no method {start}")
    b=s.find(end,a+len(start))
    if b<0: raise RuntimeError(f"{path}: no following method {end}")
    return s[:a]+replacement.rstrip()+"\n\n"+s[b:]

def port_all():
    # The Hungarian build wraps SettingsListBase.h, not the upstream SettingsList.h.
    p="src/SettingsListBase.h";s=load(p)
    needle='        SettingInfo::Toggle(StrId::STR_REMOVE_READ_FROM_RECENTS,'
    if "libraryUseMetadata" not in s:
        s=once(s,needle,'''        SettingInfo::Toggle(StrId::STR_LIBRARY_USE_METADATA, &CrossPointSettings::libraryUseMetadata,
                                "libraryUseMetadata", StrId::STR_CAT_SYSTEM),
    '''+needle,p)
        save(p,s)
    p="src/SettingsList.h"
    if Path(p+".rej").exists():
        if "getSettingsListBase" not in load(p): raise RuntimeError("Hungarian settings wrapper lost")
        Path(p+".rej").unlink()

    # New FreeInk ListNav must receive requests on the input task. Preserve the
    # Hungarian renderer's lock-free button reaction and dense row override.
    p="src/activities/UiListActivity.cpp";s=load(p)
    start="void UiListActivity::moveSelectionTo(const int index) {"
    end="void UiListActivity::loop() {"
    s=method(s,start,end,'''void UiListActivity::moveSelectionTo(const int index) {
      activeNav().requestSelection(index);
      requestUpdate();
    }''',p)
    save(p,s)

    # Keep the four-tab Hungarian tab widths and existing subtitle row overrides
    # while adopting the new SDK's renderer-owned scrolling/navigation state.
    p="src/activities/UiTabListActivity.cpp";s=load(p)
    s=method(s,"void UiTabListActivity::moveRingTo(const int ringIndex) {",
               "void UiTabListActivity::navigateButtons() {",'''void UiTabListActivity::moveRingTo(const int ringIndex) {
      activeNav().requestSelection(ringIndex);
      requestUpdate();
    }''',p)
    s=method(s,"void UiTabListActivity::syncTabListViewport(",
               "void UiTabListActivity::buildTabBar(",'''void UiTabListActivity::syncTabListViewport(UiScreen& screen, fui::ListProps& props,
                                                     const bool hasSubtitle, const int16_t rowHeightOverride) {
      if (rowHeightOverride > 0) {
        props.rowHeight = rowHeightOverride;
      } else if (!mappedInput.hasTouch()) {
        const auto& metrics = UITheme::getInstance().getMetrics();
        props.rowHeight =
            static_cast<int16_t>(hasSubtitle ? metrics.listWithSubtitleRowHeight : metrics.listRowHeight);
      }
      props.partialTrailingRow = true;
      screen.syncListViewport(activeNav(), props, listCount(), 1);
    }''',p)
    if "tabs[i].indicator = tabIndicator(i);" not in s:
        s=once(s,"    tabs[i].selected = activeTab() == i;",
                  "    tabs[i].selected = activeTab() == i;\n    tabs[i].indicator = tabIndicator(i);",p)
    # Width-limiting affects the new Library's tabs but does not replace the
    # already tested proportionally sized HU Settings and Text Settings tabs.
    if "if (tabPillMaxPad > 0)" not in s:
        anchor="  // Legacy Lyra two-state treatment:"
        s=once(s,anchor,'''  if (tabPillMaxPad > 0 && metrics.tabPillFullSlot) {
        tabProps.contentInset.left = tabPillMaxPad;
        tabProps.contentInset.right = tabPillMaxPad;
      }
    '''+anchor,p)
    save(p,s)

    p="src/activities/UiTabListActivity.h";s=load(p)
    if "tabPillMaxPad" not in s:
        s=once(s,"  std::vector<freeink::ui::ListNav> tabNavs;",
    '''  std::vector<freeink::ui::ListNav> tabNavs;
      // Optional tighter tab pills on the Library screen; other screens retain
      // their tested Hungarian proportional widths.
      int16_t tabPillMaxPad = 0;''',p)
    if "virtual freeink::ui::TabIndicator tabIndicator" not in s:
        s=once(s,"  virtual int tabWidthPercent(int index) const {",
    '''  virtual freeink::ui::TabIndicator tabIndicator(int) const {
        return freeink::ui::TabIndicator::None;
      }
      virtual int tabWidthPercent(int index) const {''',p)
    # Keep rowHeightOverride in the Hungarian interface: Text Settings uses it.
    if "int16_t rowHeightOverride = 0" not in s:
        raise RuntimeError("Hungarian Text Settings row-height contract is absent")
    save(p,s)

    # In the bookmark list an explicit subtitle height retains X4 density after
    # switching from the old ListNav API.
    p="src/activities/reader/EpubReaderBookmarksActivity.cpp";s=load(p)
    old="  syncListViewport(screen, props, /*hasSubtitle=*/true);"
    if old in s:
        s=once(s,old,'''  if (!mappedInput.hasTouch()) {
        props.rowHeight = static_cast<int16_t>(UITheme::getInstance().getMetrics().listWithSubtitleRowHeight);
      }
      syncListViewport(screen, props);''',p)
    save(p,s)

    # Extend the existing thread-safe popup, not the upstream older popup.
    p="src/components/OptionPopup.h";s=load(p)
    for needle in ("    title = I18N.get(titleId);", "    title = titleStr;"):
        occurrences=s.count(needle)
        if occurrences==0: raise RuntimeError(f"{p}: no title assignment {needle}")
        s=s.replace(needle+"\n    headline.clear();",needle+"\n")
        s=s.replace(needle,needle+"\n    headline.clear();")
    if 'void show(const char* titleStr, const char* headlineStr' not in s:
        mark="  void show(StrId titleId, const std::vector<std::string>& options,"
        addition='''  void show(const char* titleStr, const char* headlineStr, const char* const* options,
                int optionCount, int currentIndex, std::function<void(int)> onSelect) {
        show(titleStr, options, optionCount, currentIndex, std::move(onSelect));
        headline = headlineStr ? headlineStr : "";
      }

    '''
        s=once(s,mark,addition+mark,p)
    if "props.headline =" not in s:
        s=once(s,"    props.title = title.c_str();",
                  "    props.title = title.c_str();\n    props.headline = headline.empty() ? nullptr : headline.c_str();",p)
    if "  std::string headline;" not in s:
        s=once(s,"  std::string title;","  std::string title;\n  std::string headline;",p)
    save(p,s)

    # CPHUN's regenerated listIcons.h has a different set of icons than upstream.
    # Append ONLY the new blocks icon data from the upstream rejected hunk.
    p="src/components/icons/listIcons.h";s=load(p)
    if "static const freeink::Icon icon_blocks_32" not in s:
        reject=load(p+".rej")
        at=reject.find("+// blocks  (lucide: blocks)")
        if at<0: raise RuntimeError(f"{p}: no upstream blocks bitmaps in reject")
        section=reject[at:].splitlines()
        additions=[]
        for line in section:
            if line.startswith("+"): additions.append(line[1:])
            elif line.startswith("@@"): break
        payload="\n".join(additions).rstrip()+"\n"
        if "static const freeink::Icon icon_blocks_32" not in payload:
            raise RuntimeError(f"{p}: incomplete upstream blocks icon data")
        s=s.rstrip()+"\n\n"+payload
    save(p,s)

    p="src/components/icons/listIcons.manifest";s=load(p)
    if "blocks = blocks" not in s: s=s.rstrip()+"\nblocks = blocks\n"
    save(p,s)

    p="src/components/themes/BaseTheme.h";s=load(p)
    if "Blocks" not in s:
        s=once(s,"Hotspot, Bookmark };","Hotspot, Bookmark, Blocks };",p)
    save(p,s)

    # No UI patch may silently modify X4 hardware button wiring.
    for path in ("lib/hal/HalGPIO.cpp","lib/hal/HalGPIO.h","src/main.cpp"):
        if Path(path+".rej").exists(): raise RuntimeError(f"Unresolved hardware conflict: {path}")

    remaining=sorted(p for root in ("lib","src") for p in Path(root).rglob("*.rej"))
    if remaining:
        raise RuntimeError("Still rejected: "+", ".join(map(str,remaining)))
    print("CPHUN-171: all Library UI conflicts resolved while preserving HU settings/tab overrides")
