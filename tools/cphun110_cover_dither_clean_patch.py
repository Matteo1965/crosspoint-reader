from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    case EpubReaderMenuActivity::MenuAction::BOOK_COVER: {
      std::string coverPath = epub->getCoverBmpPath(false);
      if (!Storage.exists(coverPath.c_str())) epub->generateCoverBmp(false);
      if (Storage.exists(coverPath.c_str())) {
        startActivityForResult(std::make_unique<BmpViewerActivity>(renderer, mappedInput, coverPath, true),
                               [this](const ActivityResult&) { openReaderMenu(true); });
      } else {
        openReaderMenu();
      }
      break;
    }
''',
    '''    case EpubReaderMenuActivity::MenuAction::BOOK_COVER: {
      // CPHUN-110: use the same 1-bit Atkinson-dithered cover pipeline as the Home screen,
      // but generate it at the X4's full portrait height instead of enlarging the Home thumbnail.
      // A height-specific filename also bypasses any cached legacy 2-bit cover.bmp.
      const int coverHeight = std::max(renderer.getScreenWidth(), renderer.getScreenHeight());
      std::string coverPath = epub->getThumbBmpPath(coverHeight);
      if (!Storage.exists(coverPath.c_str())) epub->generateThumbBmp(coverHeight);
      if (Storage.exists(coverPath.c_str())) {
        startActivityForResult(std::make_unique<BmpViewerActivity>(renderer, mappedInput, coverPath, true),
                               [this](const ActivityResult&) { openReaderMenu(true); });
      } else {
        openReaderMenu();
      }
      break;
    }
''',
)

replace_once(
    "src/activities/util/BmpViewerActivity.cpp",
    '''      // Draw UI hints on the base layer
      GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
      // Single pass for non-grayscale images

      if (simpleBackOnly) {
        renderer.displayBuffer();
      } else {
        renderer.displayBuffer(HalDisplay::FAST_REFRESH);
      }
''',
    '''      // CPHUN-110: the reader's dedicated Book Cover view is image-only. The physical
      // Back button still exits through loop(), so no on-screen button bar is needed.
      if (!simpleBackOnly) {
        GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
      }

      if (simpleBackOnly) {
        renderer.displayBuffer();
      } else {
        renderer.displayBuffer(HalDisplay::FAST_REFRESH);
      }
''',
)

print("Applied CPHUN-110 dithered clean book-cover patch")
