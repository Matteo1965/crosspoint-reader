#pragma once
// CP-KOBO-016: Kobo Linux bridge; no device node is opened in this layer.
#include "ClaraBwPlatform.h"
#include <optional>
#include <string>
#include <vector>

namespace crosspoint::kobo {
struct RawTouch {
    int x;
    int y;
    bool pressed;
};
struct TouchCalibration {
    int minX=0, maxX=kPanelWidth-1, minY=0, maxY=kPanelHeight-1;
    bool swapAxes=false, invertX=false, invertY=false;
};
inline std::optional<Point> calibrate(RawTouch raw, TouchCalibration c) noexcept {
    if (!raw.pressed || c.maxX <= c.minX || c.maxY <= c.minY) return std::nullopt;
    if (raw.x < c.minX || raw.x > c.maxX || raw.y < c.minY || raw.y > c.maxY) return std::nullopt;
    const int normalX = (raw.x - c.minX) * (kPanelWidth-1) / (c.maxX-c.minX);
    const int normalY = (raw.y - c.minY) * (kPanelHeight-1) / (c.maxY-c.minY);
    // When axes are swapped, scale the swapped range to the destination
    // dimension rather than using raw pixel coordinates interchangeably.
    int px = c.swapAxes ? normalY*(kPanelWidth-1)/(kPanelHeight-1) : normalX;
    int py = c.swapAxes ? normalX*(kPanelHeight-1)/(kPanelWidth-1) : normalY;
    if (c.invertX) px=kPanelWidth-1-px;
    if (c.invertY) py=kPanelHeight-1-py;
    return Point{px,py};
}
inline std::optional<Point> touchToLogical(RawTouch raw, TouchCalibration c) noexcept {
    auto panel=calibrate(raw,c);
    return panel ? panelToLogical(*panel) : std::nullopt;
}
class FrameCommandSink final : public DisplaySink {
public:
    bool present(const PanelGray8& frame) override {
        if (!frame.pixels || frame.length < static_cast<size_t>(kPanelWidth)*kPanelHeight ||
            frame.width != kPanelWidth || frame.height != kPanelHeight) return false;
        ++presentCount;
        return true;  // Deliberately records only; no FBInk call.
    }
    unsigned presentCount=0;
};
class QueueTouchSource final : public TouchSource {
public:
    explicit QueueTouchSource(std::vector<Point> points): points_(std::move(points)) {}
    std::optional<Point> pollPanelPoint() override {
        if (next_ == points_.size()) return std::nullopt;
        return points_[next_++];
    }
private:
    std::vector<Point> points_;
    size_t next_=0;
};
} // namespace crosspoint::kobo
