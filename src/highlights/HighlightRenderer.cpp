#include "HighlightRenderer.h"

#include <Epub/Page.h>
#include <GfxRenderer.h>

#include "HighlightStore.h"

void HighlightRenderer::render(GfxRenderer& renderer, const Page& page, const int fontId, const int xOffset,
                               const int yOffset, const int spineIndex, const HighlightStore& store) {
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
      bool highlighted = false;
      for (const auto& anchor : store.items()) {
        const uint32_t end = anchor.visibleTextOffset + anchor.length;
        if (anchor.spineIndex == spineIndex && wordOffset >= anchor.visibleTextOffset && wordOffset < end) {
          highlighted = true;
          break;
        }
      }
      if (!highlighted) continue;
      const int x = xOffset + line.xPos + block->wordXpos(i);
      const int width = renderer.getTextAdvanceX(fontId, block->wordText(i), block->wordStyle(i));
      const int y = yOffset + line.yPos + rubyShift + lineHeight - 2;
      renderer.drawLine(x, y, x + width, y, 2, true);
    }
  }
}
