#pragma once

class GfxRenderer;
class Page;
class HighlightStore;

class HighlightRenderer {
 public:
  static void render(GfxRenderer& renderer, const Page& page, int fontId, int xOffset, int yOffset,
                     int spineIndex, const HighlightStore& store);
};
