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
