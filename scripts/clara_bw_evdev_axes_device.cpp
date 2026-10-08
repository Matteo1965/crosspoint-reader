// CP-KOBO-023: read-only evdev axis query for Kobo Clara BW.
// Designed for /dev/input/event1 (cyttsp5_mt), NO GRAB and NO event consumption.
#include <fcntl.h>
#include <linux/input.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <cerrno>
#include <cstring>
#include <iostream>
#include <string>
struct Axis { unsigned code; const char* label; };
int main(int argc,char**argv) {
    const char* dev=argc==2 ? argv[1] : "/dev/input/event1";
    int fd=open(dev,O_RDONLY|O_NONBLOCK|O_CLOEXEC);
    if(fd<0) {
        std::cerr<<"open "<<dev<<" failed errno="<<errno<<" "<<std::strerror(errno)<<"\n";
        return 2;
    }
    char name[256]={};
    if(ioctl(fd,EVIOCGNAME(sizeof(name)),name)>=0)
        std::cout<<"device: "<<name<<"\n";
    std::cout<<"event path: "<<dev<<"\n";
    const Axis axes[]={{ABS_X,"ABS_X"},{ABS_Y,"ABS_Y"},
                       {ABS_MT_POSITION_X,"ABS_MT_POSITION_X"},
                       {ABS_MT_POSITION_Y,"ABS_MT_POSITION_Y"},
                       {ABS_MT_SLOT,"ABS_MT_SLOT"},
                       {ABS_MT_TRACKING_ID,"ABS_MT_TRACKING_ID"}};
    for(const auto& a:axes) {
        input_absinfo info{};
        if(ioctl(fd,EVIOCGABS(a.code),&info)==0)
            std::cout<<a.label<<" min="<<info.minimum<<" max="<<info.maximum
                     <<" fuzz="<<info.fuzz<<" flat="<<info.flat
                     <<" resolution="<<info.resolution<<"\n";
        else
            std::cout<<a.label<<" unavailable errno="<<errno<<"\n";
    }
    close(fd);
    std::cout<<"CP-KOBO-023 evdev axis probe finished (read-only)\n";
    return 0;
}
