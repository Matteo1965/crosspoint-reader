from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-132r7: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# 1) Make the sampled dictionary sidecar dense enough for interactive misses.
#    The old 256-entry interval made a normal miss perform up to 256 byte-wise
#    headword reads. 32 keeps the sidecar tiny but cuts the worst scan by 8x.
#    The interval is stored in the sidecar header, so old .qidx/.sidx files are
#    automatically rejected as stale and rebuilt on first lookup.
# -----------------------------------------------------------------------------
replace_once(
    "src/util/Dictionary.h",
    "  static constexpr uint32_t SAMPLE_INTERVAL = 256;",
    "  static constexpr uint32_t SAMPLE_INTERVAL = 32;",
)

# A time/probe safety stop is not an SD read failure. Treat it as a bounded miss;
# real seek/open/sample failures still set readError on their own paths.
replace_once(
    "src/util/Dictionary.cpp",
    '''    if (++locateProbes > SAMPLE_INTERVAL + 8 || millis() - locateStart > 1500) {
      result.readError = true;
      break;
    }''',
    '''    if (++locateProbes > SAMPLE_INTERVAL + 8 || millis() - locateStart > 1500) {
      LOG_WRN("DICT", "Index lookup guard reached for %s", target);
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
      LOG_WRN("DICT", "Synonym lookup guard reached for %s", target);
      break;
    }''',
)

# -----------------------------------------------------------------------------
# 2) Remove the only unbounded byte loop in headword parsing. A valid StarDict
#    headword fitting wordBuf exits before this path; an overlong/corrupt entry
#    can now consume at most a fixed tail before the probe aborts.
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# 3) Do not immediately repeat a full lookup after ReadError. That retry doubled
#    the exact/synonym/morphology work and could make a slow miss look frozen.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''  bool found = ok && dict.lookup(lookupWord.c_str(), definition, headword, &result);
  if (!found && ok && result == Dictionary::LookupResult::ReadError) {
    vTaskDelay(1);
    definition.clear();
    headword.clear();
    result = Dictionary::LookupResult::NotFound;
    found = dict.lookup(lookupWord.c_str(), definition, headword, &result);
  }''',
    '''  const bool found = ok && dict.lookup(lookupWord.c_str(), definition, headword, &result);''',
)

# -----------------------------------------------------------------------------
# 4) Hungarian productive -zzák form: alkalmazzák -> alkalmaz,
#    finanszírozzák -> finanszíroz. Removing the final "zák" retains the lemma's
#    first z and is safer than a one-word exception.
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# 5) OptionPopup titles containing an explicit newline may use two lines.
#    FreeInkUI already wraps title text and optionDialogHeight measures maxLines;
#    OptionPopup forced the default maxLines=1, which caused the r6 truncation.
# -----------------------------------------------------------------------------
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
