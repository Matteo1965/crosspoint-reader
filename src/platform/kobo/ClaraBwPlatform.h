#pragma once
// CP-KOBO-015: minimal platform-independent display/touch contract.
// This contract is deliberately independent of Arduino, FBInk and evdev.
// The concrete Kobo Linux backend is NOT implemented here.
#include <cstddef>
#include <cstdint>
#include <optional>

namespace crosspoint::kobo {
constexpr int kLogicalWidth = 480;
constexpr int kLogicalHeight = 800;
constexpr int kPanelWidth = 1072;
constexpr int kPanelHeight = 1448;
constexpr int kViewportWidth = 869;
constexpr int kViewportHeight = 1448;
constexpr int kViewportX = 101;
constexpr int kViewportY = 0;

struct Point { int x; int y; };
struct Gray8Image { const uint8_t* pixels; size_t length; int width; int height; };
struct PanelGray8 { uint8_t* pixels; size_t length; int width; int height; };

inline std::optional<Point> panelToLogical(Point p) noexcept {
    if (p.x < kViewportX || p.x >= kViewportX + kViewportWidth ||
        p.y < kViewportY || p.y >= kViewportY + kViewportHeight) return std::nullopt;
    return Point{(p.x - kViewportX) * kLogicalWidth / kViewportWidth,
                 (p.y - kViewportY) * kLogicalHeight / kViewportHeight};
}
inline Point logicalToPanel(Point p) noexcept {
    return {kViewportX + p.x * kViewportWidth / kLogicalWidth,
            kViewportY + p.y * kViewportHeight / kLogicalHeight};
}
inline bool scaleNearest(const Gray8Image& source, const PanelGray8& target) noexcept {
    if (!source.pixels || !target.pixels ||
        source.width != kLogicalWidth || source.height != kLogicalHeight ||
        target.width != kPanelWidth || target.height != kPanelHeight ||
        source.length < static_cast<size_t>(kLogicalWidth) * kLogicalHeight ||
        target.length < static_cast<size_t>(kPanelWidth) * kPanelHeight) return false;
    for (int y = 0; y < kPanelHeight; ++y) {
        const int sy = y * kLogicalHeight / kViewportHeight;
        for (int x = 0; x < kPanelWidth; ++x) {
            const bool inside = x >= kViewportX && x < kViewportX + kViewportWidth;
            const int sx = inside ? (x - kViewportX) * kLogicalWidth / kViewportWidth : 0;
            target.pixels[static_cast<size_t>(y) * kPanelWidth + x] =
                inside ? source.pixels[static_cast<size_t>(sy) * kLogicalWidth + sx] : 255;
        }
    }
    return true;
}
// Platform-specific implementations may update the E Ink screen or poll touch;
// neither operation is performed by the interface itself.
class DisplaySink {
public:
    virtual ~DisplaySink() = default;
    virtual bool present(const PanelGray8& frame) = 0;
};
class TouchSource {
public:
    virtual ~TouchSource() = default;
    virtual std::optional<Point> pollPanelPoint() = 0;
};
}
