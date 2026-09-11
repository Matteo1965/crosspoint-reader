from pathlib import Path
import re

p = Path('src/activities/reader/BookInfoActivity.cpp')
s = p.read_text(encoding='utf-8')

assert 'constexpr int METADATA_VALUE_X = 184;' in s
s = s.replace('constexpr int METADATA_VALUE_X = 184;', 'constexpr int METADATA_VALUE_X = 182;')

anchor = '''std::string fileFormat(const std::string& filename) {
'''
helpers = r'''std::string hungarianLowerCopy(const std::string& value) {
  std::string out;
  out.reserve(value.size());
  for (size_t i = 0; i < value.size();) {
    const unsigned char c = static_cast<unsigned char>(value[i]);
    if (c < 0x80) {
      out.push_back(static_cast<char>(std::tolower(c)));
      ++i;
      continue;
    }
    if (i + 1 < value.size()) {
      const unsigned char c2 = static_cast<unsigned char>(value[i + 1]);
      if (c == 0xC3) {
        const unsigned char lower =
            c2 == 0x81 ? 0xA1 : c2 == 0x89 ? 0xA9 : c2 == 0x8D ? 0xAD : c2 == 0x93 ? 0xB3 :
            c2 == 0x96 ? 0xB6 : c2 == 0x9A ? 0xBA : c2 == 0x9C ? 0xBC : c2;
        out.push_back(static_cast<char>(c));
        out.push_back(static_cast<char>(lower));
        i += 2;
        continue;
      }
      if (c == 0xC5 && (c2 == 0x90 || c2 == 0xB0)) {
        out.push_back(static_cast<char>(c));
        out.push_back(static_cast<char>(c2 + 1));
        i += 2;
        continue;
      }
    }
    out.push_back(value[i++]);
  }
  return out;
}

bool isWarningSeparator(const char c) {
  return std::isspace(static_cast<unsigned char>(c)) != 0 || c == ',' || c == '.' || c == '!' || c == ':';
}

std::string removeDescriptionWarning(std::string value) {
  const std::string lowered = hungarianLowerCopy(value);
  const std::string first = "vigyázat";
  const std::string second = "cselekményleírást";
  const std::string third = "tartalmaz";
  size_t search = 0;
  while (search < value.size()) {
    const size_t a = lowered.find(first, search);
    if (a == std::string::npos) break;
    size_t p = a + first.size();
    while (p < lowered.size() && isWarningSeparator(lowered[p])) ++p;
    if (lowered.compare(p, second.size(), second) != 0) { search = a + first.size(); continue; }
    p += second.size();
    while (p < lowered.size() && isWarningSeparator(lowered[p])) ++p;
    if (lowered.compare(p, third.size(), third) != 0) { search = a + first.size(); continue; }
    p += third.size();
    while (p < lowered.size() && isWarningSeparator(lowered[p])) ++p;
    value.erase(a, p - a);
    return trimCopy(value);
  }
  return trimCopy(value);
}

std::string filenameWithoutExtension(const std::string& filename) {
  const size_t slash = filename.find_last_of("/\\");
  const size_t baseStart = slash == std::string::npos ? 0 : slash + 1;
  const size_t dot = filename.find_last_of('.');
  if (dot == std::string::npos || dot <= baseStart) return filename.substr(baseStart);
  return filename.substr(baseStart, dot - baseStart);
}

'''
assert anchor in s
s = s.replace(anchor, helpers + anchor, 1)

old_join = r'''std::string joinTags(const std::vector<std::string>& values) {
  std::string out;
  for (const auto& raw : values) {
    const std::string value = trimCopy(raw);
    if (value.empty()) continue;
    if (!out.empty()) out += ", ";
    out += value;
  }
  return out;
}
'''
new_join = r'''std::string joinTags(const std::vector<std::string>& values) {
  std::string out;
  for (const auto& raw : values) {
    std::string value = raw;
    for (char& c : value) {
      if (c == '(' || c == ')' || c == '{' || c == '}' || c == '[' || c == ']') c = ' ';
    }
    std::string lowered = hungarianLowerCopy(value);
    for (const std::string phrase : {std::string("magyar nyelvű"), std::string("magyar nyelv")}) {
      size_t pos = 0;
      while ((pos = lowered.find(phrase, pos)) != std::string::npos) {
        value.erase(pos, phrase.size());
        lowered.erase(pos, phrase.size());
      }
    }
    value = trimCopy(value);
    std::string clean;
    bool pendingSpace = false;
    for (char c : value) {
      if (std::isspace(static_cast<unsigned char>(c))) { pendingSpace = !clean.empty(); continue; }
      if (c == ',') {
        while (!clean.empty() && clean.back() == ' ') clean.pop_back();
        if (!clean.empty() && clean.back() != ',') clean.push_back(',');
        pendingSpace = true;
        continue;
      }
      if (pendingSpace && !clean.empty() && clean.back() != ',') clean.push_back(' ');
      if (pendingSpace && !clean.empty() && clean.back() == ',') clean.push_back(' ');
      pendingSpace = false;
      clean.push_back(c);
    }
    clean = trimCopy(clean);
    while (!clean.empty() && clean.back() == ',') clean.pop_back();
    clean = trimCopy(clean);
    if (clean.empty()) continue;
    if (!out.empty()) out += ", ";
    out += clean;
  }
  return out;
}
'''
assert old_join in s
s = s.replace(old_join, new_join, 1)

old_desc = '''    const auto paragraphs = parseDescriptionFragment(info_.description);
    if (paragraphs.empty()) {
      text_ = "Ehhez a könyvhöz nincs fülszöveg.";
      return;
    }
    for (size_t i = 0; i < paragraphs.size(); ++i) {
      if (i > 0) text_ += "\\n\\n";
      text_ += paragraphs[i];
    }
    return;
'''
new_desc = '''    const auto paragraphs = parseDescriptionFragment(info_.description);
    for (const auto& paragraph : paragraphs) {
      const std::string cleaned = removeDescriptionWarning(paragraph);
      if (cleaned.empty()) continue;
      if (!text_.empty()) text_ += "\\n\\n";
      text_ += cleaned;
    }
    if (text_.empty()) text_ = "Ehhez a könyvhöz nincs fülszöveg.";
    return;
'''
assert old_desc in s
s = s.replace(old_desc, new_desc, 1)
s = s.replace('add("Sorozatszám:", info_.seriesIndex);', 'add("Sorozat #:", info_.seriesIndex);')
s = s.replace('add("Fájlnév:", info_.filename);', 'add("Fájlnév:", filenameWithoutExtension(info_.filename));')
s = s.replace('const int availableHeight = renderer.getScreenHeight() - topArea - bottomArea;',
              'const int availableHeight = renderer.getScreenHeight() - topArea - bottomArea + (page_ == Page::Metadata ? 2 : 0);')
s = s.replace('(addFieldGap ? 6 : 0)', '(addFieldGap ? 3 : 0)')
s = s.replace('EpdFontFamily::BOLD);', 'EpdFontFamily::REGULAR);')
s = s.replace('y += 6;', 'y += 3;')
s = s.replace('const int bodyY = contentY + metrics.topPadding + metrics.headerHeight + metrics.verticalSpacing;',
              'const int bodyY = contentY + metrics.topPadding + metrics.headerHeight + metrics.verticalSpacing -\n                    (page_ == Page::Metadata ? 2 : 0);')

assert 'METADATA_VALUE_X = 182' in s
assert 'Sorozat #:' in s
assert 'filenameWithoutExtension(info_.filename)' in s
assert 'EpdFontFamily::BOLD' not in s
assert 'y += 6' not in s
p.write_text(s, encoding='utf-8')

# Build ID
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b = re.sub(r'CPHUN-\d{6}-\d+', 'CPHUN-260912-101', b)
bid.write_text(b, encoding='utf-8')

# Exact bitmap generated from the user-approved Dogear_X_24x24.png (black=1, MSB first).
icon = Path('src/components/icons/bookmark.h')
i = icon.read_text(encoding='utf-8')
values = [
0x00,0x00,0x00,0x80,0x00,0x00,0xC0,0x00,0x00,0xE0,0x00,0x00,
0xB0,0x00,0x00,0xD8,0x00,0x00,0xAC,0x00,0x00,0xD6,0x00,0x00,
0xAB,0x00,0x00,0xD5,0x80,0x00,0xAA,0xC0,0x00,0xD5,0x60,0x00,
0xAA,0xB0,0x00,0xD5,0x58,0x00,0xAA,0xAC,0x00,0xD5,0x56,0x00,
0xAA,0xAB,0x00,0xD5,0x55,0x80,0xAA,0xAA,0xC0,0xD5,0x55,0x60,
0xAA,0xAA,0xB0,0xD5,0x55,0x58,0xAA,0xAA,0xAC,0xFF,0xFF,0xFE]
body = '\n'.join('    ' + ', '.join(f'0x{v:02X}' for v in values[n:n+9]) + (',' if n+9 < len(values) else '') for n in range(0,len(values),9))
i, count = re.subn(r'(static const uint8_t BookmarkStatusIcon\[\] = \{).*?(\};)', r'\1\n' + body + r'\2', i, count=1, flags=re.S)
assert count == 1
icon.write_text(i, encoding='utf-8')
