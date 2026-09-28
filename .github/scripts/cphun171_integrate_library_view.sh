#!/usr/bin/env bash
set -euo pipefail
# CPHUN-171: integrate the UI portion of upstream PR #3366 on top of the
# tested CPHUN-169 generated sources (not the older repository snapshot).
# The full new LibraryListActivity and blocks icon live in this branch.
UPSTREAM=https://github.com/crosspoint-reader/crosspoint-reader.git
BASE=123f3760e8f4c9d3977df3430bd5102db927ebec
HEAD=e64317ae3b54fa1c7120e14c4bfda0ec249fb269
git -c fetch.recurseSubmodules=false fetch --no-recurse-submodules --no-tags "$UPSTREAM" "$BASE" "$HEAD"
# The CPHUN-169 build regenerates tracked files in the worktree. A three-way
# apply needs its index to reflect that exact regenerated state.
git add -u
paths=(
 lib/Epub/Epub.cpp lib/Epub/Epub.h
 lib/Epub/Epub/parsers/ContentOpfParser.cpp lib/Epub/Epub/parsers/ContentOpfParser.h
 lib/GfxRenderer/GfxRenderer.cpp lib/GfxRenderer/GfxRenderer.h
 lib/hal/HalStorage.cpp lib/hal/HalStorage.h
 src/CrossPointSettings.h src/RecentBooksStore.h src/SdCardFontSystem.cpp src/SdCardFontSystem.h src/SettingsList.h
 src/activities/ActivityManager.cpp src/activities/ActivityManager.h
 src/activities/UiListActivity.cpp src/activities/UiListActivity.h
 src/activities/UiTabListActivity.cpp src/activities/UiTabListActivity.h
 src/activities/browser/OpdsBookBrowserActivity.cpp
 src/activities/home/FileBrowserActivity.cpp
 src/activities/home/HomeActivity.cpp src/activities/home/HomeActivity.h
 src/activities/network/NetworkModeSelectionActivity.cpp src/activities/network/WifiSelectionActivity.cpp
 src/activities/reader/EndOfBookOptions.cpp src/activities/reader/EpubReaderBookmarksActivity.cpp
 src/activities/settings/ButtonRemapActivity.cpp src/activities/settings/FontDownloadActivity.cpp
 src/activities/settings/OpdsServerListActivity.cpp src/activities/settings/SettingsActivity.cpp
 src/activities/settings/SettingsActivity.h
 src/activities/util/ConfirmationActivity.cpp src/activities/util/ConfirmationActivity.h
 src/components/OptionPopup.h src/components/UIThemeTokens.h src/components/UiAppHelpers.h
 src/components/icons/listIcons.h src/components/icons/listIcons.manifest
 src/components/themes/BaseTheme.h src/components/themes/lyra/LyraTheme.cpp src/components/themes/lyra/LyraTheme.h
)
# Per-file application identifies the exact incompatibility if a Hungarian
# customization needs a manual port; it never silently discards a failed hunk.
conflicts=0
for file in "${paths[@]}"; do
  echo "::group::Library View upstream merge: $file"
  git diff --binary "$BASE" "$HEAD" -- "$file" >/tmp/library-one.patch
  if test -s /tmp/library-one.patch; then
    if ! git apply --reject --whitespace=nowarn /tmp/library-one.patch; then
      echo "Expected CPHUN merge overlap: $file (collecting rejects for resolver)"
      conflicts=$((conflicts + 1))
    fi
  fi
  echo "::endgroup::"
done
if (( conflicts > 0 )); then
  echo "Resolving $conflicts incompatible source files using uniquely anchored, non-destructive edits"
  python3 .github/scripts/cphun171_resolve_library_hunks.py
  if find lib src -name '*.rej' | grep -q .; then
    echo "::error::Manual merge required for remaining upstream Library View hunks"
    exit 1
  fi
fi
# PR #3366 depends on FreeInk UI's newer list navigation, tab indicators,
# touch long-press and GfxRendererTarget constructor.
git -C freeink-sdk fetch --no-tags origin f4e2469415044bf766faeca06075f95aecd532f6
git -C freeink-sdk checkout --detach f4e2469415044bf766faeca06075f95aecd532f6

# Existing CPHUN-170 translations were restored after regeneration.
grep -q 'goToLibrary' src/activities/ActivityManager.cpp
grep -q 'LibraryListActivity' src/activities/ActivityManager.cpp
grep -q 'STR_LIBRARY' src/activities/home/HomeActivity.cpp
grep -q 'RebuildLibraryIndex' src/activities/settings/SettingsActivity.cpp
grep -q 'libraryUseMetadata' src/CrossPointSettings.h
test -f src/activities/library/LibraryListActivity.cpp
git diff --check
echo "CPHUN-171 upstream Library View integrated into generated source"
