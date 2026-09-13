from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "src/activities/util/BmpViewerActivity.cpp",
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
    '''      // CPHUN-110: the reader's dedicated Book Cover view is image-only. The physical
      // Back button still exits through loop(), so no on-screen button bar is needed.
      if (!simpleBackOnly) {
        GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
        renderer.displayBuffer(HalDisplay::FAST_REFRESH);
      } else if (bitmap.hasGreyscale()) {
        // CPHUN-112: match the sleep-screen grayscale panel pipeline exactly.
        // First paint the grayscale base with HALF_REFRESH, then send the LSB/MSB
        // differential gray passes. This is the visible "second render" that was
        // missing from Book Cover view in CPHUN-111.
        renderer.displayGrayscaleBase(HalDisplay::HALF_REFRESH);

        bitmap.rewindToData();
        renderer.clearScreen(0x00);
        renderer.setRenderMode(GfxRenderer::GRAYSCALE_LSB);
        renderer.drawBitmap(bitmap, x, y, pageWidth, pageHeight, 0, 0);
        renderer.copyGrayscaleLsbBuffers();

        bitmap.rewindToData();
        renderer.clearScreen(0x00);
        renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
        renderer.drawBitmap(bitmap, x, y, pageWidth, pageHeight, 0, 0);
        renderer.copyGrayscaleMsbBuffers();

        renderer.displayGrayBuffer();
        renderer.setRenderMode(GfxRenderer::BW);
      } else {
        renderer.displayBuffer();
      }
''',
)

print("Applied CPHUN-112 sleep-style grayscale Book Cover display patch")
