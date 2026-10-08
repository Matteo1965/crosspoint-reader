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
// CP-KOBO-027: verified from the Clara BW cyttsp5_mt four-corner log.
// Raw MT X: 0..1447 (top to bottom); raw MT Y: 0..1071 (right to left).
inline TouchCalibration claraBwMeasuredTouchCalibration() noexcept {
    TouchCalibration c;
    c.minX=0; c.maxX=1447;
    c.minY=0; c.maxY=1071;
    c.swapAxes=true;
    c.invertX=true;   // applied after axis swap
    c.invertY=false;
    return c;
}
inline std::optional<Point> calibrate(RawTouch raw, TouchCalibration c) noexcept {
    if (!raw.pressed || c.maxX <= c.minX || c.maxY <= c.minY) return std::nullopt;
    if (raw.x < c.minX || raw.x > c.maxX || raw.y < c.minY || raw.y > c.maxY) return std::nullopt;
    // Scale the *source* axis directly into its post-swap display dimension.
    // The old implementation scaled to the unswapped dimension first, then
    // rescaled, losing precision and yielding incorrect swapped coordinates.
    auto scale=[](int value,int minimum,int maximum,int extent) noexcept -> int {
        return static_cast<int>((static_cast<int64_t>(value-minimum)*(extent-1))/
                                (maximum-minimum));
    };
    int px=c.swapAxes ? scale(raw.y,c.minY,c.maxY,kPanelWidth)
                      : scale(raw.x,c.minX,c.maxX,kPanelWidth);
    int py=c.swapAxes ? scale(raw.x,c.minX,c.maxX,kPanelHeight)
                      : scale(raw.y,c.minY,c.maxY,kPanelHeight);
    if(c.invertX) px=kPanelWidth-1-px;
    if(c.invertY) py=kPanelHeight-1-py;
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
