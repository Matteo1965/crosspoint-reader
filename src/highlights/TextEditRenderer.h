#pragma once

class GfxRenderer;
class Page;
class TextEditStore;

class TextEditRenderer {
 public:
  static void renderBackground(GfxRenderer& renderer, const Page& page, int fontId, int xOffset, int yOffset,
                               int spineIndex, const TextEditStore& store);
};
