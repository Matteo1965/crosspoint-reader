#include "../src/platform/kobo/ClaraBwBridge.h"
#include <cassert>
#include <cstdlib>
#include <iostream>
using namespace crosspoint::kobo;
static void near(Point p,int x,int y,int tolerance=3) {
    assert(std::abs(p.x-x)<=tolerance);
    assert(std::abs(p.y-y)<=tolerance);
}
int main(){
    const auto c=claraBwMeasuredTouchCalibration();
    assert(c.minX==0 && c.maxX==1447 && c.minY==0 && c.maxY==1071);
    assert(c.swapAxes && c.invertX && !c.invertY);
    near(*calibrate({0,1071,true},c),0,0,0);
    near(*calibrate({0,0,true},c),1071,0,0);
    near(*calibrate({1447,1071,true},c),0,1447,0);
    near(*calibrate({1447,0,true},c),1071,1447,0);
    near(*calibrate({724,535,true},c),536,724,2);
    // CP-KOBO-026 physical corner readings.
    near(*calibrate({64,1011,true},c),60,64);
    near(*calibrate({69,58,true},c),1013,69);
    near(*calibrate({1366,1004,true},c),67,1366);
    near(*calibrate({1394,61,true},c),1010,1394);
    assert(!calibrate({724,535,false},c));
    assert(!calibrate({1500,535,true},c));
    // Outside the narrow centered 869 px app viewport => no logical touch.
    assert(!touchToLogical({64,1011,true},c));
    auto center=touchToLogical({724,535,true},c);
    assert(center);
    near(*center,240,400,2);
    TouchCalibration generic;
    near(*calibrate({535,724,true},generic),535,724,0);
    std::cout<<"PASS CP-KOBO-027 real Clara BW corner calibration and logical viewport\n";
}
