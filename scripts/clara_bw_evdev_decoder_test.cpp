#include "../src/platform/kobo/ClaraBwEvdev.h"
#include <cassert>
#include <iostream>
using namespace crosspoint::kobo;
static input_event e(unsigned type,unsigned code,int value) {
    input_event result{}; result.type=type;result.code=code;result.value=value;return result;
}
int main(){
    EvdevTouchDecoder d;
    assert(!d.consume(e(EV_KEY,BTN_TOUCH,1)));
    assert(!d.consume(e(EV_ABS,ABS_X,716)));
    assert(!d.consume(e(EV_ABS,ABS_Y,1285)));
    auto p=d.consume(e(EV_SYN,SYN_REPORT,0));
    assert(p && p->x>=339 && p->x<=341 && p->y>=709 && p->y<=711);
    assert(!d.consume(e(EV_SYN,SYN_REPORT,0)));
    assert(!d.consume(e(EV_KEY,BTN_TOUCH,0)));
    assert(!d.consume(e(EV_SYN,SYN_REPORT,0)));
    assert(!d.consume(e(EV_KEY,BTN_TOUCH,1)));
    assert(d.consume(e(EV_SYN,SYN_REPORT,0)).has_value());
    assert(!d.consume(e(EV_SYN,SYN_DROPPED,0)));
    assert(!d.consume(e(EV_SYN,SYN_REPORT,0)));
    EvdevTouchDecoder m;
    assert(!m.consume(e(EV_ABS,ABS_MT_TRACKING_ID,1)));
    assert(!m.consume(e(EV_ABS,ABS_MT_POSITION_X,716)));
    assert(!m.consume(e(EV_ABS,ABS_MT_POSITION_Y,1285)));
    assert(m.consume(e(EV_SYN,SYN_REPORT,0)).has_value());
    assert(!m.consume(e(EV_ABS,ABS_MT_TRACKING_ID,-1)));
    assert(!m.consume(e(EV_SYN,SYN_REPORT,0)));
    std::cout<<"PASS CP-KOBO-017 Linux evdev decoder (synthetic events, no device writes)\n";
}
