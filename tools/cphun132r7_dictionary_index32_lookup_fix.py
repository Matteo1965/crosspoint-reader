from pathlib import Path
import re


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-132r7: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def regex_replace_once(path, pattern, replacement):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    text2, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"CPHUN-132r7: {path}: regex expected one match, found {count}: {pattern[:180]!r}")
    p.write_text(text2, encoding="utf-8")


# 1) Dense sampled dictionary sidecar: 256 -> 32 entries.
replace_once(
    "src/util/Dictionary.h",
    "  static constexpr uint32_t SAMPLE_INTERVAL = 256;",
    "  static constexpr uint32_t SAMPLE_INTERVAL = 32;",
)

# Guard expiry is a bounded miss, not an SD read error.
replace_once(
    "src/util/Dictionary.cpp",
    '''    if (++locateProbes > SAMPLE_INTERVAL + 8 || millis() - locateStart > 1500) {
      result.readError = true;
      break;
    }''',
    '''    if (++locateProbes > SAMPLE_INTERVAL + 8 || millis() - locateStart > 1500) {
      LOG_ERR("DICT", "Index lookup guard reached for %s", target);
      break;
    }''',
)
replace_once(
    "src/util/Dictionary.cpp",
    '''    if (++synonymProbes > SAMPLE_INTERVAL + 8 || millis() - synonymStart > 1500) {
      result.readError = true;
      break;
    }''',
    '''    if (++synonymProbes > SAMPLE_INTERVAL + 8 || millis() - synonymStart > 1500) {
      LOG_ERR("DICT", "Synonym lookup guard reached for %s", target);
      break;
    }''',
)

# 2) Bound overlong/corrupt headword tail draining.
replace_once(
    "src/util/Dictionary.cpp",
    '''  // Word too long for buffer — consume remaining bytes to stay in sync
  buf[bufSize - 1] = '\\0';
  int ch;
  do {
    ch = file.read();
  } while (ch > 0);
  return static_cast<int>(bufSize - 1);''',
    '''  // Word too long for buffer. Never drain an untrusted/corrupt entry
  // without a bound: the old do/while could keep the lookup inside one entry
  // so the outer millis() guard was never reached.
  buf[bufSize - 1] = '\\0';
  constexpr size_t MAX_OVERLONG_TAIL_BYTES = 512;
  for (size_t drained = 0; drained < MAX_OVERLONG_TAIL_BYTES; ++drained) {
    const int ch = file.read();
    if (ch == 0) return static_cast<int>(bufSize - 1);
    if (ch < 0) return -1;
  }
  LOG_ERR("DICT", "Overlong/corrupt dictionary headword");
  return -1;''',
)

# 3) Remove the immediate full-lookup retry after ReadError. Match whitespace
# robustly because the workflow's compatibility heredoc may indent this block.
retry_pattern = (
    r'^\s*bool found = ok && dict\.lookup\(lookupWord\.c_str\(\), definition, headword, &result\);\n'
    r'\s*if \(!found && ok && result == Dictionary::LookupResult::ReadError\) \{\n'
    r'\s*vTaskDelay\(1\);\n'
    r'\s*definition\.clear\(\);\n'
    r'\s*headword\.clear\(\);\n'
    r'\s*result = Dictionary::LookupResult::NotFound;\n'
    r'\s*found = dict\.lookup\(lookupWord\.c_str\(\), definition, headword, &result\);\n'
    r'\s*\}'
)
regex_replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    retry_pattern,
    '  const bool found = ok && dict.lookup(lookupWord.c_str(), definition, headword, &result);',
)

# 4) Hungarian productive -zzák form: finanszírozzák -> finanszíroz.
needle = '''    for (const char* s : {"zzanak", "zzenek"}) {
      std::string st;
      if (strip(w, s, st)) {
        add(st + "zik");
        add(st + "ik");
        add(st);
      }
    }
'''
replacement = needle + '''
    if (ends("zzák")) {
      add(w.substr(0, w.size() - strlen("zák")));
    }
'''
replace_once("src/util/Dictionary.cpp", needle, replacement)

# 5) Allow explicit two-line OptionPopup titles.
replace_once(
    "src/components/OptionPopup.h",
    '''    props.titleText.font = fui::GfxRendererTarget::FONT_BODY;
    props.titleText.bold = true;
    props.titleText.align = fui::TextAlign::Center;''',
    '''    props.titleText.font = fui::GfxRendererTarget::FONT_BODY;
    props.titleText.bold = true;
    props.titleText.align = fui::TextAlign::Center;
    props.titleText.maxLines = title.find('\\n') != std::string::npos ? 2 : 1;''',
)

print("CPHUN-132r7 dense dictionary index, bounded lookup and two-line popup fix applied")
