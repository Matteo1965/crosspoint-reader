#include "../src/platform/kobo/ClaraBwFbink.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
using namespace crosspoint::kobo;
int main(int argc,char**argv) {
    assert(argc==2);
    std::vector<uint8_t> logical(static_cast<size_t>(kLogicalWidth)*kLogicalHeight,255);
    logical[0]=0;
    std::vector<uint8_t> panel(static_cast<size_t>(kPanelWidth)*kPanelHeight);
    assert(scaleNearest({logical.data(),logical.size(),kLogicalWidth,kLogicalHeight},
                        {panel.data(),panel.size(),kPanelWidth,kPanelHeight}));
    FbinkPnmSink sink(argv[1]); // dry-run by default, never calls FBInk
    assert(sink.present({panel.data(),panel.size(),kPanelWidth,kPanelHeight}));
    assert(sink.presentCount==1);
    assert(!sink.present({nullptr,0,kPanelWidth,kPanelHeight}));
    std::ifstream file(argv[1],std::ios::binary);
    assert(file.good());
    std::string magic;
    std::getline(file,magic);
    assert(magic=="P5");
    std::string dimensions;
    std::getline(file,dimensions);
    assert(dimensions=="1072 1448");
    std::string maxValue;
    std::getline(file,maxValue);
    assert(maxValue=="255");
    std::vector<unsigned char> pixels((std::istreambuf_iterator<char>(file)),std::istreambuf_iterator<char>());
    assert(pixels.size()==panel.size());
    assert(pixels[0]==255 && pixels[100]==255 && pixels[101]==0 && pixels[kPanelWidth-1]==255);
    std::cout<<"PASS CP-KOBO-018 FBInk PNM frame sink dry-run (no device writes)\n";
}
