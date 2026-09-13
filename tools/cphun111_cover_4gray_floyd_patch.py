from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# JPEG converter: add a dedicated Floyd-Steinberg 2-bit path without changing
# the existing Atkinson behavior used elsewhere (including sleep/home paths).
replace_once(
    "lib/JpegToBmpConverter/JpegToBmpConverter.h",
    '''  static bool jpegFileToBmpStreamInternal(HalFile& jpegFile, Print& bmpOut, int targetWidth, int targetHeight,\n                                          bool oneBit, bool crop = true);\n''',
    '''  static bool jpegFileToBmpStreamInternal(HalFile& jpegFile, Print& bmpOut, int targetWidth, int targetHeight,\n                                          bool oneBit, bool crop = true, bool forceFloyd = false);\n''',
)
replace_once(
    "lib/JpegToBmpConverter/JpegToBmpConverter.h",
    '''  static bool jpegFileToBmpStreamWithSize(HalFile& jpegFile, Print& bmpOut, int targetMaxWidth, int targetMaxHeight);\n''',
    '''  static bool jpegFileToBmpStreamWithSize(HalFile& jpegFile, Print& bmpOut, int targetMaxWidth, int targetMaxHeight);\n  // Dedicated Book Cover path: 2-bit / 4 gray levels, fit-inside display, Floyd-Steinberg.\n  static bool jpegFileToFloydSteinbergBmpStream(HalFile& jpegFile, Print& bmpOut);\n''',
)
replace_once(
    "lib/JpegToBmpConverter/JpegToBmpConverter.cpp",
    '''bool JpegToBmpConverter::jpegFileToBmpStreamInternal(HalFile& jpegFile, Print& bmpOut, int targetWidth,\n                                                     int targetHeight, bool oneBit, bool crop) {\n''',
    '''bool JpegToBmpConverter::jpegFileToBmpStreamInternal(HalFile& jpegFile, Print& bmpOut, int targetWidth,\n                                                     int targetHeight, bool oneBit, bool crop, bool forceFloyd) {\n''',
)
replace_once(
    "lib/JpegToBmpConverter/JpegToBmpConverter.cpp",
    '''    outWidth = static_cast<int>(srcWidth * scale);\n    outHeight = static_cast<int>(srcHeight * scale);\n''',
    '''    // CPHUN-111: the dedicated full-screen cover path rounds to the nearest pixel.\n    // Example: a 313x500 cover fitted into 480x800 becomes 480x767, matching\n    // X4 EPUB Optimizer instead of being truncated to 480x766.\n    outWidth = static_cast<int>(srcWidth * scale + (forceFloyd ? 0.5f : 0.0f));\n    outHeight = static_cast<int>(srcHeight * scale + (forceFloyd ? 0.5f : 0.0f));\n''',
)
replace_once(
    "lib/JpegToBmpConverter/JpegToBmpConverter.cpp",
    '''  } else if (!USE_8BIT_OUTPUT) {\n    if (USE_ATKINSON) {\n      ctx.atkinsonDitherer = makeUniqueNoThrow<AtkinsonDitherer>(outWidth);\n      if (!ctx.atkinsonDitherer) {\n        LOG_ERR("JPG", "OOM: AtkinsonDitherer");\n        return false;\n      }\n    } else if (USE_FLOYD_STEINBERG) {\n      ctx.fsDitherer = makeUniqueNoThrow<FloydSteinbergDitherer>(outWidth);\n      if (!ctx.fsDitherer) {\n        LOG_ERR("JPG", "OOM: FloydSteinbergDitherer");\n        return false;\n      }\n    }\n  }\n''',
    '''  } else if (!USE_8BIT_OUTPUT) {\n    if (forceFloyd || (!USE_ATKINSON && USE_FLOYD_STEINBERG)) {\n      ctx.fsDitherer = makeUniqueNoThrow<FloydSteinbergDitherer>(outWidth);\n      if (!ctx.fsDitherer) {\n        LOG_ERR("JPG", "OOM: FloydSteinbergDitherer");\n        return false;\n      }\n    } else if (USE_ATKINSON) {\n      ctx.atkinsonDitherer = makeUniqueNoThrow<AtkinsonDitherer>(outWidth);\n      if (!ctx.atkinsonDitherer) {\n        LOG_ERR("JPG", "OOM: AtkinsonDitherer");\n        return false;\n      }\n    }\n  }\n''',
)
replace_once(
    "lib/JpegToBmpConverter/JpegToBmpConverter.cpp",
    '''bool JpegToBmpConverter::jpegFileToBmpStreamWithSize(HalFile& jpegFile, Print& bmpOut, int targetMaxWidth,\n                                                     int targetMaxHeight) {\n  return jpegFileToBmpStreamInternal(jpegFile, bmpOut, targetMaxWidth, targetMaxHeight, false);\n}\n\n// Convert to 1-bit BMP''',
    '''bool JpegToBmpConverter::jpegFileToBmpStreamWithSize(HalFile& jpegFile, Print& bmpOut, int targetMaxWidth,\n                                                     int targetMaxHeight) {\n  return jpegFileToBmpStreamInternal(jpegFile, bmpOut, targetMaxWidth, targetMaxHeight, false);\n}\n\nbool JpegToBmpConverter::jpegFileToFloydSteinbergBmpStream(HalFile& jpegFile, Print& bmpOut) {\n  const int targetWidth = display.getDisplayHeight();\n  const int targetHeight = display.getDisplayWidth();\n  return jpegFileToBmpStreamInternal(jpegFile, bmpOut, targetWidth, targetHeight, false, false, true);\n}\n\n// Convert to 1-bit BMP''',
)

# PNG converter: same dedicated Floyd-Steinberg path.
replace_once(
    "lib/PngToBmpConverter/PngToBmpConverter.h",
    '''  static bool pngFileToBmpStreamInternal(HalFile& pngFile, Print& bmpOut, int targetWidth, int targetHeight,\n                                         bool oneBit, bool crop = true);\n''',
    '''  static bool pngFileToBmpStreamInternal(HalFile& pngFile, Print& bmpOut, int targetWidth, int targetHeight,\n                                         bool oneBit, bool crop = true, bool forceFloyd = false);\n''',
)
replace_once(
    "lib/PngToBmpConverter/PngToBmpConverter.h",
    '''  static bool pngFileToBmpStreamWithSize(HalFile& pngFile, Print& bmpOut, int targetMaxWidth, int targetMaxHeight);\n''',
    '''  static bool pngFileToBmpStreamWithSize(HalFile& pngFile, Print& bmpOut, int targetMaxWidth, int targetMaxHeight);\n  static bool pngFileToFloydSteinbergBmpStream(HalFile& pngFile, Print& bmpOut);\n''',
)
replace_once(
    "lib/PngToBmpConverter/PngToBmpConverter.cpp",
    '''bool PngToBmpConverter::pngFileToBmpStreamInternal(HalFile& pngFile, Print& bmpOut, int targetWidth, int targetHeight,\n                                                   bool oneBit, bool crop) {\n''',
    '''bool PngToBmpConverter::pngFileToBmpStreamInternal(HalFile& pngFile, Print& bmpOut, int targetWidth, int targetHeight,\n                                                   bool oneBit, bool crop, bool forceFloyd) {\n''',
)
replace_once(
    "lib/PngToBmpConverter/PngToBmpConverter.cpp",
    '''    outWidth = static_cast<int>(width * scale);\n    outHeight = static_cast<int>(height * scale);\n''',
    '''    outWidth = static_cast<int>(width * scale + (forceFloyd ? 0.5f : 0.0f));\n    outHeight = static_cast<int>(height * scale + (forceFloyd ? 0.5f : 0.0f));\n''',
)
replace_once(
    "lib/PngToBmpConverter/PngToBmpConverter.cpp",
    '''  } else if (!USE_8BIT_OUTPUT) {\n    if (USE_ATKINSON) {\n      atkinsonDitherer = new AtkinsonDitherer(outWidth);\n    } else if (USE_FLOYD_STEINBERG) {\n      fsDitherer = new FloydSteinbergDitherer(outWidth);\n    }\n  }\n''',
    '''  } else if (!USE_8BIT_OUTPUT) {\n    if (forceFloyd || (!USE_ATKINSON && USE_FLOYD_STEINBERG)) {\n      fsDitherer = new FloydSteinbergDitherer(outWidth);\n    } else if (USE_ATKINSON) {\n      atkinsonDitherer = new AtkinsonDitherer(outWidth);\n    }\n  }\n''',
)
replace_once(
    "lib/PngToBmpConverter/PngToBmpConverter.cpp",
    '''bool PngToBmpConverter::pngFileToBmpStreamWithSize(HalFile& pngFile, Print& bmpOut, int targetMaxWidth,\n                                                   int targetMaxHeight) {\n  return pngFileToBmpStreamInternal(pngFile, bmpOut, targetMaxWidth, targetMaxHeight, false);\n}\n\nbool PngToBmpConverter::pngFileTo1BitBmpStreamWithSize''',
    '''bool PngToBmpConverter::pngFileToBmpStreamWithSize(HalFile& pngFile, Print& bmpOut, int targetMaxWidth,\n                                                   int targetMaxHeight) {\n  return pngFileToBmpStreamInternal(pngFile, bmpOut, targetMaxWidth, targetMaxHeight, false);\n}\n\nbool PngToBmpConverter::pngFileToFloydSteinbergBmpStream(HalFile& pngFile, Print& bmpOut) {\n  const int targetWidth = display.getDisplayHeight();\n  const int targetHeight = display.getDisplayWidth();\n  return pngFileToBmpStreamInternal(pngFile, bmpOut, targetWidth, targetHeight, false, false, true);\n}\n\nbool PngToBmpConverter::pngFileTo1BitBmpStreamWithSize''',
)

# Epub: add a separate cached Book Cover bitmap so Home thumbnails and sleep cover
# remain untouched. This file is always a 2-bit / 4-gray Floyd-Steinberg fit image.
replace_once(
    "lib/Epub/Epub.h",
    '''  bool generateCoverBmp(bool cropped = false) const;\n  std::string getThumbBmpPath() const;\n''',
    '''  bool generateCoverBmp(bool cropped = false) const;\n  std::string getBookCoverViewBmpPath() const;\n  bool generateBookCoverViewBmp() const;\n  std::string getThumbBmpPath() const;\n''',
)

insert_anchor = '''std::string Epub::getThumbBmpPath() const { return cachePath + "/thumb_[HEIGHT].bmp"; }\n'''
new_block = '''std::string Epub::getBookCoverViewBmpPath() const { return cachePath + "/cover_view_4gray_fs.bmp"; }\n\nbool Epub::generateBookCoverViewBmp() const {\n  const std::string outputPath = getBookCoverViewBmpPath();\n  if (Storage.exists(outputPath.c_str())) return true;\n  if (!bookMetadataCache || !bookMetadataCache->isLoaded()) return false;\n\n  const auto coverImageHref = bookMetadataCache->coreMetadata.coverItemHref;\n  if (coverImageHref.empty()) return false;\n\n  const bool isJpg = FsHelpers::hasJpgExtension(coverImageHref);\n  const bool isPng = FsHelpers::hasPngExtension(coverImageHref);\n  if (!isJpg && !isPng) return false;\n\n  const std::string tempPath = getCachePath() + (isJpg ? "/.cover_view.jpg" : "/.cover_view.png");\n  HalFile source;\n  if (!Storage.openFileForWrite("EBP", tempPath, source)) return false;\n  readItemContentsToStream(coverImageHref, source, 1024);\n  source.close();\n  if (!Storage.openFileForRead("EBP", tempPath, source)) return false;\n\n  HalFile out;\n  if (!Storage.openFileForWrite("EBP", outputPath, out)) {\n    source.close();\n    Storage.remove(tempPath.c_str());\n    return false;\n  }\n\n  const bool success = isJpg\n      ? JpegToBmpConverter::jpegFileToFloydSteinbergBmpStream(source, out)\n      : PngToBmpConverter::pngFileToFloydSteinbergBmpStream(source, out);\n  source.close();\n  out.close();\n  Storage.remove(tempPath.c_str());\n  if (!success) Storage.remove(outputPath.c_str());\n  return success;\n}\n\n'''
replace_once("lib/Epub/Epub.cpp", insert_anchor, new_block + insert_anchor)

# Reader: CPHUN-110 has already been applied by the workflow. Replace its 1-bit
# thumb_800 route with the dedicated 4-gray Floyd-Steinberg cover cache.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    case EpubReaderMenuActivity::MenuAction::BOOK_COVER: {\n      // CPHUN-110: use the same 1-bit Atkinson-dithered cover pipeline as the Home screen,\n      // but generate it at the X4's full portrait height instead of enlarging the Home thumbnail.\n      // A height-specific filename also bypasses any cached legacy 2-bit cover.bmp.\n      const int coverHeight = std::max(renderer.getScreenWidth(), renderer.getScreenHeight());\n      std::string coverPath = epub->getThumbBmpPath(coverHeight);\n      if (!Storage.exists(coverPath.c_str())) epub->generateThumbBmp(coverHeight);\n''',
    '''    case EpubReaderMenuActivity::MenuAction::BOOK_COVER: {\n      // CPHUN-111: dedicated 4-gray Floyd-Steinberg cover, prescaled with aspect\n      // ratio preserved so neither dimension exceeds the physical X4 screen.\n      // The generated bitmap is then shown 1:1; no post-dither downscale is needed.\n      std::string coverPath = epub->getBookCoverViewBmpPath();\n      if (!Storage.exists(coverPath.c_str())) epub->generateBookCoverViewBmp();\n''',
)

print("Applied CPHUN-111 4-gray Floyd-Steinberg book-cover patch")
