// CP-KOBO-007: portable Clara BW Variant A transform (host-testable, no device writes).
// Logical CrossPoint: 480x800. Physical panel: 1072x1448.
// Do not conflate evdev raw axis coordinates with panel coordinates:
// actual touch axis rotation/calibration requires an on-device read-only probe.
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <optional>
#include <utility>

namespace clara {
constexpr int logicalW=480, logicalH=800, panelW=1072, panelH=1448;
constexpr int viewW=869, viewH=1448, viewX=101, viewY=0;
struct Point { int x,y; };
struct GrayFrame {
    static constexpr size_t bytes=static_cast<size_t>(panelW)*panelH;
    // Borrowed target buffer, Gray8: 0 black, 255 white.
    uint8_t* data;
    size_t length;
};
std::optional<Point> panelToLogical(Point p) {
    if (p.x<viewX || p.x>=viewX+viewW || p.y<viewY || p.y>=viewY+viewH) return {};
    return Point{(p.x-viewX)*logicalW/viewW,(p.y-viewY)*logicalH/viewH};
}
Point logicalToPanel(Point p) {
    return {viewX+p.x*viewW/logicalW,viewY+p.y*viewH/logicalH};
}
// Nearest neighbor: deterministic black/white pixels, no interpolation halos.
bool scaleGray8(const uint8_t* logical, size_t srcSize, GrayFrame output) {
    if (!logical || !output.data || srcSize<logicalW*logicalH || output.length<GrayFrame::bytes) return false;
    for (int y=0;y<panelH;++y) {
        const int sy=(y-viewY)*logicalH/viewH;
        for (int x=0;x<panelW;++x) {
            const bool inside=x>=viewX && x<viewX+viewW;
            const int sx=inside ? (x-viewX)*logicalW/viewW : 0;
            output.data[static_cast<size_t>(y)*panelW+x]=inside ? logical[static_cast<size_t>(sy)*logicalW+sx] : 255;
        }
    }
    return true;
}
} // namespace clara

int main() {
    using namespace clara;
    static_assert(viewX*2+viewW==panelW-1);
    assert(!panelToLogical({100,700}));
    assert(!panelToLogical({970,700}));
    for(const Point p:std::array<Point,5>{{{0,0},{479,799},{240,400},{340,710},{420,450}}}) {
        const auto q=panelToLogical(logicalToPanel(p));
        assert(q.has_value());
        assert(q->x>=p.x-1 && q->x<=p.x+1);
        assert(q->y>=p.y-1 && q->y<=p.y+1);
    }
    std::array<uint8_t,logicalW*logicalH> input{};
    auto output=new uint8_t[GrayFrame::bytes];
    input[0]=0;
    assert(scaleGray8(input.data(),input.size(),{output,GrayFrame::bytes}));
    assert(output[0]==255);
    assert(output[100]==255);
    assert(output[101]==0);
    assert(output[panelW-1]==255);
    delete[] output;
    std::cout<<"PASS CP-KOBO-007 Clara BW 480x800 -> 1072x1448 Gray8/coordinate adapter\n";
}
