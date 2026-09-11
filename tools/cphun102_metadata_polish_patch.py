from pathlib import Path

book = Path('src/activities/reader/BookInfoActivity.cpp')
s = book.read_text(encoding='utf-8')

def replace_once(old, new):
    global s
    assert s.count(old) == 1, (old, s.count(old))
    s = s.replace(old, new, 1)

# Finalized CPHUN-102 metadata changes.
replace_once('add("Sorozat #:", info_.seriesIndex);', 'add("Sorszám:", info_.seriesIndex);')
replace_once('  add("Kiadó:", info_.publisher);\n  add("Dátum:", dateOnly(info_.date));', '''  const std::string publisher = trimCopy(info_.publisher);
  const std::string publisherLower = hungarianLowerCopy(publisher);
  if (!publisher.empty() && publisherLower != "ismeretlen" && publisherLower != "nincs" &&
      publisherLower != "nincs megadva" && publisher != "+" && publisher != "-" && publisherLower != "untitled") {
    add("Kiadó:", publisher);
  }
  const std::string displayDate = dateOnly(info_.date);
  bool showDate = false;
  if (displayDate.size() >= 4 && std::isdigit(static_cast<unsigned char>(displayDate[0])) &&
      std::isdigit(static_cast<unsigned char>(displayDate[1])) &&
      std::isdigit(static_cast<unsigned char>(displayDate[2])) &&
      std::isdigit(static_cast<unsigned char>(displayDate[3]))) {
    const int year = (displayDate[0] - '0') * 1000 + (displayDate[1] - '0') * 100 +
                     (displayDate[2] - '0') * 10 + (displayDate[3] - '0');
    showDate = year >= 1800;
  }
  if (showDate) add("Dátum:", displayDate);''')

# CPHUN-101 already uses +3 px; CPHUN-102 changes this to +2 px.
count_gap = s.count('(addFieldGap ? 3 : 0)')
assert count_gap == 2, count_gap
s = s.replace('(addFieldGap ? 3 : 0)', '(addFieldGap ? 2 : 0)')
count_y = s.count('line.metadataFieldEnd && i + 1 < static_cast<int>(lines_.size())) y += 3;')
assert count_y == 3, count_y
s = s.replace('line.metadataFieldEnd && i + 1 < static_cast<int>(lines_.size())) y += 3;',
              'line.metadataFieldEnd && i + 1 < static_cast<int>(lines_.size())) y += 2;')
book.write_text(s, encoding='utf-8')

base = Path('src/components/themes/BaseTheme.cpp')
b = base.read_text(encoding='utf-8')
old = 'drawBookmarkStatusIcon(renderer, renderer.getScreenWidth() - bookmarkStatusIconWidth, 0);'
new = 'drawBookmarkStatusIcon(renderer, renderer.getScreenWidth() - bookmarkStatusIconWidth, 2);'
assert b.count(old) == 1, b.count(old)
base.write_text(b.replace(old, new, 1), encoding='utf-8')

bid = Path('src/CPHUNBuildId.h')
i = bid.read_text(encoding='utf-8')
assert 'CPHUN-260912-101' in i
i = i.replace('CPHUN-260912-101', 'CPHUN-260912-102')
bid.write_text(i, encoding='utf-8')
