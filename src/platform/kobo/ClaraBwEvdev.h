#pragma once
// CP-KOBO-017: Linux evdev event decoder. No /dev/input access or exclusive grabs.
// Touch calibration remains device-specific and MUST be measured on real Clara BW.
#include "ClaraBwBridge.h"
#include <linux/input.h>
#include <optional>
namespace crosspoint::kobo {
class EvdevTouchDecoder {
public:
    std::optional<Point> consume(const input_event& event) noexcept {
        if (event.type == EV_ABS) {
            if (event.code == ABS_MT_POSITION_X) { x_ = event.value; haveX_ = true; multi_ = true; }
            if (event.code == ABS_MT_POSITION_Y) { y_ = event.value; haveY_ = true; multi_ = true; }
            if (!multi_ && event.code == ABS_X) { x_ = event.value; haveX_ = true; }
            if (!multi_ && event.code == ABS_Y) { y_ = event.value; haveY_ = true; }
            if (event.code == ABS_MT_TRACKING_ID) pressed_ = event.value >= 0;
        }
        if (event.type == EV_KEY && event.code == BTN_TOUCH) pressed_ = event.value != 0;
        if (event.type == EV_SYN && event.code == SYN_DROPPED) {
            haveX_ = haveY_ = pressed_ = false; return std::nullopt;
        }
        if (event.type == EV_SYN && event.code == SYN_REPORT && pressed_ && haveX_ && haveY_) {
            auto mapped = touchToLogical({x_,y_,true}, calibration);
            // One report per press, not a continuous stream of spurious taps.
            if (!delivered_) { delivered_ = true; return mapped; }
        }
        if (event.type == EV_SYN && event.code == SYN_REPORT && !pressed_) delivered_ = false;
        return std::nullopt;
    }
    TouchCalibration calibration{};
private:
    int x_=0,y_=0;
    bool haveX_=false,haveY_=false,pressed_=false,multi_=false,delivered_=false;
};
} // namespace crosspoint::kobo
