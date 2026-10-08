#include "../src/platform/kobo/ClaraBwEvdev.h"
#include "../src/platform/kobo/ClaraBwFbink.h"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>

using namespace crosspoint::kobo;
static input_event event(unsigned type,unsigned code,int value) {
    input_event e{};e.type=type;e.code=code;e.value=value;return e;
}
int main(int argc,char**argv) {
    if(argc!=2) return 2;
    std::vector<uint8_t> logical(static_cast<size_t>(kLogicalWidth)*kLogicalHeight,255);
    std::vector<uint8_t> physical(static_cast<size_t>(kPanelWidth)*kPanelHeight,255);
    logical[0]=0;
    assert(scaleNearest({logical.data(),logical.size(),kLogicalWidth,kLogicalHeight},
                        {physical.data(),physical.size(),kPanelWidth,kPanelHeight}));
    FbinkPnmSink display(argv[1]); // no hardware output
    assert(display.present({physical.data(),physical.size(),kPanelWidth,kPanelHeight}));
    EvdevTouchDecoder touch;
    assert(!touch.consume(event(EV_KEY,BTN_TOUCH,1)));
    assert(!touch.consume(event(EV_ABS,ABS_X,716)));
    assert(!touch.consume(event(EV_ABS,ABS_Y,1285)));
    auto result=touch.consume(event(EV_SYN,SYN_REPORT,0));
    assert(result && result->x>=339 && result->x<=341 && result->y>=709 && result->y<=711);
    // Simulated UI state change after the touch, and present the changed frame.
    logical[0]=255;
    logical[static_cast<size_t>(result->y)*kLogicalWidth+result->x]=0;
    assert(scaleNearest({logical.data(),logical.size(),kLogicalWidth,kLogicalHeight},
                        {physical.data(),physical.size(),kPanelWidth,kPanelHeight}));
    assert(display.present({physical.data(),physical.size(),kPanelWidth,kPanelHeight}));
    assert(display.presentCount==2);
    std::cout<<"PASS CP-KOBO-019 simulated touch -> frame update -> PNM (no device I/O)\n";
}
