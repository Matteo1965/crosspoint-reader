#include "EpubReaderActivity.h"

#include <Epub/Page.h>
#include <Epub/blocks/TextBlock.h>
#include <FontCacheManager.h>
#include <FsHelpers.h>
#include <GfxRenderer.h>
#include <HalStorage.h>
#include <I18n.h>
#include <Logging.h>
#include <Memory.h>
#include <esp_system.h>

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <iterator>
#include <limits>

#include "../../util/BookmarkFile.h"
#include "BookmarkEntry.h"
#include "BookInfoActivity.h"
#include "CrossPointSettings.h"
#include "CrossPointState.h"
#include "DictionaryWordSelectActivity.h"
#include "ManualDictionarySearchActivity.h"
#include "EpubReaderBookmarksActivity.h"
#include "EpubReaderChapterSelectionActivity.h"
#include "EpubReaderFootnotesActivity.h"
#include "FootnotePopupActivity.h"
#include "EpubReaderPercentSelectionActivity.h"
#include "EpubReaderUtils.h"
#include "KOReaderCredentialStore.h"
#include "KOReaderSyncActivity.h"
#include "MappedInputManager.h"
#include "ProgressMapper.h"
#include "QrDisplayActivity.h"
#include "ReaderActivity.h"
#include "ReaderFontSizes.h"
#include "ReaderUtils.h"
#include "RecentBooksStore.h"
#include "SdCardFontSystem.h"
#include "ReaderButtonProfileStore.h"
#include "activities/settings/SettingsActivity.h"
#include "activities/settings/TextSettingsActivity.h"
#include "activities/util/BmpViewerActivity.h"
#include "components/UITheme.h"
#include "fontIds.h"
#include "util/BookmarkUtil.h"
#include "util/ScreenshotUtil.h"
#include "highlights/HighlightRenderer.h"
#include "highlights/TextEditRenderer.h"
#include "activities/util/KeyboardEntryActivity.h"

namespace {

struct Cphun150LayoutSnapshot {
  ReaderRenderSpec spec;
  uint8_t orientation;
  uint8_t screenMargin;
  uint8_t statusBarHeight;
};

Cphun150LayoutSnapshot captureReaderLayout(const uint16_t width, const uint16_t height) {
  return {SETTINGS.readerRenderSpec(width, height), SETTINGS.orientation, SETTINGS.screenMargin,
          UITheme::getInstance().getStatusBarHeight()};
}

bool readerLayoutMatches(const Cphun150LayoutSnapshot& saved,
                         const uint16_t width, const uint16_t height) {
  if (saved.orientation != SETTINGS.orientation || saved.screenMargin != SETTINGS.screenMargin ||
      saved.statusBarHeight != UITheme::getInstance().getStatusBarHeight()) {
    return false;
  }
  const ReaderRenderSpec current = SETTINGS.readerRenderSpec(width, height);
  const ReaderRenderSpec& old = saved.spec;
  return old.fontId == current.fontId &&
         old.lineCompression == current.lineCompression &&
         old.extraParagraphSpacing == current.extraParagraphSpacing &&
         old.paragraphAlignment == current.paragraphAlignment &&
         old.viewportWidth == current.viewportWidth &&
         old.viewportHeight == current.viewportHeight &&
         old.hyphenationEnabled == current.hyphenationEnabled &&
         old.hungarianHyphenationExtended == current.hungarianHyphenationExtended &&
         old.hangingPunctuationLimitPx == current.hangingPunctuationLimitPx &&
         old.shortHyphen == current.shortHyphen &&
         old.fixedDialogueSpacing == current.fixedDialogueSpacing &&
         old.minimumSpacePercent == current.minimumSpacePercent &&
         old.letterSpacingLimitPercent == current.letterSpacingLimitPercent &&
         old.embeddedStyle == current.embeddedStyle &&
         old.imageRendering == current.imageRendering &&
         old.focusReadingEnabled == current.focusReadingEnabled;
}

constexpr int PAGE_TURN_RATES[] = {1, 1, 3, 6, 12};
constexpr size_t initialBookmarkCacheCapacity = 16;
constexpr float bookmarkProgressEpsilon = 0.0001f;

int clampPercent(int percent) {
  if (percent < 0) {
    return 0;
  }
  if (percent > 100) {
    return 100;
  }
  return percent;
}

constexpr char READ_FOLDER[] = "/read";

bool isInReadFolder(const std::string& path) {
  constexpr size_t n = sizeof(READ_FOLDER) - 1;
  return path.size() > n && path.compare(0, n, READ_FOLDER) == 0 && path[n] == '/';
}

std::string trimPlain(std::string value) {
  auto ws = [](unsigned char c) { return std::isspace(c) != 0; };
  while (!value.empty() && ws(static_cast<unsigned char>(value.front()))) value.erase(value.begin());
  while (!value.empty() && ws(static_cast<unsigned char>(value.back()))) value.pop_back();
  return value;
}

std::string htmlToPlain(const std::string& html) {
  std::string out;
  out.reserve(html.size());
  bool inTag = false;
  bool pendingSpace = false;
  for (size_t i = 0; i < html.size(); ++i) {
    const char c = html[i];
    if (c == '<') { inTag = true; pendingSpace = !out.empty(); continue; }
    if (c == '>') { inTag = false; continue; }
    if (inTag) continue;
    if (c == '&') {
      const size_t semi = html.find(';', i + 1);
      if (semi != std::string::npos && semi - i <= 8) {
        const std::string entity = html.substr(i, semi - i + 1);
        if (entity == "&nbsp;") { pendingSpace = true; i = semi; continue; }
        if (entity == "&amp;") { if (pendingSpace && !out.empty()) out.push_back(' '); out.push_back('&'); pendingSpace = false; i = semi; continue; }
        if (entity == "&quot;") { if (pendingSpace && !out.empty()) out.push_back(' '); out.push_back('\"'); pendingSpace = false; i = semi; continue; }
        if (entity == "&lt;") { if (pendingSpace && !out.empty()) out.push_back(' '); out.push_back('<'); pendingSpace = false; i = semi; continue; }
        if (entity == "&gt;") { if (pendingSpace && !out.empty()) out.push_back(' '); out.push_back('>'); pendingSpace = false; i = semi; continue; }
      }
    }
    if (std::isspace(static_cast<unsigned char>(c))) { pendingSpace = !out.empty(); continue; }
    if (pendingSpace && !out.empty()) out.push_back(' ');
    pendingSpace = false;
    out.push_back(c);
  }
  return trimPlain(std::move(out));
}

std::string htmlAttribute(const std::string& tag, const char* name) {
  const std::string needle = std::string(name) + "=";
  size_t p = tag.find(needle);
  if (p == std::string::npos) return {};
  p += needle.size();
  while (p < tag.size() && std::isspace(static_cast<unsigned char>(tag[p]))) ++p;
  if (p >= tag.size()) return {};
  const char quote = tag[p];
  if (quote != '\'' && quote != '\"') return {};
  const size_t end = tag.find(quote, p + 1);
  return end == std::string::npos ? std::string() : tag.substr(p + 1, end - p - 1);
}

bool looksLikeFootnoteLabel(const std::string& label) {
  if (label.empty() || label.size() > 24) return false;
  bool hasDigit = false;
  for (unsigned char c : label) {
    if (c >= '0' && c <= '9') { hasDigit = true; continue; }
    if (std::isspace(c) || c == '{' || c == '}' || c == '[' || c == ']' || c == '(' || c == ')' || c == '.') continue;
    return false;
  }
  return hasDigit;
}

struct ProgressRange {
  float start;
  float end;
};

ProgressRange getPageProgressRange(const std::shared_ptr<Epub>& epub, const int spineIndex, const int page,
                                   const int pageCount) {
  if (pageCount <= 1) {
    return {epub->calculateProgress(spineIndex, 0.0f), epub->calculateProgress(spineIndex, 1.0f)};
  }

  const float step = 1.0f / static_cast<float>(pageCount - 1);
  const float anchor = std::clamp(static_cast<float>(page) * step, 0.0f, 1.0f);
  const float start = std::max(0.0f, anchor - (step * 0.5f));
  const float end = std::min(1.0f, anchor + (step * 0.5f));
  return {epub->calculateProgress(spineIndex, start), epub->calculateProgress(spineIndex, end)};
}

bool bookmarkMatchesProgress(const BookmarkEntry& bookmark, const int spineIndex, const int page, const int pageCount,
                             const ProgressRange& pageRange) {
  if (bookmark.computedSpineIndex == spineIndex && bookmark.computedChapterPageCount == pageCount &&
      bookmark.computedChapterProgress == page) {
    return true;
  }

  const float bookmarkProgress = std::clamp(bookmark.percentage, 0.0f, 1.0f);
  return bookmarkProgress + bookmarkProgressEpsilon >= pageRange.start &&
         bookmarkProgress - bookmarkProgressEpsilon <= pageRange.end;
}

std::string buildReadFolderDestination(const std::string& srcPath) {
  const size_t lastSlash = srcPath.rfind('/');
  const std::string filename = (lastSlash != std::string::npos) ? srcPath.substr(lastSlash + 1) : srcPath;

  Storage.mkdir(READ_FOLDER);
  std::string dstPath = std::string(READ_FOLDER) + "/" + filename;
  if (!Storage.exists(dstPath.c_str())) {
    return dstPath;
  }

  const size_t dotPos = filename.rfind('.');
  const std::string base = (dotPos != std::string::npos) ? filename.substr(0, dotPos) : filename;
  const std::string ext = (dotPos != std::string::npos) ? filename.substr(dotPos) : "";
  int suffix = 2;
  do {
    dstPath = std::string(READ_FOLDER) + "/" + base + " (" + std::to_string(suffix) + ")" + ext;
    suffix++;
  } while (Storage.exists(dstPath.c_str()) && suffix < 100);
  return dstPath;
}

void moveFinishedBookToReadFolder(const std::string& srcPath, const std::string& dstPath,
                                  const std::string& oldCachePath) {
  LOG_INF("ERS", "Moving finished epub: %s -> %s", srcPath.c_str(), dstPath.c_str());
  if (!Storage.rename(srcPath.c_str(), dstPath.c_str())) {
    LOG_ERR("ERS", "Failed to move finished book to '/Read' folder");
    return;
  }

  const std::string newCachePath = "/.crosspoint/epub_" + std::to_string(std::hash<std::string>{}(dstPath));
  if (!oldCachePath.empty() && Storage.exists(oldCachePath.c_str())) {
    if (!Storage.rename(oldCachePath.c_str(), newCachePath.c_str())) {
      LOG_ERR("ERS", "Failed to rename cache dir %s -> %s (non-fatal)", oldCachePath.c_str(), newCachePath.c_str());
    }
  }

  RECENT_BOOKS.updatePath(srcPath, dstPath, oldCachePath, newCachePath);
  if (APP_STATE.openEpubPath == srcPath) {
    APP_STATE.openEpubPath = dstPath;
    APP_STATE.saveToFile();
  }
}

}  // namespace

EpubReaderActivity::~EpubReaderActivity() {
  renderer.clearReaderGlyphFallbackFonts();
  ImageBlock::setExtractor(nullptr, nullptr);

  if (footnoteDepth > 0 && epub) {
    const SavedPosition& origin = savedPositions[0];
    saveProgress(origin.spineIndex, origin.pageNumber, 0);
  }

  section.reset();
  if (pendingReadFolderMove && epub) {
    const std::string srcPath = epub->getPath();
    const std::string oldCachePath = epub->getCachePath();
    const std::string dstPath = buildReadFolderDestination(srcPath);
    epub.reset();
    moveFinishedBookToReadFolder(srcPath, dstPath, oldCachePath);
  } else {
    epub.reset();
  }
}

bool EpubReaderActivity::loadBook() {
  // CPHUN-163: EPUB-only glyph coverage fallback. Nearest loaded Noto Serif
  // size is chosen per missing codepoint; normal primary font stays intact.
  renderer.setReaderGlyphFallbackFonts(NOTOSERIF_12_FONT_ID, NOTOSERIF_14_FONT_ID,
                                       NOTOSERIF_16_FONT_ID, NOTOSERIF_18_FONT_ID);
  auto loadedEpub = makeUniqueNoThrow<Epub>(bookPath, "/.crosspoint");
  if (!loadedEpub) {
    LOG_ERR("ERS", "Failed to allocate EPUB object");
    return false;
  }

  const bool uncached = !Storage.exists((loadedEpub->getCachePath() + "/book.bin").c_str());
  if (uncached) {
    disableFastInitialRefresh();
    GUI.drawPopup(renderer, tr(STR_INDEXING));
  }

  bool loaded;
  {
    std::optional<GfxRenderer::FrameBufferLoan> loan;
    if (uncached) loan.emplace(renderer);
    loaded = loadedEpub->load(true, SETTINGS.embeddedStyle == 0);
  }
  if (!loaded) {
    LOG_ERR("ERS", "Failed to load EPUB");
    return false;
  }
  epub = std::move(loadedEpub);
  loadSkippedSpines();

  ImageBlock::clearSessionRenderFailures();
  ImageBlock::setExtractor(epub.get(), [](void* ctx, const char* src, const char* dest) {
    return static_cast<Epub*>(ctx)->extractItemToFile(src, dest);
  });

  epub->setupCacheDir();

  HalFile f;
  if (Storage.openFileForRead("ERS", epub->getCachePath() + "/progress.bin", f)) {
    uint8_t data[10];
    int dataSize = f.read(data, sizeof(data));
    if (dataSize == 4 || dataSize == 6 || dataSize == 10) {
      currentSpineIndex = data[0] + (data[1] << 8);
      nextPageNumber = data[2] + (data[3] << 8);
      if (nextPageNumber == UINT16_MAX) {
        LOG_DBG("ERS", "Ignoring stale last-page sentinel from progress cache");
        nextPageNumber = 0;
      }
      cachedSpineIndex = currentSpineIndex;
      LOG_DBG("ERS", "Loaded cache: %d, %d", currentSpineIndex, nextPageNumber);
    }
    if (dataSize == 6) {
      cachedChapterTotalPageCount = data[4] + (data[5] << 8);
    } else if (dataSize == 10) {
      cachedChapterTotalPageCount = data[4] + (data[5] << 8);
      cachedVisibleTextOffset = static_cast<uint32_t>(data[6]) | (static_cast<uint32_t>(data[7]) << 8) |
                                (static_cast<uint32_t>(data[8]) << 16) | (static_cast<uint32_t>(data[9]) << 24);
    }
  }

  if (currentSpineIndex == 0) {
    int textSpineIndex = epub->getSpineIndexForTextReference();
    if (textSpineIndex != 0) {
      currentSpineIndex = textSpineIndex;
      cachedVisibleTextOffset.reset();
      LOG_DBG("ERS", "Opened for first time, navigating to text reference at index %d", textSpineIndex);
    }
  }

  highlightStore = std::make_unique<HighlightStore>(epub->getPath());
  highlightStore->load();
  textEditStore = std::make_unique<TextEditStore>(epub->getPath());
  textEditStore->load();
  loadCachedBookmarks();
  return true;
}

void EpubReaderActivity::ensureBookFootnotes() {
  if (bookFootnotesIndexed || !epub) return;
  bookFootnotesIndexed = true;
  bookFootnotes.clear();

  // CPHUN-135r4i: SAFE CURRENT-SPINE INDEX ONLY.
  // Never walk the whole EPUB from the Reader menu. R4G reproduced an X4
  // abort while the synchronous whole-book scan reached Michelangelo note 132.
  // One spine/XHTML is bounded enough for an interactive menu operation while
  // still allowing notes elsewhere in the current chapter to be listed.
  constexpr size_t MAX_SPINE_FOOTNOTES = 160;
  constexpr size_t ROLLING_LIMIT = 6144;
  if (currentSpineIndex < 0 || currentSpineIndex >= epub->getSpineItemsCount()) return;

  const auto item = epub->getSpineItem(currentSpineIndex);
  const std::string tmpPath = epub->getCachePath() + "/.footnotes_spine_scan.tmp";

  auto lowerAscii = [](std::string v) {
    for (char& c : v) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return v;
  };

  auto isForwardNoteref = [&](const std::string& tag, const std::string& href, const std::string& label) {
    if (href.empty() || !looksLikeFootnoteLabel(label)) return false;
    const std::string t = lowerAscii(tag);
    const std::string h = lowerAscii(href);
    if (t.find("noteref") != std::string::npos || t.find("doc-noteref") != std::string::npos) return true;
    if (t.find("footnote") != std::string::npos || t.find("endnote") != std::string::npos) return true;

    const size_t hash = h.find('#');
    const std::string path = hash == std::string::npos ? h : h.substr(0, hash);
    const std::string frag = hash == std::string::npos ? std::string() : h.substr(hash + 1);
    if (path.find("footnote") != std::string::npos || path.find("endnote") != std::string::npos ||
        path.find("notes.") != std::string::npos || path.find("/notes") != std::string::npos ||
        path.find("note.") != std::string::npos) return true;
    if (frag.find("footnote") != std::string::npos || frag.find("endnote") != std::string::npos ||
        frag.rfind("note_", 0) == 0 || frag.rfind("note-", 0) == 0) return true;
    return false;
  };

  HalFile out;
  if (!Storage.openFileForWrite("ERS", tmpPath, out)) return;
  const bool streamed = epub->readItemContentsToStream(item.href, out, 1024);
  out.close();
  if (!streamed) {
    Storage.remove(tmpPath.c_str());
    return;
  }

  HalFile in;
  if (!Storage.openFileForRead("ERS", tmpPath, in)) {
    Storage.remove(tmpPath.c_str());
    return;
  }

  std::string pending;
  pending.reserve(2048);
  uint8_t chunk[768];
  while (bookFootnotes.size() < MAX_SPINE_FOOTNOTES) {
    const int got = in.read(chunk, sizeof(chunk));
    if (got <= 0) break;
    pending.append(reinterpret_cast<const char*>(chunk), static_cast<size_t>(got));

    while (true) {
      const size_t a = pending.find("<a");
      if (a == std::string::npos) {
        if (pending.size() > 256) pending.erase(0, pending.size() - 256);
        break;
      }
      const size_t tagEnd = pending.find('>', a + 2);
      const size_t close = pending.find("</a>", a + 2);
      if (tagEnd == std::string::npos || close == std::string::npos || close < tagEnd) {
        if (a > 0) pending.erase(0, a);
        if (pending.size() > ROLLING_LIMIT) pending.erase(0, pending.size() - 512);
        break;
      }

      const std::string tag = pending.substr(a, tagEnd - a + 1);
      std::string href = htmlAttribute(tag, "href");
      const std::string label = htmlToPlain(pending.substr(tagEnd + 1, close - tagEnd - 1));
      pending.erase(0, close + 4);
      if (!isForwardNoteref(tag, href, label)) continue;

      // CPHUN-135r4j: preserve the href exactly as it appears in the source XHTML.
      // extractFootnoteText() resolves it once, relative to currentSpineIndex.

      const bool duplicate = std::any_of(bookFootnotes.begin(), bookFootnotes.end(), [&](const FootnoteEntry& e) {
        return href == e.href;
      });
      if (duplicate) continue;

      FootnoteEntry entry;
      std::strncpy(entry.number, label.c_str(), sizeof(entry.number) - 1);
      entry.number[sizeof(entry.number) - 1] = ' ';
      std::strncpy(entry.href, href.c_str(), sizeof(entry.href) - 1);
      entry.href[sizeof(entry.href) - 1] = ' ';
      bookFootnotes.push_back(entry);
    }
  }
  in.close();
  Storage.remove(tmpPath.c_str());
  LOG_DBG("ERS", "Current-spine footnote index: spine=%d, entries=%u", currentSpineIndex,
          static_cast<unsigned>(bookFootnotes.size()));
}

std::string EpubReaderActivity::extractFootnoteText(const FootnoteEntry& footnote, const int sourceSpineIndex) const {
  if (!epub || footnote.href[0] == '\0') return {};

  const std::string href(footnote.href);
  const std::string marker(footnote.number);
  const size_t hash = href.find('#');
  const std::string hrefPath = hash == std::string::npos ? href : href.substr(0, hash);
  const std::string fragment = hash == std::string::npos ? std::string() : href.substr(hash + 1);

  std::string sourceHref;
  if (sourceSpineIndex >= 0 && sourceSpineIndex < epub->getSpineItemsCount()) {
    sourceHref = epub->getSpineItem(sourceSpineIndex).href;
  }

  auto normalizePath = [](const std::string& baseFile, const std::string& relative) {
    if (relative.empty()) return baseFile;
    if (relative.find("://") != std::string::npos) return relative;
    std::string joined;
    if (!relative.empty() && relative[0] == '/') {
      joined = relative.substr(1);
    } else {
      const size_t slash = baseFile.rfind('/');
      joined = slash == std::string::npos ? relative : baseFile.substr(0, slash + 1) + relative;
    }
    std::vector<std::string> parts;
    size_t p = 0;
    while (p <= joined.size()) {
      const size_t q = joined.find('/', p);
      const std::string part = joined.substr(p, q == std::string::npos ? std::string::npos : q - p);
      if (part == "..") {
        if (!parts.empty()) parts.pop_back();
      } else if (!part.empty() && part != ".") {
        parts.push_back(part);
      }
      if (q == std::string::npos) break;
      p = q + 1;
    }
    std::string out;
    for (size_t i = 0; i < parts.size(); ++i) {
      if (i) out += '/';
      out += parts[i];
    }
    return out;
  };

  const std::string targetHref = normalizePath(sourceHref, hrefPath);
  std::string errorCode;
  std::string diagContext;
  size_t diagnosticTargetSize = 0;
  bool diagnosticTargetSizeOk = false;

  auto writeDiagnostic = [&](const char* code) {
    constexpr const char* LOG_DIR = "/logfiles";
    const bool logDirReady = Storage.ensureDirectoryExists(LOG_DIR);
    const size_t slash = bookPath.find_last_of("/\\");
    const std::string fallbackDir = slash == std::string::npos ? std::string() : bookPath.substr(0, slash + 1);
    const std::string dir = logDirReady ? std::string(LOG_DIR) + "/" : fallbackDir;
    std::string tag = fragment.empty() ? "unknown" : fragment;
    for (char& c : tag) {
      if (!(std::isalnum(static_cast<unsigned char>(c)) || c == '-' || c == '_')) c = '_';
    }
    if (tag.size() > 40) tag.resize(40);
    const std::string logPath = dir + "footnote_error_" + std::to_string(millis()) + "_" + tag + ".txt";
    std::string log;
    log.reserve(2048);
    log += "CrossPoint Footnote Diagnostic\nFormat version: 1\n\n";
    log += "Firmware: CPHUN-260917-135R4E-EXP\n";
    log += "Book: " + epub->getTitle() + "\n";
    log += "EPUB: " + bookPath + "\n";
    log += "Source spine: " + std::to_string(sourceSpineIndex) + "\n";
    log += "Source XHTML: " + sourceHref + "\n";
    log += "Marker: " + marker + "\n";
    log += "Original href: " + href + "\n";
    log += "Resolved target: " + targetHref + "\n";
    log += "Fragment: " + fragment + "\n";
    log += "Target size lookup: ";
    log += diagnosticTargetSizeOk ? "OK" : "FAILED";
    log += "\n";
    log += "Target inflated size: " + std::to_string(diagnosticTargetSize) + "\n\n";
    log += "Error: ";
    log += code;
    log += "\n\nContext (max 1024 bytes):\n";
    if (diagContext.size() > 1024) diagContext.resize(1024);
    log += diagContext;
    log += "\n";
    if (log.size() > 8192) log.resize(8192);
    HalFile out;
    if (Storage.openFileForWrite("ERS", logPath, out)) {
      out.write(reinterpret_cast<const uint8_t*>(log.data()), log.size());
      out.close();
      LOG_DBG("ERS", "Footnote diagnostic written: %s", logPath.c_str());
    }
  };

  if (targetHref.empty() || targetHref.find("://") != std::string::npos) {
    writeDiagnostic("FOOTNOTE_TARGET_INVALID");
    return {};
  }

  diagnosticTargetSizeOk = epub->getItemSize(targetHref, &diagnosticTargetSize);
  if (!diagnosticTargetSizeOk) {
    writeDiagnostic("EPUB_ITEM_SIZE_FAILED");
    return {};
  }

  const std::string tmpPath = epub->getCachePath() + "/.footnote_resolver.tmp";

  // CPHUN-135r4k2f7: if the same XHTML target was already extracted during
  // this reader session, reuse it instead of streaming the ZIP member again.
  bool haveCachedTarget = false;
  if (footnoteResolverCachedTarget == targetHref) {
    HalFile probe;
    if (Storage.openFileForRead("ERS", tmpPath, probe)) {
      probe.close();
      haveCachedTarget = true;
    } else {
      footnoteResolverCachedTarget.clear();
    }
  }

  if (!haveCachedTarget) {
    Storage.remove(tmpPath.c_str());
    HalFile out;
    if (!Storage.openFileForWrite("ERS", tmpPath, out)) {
      writeDiagnostic("TEMP_FILE_OPEN_FAILED");
      return {};
    }

    const bool streamed = epub->readItemContentsToStream(targetHref, out, 1024);
    out.flush();
    out.close();
    if (!streamed) {
      Storage.remove(tmpPath.c_str());
      footnoteResolverCachedTarget.clear();
      writeDiagnostic("EPUB_ZIP_STREAM_FAILED");
      return {};
    }
    footnoteResolverCachedTarget = targetHref;
  }

  bool tempReadFailed = false;
  auto readNeedle = [&](const std::vector<std::string>& needles, bool fragmentSearch) -> std::string {
    HalFile in;
    if (!Storage.openFileForRead("ERS", tmpPath, in)) {
      tempReadFailed = true;
      return {};
    }
    std::string scan;
    std::string capture;
    scan.reserve(12288);
    capture.reserve(12288);
    constexpr size_t SCAN_LIMIT = 12288;
    constexpr size_t CAPTURE_LIMIT = 16384;
    uint8_t chunk[768];
    bool found = false;
    std::string blockTag;
    std::string activeNeedle;

    while (true) {
      const int got = in.read(chunk, sizeof(chunk));
      if (got <= 0) break;
      if (diagContext.size() < 1024) {
        const size_t take = std::min<size_t>(static_cast<size_t>(got), 1024 - diagContext.size());
        diagContext.append(reinterpret_cast<const char*>(chunk), take);
      }
      if (!found) {
        scan.append(reinterpret_cast<const char*>(chunk), static_cast<size_t>(got));
        size_t pos = std::string::npos;
        for (const auto& needle : needles) {
          if (needle.empty()) continue;
          const size_t candidate = scan.find(needle);
          if (candidate != std::string::npos && (pos == std::string::npos || candidate < pos)) {
            pos = candidate;
            activeNeedle = needle;
          }
        }
        if (pos == std::string::npos) {
          if (scan.size() > SCAN_LIMIT) scan.erase(0, scan.size() - 2048);
          continue;
        }

        size_t begin = pos;
        struct Block { const char* open; const char* close; };
        constexpr Block blocks[] = {{"<dl", "dl"}, {"<aside", "aside"}, {"<section", "section"},
                                    {"<li", "li"}, {"<div", "div"}, {"<p", "p"}};
        size_t best = std::string::npos;
        for (const auto& b : blocks) {
          const size_t bp = scan.rfind(b.open, pos);
          if (bp != std::string::npos && (best == std::string::npos || bp > best)) {
            best = bp;
            blockTag = b.close;
          }
        }
        if (best != std::string::npos) begin = best;
        else {
          const size_t lt = scan.rfind('<', pos);
          if (lt != std::string::npos) begin = lt;
        }
        capture.assign(scan.data() + begin, scan.size() - begin);
        found = true;
        scan.clear();
      } else {
        capture.append(reinterpret_cast<const char*>(chunk), static_cast<size_t>(got));
      }

      if (!found) continue;
      if (capture.size() > CAPTURE_LIMIT) capture.resize(CAPTURE_LIMIT);

      size_t stop = std::string::npos;
      size_t suffix = 0;
      if (!blockTag.empty() && blockTag != "p") {
        const std::string close = "</" + blockTag + ">";
        stop = capture.find(close);
        suffix = close.size();
      } else if (blockTag == "p") {
        // Some Calibre footnotes (e.g. id_Footnote_N) continue through several
        // paragraphs. For those, stop at the next note anchor instead of the
        // first </p>. Other p-based notes remain one bounded paragraph.
        bool multiParagraph = false;
        std::string family;
        if (fragment.rfind("id_Footnote_", 0) == 0) family = "id_Footnote_";
        else if (fragment.rfind("Footnote_", 0) == 0) family = "Footnote_";
        if (!family.empty()) {
          multiParagraph = true;
          const size_t first = capture.find(activeNeedle);
          size_t next = capture.find("id=\"" + family, first == std::string::npos ? 1 : first + activeNeedle.size());
          const size_t next2 = capture.find("id='" + family, first == std::string::npos ? 1 : first + activeNeedle.size());
          if (next == std::string::npos || (next2 != std::string::npos && next2 < next)) next = next2;
          if (next != std::string::npos) {
            const size_t pbegin = capture.rfind("<p", next);
            stop = pbegin == std::string::npos ? next : pbegin;
            suffix = 0;
          }
        }
        if (!multiParagraph) {
          stop = capture.find("</p>");
          suffix = 4;
        }
      }

      if (stop != std::string::npos) {
        capture.resize(stop + suffix);
        in.close();
        return trimPlain(htmlToPlain(capture));
      }
      if (capture.size() >= CAPTURE_LIMIT) {
        in.close();
        return trimPlain(htmlToPlain(capture));
      }
    }
    in.close();
    if (found && !capture.empty()) return trimPlain(htmlToPlain(capture));
    return {};
  };

  std::vector<std::string> anchorNeedles;
  if (!fragment.empty()) {
    anchorNeedles.push_back("id=\"" + fragment + "\"");
    anchorNeedles.push_back("id='" + fragment + "'");
    anchorNeedles.push_back("name=\"" + fragment + "\"");
    anchorNeedles.push_back("name='" + fragment + "'");
    std::string text = readNeedle(anchorNeedles, true);
    if (!text.empty()) {
      return text;
    }
    errorCode = "FOOTNOTE_ANCHOR_NOT_FOUND";
  }

  // Marker fallback for EPUBs without a usable fragment. Exact visible marker
  // is tried first, then common numeric note-id families.
  std::vector<std::string> markerNeedles;
  if (!marker.empty()) markerNeedles.push_back(marker);
  std::string digits;
  for (const char c : marker) if (c >= '0' && c <= '9') digits += c;
  if (!digits.empty()) {
    markerNeedles.push_back(">" + digits + "<");
    markerNeedles.push_back("{" + digits + "}");
    markerNeedles.push_back("[" + digits + "]");
    markerNeedles.push_back("id=\"note_" + digits + "\"");
    markerNeedles.push_back("id=\"Footnote_" + digits + "\"");
    markerNeedles.push_back("id=\"footnote-" + digits + "\"");
    markerNeedles.push_back("id=\"n" + digits + "\"");
  }
  if (!markerNeedles.empty()) {
    std::string text = readNeedle(markerNeedles, false);
    if (!text.empty()) {
      return text;
    }
  }

  if (tempReadFailed) {
    writeDiagnostic("TEMP_FILE_READ_FAILED");
  } else {
    writeDiagnostic(errorCode.empty() ? "FOOTNOTE_UNSUPPORTED_STRUCTURE" : errorCode.c_str());
  }
  return {};
}

void EpubReaderActivity::openFootnotePopup(const FootnoteEntry& footnote, const int sourceSpineIndex) {
  std::string text = extractFootnoteText(footnote, sourceSpineIndex);
  if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";
  startActivityForResult(
      std::make_unique<FootnotePopupActivity>(renderer, mappedInput, footnote.number, std::move(text), false),
      [this](const ActivityResult&) { requestUpdate(); });
}

const std::string& EpubReaderActivity::getCachedCurrentPageFootnoteText(const int sourceSpineIndex,
                                                                        const int noteIndex) {
  static const std::string empty;
  if (noteIndex < 0 || noteIndex >= static_cast<int>(currentPageFootnotes.size())) return empty;

  if (footnoteTextCacheSpine_ != sourceSpineIndex ||
      (section && footnoteTextCachePage_ != section->currentPage)) {
    footnoteTextCacheIndexes_.fill(-1);
    for (auto& text : footnoteTextCacheTexts_) text.clear();
    footnoteTextCacheSpine_ = sourceSpineIndex;
    footnoteTextCachePage_ = section ? section->currentPage : -1;
  }

  const size_t slot = static_cast<size_t>(noteIndex) % FOOTNOTE_TEXT_CACHE_SLOTS;
  if (footnoteTextCacheIndexes_[slot] == noteIndex && !footnoteTextCacheTexts_[slot].empty()) {
    LOG_DBG("FNT", "Cache hit note=%d heap=%u max=%u", noteIndex, static_cast<unsigned>(ESP.getFreeHeap()),
            static_cast<unsigned>(ESP.getMaxAllocHeap()));
    return footnoteTextCacheTexts_[slot];
  }

  LOG_INF("FNT", "Extract begin note=%d heap=%u max=%u", noteIndex, static_cast<unsigned>(ESP.getFreeHeap()),
          static_cast<unsigned>(ESP.getMaxAllocHeap()));
  std::string text = extractFootnoteText(currentPageFootnotes[noteIndex], sourceSpineIndex);
  if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";
  footnoteTextCacheTexts_[slot] = std::move(text);
  footnoteTextCacheIndexes_[slot] = noteIndex;
  LOG_INF("FNT", "Extract end note=%d bytes=%u heap=%u max=%u", noteIndex,
          static_cast<unsigned>(footnoteTextCacheTexts_[slot].size()), static_cast<unsigned>(ESP.getFreeHeap()),
          static_cast<unsigned>(ESP.getMaxAllocHeap()));
  return footnoteTextCacheTexts_[slot];
}

void EpubReaderActivity::openFootnotePopupSession(const bool wholeBook, const bool returnToMenu,
                                                    const int sourceSpineIndex, int noteIndex) {
  const auto& notes = wholeBook ? bookFootnotes : currentPageFootnotes;
  if (notes.empty()) {
    requestUpdate();
    return;
  }

  const int count = static_cast<int>(notes.size());
  noteIndex = (noteIndex % count + count) % count;
  const FootnoteEntry note = notes[noteIndex];

  std::string text;
  if (!wholeBook) {
    text = getCachedCurrentPageFootnoteText(sourceSpineIndex, noteIndex);
  } else {
    text = extractFootnoteText(note, sourceSpineIndex);
    if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";
  }

  startActivityForResult(
      std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), true, count > 1),
      [this, wholeBook, returnToMenu, sourceSpineIndex, noteIndex](const ActivityResult& popupResult) {
        if (popupResult.isCancelled) {
          openFootnotesList(wholeBook, returnToMenu, sourceSpineIndex);
          return;
        }
        if (const auto* nav = std::get_if<FootnotePopupNavResult>(&popupResult.data)) {
          openFootnotePopupSession(wholeBook, returnToMenu, sourceSpineIndex, noteIndex + nav->delta);
          return;
        }
        requestUpdate();  // Bezárás -> reader
      });
}

void EpubReaderActivity::openFootnotesList(const bool wholeBook, const bool returnToMenu,
                                           const int sourceSpineIndex) {
  const auto& notes = wholeBook ? bookFootnotes : currentPageFootnotes;
  if (notes.empty()) {
    if (returnToMenu) openReaderMenu();
    return;
  }

  const int sourceSpine = sourceSpineIndex >= 0 ? sourceSpineIndex : currentSpineIndex;

  // Preserve the existing one-note direct-popup behavior.
  if (notes.size() == 1) {
    const FootnoteEntry note = notes.front();
    std::string text = extractFootnoteText(note, sourceSpine);
    if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";
    startActivityForResult(
        std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), false, false),
        [this](const ActivityResult&) { requestUpdate(); });
    return;
  }

  startActivityForResult(
      std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, notes),
      [this, wholeBook, returnToMenu, sourceSpine](const ActivityResult& result) {
        if (result.isCancelled) {
          if (returnToMenu) openReaderMenu();
          else requestUpdate();
          return;
        }

        const auto& selected = std::get<FootnoteResult>(result.data);
        const auto& source = wholeBook ? bookFootnotes : currentPageFootnotes;
        const auto it = std::find_if(source.begin(), source.end(),
                                     [&](const FootnoteEntry& e) { return selected.href == e.href; });
        if (it == source.end()) {
          requestUpdate();
          return;
        }
        const int index = static_cast<int>(std::distance(source.begin(), it));
        openFootnotePopupSession(wholeBook, returnToMenu, sourceSpine, index);
      });
}

ChapterPosition EpubReaderActivity::chapterPosition() const {
  if (section) return {section->currentPage, section->estimatedTotalPages()};
  return {nextPageNumber, cachedChapterTotalPageCount};
}

int EpubReaderActivity::bookPercentFor(const ChapterPosition& position) const {
  if (!epub || epub->getBookSize() == 0 || !position.hasTotal()) return 0;
  const float progress = epub->calculateProgress(
      currentSpineIndex, std::clamp(position.chapterFraction(), 0.0f, 1.0f));
  return clampPercent(static_cast<int>(std::clamp(progress, 0.0f, 1.0f) * 100.0f + 0.5f));
}

void EpubReaderActivity::openReaderMenu(const bool startOnBookTab) {
  pendingManualTurn = 0;
  const ChapterPosition position = chapterPosition();
  const int currentPage = position.displayPage();
  const int totalPages = position.totalPages;
  const int bookProgressPercent = bookPercentFor(position);
  startActivityForResult(std::make_unique<EpubReaderMenuActivity>(
                             renderer, mappedInput, epub->getTitle(), currentPage, totalPages, bookProgressPercent,
                             SETTINGS.orientation, true,
                             !cachedBookmarks.empty() || (highlightStore && !highlightStore->items().empty()), startOnBookTab),
                         [this](const ActivityResult& result) {
                           const auto& menu = std::get<MenuResult>(result.data);
                           if (SETTINGS.orientation != menu.orientation) {
                             applyOrientation(menu.orientation);
                           }
                           toggleAutoPageTurn(menu.pageTurnOption);
                           if (!result.isCancelled) {
                             onReaderMenuConfirm(static_cast<EpubReaderMenuActivity::MenuAction>(menu.action));
                           }
                         });
}

bool EpubReaderActivity::buildTickHeapGate() {
  const size_t freeHeap = ESP.getFreeHeap();
  const size_t maxBlock = ESP.getMaxAllocHeap();
  buildHeapPaused = freeHeap < BACKGROUND_BUILD_MIN_FREE_HEAP || maxBlock < BACKGROUND_BUILD_MIN_MAX_ALLOC;
  return !buildHeapPaused;
}

void EpubReaderActivity::showBuildPopup(GfxRenderer& renderer, int& pagesUntilFullRefresh) {
  if (!buildPopupPending || !renderer.hasFrameBuffer()) return;
  GUI.drawPopup(renderer, tr(STR_INDEXING));
  pagesUntilFullRefresh = 1;
  buildPopupPending = false;
}

void EpubReaderActivity::openEditKeyboard(HighlightResult selection) {
  if (!epub) return;
  if (!textEditStore) {
    textEditStore = std::make_unique<TextEditStore>(epub->getPath());
    textEditStore->load();
  }
  std::string initialText = selection.text;
  if (textEditStore) {
    if (const auto* old = textEditStore->find(selection.spineIndex, selection.visibleTextOffset)) {
      initialText = old->replacementText;
    }
  }

  startActivityForResult(
      std::make_unique<KeyboardEntryActivity>(renderer, mappedInput, "Szerkesztés", initialText, 0, InputType::Text),
      [this, selection = std::move(selection)](const ActivityResult& result) {
        if (!result.isCancelled) {
          if (const auto* keyboard = std::get_if<KeyboardResult>(&result.data)) {
            if (textEditStore) {
              textEditStore->upsert({selection.spineIndex, selection.visibleTextOffset, selection.length,
                                     selection.text, keyboard->text, keyboard->text.empty()});
            }
          }
        }
        requestUpdate();
      });
}

void EpubReaderActivity::openDictionaryWordSelect(const WordSelectionMode mode) {
  if (!section) return;
  auto page = section->loadPage(section->currentPage);
  if (!page) return;

  int orientedMarginTop, orientedMarginRight, orientedMarginBottom, orientedMarginLeft;
  renderer.getOrientedViewableTRBL(&orientedMarginTop, &orientedMarginRight, &orientedMarginBottom,
                                   &orientedMarginLeft);
  const int verticalScreenMargin =
      SETTINGS.screenMargin == 5 ? 4 : std::max(0, static_cast<int>(SETTINGS.screenMargin) - 6);
  orientedMarginTop += verticalScreenMargin;
  orientedMarginLeft += SETTINGS.screenMargin;

  const std::string highlightBookPath = epub->getPath();
  std::vector<uint32_t> highlightedOffsets;
  if (highlightStore) {
    for (const auto& item : highlightStore->items()) {
      if (item.spineIndex == currentSpineIndex) highlightedOffsets.push_back(item.visibleTextOffset);
    }
  }
  // CPHUN-132r1: the dictionary index/lookup path is memory-sensitive. The
  // highlight list is persisted already, so release its heap while the word
  // selector/dictionary owns the foreground, then reload it on return.
  highlightStore.reset();
  auto selector = std::make_unique<DictionaryWordSelectActivity>(renderer, mappedInput, std::move(page),
                                                                 orientedMarginLeft, orientedMarginTop,
                                                                 currentSpineIndex, mode,
                                                                 std::move(highlightedOffsets));
  if (section->currentPage > 0) selector->setPreviousBoundaryPage(section->loadPage(section->currentPage - 1));
  if (section->currentPage + 1 < static_cast<int>(section->pageCount))
    selector->setNextBoundaryPage(section->loadPage(section->currentPage + 1));
  startActivityForResult(
      std::move(selector),
      [this, highlightBookPath, mode](const ActivityResult& result) {
        highlightStore = std::make_unique<HighlightStore>(highlightBookPath);
        highlightStore->load();
        if (!result.isCancelled) {
          if (const auto* selected = std::get_if<HighlightResult>(&result.data)) {
            if (mode == WordSelectionMode::Edit) {
              pendingEditSelection = *selected;
              requestUpdate();
              return;
            }
            if (highlightStore) {
              highlightStore->toggle({selected->spineIndex, selected->visibleTextOffset, selected->length, selected->text});
            }
          }
        }
        requestUpdate();
      });
}

void EpubReaderActivity::openSearchFootnotePopup(const WordSelectionMode mode, const int sourceSpineIndex,
                                                   int noteIndex) {
  if (currentPageFootnotes.empty()) {
    openDictionaryWordSelect(mode);
    return;
  }

  const int count = static_cast<int>(currentPageFootnotes.size());
  noteIndex = (noteIndex % count + count) % count;
  const FootnoteEntry note = currentPageFootnotes[noteIndex];

  std::string text = getCachedCurrentPageFootnoteText(sourceSpineIndex, noteIndex);

  startActivityForResult(
      std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), true, count > 1),
      [this, mode, sourceSpineIndex, noteIndex](const ActivityResult& popupResult) {
        if (popupResult.isCancelled) {
          openDictionaryWordSelect(mode);  // Shortcut: Vissza -> selected word mode, never the list.
          return;
        }
        if (const auto* nav = std::get_if<FootnotePopupNavResult>(&popupResult.data)) {
          openSearchFootnotePopup(mode, sourceSpineIndex, noteIndex + nav->delta);
          return;
        }
        requestUpdate();  // Bezárás -> reader
      });
}

void EpubReaderActivity::openSearchFootnoteList(const WordSelectionMode mode, const int sourceSpineIndex) {
  if (currentPageFootnotes.empty()) {
    openDictionaryWordSelect(mode);
    return;
  }
  if (currentPageFootnotes.size() == 1) {
    openSearchFootnotePopup(mode, sourceSpineIndex, 0);
    return;
  }

  startActivityForResult(
      std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, currentPageFootnotes),
      [this, mode, sourceSpineIndex](const ActivityResult& result) {
        if (result.isCancelled) {
          openDictionaryWordSelect(mode);  // Vissza from list -> selected word mode
          return;
        }

        const auto& selected = std::get<FootnoteResult>(result.data);
        const auto it = std::find_if(currentPageFootnotes.begin(), currentPageFootnotes.end(),
                                     [&](const FootnoteEntry& e) { return selected.href == e.href; });
        if (it == currentPageFootnotes.end()) {
          openDictionaryWordSelect(mode);
          return;
        }
        const int index = static_cast<int>(std::distance(currentPageFootnotes.begin(), it));
        openSearchFootnotePopup(mode, sourceSpineIndex, index);
      });
}

void EpubReaderActivity::openSearchFootnoteOrWordSelect(const WordSelectionMode mode) {
  if (currentPageFootnotes.empty()) {
    openDictionaryWordSelect(mode);
    return;
  }

  const int sourceSpine = currentSpineIndex;
  // CPHUN-144 shortcut UX: for any non-empty page, open the first footnote
  // immediately. Sibling footnotes remain reachable with front buttons 3/4.
  openSearchFootnotePopup(mode, sourceSpine, 0);
}

namespace {
constexpr char SKIPPED_SPINES_FILE[] = "/skipped_spines.bin";
}

void EpubReaderActivity::loadSkippedSpines() {
  skippedSpines.clear();
  if (!epub) return;
  HalFile file;
  if (!Storage.openFileForRead("ERS", epub->getCachePath() + SKIPPED_SPINES_FILE, file)) return;
  const size_t size = file.size();
  if (size == 0 || size > 1024 || (size % 2) != 0) {
    file.close();
    return;
  }
  for (size_t i = 0; i < size / 2; ++i) {
    uint8_t bytes[2] = {};
    if (file.read(bytes, sizeof(bytes)) != static_cast<int>(sizeof(bytes))) break;
    const uint16_t spine = static_cast<uint16_t>(bytes[0]) | (static_cast<uint16_t>(bytes[1]) << 8);
    if (std::find(skippedSpines.begin(), skippedSpines.end(), spine) == skippedSpines.end()) {
      skippedSpines.push_back(spine);
    }
  }
  file.close();
}

bool EpubReaderActivity::isSpineSkipped(const int spineIndex) const {
  return spineIndex >= 0 &&
         std::find(skippedSpines.begin(), skippedSpines.end(), static_cast<uint16_t>(spineIndex)) !=
             skippedSpines.end();
}

bool EpubReaderActivity::persistSkippedSpine(const int spineIndex) {
  if (!epub || spineIndex < 0 || spineIndex >= epub->getSpineItemsCount()) return false;
  const uint16_t spine = static_cast<uint16_t>(spineIndex);
  if (std::find(skippedSpines.begin(), skippedSpines.end(), spine) == skippedSpines.end()) {
    skippedSpines.push_back(spine);
    std::sort(skippedSpines.begin(), skippedSpines.end());
  }
  HalFile out;
  if (!Storage.openFileForWrite("ERS", epub->getCachePath() + SKIPPED_SPINES_FILE, out)) return false;
  bool ok = true;
  for (const uint16_t item : skippedSpines) {
    const uint8_t bytes[2] = {static_cast<uint8_t>(item & 0xFF), static_cast<uint8_t>(item >> 8)};
    if (out.write(bytes, sizeof(bytes)) != sizeof(bytes)) {
      ok = false;
      break;
    }
  }
  out.close();
  return ok;
}

void EpubReaderActivity::advancePastSkippedSpines(const bool forward) {
  if (!epub) return;
  if (forward) {
    while (currentSpineIndex < epub->getSpineItemsCount() && isSpineSkipped(currentSpineIndex)) {
      LOG_DBG("ERS", "Skipping user-approved malformed spine %d", currentSpineIndex);
      ++currentSpineIndex;
      nextPageNumber = 0;
      pendingPageJump.reset();
      pendingAnchor.clear();
    }
  } else {
    while (currentSpineIndex >= 0 && isSpineSkipped(currentSpineIndex)) {
      LOG_DBG("ERS", "Skipping user-approved malformed spine %d (backward)", currentSpineIndex);
      --currentSpineIndex;
      nextPageNumber = 0;
      pendingPageJump = std::numeric_limits<uint16_t>::max();
      pendingAnchor.clear();
    }
    if (currentSpineIndex < 0) currentSpineIndex = 0;
  }
}

void EpubReaderActivity::showIndexBuildError() {
  failedSpineIndex = currentSpineIndex;
  automaticPageTurnActive = false;
  showIndexErrorMain();
}

void EpubReaderActivity::showIndexErrorMain() {
  indexErrorDialog = IndexErrorDialog::Main;
  const char* options[] = {"OK", "Javítás"};
  indexErrorPopup.show("", options, 2, 0, [this](int idx) {
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
    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 45, "Indexelési hiba - hibás könyv", true, EpdFontFamily::BOLD);
    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 100, "A könyv egyik része nem", true, EpdFontFamily::REGULAR);
    renderer.drawCenteredText(NOTOSANS_14_FONT_ID, 130, "dolgozható fel.", true, EpdFontFamily::REGULAR);
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

void EpubReaderActivity::loop() {
  if (pendingEditSelection) {
    HighlightResult selection = std::move(*pendingEditSelection);
    pendingEditSelection.reset();
    openEditKeyboard(std::move(selection));
    return;
  }
  if (handleIndexErrorDialogInput()) return;
  if (!epub) {
    finish();
    return;
  }

  constexpr unsigned long IDLE_PREWARM_DEBOUNCE_MS = 400;
  if (section && !section->isBuilding() && !RenderLock::peek() && renderer.hasFrameBuffer() &&
      lastRenderCompleteMs != 0 && millis() - lastRenderCompleteMs > IDLE_PREWARM_DEBOUNCE_MS &&
      ESP.getFreeHeap() > RENDER_MIN_FREE_HEAP && ESP.getMaxAllocHeap() > BACKGROUND_BUILD_MIN_MAX_ALLOC &&
      (idlePrewarmSpine != currentSpineIndex || idlePrewarmPage != section->currentPage)) {
    RenderLock lock;
    if (section && !section->isBuilding() &&
        (idlePrewarmSpine != currentSpineIndex || idlePrewarmPage != section->currentPage)) {
      idlePrewarmSpine = currentSpineIndex;
      idlePrewarmPage = section->currentPage;
      const int nextPage = section->currentPage + 1;
      if (nextPage < static_cast<int>(section->pageCount)) {
        if (const auto p = section->loadPage(nextPage)) {
          if (auto* fcm = renderer.getFontCacheManager()) {
            const auto t0 = millis();
            auto scope = fcm->createPrewarmScope();
            p->render(renderer, SETTINGS.getReaderFontId(), 0, 0);
            scope.endScanAndPrewarm();
            LOG_DBG("ERS", "Idle prewarm: page %d in %lums", nextPage, millis() - t0);
          }
        }
      }
    }
  }

  if (section && !section->isBuilding() && section->isPartial() && !RenderLock::peek() && buildViewportWidth > 0 &&
      !partialRebuildStartFailed &&
      section->currentPage + PARTIAL_REBUILD_START_MARGIN >= static_cast<int>(section->pageCount)) {
    RenderLock lock;
    const ReaderRenderSpec buildSpec = SETTINGS.readerRenderSpec(buildViewportWidth, buildViewportHeight);
    if (!section->startBuild(buildSpec)) {
      partialRebuildStartFailed = true;
      LOG_ERR("ERS", "Failed to start deferred partial extension build");
    } else {
      LOG_DBG("ERS", "Reader near partial watermark (%d/%d), resuming extension build", section->currentPage,
              section->pageCount);
    }
  }

  if (section && section->isBuilding() && !RenderLock::peek() &&
      (section->isPartial() || static_cast<int>(section->pageCount) < section->currentPage + BUILD_WINDOW_AHEAD) &&
      buildTickHeapGate()) {
    RenderLock lock;
    if (section->isBuilding() && buildTickHeapGate()) {
      if (!section->buildSomeMore(BACKGROUND_BUILD_PAGES_PER_TICK)) {
        LOG_ERR("ERS", "Background section build failed");
        section.reset();
        requestUpdate();
      } else if (section->isBuildComplete() && applyDeferredReposition()) {
        requestUpdate();
      }
    }
  }

  const bool atEndOfBook = currentSpineIndex > 0 && currentSpineIndex >= epub->getSpineItemsCount();
  clearEndOfBookOptionsIfNeeded();

  if (SETTINGS.removeReadBooksFromRecents) {
    if (atEndOfBook && !recentsEntryRemoved) {
      recentsEntryRemoved = RECENT_BOOKS.removeByPath(epub->getPath());
    } else if (!atEndOfBook && recentsEntryRemoved) {
      RECENT_BOOKS.addBook(epub->getPath(), epub->getTitle(), epub->getAuthor(), epub->getThumbBmpPath());
      recentsEntryRemoved = false;
    }
  }

  if (atEndOfBook) {
    pendingReadFolderMove = SETTINGS.moveFinishedToReadFolder && !isInReadFolder(epub->getPath());
  } else {
    pendingReadFolderMove = false;
  }

  const auto touch = ReaderUtils::detectTouchPageTurn(renderer, mappedInput);

  // CPHUN-36 2x front-button test v2.
  // IMPORTANT: never return merely because a front button was pressed. Side
  // buttons, Power and all legacy hold processing must continue through this
  // reader loop. Only the four front buttons' SHORT actions are deferred.
  struct Cphun36DoubleState {
    int raw = -1;
    unsigned long firstReleaseMs = 0;
    bool waitingSecond = false;
  };
  static Cphun36DoubleState cphun36;
  constexpr unsigned long CPHUN36_DOUBLE_MS = 400;

  const int cphun36PressedRaw = mappedInput.getPressedFrontButton();
  const int cphun36ReleasedRaw = mappedInput.getReleasedFrontButton();
  const unsigned long cphun36HeldMs = mappedInput.getHeldTime();

  const auto cphun36RebuildReader = [this]() {
    RenderLock lock;
    if (section) {
      rememberCurrentContentOffset();
      cachedSpineIndex = currentSpineIndex;
      cachedChapterTotalPageCount = section->pageCount;
      nextPageNumber = section->currentPage;
    }
    section.reset();
    requestUpdate();
  };

  const auto cphun36OpenSettings = [this]() {
    const auto before = captureReaderLayout(buildViewportWidth, buildViewportHeight);
    startActivityForResult(std::make_unique<SettingsActivity>(renderer, mappedInput),
                           [this, before](const ActivityResult&) {
                             if (!readerLayoutMatches(before, buildViewportWidth, buildViewportHeight)) {
                               RenderLock lock;
                               if (section) {
                                 rememberCurrentContentOffset();
                                 cachedSpineIndex = currentSpineIndex;
                                 cachedChapterTotalPageCount = section->pageCount;
                                 nextPageNumber = section->currentPage;
                               }
                               section.reset();
                               LOG_INF("ERS", "CPHUN-150: settings changed layout; refreshing section");
                             } else {
                               LOG_DBG("ERS", "CPHUN-150: settings unchanged; retaining section");
                             }
                             requestUpdate();
                           });
  };

  const auto cphun36OpenLayout = [this]() {
    const auto before = captureReaderLayout(buildViewportWidth, buildViewportHeight);
    startActivityForResult(
        std::make_unique<TextSettingsActivity>(renderer, mappedInput, &sdFontSystem.registry(),
                                               TextSettingsActivity::Tab::Layout),
        [this, before](const ActivityResult&) {
          if (!readerLayoutMatches(before, buildViewportWidth, buildViewportHeight)) {
            RenderLock lock;
            if (section) {
              rememberCurrentContentOffset();
              cachedSpineIndex = currentSpineIndex;
              cachedChapterTotalPageCount = section->pageCount;
              nextPageNumber = section->currentPage;
            }
            section.reset();
            LOG_INF("ERS", "CPHUN-150: layout changed; refreshing section");
          } else {
            LOG_DBG("ERS", "CPHUN-150: layout unchanged; retaining section");
          }
          requestUpdate();
        });
  };

  const auto cphun36GestureAction = [this, &cphun36OpenSettings, &cphun36OpenLayout, &cphun36RebuildReader](
                                      const int raw, const ReaderButtonGesture gesture) -> bool {
    ReaderPhysicalButton physical = ReaderPhysicalButton::Back;
    if (raw == HalGPIO::BTN_CONFIRM) physical = ReaderPhysicalButton::Confirm;
    else if (raw == HalGPIO::BTN_LEFT) physical = ReaderPhysicalButton::Left;
    else if (raw == HalGPIO::BTN_RIGHT) physical = ReaderPhysicalButton::Right;
    const ReaderAction configured = READER_BUTTONS.get(physical, gesture);
    if (configured == ReaderAction::None) {
      if (gesture != ReaderButtonGesture::Double) return false;
      // Compatibility fallback: preserve the four device-confirmed CPHUN-36 v2
      // double-click shortcuts until the user assigns an explicit 2x mapping.
      if (raw == HalGPIO::BTN_BACK) { cphun36OpenSettings(); return true; }
      if (raw == HalGPIO::BTN_CONFIRM) { cphun36OpenLayout(); return true; }
      if (raw == HalGPIO::BTN_LEFT) {
        if (SETTINGS.screenMargin > CrossPointSettings::SCREEN_MARGIN_MIN) {
          SETTINGS.screenMargin = std::max<int>(CrossPointSettings::SCREEN_MARGIN_MIN,
                                                SETTINGS.screenMargin - CrossPointSettings::SCREEN_MARGIN_STEP);
          SETTINGS.saveToFile(); cphun36RebuildReader();
        }
        return true;
      }
      if (raw == HalGPIO::BTN_RIGHT && SETTINGS.screenMargin < CrossPointSettings::SCREEN_MARGIN_MAX) {
        SETTINGS.screenMargin = std::min<int>(CrossPointSettings::SCREEN_MARGIN_MAX,
                                              SETTINGS.screenMargin + CrossPointSettings::SCREEN_MARGIN_STEP);
        SETTINGS.saveToFile(); cphun36RebuildReader();
      }
      return true;
    }
    if (configured == ReaderAction::ReaderBack) {
      if (footnoteDepth > 0) restoreSavedPosition();
      else if (SETTINGS.backShortToFileBrowser) activityManager.goToFileBrowser(bookPath);
      else onGoHome();
      return true;
    }
    if (configured == ReaderAction::PreviousPage || configured == ReaderAction::NextPage) {
      const bool previous = configured == ReaderAction::PreviousPage;
      const bool next = configured == ReaderAction::NextPage;
      if (handleEndOfBookPageTurn(previous, next)) return true;
      constexpr unsigned long kCphun43MinTurnGapMs = 200;
      if (RenderLock::peek() || (millis() - lastPageTurnTime) < kCphun43MinTurnGapMs) {
        pendingManualTurn = previous ? -1 : 1;
        return true;
      }
      if (!section) { requestUpdate(); return true; }
      pageTurn(next);
      requestUpdate();
      return true;
    }
    if (configured == ReaderAction::OpenDictionary) {
      WordSelectionMode mode = WordSelectionMode::Dictionary;
      if (SETTINGS.wordSelectionMode == 1) mode = WordSelectionMode::Highlight;
      else if (SETTINGS.wordSelectionMode == 2) mode = WordSelectionMode::Edit;
      openSearchFootnoteOrWordSelect(mode);
      return true;
    }
    if (configured == ReaderAction::OpenHighlight) { openDictionaryWordSelect(WordSelectionMode::Highlight); return true; }
    if (configured == ReaderAction::OpenManualDictionarySearch) {
      onReaderMenuConfirm(EpubReaderMenuActivity::MenuAction::MANUAL_DICTIONARY_SEARCH);
      return true;
    }
    if (configured == ReaderAction::OpenSettings) { cphun36OpenSettings(); return true; }
    if (configured == ReaderAction::OpenChapterSelection) {
      onReaderMenuConfirm(EpubReaderMenuActivity::MenuAction::SELECT_CHAPTER);
      return true;
    }
    if (configured == ReaderAction::FontSizeUp || configured == ReaderAction::FontSizeDown) {
      const auto points = readerFontPointSizes(&sdFontSystem.registry(), SETTINGS.sdFontFamilyName);
      if (!points.empty()) {
        const uint8_t current = snapToNearestPointSize(points, SETTINGS.fontPointSize);
        auto it = std::find(points.begin(), points.end(), current);
        size_t idx = it == points.end() ? 0 : static_cast<size_t>(std::distance(points.begin(), it));
        if (configured == ReaderAction::FontSizeUp) idx = (idx + 1) % points.size();
        else idx = (idx + points.size() - 1) % points.size();
        {
          RenderLock lock;
          SETTINGS.fontPointSize = points[idx];
          sdFontSystem.ensureLoaded(renderer);
        }
        SETTINGS.saveToFile();
        cphun36RebuildReader();
      }
      return true;
    }
    if (configured == ReaderAction::LineSpacingNext || configured == ReaderAction::LineSpacingPrevious) {
      constexpr uint8_t kLineSpacingValues[] = {
          CrossPointSettings::TIGHT, CrossPointSettings::NORMAL, CrossPointSettings::NORMAL_PLUS,
          CrossPointSettings::WIDE, CrossPointSettings::WIDE_PLUS, CrossPointSettings::EXTRA_WIDE};
      int idx = 1;
      for (int i = 0; i < static_cast<int>(std::size(kLineSpacingValues)); ++i) {
        if (kLineSpacingValues[i] == SETTINGS.lineSpacing) { idx = i; break; }
      }
      if (configured == ReaderAction::LineSpacingNext && idx + 1 < static_cast<int>(std::size(kLineSpacingValues))) ++idx;
      if (configured == ReaderAction::LineSpacingPrevious && idx > 0) --idx;
      SETTINGS.lineSpacing = kLineSpacingValues[idx];
      SETTINGS.saveToFile();
      cphun36RebuildReader();
      return true;
    }
    if (configured == ReaderAction::LetterSpacingCorrectionUp ||
        configured == ReaderAction::LetterSpacingCorrectionDown) {
      // CPHUN-113/128 UI order: KI,10,20,...70% maps to 0,360,340,...240.
      constexpr uint16_t values[] = {0, 360, 340, 320, 300, 280, 260, 240};
      int idx = 0;
      for (int i = 0; i < static_cast<int>(std::size(values)); ++i) {
        if (values[i] == SETTINGS.letterSpacingLimitPercent) { idx = i; break; }
      }
      if (configured == ReaderAction::LetterSpacingCorrectionUp && idx + 1 < static_cast<int>(std::size(values))) ++idx;
      if (configured == ReaderAction::LetterSpacingCorrectionDown && idx > 0) --idx;
      SETTINGS.letterSpacingLimitPercent = values[idx];
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::LetterSpacingOptimizationUp ||
        configured == ReaderAction::LetterSpacingOptimizationDown) {
      SETTINGS.letterSpacingOptimization =
          configured == ReaderAction::LetterSpacingOptimizationUp ? 4 : 0;
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::ExtraParagraphSpacingUp ||
        configured == ReaderAction::ExtraParagraphSpacingDown) {
      // Six UI states: KI, 0, 25, 50, 75, 100%.
      int idx = !SETTINGS.extraParagraphSpacingEnabled
                    ? 0
                    : (SETTINGS.extraParagraphSpacing == 0
                           ? 1
                           : std::clamp<int>(SETTINGS.extraParagraphSpacing / 25 + 1, 2, 5));
      if (configured == ReaderAction::ExtraParagraphSpacingUp && idx < 5) ++idx;
      if (configured == ReaderAction::ExtraParagraphSpacingDown && idx > 0) --idx;
      SETTINGS.extraParagraphSpacingEnabled = idx == 0 ? 0 : 1;
      SETTINGS.extraParagraphSpacing = idx <= 1 ? 0 : static_cast<uint8_t>((idx - 1) * 25);
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::MinimumSpaceUp || configured == ReaderAction::MinimumSpaceDown) {
      int value = std::clamp<int>(SETTINGS.minimumSpacePercent, 50, 100);
      value = ((value - 50) / 10) * 10 + 50;
      if (configured == ReaderAction::MinimumSpaceUp && value < 100) value += 10;
      if (configured == ReaderAction::MinimumSpaceDown && value > 50) value -= 10;
      SETTINGS.minimumSpacePercent = static_cast<uint8_t>(value);
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::TestLetterSpacingCorrectionMinMax) {
      // 10% <-> 70%; any non-minimum state returns to minimum for deterministic A/B tests.
      SETTINGS.letterSpacingLimitPercent = SETTINGS.letterSpacingLimitPercent == 360 ? 240 : 360;
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::TestLetterSpacingOptimizationOff100) {
      SETTINGS.letterSpacingOptimization = SETTINGS.letterSpacingOptimization == 0 ? 4 : 0;
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::TestLineSpacingMinMax) {
      SETTINGS.lineSpacing = SETTINGS.lineSpacing == CrossPointSettings::TIGHT
                                 ? CrossPointSettings::EXTRA_WIDE
                                 : CrossPointSettings::TIGHT;
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::TestExtraParagraphSpacingOffMax) {
      if (!SETTINGS.extraParagraphSpacingEnabled) {
        SETTINGS.extraParagraphSpacingEnabled = 1;
        SETTINGS.extraParagraphSpacing = 100;
      } else {
        SETTINGS.extraParagraphSpacingEnabled = 0;
      }
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::TestMinimumSpaceMinMax) {
      SETTINGS.minimumSpacePercent = SETTINGS.minimumSpacePercent == 50 ? 100 : 50;
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }

    if (configured == ReaderAction::ToggleBookmark) { addBookmark(); return true; }
    if (configured == ReaderAction::OpenBookmarks) {
      onReaderMenuConfirm(EpubReaderMenuActivity::MenuAction::BOOKMARKS);
      return true;
    }
    if (configured == ReaderAction::Screenshot) {
      onReaderMenuConfirm(EpubReaderMenuActivity::MenuAction::SCREENSHOT);
      return true;
    }
    if (configured == ReaderAction::OpenTextSettings) { cphun36OpenLayout(); return true; }
    if (configured == ReaderAction::OpenLayoutMenu) { cphun36OpenLayout(); return true; }
    if (configured == ReaderAction::ScreenMarginDown) {
      constexpr uint8_t kMargins[] = {5, 10, 12, 14, 16, 18, 20, 25};
      uint8_t next = kMargins[0];
      for (const uint8_t value : kMargins) {
        if (value >= SETTINGS.screenMargin) break;
        next = value;
      }
      if (next != SETTINGS.screenMargin) {
        SETTINGS.screenMargin = next;
        SETTINGS.saveToFile();
        cphun36RebuildReader();
      }
      return true;
    }
    if (configured == ReaderAction::ScreenMarginUp) {
      constexpr uint8_t kMargins[] = {5, 10, 12, 14, 16, 18, 20, 25};
      uint8_t next = kMargins[7];
      for (const uint8_t value : kMargins) {
        if (value > SETTINGS.screenMargin) {
          next = value;
          break;
        }
      }
      if (next != SETTINGS.screenMargin) {
        SETTINGS.screenMargin = next;
        SETTINGS.saveToFile();
        cphun36RebuildReader();
      }
      return true;
    }
    if (configured == ReaderAction::GoHome) { onGoHome(); return true; }
    if (configured == ReaderAction::OpenReaderMenu) { openReaderMenu(); return true; }
    if (configured == ReaderAction::ToggleNightMode) { SETTINGS.screenInverted = !SETTINGS.screenInverted; SETTINGS.saveToFile(); requestUpdate(); return true; }
    if (configured == ReaderAction::ToggleHyphenation) { SETTINGS.hyphenationEnabled = !SETTINGS.hyphenationEnabled; SETTINGS.saveToFile(); cphun36RebuildReader(); return true; }
    if (configured == ReaderAction::ToggleSoftHyphen) { SETTINGS.softHyphenEnabled = !SETTINGS.softHyphenEnabled; SETTINGS.saveToFile(); cphun36RebuildReader(); return true; }
    // Temporary fallback for actions not yet specialized in this integration: preserve known v2 test behavior.

    if (raw == HalGPIO::BTN_BACK) {
      cphun36OpenSettings();
      return true;
    }
    if (raw == HalGPIO::BTN_CONFIRM) {
      cphun36OpenLayout();
      return true;
    }
    if (raw == HalGPIO::BTN_LEFT) {
      constexpr uint8_t kMargins[] = {5, 10, 12, 14, 16, 18, 20, 25};
      uint8_t next = kMargins[0];
      for (const uint8_t value : kMargins) {
        if (value >= SETTINGS.screenMargin) break;
        next = value;
      }
      if (next != SETTINGS.screenMargin) {
        SETTINGS.screenMargin = next;
        SETTINGS.saveToFile();
        cphun36RebuildReader();
      }
      return true;
    }
    if (raw == HalGPIO::BTN_RIGHT) {
      constexpr uint8_t kMargins[] = {5, 10, 12, 14, 16, 18, 20, 25};
      uint8_t next = kMargins[7];
      for (const uint8_t value : kMargins) {
        if (value > SETTINGS.screenMargin) {
          next = value;
          break;
        }
      }
      if (next != SETTINGS.screenMargin) {
        SETTINGS.screenMargin = next;
        SETTINGS.saveToFile();
        cphun36RebuildReader();
      }
    }
    return true;
  };

  const auto cphun36LegacyShort = [this, &cphun36GestureAction](const int raw) {
    if (cphun36GestureAction(raw, ReaderButtonGesture::Single)) return;
    if (raw == SETTINGS.frontButtonBack) {
      if (footnoteDepth > 0) {
        restoreSavedPosition();
      } else if (SETTINGS.backShortToFileBrowser) {
        activityManager.goToFileBrowser(bookPath);
      } else {
        onGoHome();
      }
      return;
    }
    if (raw == SETTINGS.frontButtonConfirm) {
      openReaderMenu();
      return;
    }

    bool previous = raw == SETTINGS.frontButtonLeft;
    bool next = raw == SETTINGS.frontButtonRight;
    if (!previous && !next) return;
    if (mappedInput.isNavDirectionSwapped()) std::swap(previous, next);
    if (handleEndOfBookPageTurn(previous, next)) return;
    constexpr unsigned long kCphun36MinTurnGapMs = 200;
    if (RenderLock::peek() || (millis() - lastPageTurnTime) < kCphun36MinTurnGapMs) {
      pendingManualTurn = previous ? -1 : 1;
      return;
    }
    if (!section) {
      requestUpdate();
      return;
    }
    pageTurn(next);
    requestUpdate();
  };

  // A completed first short release is held for 400 ms. A matching second
  // short release runs the 2x action. Long releases are never consumed here.
  bool cphun36ConsumeFrontShort = false;
  if (cphun36ReleasedRaw >= 0) {
    bool legacyHold = false;
    if (cphun36ReleasedRaw == SETTINGS.frontButtonBack) {
      legacyHold = cphun36HeldMs >= ReaderUtils::GO_BACK_OR_HOME_MS;
    } else if (cphun36ReleasedRaw == SETTINGS.frontButtonConfirm) {
      switch (SETTINGS.longPressMenuFunction) {
        case CrossPointSettings::LP_MENU_BOOKMARK:
        case CrossPointSettings::LP_MENU_DICTIONARY:
          legacyHold = cphun36HeldMs >= ReaderUtils::BOOKMARK_HOLD_MS;
          break;
        case CrossPointSettings::LP_MENU_KOSYNC:
          legacyHold = cphun36HeldMs >= ReaderUtils::GO_HOME_MS;
          break;
        default:
          break;
      }
    } else if ((cphun36ReleasedRaw == SETTINGS.frontButtonLeft ||
                cphun36ReleasedRaw == SETTINGS.frontButtonRight) &&
               SETTINGS.longPressButtonBehavior != SETTINGS.OFF) {
      legacyHold = cphun36HeldMs > ReaderUtils::SKIP_HOLD_MS;
    }

    if (!legacyHold) {
      cphun36ConsumeFrontShort = true;
      if (cphun36.waitingSecond && cphun36.raw == cphun36ReleasedRaw &&
          millis() - cphun36.firstReleaseMs <= CPHUN36_DOUBLE_MS) {
        cphun36.waitingSecond = false;
        cphun36GestureAction(cphun36ReleasedRaw, ReaderButtonGesture::Double);
      } else {
        if (cphun36.waitingSecond) cphun36LegacyShort(cphun36.raw);
        cphun36.raw = cphun36ReleasedRaw;
        cphun36.firstReleaseMs = millis();
        cphun36.waitingSecond = true;
      }
    } else {
      if (cphun36.waitingSecond && cphun36.raw == cphun36ReleasedRaw) cphun36.waitingSecond = false;
      if (cphun36GestureAction(cphun36ReleasedRaw, ReaderButtonGesture::Hold)) {
        cphun36ConsumeFrontShort = true;
      }
    }
  }

  if (cphun36.waitingSecond && millis() - cphun36.firstReleaseMs > CPHUN36_DOUBLE_MS) {
    const int raw = cphun36.raw;
    cphun36.waitingSecond = false;
    cphun36LegacyShort(raw);
  }

  if (automaticPageTurnActive) {
    if (mappedInput.wasReleased(MappedInputManager::Button::Confirm) ||
        mappedInput.wasReleased(MappedInputManager::Button::Back) ||
        ReaderUtils::isTouchMenuGesture(renderer, mappedInput)) {
      automaticPageTurnActive = false;
      requestUpdate();
      return;
    }

    if (!section) {
      requestUpdate();
      return;
    }

    if (RenderLock::peek()) {
      lastPageTurnTime = millis();
      return;
    }

    if ((millis() - lastPageTurnTime) >= pageTurnDuration) {
      pageTurn(true);
      requestUpdate();
      return;
    }
  }

  if (showBookmarkMessage && (millis() - bookmarkMessageTime) >= ReaderUtils::BOOKMARK_MESSAGE_DURATION_MS) {
    showBookmarkMessage = false;
    requestUpdate();
  }

  if (showDictionaryMessage && (millis() - dictionaryMessageTime) >= ReaderUtils::BOOKMARK_MESSAGE_DURATION_MS) {
    showDictionaryMessage = false;
    requestUpdate();
  }
  if (showExportSuccess && millis() - exportSuccessTime >= 2000UL) {
    showExportSuccess = false;
    requestUpdate();
  }

  const bool confirmReleased = !cphun36ConsumeFrontShort && mappedInput.wasReleased(MappedInputManager::Button::Confirm);
  if (confirmReleased) {
    switch (SETTINGS.longPressMenuFunction) {
      case CrossPointSettings::LP_MENU_BOOKMARK:
        if (mappedInput.getHeldTime() >= ReaderUtils::BOOKMARK_HOLD_MS) {
          addBookmark();
          showBookmarkMessage = true;
          bookmarkMessageTime = millis();
          requestUpdate();
          return;
        }
        break;
      case CrossPointSettings::LP_MENU_KOSYNC:
        if (mappedInput.getHeldTime() >= ReaderUtils::GO_HOME_MS && launchKOReaderSync()) return;
        break;
      case CrossPointSettings::LP_MENU_DICTIONARY:
        if (mappedInput.getHeldTime() >= ReaderUtils::BOOKMARK_HOLD_MS) {
          openDictionaryWordSelect();
          return;
        }
        break;
      case CrossPointSettings::LP_MENU_READER_MENU:
        // Confirm already opens the menu on release. This option exists for
        // boards whose capacitive Home key supplies the long-press action.
        break;
      case CrossPointSettings::LP_MENU_DISABLED:
      default:
        break;
    }
  }

  // Home-key boards have no front Confirm button, so a Home-key hold runs the
  // same user-selected long-press action. The SDK emits this event once per
  // hold and suppresses the short Home tap for the same contact.
  if (mappedInput.wasHomeKeyHold()) {
    switch (SETTINGS.longPressMenuFunction) {
      case CrossPointSettings::LP_MENU_BOOKMARK:
        if (!showBookmarkMessage) {
          addBookmark();
          showBookmarkMessage = true;
          bookmarkMessageTime = millis();
          requestUpdate();
        }
        return;
      case CrossPointSettings::LP_MENU_KOSYNC:
        launchKOReaderSync();
        return;
      case CrossPointSettings::LP_MENU_DICTIONARY:
        if (!showDictionaryMessage) {
          openDictionaryWordSelect();
        }
        return;
      case CrossPointSettings::LP_MENU_READER_MENU:
        openReaderMenu();
        return;
      case CrossPointSettings::LP_MENU_DISABLED:
      default:
        break;
    }
  }

  if (handleEndOfBookMenu()) {
    return;
  }

  if (confirmReleased || ReaderUtils::isTouchMenuGesture(renderer, mappedInput)) {
    openReaderMenu();
  }

  if (!cphun36ConsumeFrontShort && footnoteDepth > 0 && mappedInput.wasReleased(MappedInputManager::Button::Back) &&
      mappedInput.getHeldTime() < ReaderUtils::GO_BACK_OR_HOME_MS) {
    restoreSavedPosition();
    return;
  }

  if (!cphun36ConsumeFrontShort && handleBackNavigation()) {
    return;
  }

  if (SETTINGS.shortPwrBtn == CrossPointSettings::SHORT_PWRBTN::FOOTNOTES &&
      mappedInput.wasReleased(MappedInputManager::Button::Power) &&
      !mappedInput.wasReleased(MappedInputManager::Button::Down)) {
    if (footnoteDepth > 0) {
      restoreSavedPosition();
    } else {
      if (currentPageFootnotes.size() == 1) {
        openFootnotePopup(currentPageFootnotes[0], currentSpineIndex);
      } else if (currentPageFootnotes.size() > 1) {
        openFootnotesList(false, false);
      }
    }
    return;
  }

  constexpr unsigned long kMinManualTurnGapMs = 200;
  const bool turnGuardActive = RenderLock::peek() || (millis() - lastPageTurnTime) < kMinManualTurnGapMs;
  if (pendingManualTurn != 0 && !turnGuardActive) {
    if (!section) {
      pendingManualTurn = 0;
      return;
    }
    const bool forward = pendingManualTurn > 0;
    pendingManualTurn = 0;
    pageTurn(forward);
    requestUpdate();
    return;
  }

  auto [prevTriggered, nextTriggered, fromTilt] = ReaderUtils::detectPageTurn(mappedInput);
  if (!fromTilt && (cphun36PressedRaw >= 0 || cphun36ConsumeFrontShort)) {
    const bool sidePrev = mappedInput.wasReleased(MappedInputManager::Button::PageBack) ||
                          mappedInput.wasPressed(MappedInputManager::Button::PageBack);
    const bool sideNext = mappedInput.wasReleased(MappedInputManager::Button::PageForward) ||
                          mappedInput.wasPressed(MappedInputManager::Button::PageForward);
    prevTriggered = sidePrev;
    nextTriggered = sideNext;
  }
  prevTriggered = prevTriggered || touch.prev;
  nextTriggered = nextTriggered || touch.next;
  if (!prevTriggered && !nextTriggered) {
    return;
  }

  if (handleEndOfBookPageTurn(prevTriggered, nextTriggered)) {
    return;
  }

  const unsigned long heldMs = (touch.prev || touch.next) ? touch.heldMs : mappedInput.getHeldTime();
  const bool longPress = !fromTilt && heldMs > ReaderUtils::SKIP_HOLD_MS;

  if (mappedInput.wasReleased(MappedInputManager::Button::Power) &&
      mappedInput.wasReleased(MappedInputManager::Button::Down)) {
    return;
  }

  if (longPress && SETTINGS.longPressButtonBehavior == SETTINGS.CHAPTER_SKIP) {
    skipPages(nextTriggered ? 1 : -1);
    requestUpdate();
    return;
  }

  if (longPress && SETTINGS.longPressButtonBehavior == SETTINGS.ORIENTATION_CHANGE) {
    const uint8_t newOrientation =
        nextTriggered ? (SETTINGS.orientation - 1 + SETTINGS.ORIENTATION_COUNT) % SETTINGS.ORIENTATION_COUNT
                      : (SETTINGS.orientation + 1) % SETTINGS.ORIENTATION_COUNT;
    applyOrientation(newOrientation);
    requestUpdate();
    return;
  }

  if (!section) {
    requestUpdate();
    return;
  }

  if (turnGuardActive) {
    pendingManualTurn = prevTriggered ? -1 : 1;
    return;
  }

  if (prevTriggered) {
    pageTurn(false);
  } else {
    pageTurn(true);
  }
  requestUpdate();
}

void EpubReaderActivity::jumpToPercent(int percent) {
  if (!epub) return;
  const size_t bookSize = epub->getBookSize();
  if (bookSize == 0) return;

  percent = clampPercent(percent);

  size_t targetSize =
      (bookSize / 100) * static_cast<size_t>(percent) + (bookSize % 100) * static_cast<size_t>(percent) / 100;
  if (percent >= 100) targetSize = bookSize - 1;

  const int spineCount = epub->getSpineItemsCount();
  if (spineCount == 0) return;

  int targetSpineIndex = spineCount - 1;
  size_t prevCumulative = 0;

  for (int i = 0; i < spineCount; i++) {
    const size_t cumulative = epub->getCumulativeSpineItemSize(i);
    if (targetSize <= cumulative) {
      targetSpineIndex = i;
      prevCumulative = (i > 0) ? epub->getCumulativeSpineItemSize(i - 1) : 0;
      break;
    }
  }

  const size_t cumulative = epub->getCumulativeSpineItemSize(targetSpineIndex);
  const size_t spineSize = (cumulative > prevCumulative) ? (cumulative - prevCumulative) : 0;
  pendingSpineProgress =
      (spineSize == 0) ? 0.0f : static_cast<float>(targetSize - prevCumulative) / static_cast<float>(spineSize);
  pendingSpineProgress = std::clamp(pendingSpineProgress, 0.0f, 1.0f);

  {
    RenderLock lock;
    clearDeferredReposition();
    currentSpineIndex = targetSpineIndex;
    nextPageNumber = 0;
    pendingPercentJump = true;
    section.reset();
  }
  requestUpdate();
}


bool EpubReaderActivity::exportEditsTsv() {
  if (!epub) return false;

  constexpr const char* EXPORT_DIR = "/edits";
  if (!Storage.exists(EXPORT_DIR) && !Storage.mkdir(EXPORT_DIR)) {
    LOG_ERR("ERS", "Failed to create edits export directory");
    return false;
  }

  const std::string bookPath = epub->getPath();
  const size_t slash = bookPath.find_last_of("/\\");
  const std::string bookFile = slash == std::string::npos ? bookPath : bookPath.substr(slash + 1);

  // Filename uses the full SD path so same-title test EPUBs in different
  // directories remain distinct:
  // /BOOX/test_v3/Michelangelo.epub -> /edits/BOOX_test_v3_Michelangelo.tsv
  std::string exportBase = bookPath;
  while (!exportBase.empty() && (exportBase.front() == '/' || exportBase.front() == '\\')) exportBase.erase(0, 1);
  const size_t dot = exportBase.find_last_of('.');
  if (dot != std::string::npos) exportBase.erase(dot);
  for (char& c : exportBase) {
    const unsigned char u = static_cast<unsigned char>(c);
    if (c == '/' || c == '\\' || c == '<' || c == '>' || c == ':' || c == '"' || c == '|' || c == '?' ||
        c == '*' || u < 32) {
      c = '_';
    }
  }
  if (exportBase.empty()) exportBase = "book";
  if (exportBase.size() > 180) exportBase.erase(0, exportBase.size() - 180);
  const std::string exportPath = std::string(EXPORT_DIR) + "/" + exportBase + ".tsv";

  auto field = [](std::string value) {
    for (char& c : value) {
      if (c == '\t' || c == '\r' || c == '\n') c = ' ';
    }
    return value;
  };

  auto xhtmlForSpine = [this](const int spine) -> std::string {
    if (!epub || spine < 0 || spine >= epub->getSpineItemsCount()) return {};
    return epub->getSpineItem(spine).href;
  };

  Storage.remove(exportPath.c_str());
  HalFile out;
  if (!Storage.openFileForWrite("ERS", exportPath, out)) {
    LOG_ERR("ERS", "Failed to open TSV export: %s", exportPath.c_str());
    return false;
  }

  auto writeText = [&](const std::string& text) -> bool {
    return text.empty() ||
           out.write(reinterpret_cast<const uint8_t*>(text.data()), text.size()) == static_cast<int>(text.size());
  };

  auto writeRow = [&](const uint32_t id, const char* type, const int spine, const uint32_t offset,
                      const uint16_t length, const std::string& original, const std::string& replacement) -> bool {
    std::string row;
    row.reserve(512 + original.size() + replacement.size());
    row += "1\t";
    row += std::to_string(id);
    row += "\t";
    row += type;
    row += "\t";
    row += field(bookPath);
    row += "\t";
    row += field(bookFile);
    row += "\t";
    row += field(epub->getTitle());
    row += "\t";
    row += field(epub->getAuthor());
    row += "\t";
    row += field(xhtmlForSpine(spine));
    row += "\t";
    row += std::to_string(spine);
    row += "\t";
    row += std::to_string(offset);
    row += "\t";
    row += std::to_string(length);
    row += "\t";
    row += field(original);
    row += "\t";
    row += field(replacement);
    // Reserved for later Calibre-assisted context verification. Intentionally
    // blank on-device to avoid rereading/inflating full XHTML only for export.
    row += "\t\t\n";
    return writeText(row);
  };

  // UTF-8 BOM: Windows Excel otherwise often opens a .tsv using the
  // current ANSI code page and displays Hungarian accented characters incorrectly.
  const uint8_t utf8Bom[] = {0xEF, 0xBB, 0xBF};
  bool ok = out.write(utf8Bom, sizeof(utf8Bom)) == static_cast<int>(sizeof(utf8Bom));

  const std::string header =
      "version\tid\ttype\tbook_path\tbook_file\tbook_title\tbook_author\txhtml\tspine\tvisible_offset\tlength\t"
      "original\treplacement\tcontext_before\tcontext_after\n";
  if (ok) ok = writeText(header);
  uint32_t id = 1;

  if (ok && highlightStore) {
    for (const auto& mark : highlightStore->items()) {
      if (!writeRow(id++, "MARK", mark.spineIndex, mark.visibleTextOffset, mark.length, mark.text, "")) {
        ok = false;
        break;
      }
    }
  }

  if (ok && textEditStore) {
    for (const auto& edit : textEditStore->items()) {
      if (!writeRow(id++, "EDIT", edit.spineIndex, edit.visibleTextOffset, edit.length, edit.originalText,
                    edit.replacementText)) {
        ok = false;
        break;
      }
    }
  }

  out.flush();
  out.close();
  if (!ok) {
    Storage.remove(exportPath.c_str());
    LOG_ERR("ERS", "TSV export failed: %s", exportPath.c_str());
    return false;
  }

  LOG_INF("ERS", "TSV edits exported to %s (%lu records)", exportPath.c_str(),
          static_cast<unsigned long>(id - 1));
  return true;
}

void EpubReaderActivity::onReaderMenuConfirm(EpubReaderMenuActivity::MenuAction action) {
  auto progressChangeResultHandler = [this](const ActivityResult& result) {
    loadCachedBookmarks();
    if (result.isCancelled) {
      openReaderMenu();
    } else {
      const auto& sync = std::get<ProgressChangeResult>(result.data);

      if (sync.hasVisibleTextOffset && sync.spineIndex >= 0 && sync.spineIndex < epub->getSpineItemsCount()) {
        RenderLock lock;
        clearDeferredReposition();
        if (section && currentSpineIndex == sync.spineIndex) {
          const auto page = section->getPageForVisibleTextOffset(sync.visibleTextOffset);
          section->currentPage = page.value_or(std::max(0, sync.page));
        } else {
          currentSpineIndex = sync.spineIndex;
          pendingOffsetJump = sync.visibleTextOffset;
          nextPageNumber = std::max(0, sync.page);
          section.reset();
        }
        requestUpdate();
        return;
      }

      int targetSpineIndex = sync.spineIndex;
      int targetPage = sync.page;
      const int activeTotalPages = section ? section->estimatedTotalPages() : 0;
      const bool cachedPageMatchesActiveSection = section && sync.totalPages > 0 &&
                                                  currentSpineIndex == sync.spineIndex && sync.page >= 0 &&
                                                  sync.page < sync.totalPages && activeTotalPages == sync.totalPages;

      if (!cachedPageMatchesActiveSection && sync.hasSavedProgress) {
        const int totalPages = section ? section->estimatedTotalPages() : cachedChapterTotalPageCount;
        CrossPointPosition fallback =
            ProgressMapper::toCrossPoint(epub, {sync.xpath, sync.percentage}, renderer, currentSpineIndex, totalPages);
        targetSpineIndex = fallback.spineIndex;
        targetPage = fallback.pageNumber;
      }

      RenderLock lock;
      clearDeferredReposition();

      if (currentSpineIndex != targetSpineIndex) {
        currentSpineIndex = targetSpineIndex;
        nextPageNumber = targetPage;
        section.reset();
      } else if (section && section->currentPage != targetPage) {
        const int clampedTargetPage = std::max(0, targetPage);
        section->currentPage = clampedTargetPage;
      } else if (!section) {
        nextPageNumber = targetPage;
      }
      requestUpdate();
    }
  };

  switch (action) {
    case EpubReaderMenuActivity::MenuAction::SELECT_CHAPTER: {
      const int spineIdx = currentSpineIndex;
      std::vector<EpubReaderChapterSelectionActivity::VirtualChapter> virtualChapters;

      // CPHUN-135r4k2: virtual chapter rows must not depend on the small
      // incremental-build watermark (section->pageCount). Use the Section's
      // estimated total instead, and store each target as relative progress.
      // The selected target is resolved after the normal full-build percent path,
      // then snapped to a real paragraph boundary.
      size_t spineBytes = 0;
      const auto spineItemForSplit = epub->getSpineItem(spineIdx);
      const bool oversizedSpine =
          epub->getItemSize(spineItemForSplit.href, &spineBytes) && spineBytes >= (128u * 1024u);

      if (section && oversizedSpine) {
        const uint16_t estimatedPages = section->estimatedTotalPages();
        if (estimatedPages >= 24) {
          int tocIndex = epub->getTocIndexForSpineIndex(spineIdx);
          std::string parentTitle = "Fejezet";
          if (tocIndex >= 0 && tocIndex < epub->getTocItemsCount()) {
            parentTitle = epub->getTocItem(tocIndex).title;
            if (parentTitle.empty()) parentTitle = "Fejezet";
          }

          constexpr uint16_t TARGET_PAGES = 12;
          constexpr uint16_t MIN_TAIL_PAGES = 6;
          uint16_t lastPermille = 0;
          int part = 2;

          for (uint16_t target = TARGET_PAGES;
               target + MIN_TAIL_PAGES < estimatedPages;
               target = static_cast<uint16_t>(target + TARGET_PAGES)) {
            uint16_t permille =
                static_cast<uint16_t>((static_cast<uint32_t>(target) * 1000u) / estimatedPages);
            permille = std::max<uint16_t>(1, std::min<uint16_t>(999, permille));
            if (permille <= lastPermille + 20) continue;

            EpubReaderChapterSelectionActivity::VirtualChapter v;
            v.title = parentTitle + " – " + std::to_string(part++);
            v.spineIndex = spineIdx;
            v.progressPermille = permille;
            virtualChapters.push_back(std::move(v));
            lastPermille = permille;
          }
        }
      }

      // Release the section while the chapter list is up (mirrors the
      // TEXT_SETTINGS path): picking a chapter resets it anyway, and its
      // tens-of-KB footprint is the difference between the chapter list
      // holding its CJK glyph arena (RAM-only repaints) and re-reading
      // glyphs from SD on every row step. Cancel restores via the same
      // cached-position rebuild TEXT_SETTINGS uses.
      {
        RenderLock lock;
        if (section) {
          rememberCurrentContentOffset();
          cachedSpineIndex = currentSpineIndex;
          cachedChapterTotalPageCount = section->pageCount;
          nextPageNumber = section->currentPage;
        }
        section.reset();
      }
      startActivityForResult(
          std::make_unique<EpubReaderChapterSelectionActivity>(renderer, mappedInput, epub, spineIdx,
                                                                std::move(virtualChapters)),
          [this](const ActivityResult& result) {
            if (result.isCancelled) {
              openReaderMenu();
              return;
            }
            const auto& chapterResult = std::get<ChapterResult>(result.data);
            RenderLock lock;
            clearDeferredReposition();
            currentSpineIndex = chapterResult.spineIndex;
            constexpr const char* VIRTUAL_PERCENT_PREFIX = "__cphun_pct_";
            constexpr const char* VIRTUAL_PAGE_PREFIX = "__cphun_page_";
            if (chapterResult.anchor.rfind(VIRTUAL_PERCENT_PREFIX, 0) == 0) {
              const int permille =
                  std::clamp(atoi(chapterResult.anchor.c_str() + strlen(VIRTUAL_PERCENT_PREFIX)), 1, 999);
              pendingAnchor.clear();
              pendingPageJump.reset();
              pendingSpineProgress = static_cast<float>(permille) / 1000.0f;
              pendingPercentJump = true;
              pendingVirtualChapterJump = true;
              nextPageNumber = 0;
            } else if (chapterResult.anchor.rfind(VIRTUAL_PAGE_PREFIX, 0) == 0) {
              const int page = std::max(0, atoi(chapterResult.anchor.c_str() + strlen(VIRTUAL_PAGE_PREFIX)));
              pendingAnchor.clear();
              pendingPageJump = static_cast<uint16_t>(std::min(page, static_cast<int>(UINT16_MAX - 1)));
              pendingVirtualChapterJump = false;
              nextPageNumber = page;
            } else {
              pendingPageJump.reset();
              pendingVirtualChapterJump = false;
              pendingAnchor = chapterResult.anchor;
              nextPageNumber = 0;
            }
            section.reset();
            requestUpdate();
          });
      break;
    }
    case EpubReaderMenuActivity::MenuAction::FOOTNOTES: {
      // CPHUN-135r4k2f5 SAFE: current-page data only. Do not start a
      // current-spine or whole-book XHTML scan from an interactive menu.
      if (currentPageFootnotes.empty()) {
        constexpr const char* LOG_DIR = "/logfiles";
        if (Storage.ensureDirectoryExists(LOG_DIR)) {
          const std::string path =
              std::string(LOG_DIR) + "/footnote_index_error_" + std::to_string(millis()) + ".txt";
          HalFile logFile;
          if (Storage.openFileForWrite("ERS", path, logFile)) {
            std::string log = "CrossPoint Footnote Index Diagnostic\nFormat version: 1\n\n";
            log += "Firmware: CPHUN-135R4K2F5-SAFE\n";
            log += "Book: " + epub->getTitle() + "\n";
            log += "EPUB: " + epub->getPath() + "\n";
            log += "Source spine: " + std::to_string(currentSpineIndex) + "\n";
            if (currentSpineIndex >= 0 && currentSpineIndex < epub->getSpineItemsCount()) {
              log += "Source XHTML: " + epub->getSpineItem(currentSpineIndex).href + "\n";
            }
            log += "Rendered page: " + std::to_string(section ? section->currentPage : 0) + "\n";
            log += "Current-page indexed footnotes: 0\n\n";
            log += "Error: CURRENT_PAGE_FOOTNOTE_INDEX_EMPTY\n";
            logFile.write(reinterpret_cast<const uint8_t*>(log.data()), log.size());
            logFile.flush();
            logFile.close();
          }
        }
      }
      openFootnotesList(false, true);
      break;
    }
    case EpubReaderMenuActivity::MenuAction::BOOK_DESCRIPTION: {
      startActivityForResult(
          std::make_unique<BookInfoActivity>(renderer, mappedInput, epub, BookInfoActivity::Page::Description),
          [this](const ActivityResult&) { openReaderMenu(true); });
      break;
    }
    case EpubReaderMenuActivity::MenuAction::BOOK_METADATA: {
      startActivityForResult(
          std::make_unique<BookInfoActivity>(renderer, mappedInput, epub, BookInfoActivity::Page::Metadata),
          [this](const ActivityResult&) { openReaderMenu(true); });
      break;
    }
    case EpubReaderMenuActivity::MenuAction::EXPORT_EDITS: {
      // Direct export: no confirmation popup.
      if (exportEditsTsv()) {
        showExportSuccess = true;
        exportSuccessTime = millis();
      }
      requestUpdate();
      break;
    }
    case EpubReaderMenuActivity::MenuAction::BOOK_COVER: {
      // CPHUN-111: dedicated 4-gray Floyd-Steinberg cover, prescaled with aspect
      // ratio preserved so neither dimension exceeds the physical X4 screen.
      // The generated bitmap is then shown 1:1; no post-dither downscale is needed.
      std::string coverPath = epub->getBookCoverViewBmpPath();
      if (!Storage.exists(coverPath.c_str())) epub->generateBookCoverViewBmp();
      if (Storage.exists(coverPath.c_str())) {
        startActivityForResult(std::make_unique<BmpViewerActivity>(renderer, mappedInput, coverPath, true),
                               [this](const ActivityResult&) { openReaderMenu(true); });
      } else {
        openReaderMenu();
      }
      break;
    }
    case EpubReaderMenuActivity::MenuAction::TEXT_SETTINGS: {
      const auto before = captureReaderLayout(buildViewportWidth, buildViewportHeight);
      startActivityForResult(std::make_unique<TextSettingsActivity>(renderer, mappedInput, &sdFontSystem.registry(),
                                                                    TextSettingsActivity::Tab::Family),
                             [this, before](const ActivityResult&) {
                               if (!readerLayoutMatches(before, buildViewportWidth, buildViewportHeight)) {
                                 RenderLock lock;
                                 if (section) {
                                   rememberCurrentContentOffset();
                                   cachedSpineIndex = currentSpineIndex;
                                   cachedChapterTotalPageCount = section->pageCount;
                                   nextPageNumber = section->currentPage;
                                 }
                                 section.reset();
                                 LOG_INF("ERS", "CPHUN-150: text settings changed; refreshing section");
                               } else {
                                 LOG_DBG("ERS", "CPHUN-150: text settings unchanged; retaining section");
                               }
                               openReaderMenu();
                             });
      break;
    }
    case EpubReaderMenuActivity::MenuAction::NIGHT_MODE:
      // Handled in-place by EpubReaderMenuActivity so its On/Off value updates
      // without closing the menu.
      break;
    case EpubReaderMenuActivity::MenuAction::FRONTLIGHT:
      // Handled in-place by EpubReaderMenuActivity using the live frontlight HAL.
      break;
    case EpubReaderMenuActivity::MenuAction::GO_TO_PERCENT: {
      float bookProgress = 0.0f;
      if (epub && epub->getBookSize() > 0 && section && section->pageCount > 0) {
        const float chapterProgress = static_cast<float>(section->currentPage) / static_cast<float>(section->pageCount);
        bookProgress = epub->calculateProgress(currentSpineIndex, chapterProgress) * 100.0f;
      }
      const int initialPercent = clampPercent(static_cast<int>(bookProgress + 0.5f));
      startActivityForResult(
          std::make_unique<EpubReaderPercentSelectionActivity>(renderer, mappedInput, initialPercent),
          [this](const ActivityResult& result) {
            if (result.isCancelled) {
              openReaderMenu();
            } else {
              jumpToPercent(std::get<PercentResult>(result.data).percent);
            }
          });
      break;
    }
    case EpubReaderMenuActivity::MenuAction::DICTIONARY: {
      openDictionaryWordSelect(WordSelectionMode::Dictionary);
      break;
    }
    case EpubReaderMenuActivity::MenuAction::HIGHLIGHT: {
      openDictionaryWordSelect(WordSelectionMode::Highlight);
      break;
    }
    case EpubReaderMenuActivity::MenuAction::EDIT: {
      openDictionaryWordSelect(WordSelectionMode::Edit);
      break;
    }
    case EpubReaderMenuActivity::MenuAction::MANUAL_DICTIONARY_SEARCH: {
      if (SETTINGS.dictionaryName[0] == '\0') {
        showDictionaryMessage = true;
        dictionaryMessageTime = millis();
        requestUpdate();
        break;
      }
      startActivityForResult(std::make_unique<ManualDictionarySearchActivity>(renderer, mappedInput),
                             [this](const ActivityResult&) { openReaderMenu(); });
      break;
    }
    case EpubReaderMenuActivity::MenuAction::DISPLAY_QR: {
      if (section && section->currentPage >= 0 && section->currentPage < section->pageCount) {
        std::string fullText = section->getTextFromSectionFile();
        if (!fullText.empty()) {
          startActivityForResult(std::make_unique<QrDisplayActivity>(renderer, mappedInput, fullText),
                                 [this](const ActivityResult&) { openReaderMenu(); });
          break;
        }
      }
      requestUpdate();
      break;
    }
    case EpubReaderMenuActivity::MenuAction::GO_HOME: {
      onGoHome();
      return;
    }
    case EpubReaderMenuActivity::MenuAction::REINDEX_CHAPTER: {
      if (!epub || currentSpineIndex < 0 || currentSpineIndex >= epub->getSpineItemsCount()) {
        break;
      }

      bool cleared = false;
      {
        RenderLock lock;
        if (section) {
          rememberCurrentContentOffset();
          cachedSpineIndex = currentSpineIndex;
          cachedChapterTotalPageCount = section->pageCount;
          nextPageNumber = section->currentPage;
          section->abandonBuild();
          cleared = section->clearCache();
          section.reset();
        } else {
          // A chapter may be temporarily unloaded when this action is invoked.
          Section chapterCache(epub, currentSpineIndex, renderer);
          cleared = chapterCache.clearCache();
        }

        if (cleared) {
          // Always rebuild the entire current chapter, even if the existing
          // HTML cache permits a very fast, normally invisible reflow.
          forceChapterReindex = true;
          buildPopupPending = false;
          pendingPercentJump = false;
        }
      }
      if (!cleared) {
        LOG_ERR("ERS", "CPHUN-151: failed to remove chapter page cache");
        showIndexBuildError();
        break;
      }

      LOG_INF("ERS", "CPHUN-151: reindexing current chapter %d", currentSpineIndex);
      requestUpdate();
      break;
    }
    case EpubReaderMenuActivity::MenuAction::DELETE_CACHE: {
      {
        RenderLock lock;
        if (epub && section) {
          const uint16_t backupSpine = currentSpineIndex;
          const uint16_t backupPage = section->currentPage;
          const uint16_t backupPageCount = section->pageCount;
          // Persist the newest position while the cache is still intact; the cache
          // clear below snapshots and restores progress.bin.
          if (!saveProgress(backupSpine, backupPage, backupPageCount)) {
            LOG_ERR("ERS", "Failed to save progress before cache clear");
          }
          section.reset();
          if (!epub->clearCachePreservingProgress()) {
            LOG_ERR("ERS", "Failed to clear current book cache");
          } else if (!epub->cacheReadyForCleanRebuild()) {
            LOG_ERR("ERS", "Current-book cache clear left stale rebuild artifacts");
          } else {
            LOG_DBG("ERS", "Current-book cache verified clean for rebuild");
          }
        }
      }
      onGoHome();
      return;
    }
    case EpubReaderMenuActivity::MenuAction::SCREENSHOT: {
      {
        RenderLock lock;
        pendingScreenshot = true;
      }
      requestUpdate();
      break;
    }
    case EpubReaderMenuActivity::MenuAction::SYNC: {
      launchKOReaderSync();
      break;
    }
    case EpubReaderMenuActivity::MenuAction::BOOKMARKS: {
      startActivityForResult(
          std::make_unique<EpubReaderBookmarksActivity>(renderer, mappedInput, epub, epub->getPath()),
          progressChangeResultHandler);
      break;
    }
    case EpubReaderMenuActivity::MenuAction::TOGGLE_BOOKMARK: {
      addBookmark();
      break;
    }
  }
}

bool EpubReaderActivity::launchKOReaderSync() {
  if (!KOREADER_STORE.hasCredentials()) return false;

  const int currentPage = section ? section->currentPage : nextPageNumber;
  const int totalPages = section ? section->estimatedTotalPages() : cachedChapterTotalPageCount;
  std::optional<uint16_t> paragraphIndex;
  if (section && currentPage >= 0 && currentPage < section->pageCount) {
    const uint16_t paragraphPage =
        currentPage > 0 ? static_cast<uint16_t>(currentPage - 1) : static_cast<uint16_t>(currentPage);
    if (const auto pIdx = section->getParagraphIndexForPage(paragraphPage)) {
      paragraphIndex = *pIdx;
    }
  }

  CrossPointPosition localPos = getCurrentPosition();
  SavedProgressPosition localKoPos = ProgressMapper::toSavedProgress(epub, localPos);
  const int tocIdx = epub->getTocIndexForSpineIndex(currentSpineIndex);
  std::string localChapterName = (tocIdx >= 0) ? epub->getTocItem(tocIdx).title : "";
  const std::string savedEpubPath = epub->getPath();

  if (!saveProgress(currentSpineIndex, currentPage, totalPages)) {
    LOG_ERR("KOSync", "Aborting sync because current progress could not be saved");
    pendingSyncSaveError = true;
    requestUpdate();
    return true;
  }

  LOG_DBG("KOSync", "Releasing epub for sync (heap before: %u)", (unsigned)ESP.getFreeHeap());
  {
    RenderLock lock;
    if (section) {
      nextPageNumber = section->currentPage;
    }
    ImageBlock::setExtractor(nullptr, nullptr);
    section.reset();
    epub.reset();
  }
  LOG_DBG("KOSync", "Epub released (heap after: %u)", (unsigned)ESP.getFreeHeap());

  activityManager.replaceActivity(std::make_unique<KOReaderSyncActivity>(
      renderer, mappedInput, savedEpubPath, currentSpineIndex, currentPage, totalPages, std::move(localKoPos),
      std::move(localChapterName), paragraphIndex));
  return true;
}

void EpubReaderActivity::applyOrientation(const uint8_t orientation) {
  if (SETTINGS.orientation == orientation) {
    return;
  }

  RenderLock lock(*this);
  if (section) {
    rememberCurrentContentOffset();
    cachedSpineIndex = currentSpineIndex;
    cachedChapterTotalPageCount = section->pageCount;
    nextPageNumber = section->currentPage;
  }

  SETTINGS.orientation = orientation;
  SETTINGS.saveToFile();
  ReaderUtils::applyOrientation(renderer, SETTINGS.orientation);
  section.reset();
}

void EpubReaderActivity::toggleAutoPageTurn(const uint8_t selectedPageTurnOption) {
  if (selectedPageTurnOption == 0 || selectedPageTurnOption >= std::size(PAGE_TURN_RATES)) {
    automaticPageTurnActive = false;
    return;
  }

  lastPageTurnTime = millis();
  pageTurnDuration = (1UL * 60 * 1000) / PAGE_TURN_RATES[selectedPageTurnOption];
  automaticPageTurnActive = true;

  const uint8_t statusBarHeight = UITheme::getInstance().getStatusBarHeight();
  if (statusBarHeight == 0 || statusBarHeight == UITheme::getInstance().getProgressBarHeight()) {
    RenderLock lock;
    if (section) {
      rememberCurrentContentOffset();
      cachedSpineIndex = currentSpineIndex;
      cachedChapterTotalPageCount = section->pageCount;
      nextPageNumber = section->currentPage;
    }
    section.reset();
  }
}

bool EpubReaderActivity::pageTurn(bool isForwardTurn) {
  if (!section) return false;
  {
    RenderLock lock;
    clearDeferredReposition();
  }
  if (isForwardTurn) {
    if (section->currentPage < section->pageCount - 1 || section->isBuilding()) {
      section->currentPage++;
      lastPageTurnTime = millis();
      return true;
    } else if (currentSpineIndex + 1 < epub->getSpineItemsCount()) {
      RenderLock lock;
      nextPageNumber = 0;
      currentSpineIndex++;
      advancePastSkippedSpines(true);
      section.reset();
      lastPageTurnTime = millis();
      return true;
    } else {
      currentSpineIndex = epub->getSpineItemsCount();
      lastPageTurnTime = millis();
      return true;
    }
  } else {
    if (section->currentPage > 0) {
      section->currentPage--;
      lastPageTurnTime = millis();
      return true;
    } else if (currentSpineIndex > 0) {
      RenderLock lock;
      nextPageNumber = 0;
      pendingPageJump = std::numeric_limits<uint16_t>::max();
      currentSpineIndex--;
      advancePastSkippedSpines(false);
      section.reset();
      lastPageTurnTime = millis();
      return true;
    }
  }
  return false;
}

bool EpubReaderActivity::skipPages(int amount) {
  if (!section) return false;
  if (amount > 0) {
    RenderLock lock;
    nextPageNumber = 0;
    currentSpineIndex++;
    advancePastSkippedSpines(true);
    section.reset();
    return true;
  } else {
    if (section->currentPage > 0) {
      section->currentPage = 0;
      return true;
    } else if (currentSpineIndex > 0) {
      RenderLock lock;
      nextPageNumber = 0;
      currentSpineIndex--;
      advancePastSkippedSpines(false);
      section.reset();
      return true;
    }
  }
  return false;
}

bool EpubReaderActivity::isAtEndOfBook() const { return epub && currentSpineIndex >= epub->getSpineItemsCount(); }

void EpubReaderActivity::onReturnFromEndOfBook() {
  if (epub && epub->getSpineItemsCount() > 0) {
    currentSpineIndex = epub->getSpineItemsCount() - 1;
    nextPageNumber = 0;
    pendingPageJump = std::numeric_limits<uint16_t>::max();
  }
}

bool EpubReaderActivity::skipLoopDelay() {
  return section && section->isBuilding() && !buildHeapPaused &&
         (section->isPartial() || static_cast<int>(section->pageCount) < section->currentPage + BUILD_WINDOW_AHEAD);
}

void EpubReaderActivity::renderBook() {
  if (!epub) return;
  if (indexErrorDialog != IndexErrorDialog::None) {
    renderIndexErrorDialog();
    return;
  }

  const auto showPendingSyncSaveError = [this]() {
    if (!pendingSyncSaveError) return;
    pendingSyncSaveError = false;
    GUI.drawPopup(renderer, tr(STR_SAVE_PROGRESS_FAILED));
  };

  const auto showBuildError = [this]() { showIndexBuildError(); };

  if (currentSpineIndex < 0) currentSpineIndex = 0;
  if (currentSpineIndex > epub->getSpineItemsCount()) currentSpineIndex = epub->getSpineItemsCount();
  advancePastSkippedSpines(true);

  if (currentSpineIndex == epub->getSpineItemsCount()) {
    return;
  }

  int orientedMarginTop, orientedMarginRight, orientedMarginBottom, orientedMarginLeft;
  renderer.getOrientedViewableTRBL(&orientedMarginTop, &orientedMarginRight, &orientedMarginBottom,
                                   &orientedMarginLeft);
  const int verticalScreenMargin =
      SETTINGS.screenMargin == 5 ? 4 : std::max(0, static_cast<int>(SETTINGS.screenMargin) - 6);
  orientedMarginTop += verticalScreenMargin;
  orientedMarginLeft += SETTINGS.screenMargin;
  orientedMarginRight += SETTINGS.screenMargin;

  const uint8_t statusBarHeight = UITheme::getInstance().getStatusBarHeight();

  if (automaticPageTurnActive &&
      (statusBarHeight == 0 || statusBarHeight == UITheme::getInstance().getProgressBarHeight())) {
    orientedMarginBottom +=
        std::max(verticalScreenMargin,
                 static_cast<int>(statusBarHeight + UITheme::getInstance().getMetrics().statusBarVerticalMargin));
  } else {
    orientedMarginBottom += std::max(verticalScreenMargin, static_cast<int>(statusBarHeight));
  }

  const uint16_t viewportWidth = renderer.getScreenWidth() - orientedMarginLeft - orientedMarginRight;
  const uint16_t viewportHeight = renderer.getScreenHeight() - orientedMarginTop - orientedMarginBottom;
  buildViewportWidth = viewportWidth;
  buildViewportHeight = viewportHeight;

  const ReaderRenderSpec renderSpec = SETTINGS.readerRenderSpec(viewportWidth, viewportHeight);

  if (!section) {
    const auto filepath = epub->getSpineItem(currentSpineIndex).href;
    LOG_DBG("ERS", "Loading file: %s, index: %d", filepath.c_str(), currentSpineIndex);
    section = std::unique_ptr<Section>(new Section(epub, currentSpineIndex, renderer));
    partialRebuildStartFailed = false;

    const bool cacheLoaded = section->loadSectionFile(renderSpec);
    if (cacheLoaded) {
      cachedChapterTotalPageCount = 0;
      cachedVisibleTextOffset.reset();
    }
    const bool cacheComplete = cacheLoaded && !section->isPartial();
    const bool explicitOffsetJump = pendingOffsetJump.has_value();
    const std::optional<uint32_t> offsetJump =
        explicitOffsetJump ? pendingOffsetJump
        : (pendingPageJump.has_value() || !pendingAnchor.empty() || currentSpineIndex != cachedSpineIndex)
            ? std::nullopt
            : cachedVisibleTextOffset;
    if (!cacheComplete) {
      if (section->isPartial()) {
        LOG_DBG("ERS", "Partial cache found (%d pages), resuming build...", section->pageCount);
      } else {
        LOG_DBG("ERS", "Cache not found, building...");
      }

      const bool needsFullBuild = pendingPercentJump || forceChapterReindex;
      if (needsFullBuild) {
        GUI.drawPopup(renderer, tr(STR_INDEXING));
        pagesUntilFullRefresh = 1;
        const auto popupFn = [this]() {
          if (renderer.hasFrameBuffer()) GUI.drawPopup(renderer, tr(STR_INDEXING));
        };
        GfxRenderer::FrameBufferLoan loan(renderer);
        if (!section->createSectionFile(renderSpec, popupFn)) {
          LOG_ERR("ERS", "Failed to persist page data to SD");
          section.reset();
          loan.end();
          showBuildError();
          return;
        }
        loan.end();
        forceChapterReindex = false;
      } else {
        const int target = pendingPageJump.has_value() ? *pendingPageJump : (nextPageNumber < 0 ? 0 : nextPageNumber);
        const bool anchorJump = !pendingAnchor.empty();

        if (section->isPartial() &&
            (anchorJump ? section->getPageForAnchor(pendingAnchor).has_value()
                        : target + PARTIAL_REBUILD_START_MARGIN < static_cast<int>(section->pageCount))) {
          LOG_DBG("ERS", "Partial covers target %d of %d; deferring extension build", target, section->pageCount);
        } else {
          const size_t spineBytes =
              epub->getCumulativeSpineItemSize(currentSpineIndex) -
              (currentSpineIndex > 0 ? epub->getCumulativeSpineItemSize(currentSpineIndex - 1) : 0);
          const bool willInflate = !section->hasHtmlCache();
          bool showPopup;
          if (anchorJump) {
            showPopup = !section->findAnchor(pendingAnchor).has_value() && spineBytes > BUILD_POPUP_BYTE_THRESHOLD;
          } else {
            const bool targetAvailable = target < static_cast<int>(section->pageCount);
            showPopup = !targetAvailable && ((spineBytes > BUILD_POPUP_BYTE_THRESHOLD && willInflate) ||
                                             target > BUILD_POPUP_PAGE_THRESHOLD);
          }
          if (showPopup) {
            GUI.drawPopup(renderer, tr(STR_INDEXING));
            pagesUntilFullRefresh = 1;
          }
          buildPopupPending = !showPopup;
          const unsigned long buildStartMs = millis();
          bool started;
          {
            GfxRenderer::FrameBufferLoan loan(renderer);
            started = section->startBuild(renderSpec, [this] { showBuildPopup(renderer, pagesUntilFullRefresh); });
          }
          if (!started) {
            LOG_ERR("ERS", "Failed to start section build");
            section.reset();
            buildPopupPending = false;
            showBuildError();
            return;
          }
          while (!section->isBuildComplete() &&
                 (anchorJump               ? !section->findAnchor(pendingAnchor)
                  : offsetJump.has_value() ? !section->buildReachedVisibleTextOffset(*offsetJump)
                                           : static_cast<int>(section->pageCount) <= target)) {
            if (buildPopupPending && millis() - buildStartMs >= BUILD_POPUP_DEADLINE_MS) {
              showBuildPopup(renderer, pagesUntilFullRefresh);
            }
            if (!section->buildSomeMore(BUILD_PAGES_PER_CHUNK)) {
              LOG_ERR("ERS", "Failed during incremental section build");
              section.reset();
              buildPopupPending = false;
              showBuildError();
              return;
            }
          }
          buildPopupPending = false;
        }
      }
    } else {
      LOG_DBG("ERS", "Cache found, skipping build...");
    }

    if (pendingPageJump.has_value()) {
      section->currentPage = *pendingPageJump;
      pendingPageJump.reset();
    } else {
      section->currentPage = nextPageNumber;
      if (section->currentPage < 0) section->currentPage = 0;
    }

    if (offsetJump.has_value()) {
      if (const auto offsetPage = section->getPageForVisibleTextOffset(*offsetJump)) {
        section->currentPage = *offsetPage;
        clearDeferredReposition();
      }
    }
    if (explicitOffsetJump) {
      clearDeferredReposition();
    }
    pendingOffsetJump.reset();

    if (!pendingAnchor.empty()) {
      const auto page = section->findAnchor(pendingAnchor);
      if (page) {
        section->currentPage = *page;
        LOG_DBG("ERS", "Resolved anchor '%s' to page %d", pendingAnchor.c_str(), *page);
      }
      pendingAnchor.clear();
    }

    if (pendingPercentJump && section->pageCount > 0) {
      int newPage = static_cast<int>(pendingSpineProgress * static_cast<float>(section->pageCount));
      if (newPage >= section->pageCount) newPage = section->pageCount - 1;

      if (pendingVirtualChapterJump && newPage > 0) {
        constexpr int PARAGRAPH_SEARCH_PAGES = 12;
        const int searchEnd =
            std::min<int>(section->pageCount - 1, newPage + PARAGRAPH_SEARCH_PAGES);
        for (int page = newPage; page <= searchEnd; ++page) {
          const auto here = section->getParagraphIndexForPage(static_cast<uint16_t>(page));
          const auto prev = section->getParagraphIndexForPage(static_cast<uint16_t>(page - 1));
          if (here && prev && *here != *prev) {
            newPage = page;
            break;
          }
        }
      }

      section->currentPage = newPage;
      pendingPercentJump = false;
      pendingVirtualChapterJump = false;
    }
  }

  if (section->isPartial() && section->currentPage >= static_cast<int>(section->pageCount)) {
    GUI.drawPopup(renderer, tr(STR_INDEXING));
    pagesUntilFullRefresh = 1;
  }
  while (section->isPartial() && section->currentPage >= static_cast<int>(section->pageCount)) {
    if (!section->isBuilding() && !section->startBuild(renderSpec)) {
      LOG_ERR("ERS", "Failed to start partial extension build");
      section.reset();
      showBuildError();
      return;
    }
    while (!section->isBuildComplete() && section->currentPage >= static_cast<int>(section->pageCount)) {
      if (!section->buildSomeMore(BUILD_PAGES_PER_CHUNK)) {
        LOG_ERR("ERS", "Failed during incremental section build");
        section.reset();
        showBuildError();
        return;
      }
    }
  }
  if (section->isBuilding()) {
    while (!section->isBuildComplete() && section->currentPage >= static_cast<int>(section->pageCount)) {
      if (!section->buildSomeMore(BUILD_PAGES_PER_CHUNK)) {
        LOG_ERR("ERS", "Failed during incremental section build");
        section.reset();
        showBuildError();
        return;
      }
    }
  }

  if (!section->isBuilding() && section->pageCount > 0 &&
      section->currentPage >= static_cast<int>(section->pageCount)) {
    section->currentPage = section->pageCount - 1;
  }

  applyDeferredReposition();

  renderer.clearScreen();

  if (section->pageCount == 0) {
    LOG_DBG("ERS", "No pages to render");
    renderer.drawCenteredText(UI_12_FONT_ID, 300, tr(STR_EMPTY_CHAPTER), true, EpdFontFamily::BOLD);
    if (!fullScreenCover) renderStatusBar();
    renderer.displayBuffer();
    automaticPageTurnActive = false;
    showPendingSyncSaveError();
    return;
  }

  if (section->currentPage < 0 || section->currentPage >= section->pageCount) {
    LOG_DBG("ERS", "Page out of bounds: %d (max %d)", section->currentPage, section->pageCount);
    renderer.drawCenteredText(UI_12_FONT_ID, 300, tr(STR_OUT_OF_BOUNDS), true, EpdFontFamily::BOLD);
    if (!fullScreenCover) renderStatusBar();
    renderer.displayBuffer();
    automaticPageTurnActive = false;
    showPendingSyncSaveError();
    return;
  }

  updateBookmarkFlag();

  {
    auto p = section->loadPage(section->currentPage);
    if (!p) {
      LOG_ERR("ERS", "Failed to load page from SD - clearing section cache");
      automaticPageTurnActive = false;
      const bool giveUp = ++pageLoadRetryCount > MAX_PAGE_LOAD_RETRIES;
      section->abandonBuild();
      section->clearCache();
      section.reset();
      if (giveUp) {
        LOG_ERR("ERS", "Page load retry limit reached, aborting");
        pageLoadRetryCount = 0;
        renderer.clearScreen();
        renderer.drawCenteredText(UI_12_FONT_ID, 300, tr(STR_PAGE_LOAD_ERROR), true, EpdFontFamily::BOLD);
        renderer.displayBuffer();
        showPendingSyncSaveError();
        return;
      }
      requestUpdate();
      showPendingSyncSaveError();
      return;
    }
    pageLoadRetryCount = 0;

    currentPageVisibleOffset = p->visibleTextOffset;
    currentPageFootnotes = std::move(p->footnotes);
    if (footnoteTextCacheSpine_ != currentSpineIndex || footnoteTextCachePage_ != section->currentPage) {
      footnoteTextCacheIndexes_.fill(-1);
      for (auto& text : footnoteTextCacheTexts_) text.clear();
      footnoteTextCacheSpine_ = currentSpineIndex;
      footnoteTextCachePage_ = section->currentPage;
    }

    const auto start = millis();
    renderContents(std::move(p), orientedMarginTop, orientedMarginRight, orientedMarginBottom, orientedMarginLeft);
    LOG_DBG("ERS", "Rendered page in %dms", millis() - start);
    lastRenderCompleteMs = millis();
  }

  if (currentSpineIndex != lastSavedSpineIndex || section->currentPage != lastSavedPage ||
      section->pageCount != lastSavedPageCount) {
    if (saveProgress(currentSpineIndex, section->currentPage, section->estimatedTotalPages())) {
      lastSavedSpineIndex = currentSpineIndex;
      lastSavedPage = section->currentPage;
      lastSavedPageCount = section->estimatedTotalPages();
    }
  }

  showPendingSyncSaveError();

  if (pendingScreenshot) {
    pendingScreenshot = false;
    ScreenshotUtil::takeScreenshot(renderer);
  }

  if (showBookmarkMessage) {
    GUI.drawPopup(renderer, bookmarkRemoved ? tr(STR_BOOKMARK_REMOVED) : tr(STR_BOOKMARK_ADDED));
  }

  if (showDictionaryMessage) {
    GUI.drawPopup(renderer, tr(STR_DICT_NO_DICT_SET));
  }
  if (showExportSuccess) {
    GUI.drawPopup(renderer, "Sikeres exportálás.");
  }
}

void EpubReaderActivity::onEndOfBookRendered() {
  automaticPageTurnActive = false;
  if (pendingSyncSaveError) {
    pendingSyncSaveError = false;
    GUI.drawPopup(renderer, tr(STR_SAVE_PROGRESS_FAILED));
  }
}

bool EpubReaderActivity::applyDeferredReposition() {
  if ((!cachedVisibleTextOffset.has_value() && cachedChapterTotalPageCount == 0) || !section || section->isBuilding()) {
    return false;
  }
  bool changed = false;
  if (currentSpineIndex == cachedSpineIndex) {
    int newPage = section->currentPage;
    bool mappedOffset = false;
    if (cachedVisibleTextOffset.has_value()) {
      if (const auto offsetPage = section->getPageForVisibleTextOffset(*cachedVisibleTextOffset)) {
        newPage = *offsetPage;
        mappedOffset = true;
      }
    }
    if (!mappedOffset && cachedChapterTotalPageCount > 0 && section->pageCount != cachedChapterTotalPageCount) {
      const float progress = static_cast<float>(section->currentPage) / static_cast<float>(cachedChapterTotalPageCount);
      newPage = static_cast<int>(progress * static_cast<float>(section->pageCount));
    }
    if (newPage < 0) newPage = 0;
    if (section->pageCount > 0 && newPage >= static_cast<int>(section->pageCount)) {
      newPage = section->pageCount - 1;
    }
    if (newPage != section->currentPage) {
      section->currentPage = newPage;
      changed = true;
    }
  }
  clearDeferredReposition();
  return changed;
}

void EpubReaderActivity::clearDeferredReposition() {
  cachedChapterTotalPageCount = 0;
  cachedVisibleTextOffset.reset();
}

bool EpubReaderActivity::saveProgress(int spineIndex, int currentPage, int pageCount) {
  std::optional<uint32_t> offset;
  if (section && spineIndex == currentSpineIndex && currentPage >= 0 && currentPage < section->pageCount) {
    offset = (currentPage == section->currentPage && currentPageVisibleOffset.has_value())
                 ? currentPageVisibleOffset
                 : section->getVisibleTextOffsetForPage(static_cast<uint16_t>(currentPage));
  }
  return EpubReaderUtils::saveProgress(*epub, spineIndex, currentPage, pageCount, offset);
}

void EpubReaderActivity::rememberCurrentContentOffset() {
  cachedVisibleTextOffset.reset();
  if (section && section->currentPage >= 0 && section->currentPage < section->pageCount) {
    cachedVisibleTextOffset = section->getVisibleTextOffsetForPage(static_cast<uint16_t>(section->currentPage));
  }
}

void EpubReaderActivity::renderContents(std::unique_ptr<Page> page, const int orientedMarginTop,
                                        const int orientedMarginRight, const int orientedMarginBottom,
                                        const int orientedMarginLeft) {
  const auto t0 = millis();
  const int fontId = SETTINGS.getReaderFontId();
  const bool fullScreenCover = page->isFullScreenCover();

  struct PxcSlotGuard {
    ~PxcSlotGuard() { ImageBlock::releaseRenderCache(); }
  } pxcSlotGuard;

  auto* fcm = renderer.getFontCacheManager();
  auto scope = fcm->createPrewarmScope();
  page->render(renderer, fontId, orientedMarginLeft, orientedMarginTop);
  // Scan the status bar too: a CJK book/chapter title redirected to the SD
  // fallback font joins the page's single batch prewarm instead of triggering
  // its own SD pass after the scope ends.
  if (!fullScreenCover) renderStatusBar();
  scope.endScanAndPrewarm();
  const auto tPrewarm = millis();

  const bool pageHasImages = page->hasImages();
  const bool pageHasImagesNeedingDecode = pageHasImages && page->hasImagesNeedingDecode();
  const bool manualRefreshPending = forcedRefreshPending;
  forcedRefreshPending = false;
  const bool cleanImageBasePending = manualRefreshPending || pagesUntilFullRefresh <= 1;
  const bool needsTextGrayscale = SETTINGS.textAntiAliasing;
  const bool needsAnyGrayscale = needsTextGrayscale || pageHasImages;
  const auto absoluteCaps = renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute);
  // CPHUN-182: X4/SSD1677 image pages use the factory-quality Absolute path.
  // Absolute supplies both complete gray planes and activates the panel only
  // once, after every image/text/status-bar pixel has been staged.
  const bool absoluteImagePage =
      pageHasImages && SETTINGS.imageRendering == CrossPointSettings::IMAGES_DISPLAY &&
      absoluteCaps.supported() && absoluteCaps.stripUploads;
  const bool tiledGrayscale = needsAnyGrayscale && renderer.supportsStripGrayscale();
  // Paper Mono only (no other panel combines): defer the B/W base activation so
  // the gray planes join it in a single waveform. Displaying the base
  // separately makes the gray pass re-drive the whole text body — a visible
  // flash on every AA page.
  const bool combinedGrayscaleBase = tiledGrayscale && !pageHasImages && renderer.combinesGrayscaleBase();
  const bool overlapRefresh = tiledGrayscale && renderer.supportsAsyncRefresh() && !pageHasImages;
  auto renderGrayscalePass = [&]() {
    if (needsTextGrayscale) {
      page->render(renderer, fontId, orientedMarginLeft, orientedMarginTop);
    } else {
      page->renderImages(renderer, fontId, orientedMarginLeft, orientedMarginTop);
    }
  };

  if (pageHasImagesNeedingDecode && !absoluteImagePage) {
    // Legacy fallback only. CPHUN-182 Absolute pages decode/cache off-screen
    // and never expose the placeholder as an intermediate panel refresh.
    page->renderWithImagePlaceholders(renderer, fontId, orientedMarginLeft, orientedMarginTop);
    if (!fullScreenCover) renderStatusBar();
    renderer.displayBuffer(HalDisplay::FAST_REFRESH);
    renderer.clearScreen();
  }

  if (textEditStore) {
    TextEditRenderer::renderBackground(renderer, *page, fontId, orientedMarginLeft, orientedMarginTop,
                                       currentSpineIndex, *textEditStore);
  }
  page->render(renderer, fontId, orientedMarginLeft, orientedMarginTop);
  if (!fullScreenCover) renderStatusBar();
  const auto tBwRender = millis();
  if (highlightStore) {
    HighlightRenderer::render(renderer, *page, fontId, orientedMarginLeft, orientedMarginTop,
                              currentSpineIndex, *highlightStore);
  }


  if (absoluteImagePage) {
    // CPHUN-182 intentionally does NOT refresh the B/W base here. The complete
    // page is already in the framebuffer; Absolute staging below starts from
    // that crisp B/W page, overlays image grays (and text AA when enabled),
    // then performs one factory Atkinson activation.
  } else if (pageHasImages) {
    // Legacy fallback for panels without Absolute grayscale.
    renderer.displayBuffer(cleanImageBasePending ? HalDisplay::HALF_REFRESH : HalDisplay::FAST_REFRESH);
    pagesUntilFullRefresh = 1;
  } else if (combinedGrayscaleBase) {
    // Stash the base without activating; displayGrayBuffer() below commits
    // base + grays as one waveform.
    ReaderUtils::displayBaseWithRefreshCycle(renderer, pagesUntilFullRefresh);
  } else {
    ReaderUtils::displayWithRefreshCycle(renderer, pagesUntilFullRefresh, overlapRefresh);
  }
  const auto tDisplay = millis();

  if (absoluteImagePage) {
    constexpr int STRIP_ROWS = 80;
    const int gh = renderer.getDisplayHeight();
    const int gwBytes = renderer.getDisplayWidthBytes();
    auto scratch = makeUniqueNoThrow<uint8_t[]>(static_cast<size_t>(gwBytes) * STRIP_ROWS);

    if (!scratch) {
      // Keep a visible page even under severe heap pressure. This is the only
      // CPHUN-182 fallback that can still show the legacy two-stage behavior.
      LOG_ERR("ERS", "CPHUN-182 OOM: Absolute strip scratch (%d bytes); using legacy image grayscale",
              gwBytes * STRIP_ROWS);
      renderer.displayBuffer(cleanImageBasePending ? HalDisplay::HALF_REFRESH : HalDisplay::FAST_REFRESH);
      pagesUntilFullRefresh = 1;
    } else if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute,
                                               cleanImageBasePending ? HalDisplay::HALF_REFRESH
                                                                     : HalDisplay::FAST_REFRESH)) {
      LOG_ERR("ERS", "CPHUN-182: Absolute grayscale start failed; using legacy image grayscale");
      renderer.displayBuffer(cleanImageBasePending ? HalDisplay::HALF_REFRESH : HalDisplay::FAST_REFRESH);
      pagesUntilFullRefresh = 1;
    } else {
      const uint8_t* bwBase = renderer.getFrameBuffer();

      auto stagePlane = [&](const bool lsbPlane) {
        renderer.setRenderMode(lsbPlane ? GfxRenderer::GRAYSCALE_LSB : GfxRenderer::GRAYSCALE_MSB);
        for (int y = 0; y < gh; y += STRIP_ROWS) {
          const int rows = (gh - y < STRIP_ROWS) ? (gh - y) : STRIP_ROWS;
          // Public Absolute encoding uses the same 1-bit values for pure B/W
          // (black=00, white=11), so the finished B/W page is the correct seed
          // for both planes. Images then overwrite every pixel in their rect.
          memcpy(scratch.get(), bwBase + static_cast<size_t>(y) * gwBytes,
                 static_cast<size_t>(rows) * gwBytes);
          renderer.beginStripTarget(scratch.get(), y, rows);
          if (needsTextGrayscale) {
            page->render(renderer, fontId, orientedMarginLeft, orientedMarginTop);
            if (!fullScreenCover) renderStatusBar();
          } else {
            page->renderImages(renderer, fontId, orientedMarginLeft, orientedMarginTop);
          }
          renderer.endStripTarget();
          renderer.writeGrayscalePlaneStrip(lsbPlane, scratch.get(), y, rows);
        }
      };

      const auto tAbsStart = millis();
      stagePlane(true);
      const auto tAbsLsb = millis();
      stagePlane(false);
      const auto tAbsMsb = millis();

      // Do not switch back to BW before displayGrayBuffer(): CPHUN-177 uses
      // that transition as an abort/cleanup guard for an unfinished Absolute
      // pass. The final factory waveform is the page's sole visible refresh.
      renderer.displayGrayBuffer();
      const auto tAbsDisplay = millis();
      renderer.setRenderMode(GfxRenderer::BW);
      renderer.cleanupGrayscaleWithFrameBuffer();
      pagesUntilFullRefresh = 1;
      const auto tAbsEnd = millis();

      LOG_DBG("ERS",
              "CPHUN-182 Absolute image page: prewarm=%lums bw_render=%lums stage_lsb=%lums "
              "stage_msb=%lums display=%lums cleanup=%lums total=%lums",
              tPrewarm - t0, tBwRender - tPrewarm, tAbsLsb - tAbsStart, tAbsMsb - tAbsLsb,
              tAbsDisplay - tAbsMsb, tAbsEnd - tAbsDisplay, tAbsEnd - t0);
      return;
    }
  }

  if (tiledGrayscale) {
    constexpr int STRIP_ROWS = 80;
    const int gh = renderer.getDisplayHeight();
    const int gwBytes = renderer.getDisplayWidthBytes();
    const size_t planeBytes = static_cast<size_t>(gwBytes) * gh;

    auto renderPlaneToBuffer = [&](const bool lsbPlane, uint8_t* buf) {
      renderer.setRenderMode(lsbPlane ? GfxRenderer::GRAYSCALE_LSB : GfxRenderer::GRAYSCALE_MSB);
      for (int y = 0; y < gh; y += STRIP_ROWS) {
        const int rows = (gh - y < STRIP_ROWS) ? (gh - y) : STRIP_ROWS;
        renderer.beginStripTarget(buf + static_cast<size_t>(y) * gwBytes, y, rows);
        renderer.clearScreen(0x00);
        renderGrayscalePass();
        renderer.endStripTarget();
      }
    };

    constexpr size_t PLANE_BUF_HEADROOM = 60000;
    constexpr size_t PLANE_BUF_MAX_ALLOC_RESERVE = 16 * 1024;
    const auto planeBufFits = [planeBytes] {
      return ESP.getFreeHeap() >= planeBytes + PLANE_BUF_HEADROOM &&
             ESP.getMaxAllocHeap() >= planeBytes + PLANE_BUF_MAX_ALLOC_RESERVE;
    };
    auto lsbPlaneBuf = (overlapRefresh && planeBufFits()) ? makeUniqueNoThrow<uint8_t[]>(planeBytes) : nullptr;
    auto msbPlaneBuf = (lsbPlaneBuf && planeBufFits()) ? makeUniqueNoThrow<uint8_t[]>(planeBytes) : nullptr;

    if (lsbPlaneBuf) {
      renderPlaneToBuffer(true, lsbPlaneBuf.get());
      if (msbPlaneBuf) renderPlaneToBuffer(false, msbPlaneBuf.get());
      const auto tGrayRender = millis();

      renderer.waitRefreshComplete();
      const auto tWait = millis();

      renderer.writeGrayscalePlaneStrip(true, lsbPlaneBuf.get(), 0, gh);
      if (msbPlaneBuf) {
        renderer.writeGrayscalePlaneStrip(false, msbPlaneBuf.get(), 0, gh);
      } else {
        renderPlaneToBuffer(false, lsbPlaneBuf.get());
        renderer.writeGrayscalePlaneStrip(false, lsbPlaneBuf.get(), 0, gh);
      }
      const auto tGrayWrite = millis();

      renderer.setRenderMode(GfxRenderer::BW);
      renderer.displayGrayBuffer();
      const auto tGrayDisplay = millis();

      renderer.cleanupGrayscaleWithFrameBuffer();
      const auto tEnd = millis();

      LOG_DBG("ERS",
              "Page render (tiled async): prewarm=%lums bw_render=%lums display=%lums gray_render=%lums "
              "wait=%lums gray_write=%lums gray_display=%lums cleanup=%lums total=%lums (planes buffered: %d)",
              tPrewarm - t0, tBwRender - tPrewarm, tDisplay - tBwRender, tGrayRender - tDisplay, tWait - tGrayRender,
              tGrayWrite - tWait, tGrayDisplay - tGrayWrite, tEnd - tGrayDisplay, tEnd - t0, msbPlaneBuf ? 2 : 1);
    } else {
      auto scratch = makeUniqueNoThrow<uint8_t[]>(static_cast<size_t>(gwBytes) * STRIP_ROWS);
      renderer.waitRefreshComplete();
      if (!scratch) {
        LOG_ERR("ERS", "OOM: grayscale strip scratch (%d bytes); skipping AA this page", gwBytes * STRIP_ROWS);
        if (overlapRefresh || combinedGrayscaleBase) {
          // The BW refresh ran the shadow-free async path, so controller RAM's
          // differential baseline was never rebuilt. Even with AA skipped it must
          // be re-synced from the intact BW framebuffer, or the next differential
          // update diffs against stale contents. On the combined-base path the
          // base activation is still deferred; this cleanup commits it so the
          // page reaches the panel even without its grays.
          renderer.cleanupGrayscaleWithFrameBuffer();
        }
      } else {
        renderer.setRenderMode(GfxRenderer::GRAYSCALE_LSB);
        for (int y = 0; y < gh; y += STRIP_ROWS) {
          const int rows = (gh - y < STRIP_ROWS) ? (gh - y) : STRIP_ROWS;
          renderer.beginStripTarget(scratch.get(), y, rows);
          renderer.clearScreen(0x00);
          renderGrayscalePass();
          renderer.endStripTarget();
          renderer.writeGrayscalePlaneStrip(true, scratch.get(), y, rows);
        }
        const auto tGrayLsb = millis();

        renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
        for (int y = 0; y < gh; y += STRIP_ROWS) {
          const int rows = (gh - y < STRIP_ROWS) ? (gh - y) : STRIP_ROWS;
          renderer.beginStripTarget(scratch.get(), y, rows);
          renderer.clearScreen(0x00);
          renderGrayscalePass();
          renderer.endStripTarget();
          renderer.writeGrayscalePlaneStrip(false, scratch.get(), y, rows);
        }
        const auto tGrayMsb = millis();

        renderer.setRenderMode(GfxRenderer::BW);
        renderer.displayGrayBuffer();
        const auto tGrayDisplay = millis();

        renderer.cleanupGrayscaleWithFrameBuffer();
        const auto tCleanup = millis();

        const auto tEnd = millis();
        LOG_DBG("ERS",
                "Page render (tiled): prewarm=%lums bw_render=%lums display=%lums gray_lsb=%lums "
                "gray_msb=%lums gray_display=%lums cleanup=%lums total=%lums",
                tPrewarm - t0, tBwRender - tPrewarm, tDisplay - tBwRender, tGrayLsb - tDisplay, tGrayMsb - tGrayLsb,
                tGrayDisplay - tGrayMsb, tCleanup - tGrayDisplay, tEnd - t0);
      }
    }
  } else {
    if (needsAnyGrayscale) {
      if (!renderer.storeBwBuffer()) {
        LOG_ERR("ERS", "Failed to store BW buffer for grayscale render; skipping grayscale this page");
        return;
      }
      const auto tBwStore = millis();

      renderer.clearScreen(0x00);
      renderer.setRenderMode(GfxRenderer::GRAYSCALE_LSB);
      renderGrayscalePass();
      renderer.copyGrayscaleLsbBuffers();
      const auto tGrayLsb = millis();

      renderer.clearScreen(0x00);
      renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
      renderGrayscalePass();
      renderer.copyGrayscaleMsbBuffers();
      const auto tGrayMsb = millis();

      renderer.displayGrayBuffer();
      const auto tGrayDisplay = millis();
      renderer.setRenderMode(GfxRenderer::BW);
      renderer.restoreBwBuffer();
      const auto tBwRestore = millis();

      const auto tEnd = millis();
      LOG_DBG("ERS",
              "Page render: prewarm=%lums bw_render=%lums display=%lums bw_store=%lums "
              "gray_lsb=%lums gray_msb=%lums gray_display=%lums bw_restore=%lums total=%lums",
              tPrewarm - t0, tBwRender - tPrewarm, tDisplay - tBwRender, tBwStore - tDisplay, tGrayLsb - tBwStore,
              tGrayMsb - tGrayLsb, tGrayDisplay - tGrayMsb, tBwRestore - tGrayDisplay, tEnd - t0);
    } else {
      const auto tEnd = millis();
      LOG_DBG("ERS", "Page render: prewarm=%lums bw_render=%lums display=%lums total=%lums", tPrewarm - t0,
              tBwRender - tPrewarm, tDisplay - tBwRender, tEnd - t0);
    }
  }
}

void EpubReaderActivity::renderStatusBar() const {
  const int currentPage = section ? section->currentPage + 1 : 1;
  const float pageCount = section ? section->estimatedTotalPages() : 1;
  const float sectionChapterProg = (pageCount > 0) ? (static_cast<float>(currentPage) / pageCount) : 0;
  const float bookProgress = epub ? (epub->calculateProgress(currentSpineIndex, sectionChapterProg) * 100) : 0;

  std::string title;
  int textYOffset = 0;
  const auto sb = SETTINGS.statusBarSpec();

  if (automaticPageTurnActive) {
    title = tr(STR_AUTO_TURN_ENABLED) + std::to_string(60 * 1000 / pageTurnDuration);
    const uint8_t statusBarHeight = UITheme::getInstance().getStatusBarHeight();
    if (statusBarHeight == 0 || statusBarHeight == UITheme::getInstance().getProgressBarHeight()) {
      textYOffset += UITheme::getInstance().getMetrics().statusBarVerticalMargin;
    }
  } else if (sb.titleMode == CrossPointSettings::STATUS_BAR_TITLE::CHAPTER_TITLE) {
    title = tr(STR_UNNAMED);
    if (epub) {
      const int tocIndex = epub->getTocIndexForSpineIndex(currentSpineIndex);
      if (tocIndex != -1) {
        const auto tocItem = epub->getTocItem(tocIndex);
        title = tocItem.title;
      }
    }
  } else if (sb.titleMode == CrossPointSettings::STATUS_BAR_TITLE::BOOK_TITLE) {
    title = epub ? epub->getTitle() : "";
  }

  GUI.drawStatusBar(renderer, bookProgress, currentPage, pageCount, title, 0, textYOffset, true, currentPageBookmarked,
                    section ? section->isBuilding() : false);
}

void EpubReaderActivity::navigateToHref(const std::string& hrefStr, const bool savePosition) {
  if (!epub) return;

  if (savePosition && section && footnoteDepth < MAX_FOOTNOTE_DEPTH) {
    savedPositions[footnoteDepth] = {currentSpineIndex, section->currentPage};
    footnoteDepth++;
    LOG_DBG("ERS", "Saved position [%d]: spine %d, page %d", footnoteDepth, currentSpineIndex, section->currentPage);
  }

  std::string anchor;
  const auto hashPos = hrefStr.find('#');
  if (hashPos != std::string::npos && hashPos + 1 < hrefStr.size()) {
    anchor = hrefStr.substr(hashPos + 1);
  }

  bool sameFile = !hrefStr.empty() && hrefStr[0] == '#';
  int targetSpineIndex = sameFile ? currentSpineIndex : epub->resolveHrefToSpineIndex(hrefStr);

  if (targetSpineIndex < 0) {
    LOG_DBG("ERS", "Could not resolve href: %s", hrefStr.c_str());
    if (savePosition && footnoteDepth > 0) footnoteDepth--;
    return;
  }

  {
    RenderLock lock;
    clearDeferredReposition();
    pendingAnchor = std::move(anchor);
    currentSpineIndex = targetSpineIndex;
    nextPageNumber = 0;
    section.reset();
  }
  requestUpdate();
  LOG_DBG("ERS", "Navigated to spine %d for href: %s", targetSpineIndex, hrefStr.c_str());
}

void EpubReaderActivity::restoreSavedPosition() {
  if (footnoteDepth <= 0) return;
  footnoteDepth--;
  const auto& pos = savedPositions[footnoteDepth];
  LOG_DBG("ERS", "Restoring position [%d]: spine %d, page %d", footnoteDepth, pos.spineIndex, pos.pageNumber);

  {
    RenderLock lock;
    clearDeferredReposition();
    currentSpineIndex = pos.spineIndex;
    nextPageNumber = pos.pageNumber;
    section.reset();
  }
  requestUpdate();
}

void EpubReaderActivity::loadCachedBookmarks() {
  cachedBookmarks.clear();
  if (cachedBookmarks.capacity() < initialBookmarkCacheCapacity) {
    cachedBookmarks.reserve(initialBookmarkCacheCapacity);
  }
  if (!epub) {
    currentPageBookmarked = false;
    return;
  }

  BookmarkFile::load(epub->getPath(), cachedBookmarks);
  updateBookmarkFlag();
}

void EpubReaderActivity::addBookmark() {
  if (!section || !epub) return;
  LOG_DBG("ERS", "Toggle bookmark at spine %d, page %d", currentSpineIndex, section ? section->currentPage : -1);
  int currentPage;
  int pageCount;
  {
    RenderLock lock;
    pageCount = section->estimatedTotalPages();
    currentPage = section->currentPage;
  }

  SavedProgressPosition progress = ProgressMapper::toSavedProgress(epub, getCurrentPosition());
  const ProgressRange pageRange = getPageProgressRange(epub, currentSpineIndex, currentPage, pageCount);

  const size_t bookmarkCountBeforeToggle = cachedBookmarks.size();
  cachedBookmarks.erase(std::remove_if(cachedBookmarks.begin(), cachedBookmarks.end(),
                                       [&](const BookmarkEntry& b) {
                                         return bookmarkMatchesProgress(b, currentSpineIndex, currentPage, pageCount,
                                                                        pageRange);
                                       }),
                        cachedBookmarks.end());
  if (cachedBookmarks.size() != bookmarkCountBeforeToggle) {
    bookmarkRemoved = true;
    currentPageBookmarked = false;
  } else {
    std::string pageText;
    if (currentPage >= 0 && currentPage < pageCount) {
      pageText = section->getTextFromSectionFile();
    }
    BookmarkEntry entry;
    entry.percentage = progress.percentage;
    entry.xpath = progress.xpath;
    entry.summary = BookmarkUtil::sanitizeBookmarkSummary(pageText);
    entry.computedSpineIndex = currentSpineIndex;
    entry.computedChapterPageCount = pageCount;
    entry.computedChapterProgress = currentPage;
    const std::optional<uint32_t> offset =
        currentPageVisibleOffset.has_value() ? currentPageVisibleOffset
        : (currentPage >= 0 && currentPage < section->pageCount)
            ? section->getVisibleTextOffsetForPage(static_cast<uint16_t>(currentPage))
            : std::nullopt;
    if (offset.has_value()) {
      entry.visibleTextOffset = *offset;
      entry.hasVisibleTextOffset = true;
    }
    cachedBookmarks.insert(cachedBookmarks.begin(), entry);
    bookmarkRemoved = false;
    currentPageBookmarked = true;
  }

  if (!BookmarkFile::save(epub->getPath(), cachedBookmarks)) {
    LOG_ERR("ERS", "Failed to save bookmarks");
  }
  requestUpdate();
}

void EpubReaderActivity::updateBookmarkFlag() {
  if (!section || !epub || cachedBookmarks.empty()) {
    currentPageBookmarked = false;
    return;
  }
  const int pageCount = section->estimatedTotalPages();
  const ProgressRange pageRange = getPageProgressRange(epub, currentSpineIndex, section->currentPage, pageCount);
  currentPageBookmarked = std::any_of(cachedBookmarks.begin(), cachedBookmarks.end(), [&](const BookmarkEntry& b) {
    return bookmarkMatchesProgress(b, currentSpineIndex, section->currentPage, pageCount, pageRange);
  });
}

ScreenshotInfo EpubReaderActivity::getScreenshotInfo() const {
  ScreenshotInfo info;
  info.readerType = ScreenshotInfo::ReaderType::Epub;
  if (epub) {
    snprintf(info.title, sizeof(info.title), "%s", epub->getTitle().c_str());
    info.spineIndex = currentSpineIndex;
  }
  if (section) {
    info.currentPage = section->currentPage + 1;
    info.totalPages = section->estimatedTotalPages();
    if (epub && epub->getBookSize() > 0 && info.totalPages > 0) {
      const float chapterProgress = static_cast<float>(section->currentPage) / static_cast<float>(info.totalPages);
      int pct = static_cast<int>(epub->calculateProgress(currentSpineIndex, chapterProgress) * 100.0f + 0.5f);
      if (pct < 0) pct = 0;
      if (pct > 100) pct = 100;
      info.progressPercent = pct;
    }
  }
  return info;
}

CrossPointPosition EpubReaderActivity::getCurrentPosition() const {
  const int currentPage = section ? section->currentPage : nextPageNumber;
  const int totalPages = section ? section->estimatedTotalPages() : cachedChapterTotalPageCount;
  std::optional<uint16_t> paragraphIndex;
  if (section && currentPage >= 0 && currentPage < section->pageCount) {
    const uint16_t paragraphPage =
        currentPage > 0 ? static_cast<uint16_t>(currentPage - 1) : static_cast<uint16_t>(currentPage);
    if (const auto pIdx = section->getParagraphIndexForPage(paragraphPage)) {
      paragraphIndex = *pIdx;
    }
  }

  CrossPointPosition localPos = {currentSpineIndex, currentPage, totalPages};
  if (section && currentPage >= 0 && currentPage < section->pageCount) {
    if (const auto offset = section->getVisibleTextOffsetForPage(static_cast<uint16_t>(currentPage))) {
      localPos.visibleTextOffset = *offset;
      localPos.hasVisibleTextOffset = true;
    }
  }
  if (paragraphIndex.has_value()) {
    localPos.paragraphIndex = *paragraphIndex;
    localPos.hasParagraphIndex = true;
  }
  return localPos;
}
