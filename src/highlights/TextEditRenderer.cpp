#include "TextEditRenderer.h"

#include <Epub/Page.h>
#include <GfxRenderer.h>

#include "TextEditStore.h"

void TextEditRenderer::renderBackground(GfxRenderer& renderer, const Page& page, const int fontId, const int xOffset,
                                        const int yOffset, const int spineIndex, const TextEditStore& store) {
  const int lineHeight = renderer.getLineHeight(fontId);
  const int ascender = renderer.getFontAscenderSize(fontId);
  for (const auto& element : page.elements) {
    if (element->getTag() != TAG_PageLine) continue;
    const auto& line = static_cast<const PageLine&>(*element);
    const auto& block = line.getBlock();
    if (!block || !block->valid()) continue;
    const int rubyShift = block->getRubyShift(ascender);
    for (uint16_t i = 0; i < block->wordCount(); ++i) {
      const uint32_t wordOffset = block->wordVisibleTextOffset(i);
      bool edited = false;
      for (const auto& edit : store.items()) {
        const uint32_t end = edit.visibleTextOffset + edit.length;
        if (edit.spineIndex == spineIndex && wordOffset >= edit.visibleTextOffset && wordOffset < end) {
          edited = true;
          break;
        }
      }
      if (!edited) continue;
      const int x = xOffset + line.xPos + block->wordXpos(i);
      const int width = renderer.getTextAdvanceX(fontId, block->wordText(i), block->wordStyle(i));
      const int y = yOffset + line.yPos + rubyShift;
      if (width > 0 && lineHeight > 0) renderer.fillRectDither(x, y, width, lineHeight, Color::LightGray);
    }
  }
}
