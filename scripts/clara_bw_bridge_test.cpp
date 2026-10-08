#include "../src/platform/kobo/ClaraBwBridge.h"
#include <cassert>
#include <iostream>
#include <vector>
using namespace crosspoint::kobo;
int main() {
    TouchCalibration calibration;
    assert(!touchToLogical({340,710,false},calibration));
    auto point=touchToLogical({716,1285,true},calibration);
    assert(point && point->x >= 339 && point->x <= 341 && point->y >= 709 && point->y <= 711);
    assert(!touchToLogical({0,700,true},calibration)); // outside viewport
    calibration.invertX=true;
    assert(!touchToLogical({0,700,true},calibration));
    QueueTouchSource source({{716,1285},{535,724}});
    assert(source.pollPanelPoint().has_value());
    assert(source.pollPanelPoint().has_value());
    assert(!source.pollPanelPoint());
    FrameCommandSink sink;
    std::vector<uint8_t> frame(static_cast<size_t>(kPanelWidth)*kPanelHeight,255);
    assert(sink.present({frame.data(),frame.size(),kPanelWidth,kPanelHeight}));
    assert(sink.presentCount == 1);
    assert(!sink.present({nullptr,0,kPanelWidth,kPanelHeight}));
    std::cout << "PASS CP-KOBO-016 no-I/O display/touch integration\n";
}
