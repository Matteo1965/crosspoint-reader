#!/usr/bin/env bash
set -euo pipefail

# CPHUN-172: bring the Library View from the PR #3366 baseline up to the
# functional state shipped in CrossPoint 1.6.5, while keeping CPHUN-specific
# reader/typography code untouched.
UPSTREAM=https://github.com/crosspoint-reader/crosspoint-reader.git
RELEASE=93e98bb78702e29868a16a13b80c40e6b36ccdff

# Post-#3366 Library commits included in 1.6.5.
commits=(
  bac8f73c222481bac5702717c978f9e75be3ec60
  6c83eddbf3feeb375cef20fe702f7c99e5d38703
  10d0aa1ecd4e891de48860c855c7f90c736fe64e
  4a6283db9c9692e059eaf2d57d5b7a36d85a2f4d
)

git -c fetch.recurseSubmodules=false fetch --no-recurse-submodules --no-tags "$UPSTREAM" "$RELEASE" "${commits[@]}"

apply_commit_paths() {
  local commit="$1"; shift
  local parent="${commit}^"
  local file patch failed=0
  for file in "$@"; do
    echo "::group::CPHUN-172 release sync: $commit $file"
    git diff --binary "$parent" "$commit" -- "$file" >/tmp/cphun172-one.patch
    if test -s /tmp/cphun172-one.patch; then
      if ! git apply --reject --whitespace=nowarn /tmp/cphun172-one.patch; then
        echo "::notice file=$file::Release Library hunk needs CPHUN resolver"
        failed=1
      fi
    fi
    echo "::endgroup::"
  done
  return "$failed"
}

# Back navigation from collapsed groups must expand before focus returns to tabs.
apply_commit_paths "${commits[0]}" src/activities/library/LibraryListActivity.cpp || true

# X4 button navigation wraps inside the list instead of forcing a trip through tabs.
apply_commit_paths "${commits[1]}" src/activities/library/LibraryListActivity.cpp || true

# Library-local refresh, Recent-row options and stale-index tracking.
apply_commit_paths "${commits[2]}"   lib/I18n/translations/english.yaml   lib/LibraryIndex/LibraryBuilder.cpp lib/LibraryIndex/LibraryBuilder.h   src/activities/browser/OpdsBookBrowserActivity.cpp   src/activities/library/LibraryListActivity.cpp src/activities/library/LibraryListActivity.h   src/activities/settings/SettingsActivity.cpp src/activities/settings/SettingsActivity.h   src/components/icons/listIcons.h src/components/icons/listIcons.manifest   src/network/CrossPointWebServer.cpp || true

# Final 1.6.5 sort/search semantics: leading title words/articles are preserved.
apply_commit_paths "${commits[3]}"   lib/LibraryIndex/LibraryBuilder.cpp lib/LibraryIndex/LibraryFormat.h   lib/LibraryIndex/LibraryText.cpp lib/LibraryIndex/LibraryText.h   src/activities/library/LibraryListActivity.cpp   test/library_text/LibraryTextTest.cpp || true

# Resolve the few predictable collisions caused by CPHUN long-press/UI changes.
python3 .github/scripts/cphun172_release_library_sync.py

if find lib src test -name '*.rej' | grep -q .; then
  echo "::error::Unresolved CPHUN-172 Library release hunks remain"
  find lib src test -name '*.rej' -print
  exit 1
fi

# PR #3608 needs the SDK revision that added the adjacent header action support.
git -C freeink-sdk fetch --no-tags origin 13418e0986b05039bf056e050a6df5305d47c209
git -C freeink-sdk checkout --detach 13418e0986b05039bf056e050a6df5305d47c209

# Hungarian labels absent from upstream's HU catalogue at the time of the PR.
python3 - <<'PY'
from pathlib import Path
p=Path('lib/I18n/translations/hungarian.yaml')
s=p.read_text(encoding='utf-8')
updates={
 'STR_LIBRARY_HOLD_OPTIONS':'Hosszan: Műveletek',
 'STR_LIBRARY_REBUILD':'Könyvtár frissítése',
 'STR_REMOVE_FROM_RECENTS':'Eltávolítás a legutóbbiak közül',
}
lines=s.splitlines()
for key,val in updates.items():
    found=False
    for i,line in enumerate(lines):
        if line.startswith(key+':'):
            lines[i]=f'{key}: "{val}"'; found=True; break
    if not found:
        lines.append(f'{key}: "{val}"')
p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
PY

# Release-level invariants.
grep -Fq 'CLIX_FOLD_VERSION = 4' lib/LibraryIndex/LibraryFormat.h
grep -Fq 'showRecentBookOptions' src/activities/library/LibraryListActivity.cpp
grep -Fq 'promptRebuildIndex' src/activities/library/LibraryListActivity.cpp
grep -Fq 'isLibraryIndexDirty' src/activities/library/LibraryListActivity.cpp
grep -Fq 'markLibraryIndexDirty' lib/LibraryIndex/LibraryBuilder.cpp
grep -Fq 'STR_LIBRARY_HOLD_OPTIONS' lib/I18n/translations/hungarian.yaml
! grep -Fq 'stripArticle' lib/LibraryIndex/LibraryText.h
git diff --check

echo "CPHUN-172 Library View synchronized with final 1.6.5 functional changes for X4"
