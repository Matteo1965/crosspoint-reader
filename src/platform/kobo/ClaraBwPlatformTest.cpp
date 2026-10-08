#include "ClaraBwPlatform.h"
#include <array>
#include <cassert>
#include <iostream>
#include <vector>
using namespace crosspoint::kobo;
int main() {
    std::array<uint8_t,kLogicalWidth*kLogicalHeight> source{};
    std::vector<uint8_t> dest(static_cast<size_t>(kPanelWidth)*kPanelHeight, 73);
    source[0]=42;
    assert(scaleNearest({source.data(),source.size(),kLogicalWidth,kLogicalHeight},
                        {dest.data(),dest.size(),kPanelWidth,kPanelHeight}));
    assert(dest[0] == 255 && dest[100] == 255 && dest[101] == 42 &&
           dest[kPanelWidth-1] == 255);
    assert(!panelToLogical({100,400}));
    for (auto p : {Point{0,0},Point{479,799},Point{240,400},Point{340,710}}) {
        auto q=panelToLogical(logicalToPanel(p));
        assert(q && q->x >= p.x-1 && q->x <= p.x+1 && q->y >= p.y-1 && q->y <= p.y+1);
    }
    std::cout << "PASS CP-KOBO-015 portable display/touch contract\n";
}
