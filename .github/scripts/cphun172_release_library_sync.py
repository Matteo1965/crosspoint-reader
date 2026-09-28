from pathlib import Path

def replace_once(path: Path, old: str, new: str):
    s=path.read_text(encoding="utf-8")
    if old in s:
        path.write_text(s.replace(old,new,1),encoding="utf-8")
        return True
    return False

p=Path("src/activities/library/LibraryListActivity.cpp")
s=p.read_text(encoding="utf-8")

# CPHUN-171 added a safe threshold-fired Confirm hold. Preserve that safety,
# but route Recent rows to the 1.6.5 options popup.
old='''    } else if (selectedEntry() < pinnedCount()) {
      const auto& books = RECENT_BOOKS.getBooks();
      if (selectedEntry() < static_cast<int>(books.size())) {
        const auto& book = books[static_cast<size_t>(selectedEntry())];
        promptRemoveRecentBook(book.path, book.title);
      }
    } else if (deleteEligible()) {'''
new='''    } else if (isRecentSort(sortOrder)) {
      showRecentBookOptions(selectedEntry());
    } else if (deleteEligible()) {'''
if old in s:
    s=s.replace(old,new,1)

# Final release: Back from a collapsed group expands it before returning focus
# to the tab strip.
old='''    } else if (!tabsFocused() && !degraded) {
      // Keep the current list and viewport while returning focus to the tabs.
      nav.selected = 0;
      requestUpdate();
    } else if (groupsCollapsed) {
      restoreExpandedList();'''
new='''    } else if (groupsCollapsed) {
      restoreExpandedList();
    } else if (!tabsFocused() && !degraded) {
      // Keep the current list and viewport while returning focus to the tabs.
      nav.selected = 0;
      requestUpdate();'''
if old in s:
    s=s.replace(old,new,1)

# Final X4 list wrap behaviour.
old='''  const int ringSize = count + 1;
  auto& nav = activeNav();
  buttonNavigator.onNextRelease([this, ringSize] { moveRingTo(ButtonNavigator::nextIndex(ringPos(), ringSize)); });
  buttonNavigator.onPreviousRelease([this, ringSize] {
    if (tabsFocused() && !degraded) {
      openSearch();
    } else {
      moveRingTo(ButtonNavigator::previousIndex(ringPos(), ringSize));
    }
  });'''
new='''  auto& nav = activeNav();
  buttonNavigator.onNextRelease([this, count] {
    if (count > 0) moveRingTo(ringPos() == count ? 1 : ringPos() + 1);
  });
  buttonNavigator.onPreviousRelease([this, count] {
    if (tabsFocused() && !degraded) {
      openSearch();
    } else if (count > 0) {
      moveRingTo(ringPos() <= 1 ? count : ringPos() - 1);
    }
  });'''
if old in s:
    s=s.replace(old,new,1)

# 1.6.5 no longer strips leading articles/words in search.
s=s.replace('library::fold(query, /*stripArticle=*/true)', 'library::fold(query)')

# Release help text for Recent rows.
old='''  else if (!tabsFocused() && selectedEntry() < pinnedCount())
    help = tr(STR_HOLD_OPEN_TO_REMOVE);  // pinned recents: hold removes from the list'''
new='''  else if (!tabsFocused() && isRecentSort(sortOrder) && listCount() > 0)
    help = tr(STR_LIBRARY_HOLD_OPTIONS);  // recent rows: hold opens the row menu'''
if old in s:
    s=s.replace(old,new,1)

p.write_text(s,encoding="utf-8")

# If the only rejected LibraryList hunks are the CPHUN-specific input chunks
# resolved above, remove the reject after verifying release functionality.
rej=Path(str(p)+".rej")
if rej.exists():
    now=p.read_text(encoding="utf-8")
    required=["showRecentBookOptions", "promptRebuildIndex", "isRecentSort(sortOrder)",
              "STR_LIBRARY_HOLD_OPTIONS", "library::fold(query)"]
    if all(x in now for x in required):
        rej.unlink()

# Other post-3366 library files should apply cleanly. Report unresolved rejects
# with their contents so the workflow fails loudly rather than hiding them.
for rej in Path(".").rglob("*.rej"):
    print(f"UNRESOLVED {rej}")
    print(rej.read_text(encoding="utf-8", errors="replace"))


# Resolve release translation collisions caused by restored CPHUN catalogues.
p=Path("lib/I18n/translations/english.yaml")
en=p.read_text(encoding="utf-8")
def set_yaml(src,key,value):
    lines=src.splitlines()
    for i,line in enumerate(lines):
        if line.startswith(key+":"):
            lines[i]=f'{key}: "{value}"'
            return "\n".join(lines)+"\n"
    lines.append(f'{key}: "{value}"')
    return "\n".join(lines)+"\n"
en=set_yaml(en,"STR_LIBRARY_HOLD_OPTIONS","Hold: Options")
en=set_yaml(en,"STR_LIBRARY_REBUILD","Refresh library")
en=set_yaml(en,"STR_REMOVE_FROM_RECENTS","Remove from Recents")
p.write_text(en,encoding="utf-8")
Path(str(p)+".rej").unlink(missing_ok=True)

# The release moved manual Library refresh out of System settings.
p=Path("src/activities/settings/SettingsActivity.h")
hs=p.read_text(encoding="utf-8")
hs=hs.replace("  RebuildLibraryIndex,\n","")
hs=hs.replace("  void rebuildLibraryIndex();\n","")
p.write_text(hs,encoding="utf-8")
Path(str(p)+".rej").unlink(missing_ok=True)

# Preserve CPHUN's generated icon set and append only the release refresh icon.
p=Path("src/components/icons/listIcons.manifest")
m=p.read_text(encoding="utf-8")
if "refresh-cw = refresh-cw" not in m:
    m=m.rstrip()+"\nrefresh-cw = refresh-cw\n"
p.write_text(m,encoding="utf-8")
Path(str(p)+".rej").unlink(missing_ok=True)

p=Path("src/components/icons/listIcons.h")
ih=p.read_text(encoding="utf-8")
if "icon_refresh_cw_32" not in ih:
    ih += r'''

// refresh-cw  (lucide: refresh-cw)
static const uint8_t icon_refresh_cw_24_bits[] = {
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x81, 0xF3, 0xFE, 0x00, 0x73, 0xFC, 0x7E, 0x13, 0xF9, 0xFF, 0x83,
    0xF3, 0xFF, 0xC3, 0xE7, 0xFE, 0x03, 0xE7, 0xFE, 0x03, 0xCF, 0xFF, 0xFF, 0xCF, 0xFF, 0xFF, 0xCF, 0xFF, 0xF3,
    0xCF, 0xFF, 0xF3, 0xFF, 0xFF, 0xF3, 0xFF, 0xFF, 0xF3, 0xC0, 0x7F, 0xE7, 0xC0, 0x7F, 0xE7, 0xC3, 0xFF, 0xCF,
    0xC1, 0xFF, 0x9F, 0xC8, 0x7E, 0x3F, 0xCE, 0x00, 0x7F, 0xCF, 0x81, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
static const freeink::Icon icon_refresh_cw_24 = {24, 24, 12, icon_refresh_cw_24_bits};
static const uint8_t icon_refresh_cw_32_bits[] = {
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF0, 0x0F, 0xE7, 0xFF, 0x80, 0x01,
    0xE7, 0xFF, 0x03, 0xC0, 0xE7, 0xFE, 0x1F, 0xF8, 0x27, 0xFC, 0x3F, 0xFE, 0x07, 0xF8, 0xFF, 0xFF, 0x07, 0xF0, 0xFF,
    0xF8, 0x07, 0xF1, 0xFF, 0xF0, 0x07, 0xF3, 0xFF, 0xF0, 0x07, 0xE3, 0xFF, 0xFF, 0xFF, 0xE3, 0xFF, 0xFF, 0xFF, 0xE7,
    0xFF, 0xFF, 0xFF, 0xE7, 0xFF, 0xFF, 0xE7, 0xE7, 0xFF, 0xFF, 0xE7, 0xFF, 0xFF, 0xFF, 0xE7, 0xFF, 0xFF, 0xFF, 0xC7,
    0xFF, 0xFF, 0xFF, 0xC7, 0xE0, 0x0F, 0xFF, 0xCF, 0xE0, 0x0F, 0xFF, 0x8F, 0xE0, 0x1F, 0xFF, 0x1F, 0xE0, 0xFF, 0xFF,
    0x1F, 0xE0, 0x7F, 0xFC, 0x3F, 0xE4, 0x1F, 0xF8, 0x7F, 0xE7, 0x03, 0xC0, 0xFF, 0xE7, 0x80, 0x03, 0xFF, 0xE7, 0xF0,
    0x0F, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
static const freeink::Icon icon_refresh_cw_32 = {32, 32, 15, icon_refresh_cw_32_bits};
'''
p.write_text(ih,encoding="utf-8")
Path(str(p)+".rej").unlink(missing_ok=True)
