from pathlib import Path
import re


def replace(path, old, new):
    p = Path(path)
    text = p.read_text()
    if old not in text:
        raise SystemExit(f"pattern not found in {path}: {old[:80]!r}")
    p.write_text(text.replace(old, new, 1))

# Build ID
replace("src/CPHUNBuildId.h", 'CPHUN-260910-93', 'CPHUN-260911-94')

# Extended OPF metadata collection.
p = Path("lib/Epub/Epub/parsers/ContentOpfParser.cpp")
s = p.read_text()
needle = '''  if (self->state == IN_METADATA && xmlLocalNameEquals(name, "language")) {
    self->state = IN_BOOK_LANGUAGE;
    return;
  }
'''
insert = needle + '''
  if (self->state == IN_METADATA && xmlLocalNameEquals(name, "description")) {
    self->state = IN_BOOK_DESCRIPTION;
    return;
  }

  if (self->state == IN_METADATA && xmlLocalNameEquals(name, "publisher")) {
    self->state = IN_BOOK_PUBLISHER;
    return;
  }

  if (self->state == IN_METADATA && xmlLocalNameEquals(name, "date")) {
    self->state = IN_BOOK_DATE;
    return;
  }

  if (self->state == IN_METADATA && xmlLocalNameEquals(name, "identifier")) {
    self->state = IN_BOOK_IDENTIFIER;
    return;
  }
'''
if needle not in s:
    raise SystemExit("metadata insertion point missing")
s = s.replace(needle, insert, 1)

old_meta = '''  if (self->state == IN_METADATA && xmlLocalNameEquals(name, "meta")) {
    bool isCover = false;
    std::string coverItemId;

    for (int i = 0; atts[i]; i += 2) {
      if (strcmp(atts[i], "name") == 0 && strcmp(atts[i + 1], "cover") == 0) {
        isCover = true;
      } else if (strcmp(atts[i], "content") == 0) {
        coverItemId = atts[i + 1];
      }
    }

    if (isCover) {
      self->coverItemId = coverItemId;
    }
    return;
  }
'''
new_meta = '''  if (self->state == IN_METADATA && xmlLocalNameEquals(name, "meta")) {
    std::string metaName;
    std::string content;
    for (int i = 0; atts[i]; i += 2) {
      if (strcmp(atts[i], "name") == 0) metaName = atts[i + 1];
      else if (strcmp(atts[i], "content") == 0) content = atts[i + 1];
    }
    if (metaName == "cover") self->coverItemId = content;
    else if (metaName == "calibre:series") self->series = content;
    else if (metaName == "calibre:series_index") self->seriesIndex = content;
    return;
  }
'''
if old_meta not in s:
    raise SystemExit("meta block missing")
s = s.replace(old_meta, new_meta, 1)

char_needle = '''  if (self->state == IN_BOOK_LANGUAGE) {
    self->language.append(s, len);
    return;
  }
'''
char_insert = char_needle + '''
  if (self->state == IN_BOOK_DESCRIPTION) {
    self->description.append(s, len);
    return;
  }
  if (self->state == IN_BOOK_PUBLISHER) {
    self->publisher.append(s, len);
    return;
  }
  if (self->state == IN_BOOK_DATE) {
    self->date.append(s, len);
    return;
  }
  if (self->state == IN_BOOK_IDENTIFIER) {
    if (self->identifier.empty()) self->identifier.append(s, len);
    return;
  }
'''
if char_needle not in s:
    raise SystemExit("character data insertion missing")
s = s.replace(char_needle, char_insert, 1)

end_needle = '''  if (self->state == IN_BOOK_LANGUAGE && xmlLocalNameEquals(name, "language")) {
    self->state = IN_METADATA;
    return;
  }
'''
end_insert = end_needle + '''
  if (self->state == IN_BOOK_DESCRIPTION && xmlLocalNameEquals(name, "description")) {
    self->state = IN_METADATA;
    return;
  }
  if (self->state == IN_BOOK_PUBLISHER && xmlLocalNameEquals(name, "publisher")) {
    self->state = IN_METADATA;
    return;
  }
  if (self->state == IN_BOOK_DATE && xmlLocalNameEquals(name, "date")) {
    self->state = IN_METADATA;
    return;
  }
  if (self->state == IN_BOOK_IDENTIFIER && xmlLocalNameEquals(name, "identifier")) {
    self->state = IN_METADATA;
    return;
  }
'''
if end_needle not in s:
    raise SystemExit("end metadata insertion missing")
s = s.replace(end_needle, end_insert, 1)
p.write_text(s)

# On-demand book metadata reader: does not change book.bin layout.
p = Path("lib/Epub/Epub.cpp")
s = p.read_text()
needle = '''const std::string& Epub::getLanguage() const {
  static std::string blank;
  if (!bookMetadataCache || !bookMetadataCache->isLoaded()) {
    return blank;
  }

  return bookMetadataCache->coreMetadata.language;
}
'''
addition = needle + '''

bool Epub::readBookInfo(BookInfo& info) const {
  info = {};
  info.title = getTitle();
  info.author = getAuthor();
  info.language = getLanguage();
  const size_t slash = filepath.find_last_of('/');
  info.filename = slash == std::string::npos ? filepath : filepath.substr(slash + 1);

  HalFile source;
  if (Storage.openFileForRead("EBP", filepath, source)) {
    info.fileSize = source.size();
    source.close();
  }

  std::string opfPath;
  if (!findContentOpfFile(&opfPath)) return false;
  const std::string base = opfPath.substr(0, opfPath.find_last_of('/') + 1);
  size_t opfSize = 0;
  if (!getItemSize(opfPath, &opfSize)) return false;
  ContentOpfParser parser(cachePath, base, opfSize, nullptr);
  if (!parser.setup() || !readItemContentsToStream(opfPath, parser, 1024)) return false;
  if (!parser.title.empty()) info.title = utf8ComposeNfc(parser.title);
  if (!parser.author.empty()) info.author = parser.author;
  if (!parser.language.empty()) info.language = parser.language;
  info.description = parser.description;
  info.publisher = parser.publisher;
  info.date = parser.date;
  info.identifier = parser.identifier;
  info.series = parser.series;
  info.seriesIndex = parser.seriesIndex;
  return true;
}
'''
if needle not in s:
    raise SystemExit("Epub getLanguage block missing")
s = s.replace(needle, addition, 1)
p.write_text(s)

# Reader: Book Info action + themed error dialogs.
p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text()
if '#include "BookInfoActivity.h"' not in s:
    s = s.replace('#include "BookmarkEntry.h"\n', '#include "BookmarkEntry.h"\n#include "BookInfoActivity.h"\n', 1)

case_needle = '''    case EpubReaderMenuActivity::MenuAction::TEXT_SETTINGS: {
'''
book_case = '''    case EpubReaderMenuActivity::MenuAction::BOOK_INFO: {
      startActivityForResult(std::make_unique<BookInfoActivity>(renderer, mappedInput, epub),
                             [this](const ActivityResult&) { openReaderMenu(); });
      break;
    }
''' + case_needle
if case_needle not in s:
    raise SystemExit("TEXT_SETTINGS case missing")
s = s.replace(case_needle, book_case, 1)

pattern = re.compile(r'''void EpubReaderActivity::showIndexBuildError\(\) \{.*?\n\}\n\nvoid EpubReaderActivity::loop\(\) \{''', re.S)
replacement = r'''void EpubReaderActivity::showIndexBuildError() {
  failedSpineIndex = currentSpineIndex;
  automaticPageTurnActive = false;
  showIndexErrorMain();
}

void EpubReaderActivity::showIndexErrorMain() {
  indexErrorDialog = IndexErrorDialog::Main;
  const char* options[] = {"OK", "Javítás"};
  indexErrorPopup.show("Indexelési hiba - hibás könyv", options, 2, 0, [this](int idx) {
    if (idx == 0) {
      indexErrorDialog = IndexErrorDialog::None;
      onGoHome();
    } else {
      showIndexRepairConfirm();
    }
  });
  requestUpdate(true);
}

void EpubReaderActivity::showIndexRepairConfirm() {
  indexErrorDialog = IndexErrorDialog::RepairConfirm;
  const char* options[] = {"Mégse", "Javítás"};
  indexErrorPopup.show("Hibás részek kihagyása", options, 2, 0, [this](int idx) {
    if (idx == 0) {
      showIndexErrorMain();
      return;
    }
    const int badSpine = failedSpineIndex;
    if (!persistSkippedSpine(badSpine)) {
      LOG_ERR("ERS", "Failed to persist skipped malformed spine %d", badSpine);
      showIndexErrorMain();
      return;
    }
    LOG_DBG("ERS", "User approved skipping malformed spine %d", badSpine);
    indexErrorDialog = IndexErrorDialog::None;
    failedSpineIndex = -1;
    section.reset();
    currentSpineIndex = badSpine + 1;
    nextPageNumber = 0;
    clearDeferredReposition();
    advancePastSkippedSpines(true);
    requestUpdate();
  });
  requestUpdate(true);
}

void EpubReaderActivity::renderIndexErrorDialog() {
  renderer.clearScreen();
  if (indexErrorDialog == IndexErrorDialog::Main) {
    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 105, "A könyv egyik része nem", true, EpdFontFamily::REGULAR);
    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 135, "dolgozható fel.", true, EpdFontFamily::REGULAR);
  } else if (indexErrorDialog == IndexErrorDialog::RepairConfirm) {
    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 70, "A CrossPoint megpróbálja", true, EpdFontFamily::REGULAR);
    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 100, "megnyitni a könyvet, és kihagyja", true,
                              EpdFontFamily::REGULAR);
    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 130, "a nem feldolgozható részeket.", true,
                              EpdFontFamily::REGULAR);
    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 160, "Az eredeti EPUB nem módosul.", true,
                              EpdFontFamily::REGULAR);
  }
  indexErrorPopup.processRender(renderer, mappedInput);
}

bool EpubReaderActivity::handleIndexErrorDialogInput() {
  if (indexErrorDialog == IndexErrorDialog::None) return false;
  indexErrorPopup.handleInput(mappedInput, [this] { requestUpdate(); });
  return true;
}

void EpubReaderActivity::loop() {'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f"error dialog block replacement count={n}")
s = s2

render_sig = 'void EpubReaderActivity::renderBook() {\n  if (!epub) return;\n'
render_new = 'void EpubReaderActivity::renderBook() {\n  if (!epub) return;\n  if (indexErrorDialog != IndexErrorDialog::None) {\n    renderIndexErrorDialog();\n    return;\n  }\n'
if render_sig not in s:
    raise SystemExit("renderBook signature missing")
s = s.replace(render_sig, render_new, 1)
p.write_text(s)

print("CPHUN-94 patch applied")
