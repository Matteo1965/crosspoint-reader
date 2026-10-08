// CP-KOBO-020: single-file ARM Linux read-only Clara BW hardware probe.
// Does not open /dev/fb*, stop Nickel, take evdev grabs, or touch system config.
#include <dirent.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/utsname.h>
static std::string read(const std::string& p) {
    std::ifstream f(p, std::ios::binary);
    if (!f) return "(unavailable)";
    std::string s; std::getline(f,s);
    while (!s.empty() && (s.back()=='\0'||s.back()=='\r'||s.back()=='\n')) s.pop_back();
    return s;
}
int main() {
    struct utsname u{};
    if (uname(&u)==0) std::cout<<"kernel: "<<u.release<<" arch: "<<u.machine<<"\n";
    std::cout<<"model: "<<read("/proc/device-tree/model")<<"\n";
    for(int i=0;i<8;++i) {
        const std::string path="/sys/class/graphics/fb"+std::to_string(i);
        std::ifstream probe(path+"/virtual_size");
        if (!probe) continue;
        std::cout<<"fb"<<i<<" name="<<read(path+"/name")
                 <<" size="<<read(path+"/virtual_size")
                 <<" bpp="<<read(path+"/bits_per_pixel")
                 <<" stride="<<read(path+"/stride")<<"\n";
    }
    std::ifstream input("/proc/bus/input/devices");
    if (input) {
        std::string line;
        while (std::getline(input,line))
            if (line.rfind("N: Name=",0)==0 || line.rfind("H: Handlers=",0)==0)
                std::cout<<"input "<<line<<"\n";
    }
    std::cout<<"CP-KOBO-020 probe finished (read-only)\n";
}
