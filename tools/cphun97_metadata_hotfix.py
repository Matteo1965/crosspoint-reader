from pathlib import Path

path = Path("src/activities/reader/BookInfoActivity.cpp")
text = path.read_text()
old = '''          while (!out.empty() && out.back() == ' ') out.pop_back();
          if (out.empty()) break;
          do {
            out.pop_back();
          } while (!out.empty() && (static_cast<unsigned char>(out.back()) & 0xC0) == 0x80);
'''
new = '''          while (!out.empty() && out.back() == ' ') out.pop_back();
          if (out.empty()) break;
          size_t cut = out.size() - 1;
          while (cut > 0 && (static_cast<unsigned char>(out[cut]) & 0xC0) == 0x80) --cut;
          out.resize(cut);
'''
count = text.count(old)
if count != 1:
    raise SystemExit(f"Expected one UTF-8 trim block, found {count}")
path.write_text(text.replace(old, new, 1))
print("CPHUN-97 metadata UTF-8 truncation is codepoint-safe.")
