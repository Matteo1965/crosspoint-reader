// CP-KOBO-024: read-only four-corner evdev touch calibration.
// Reads event1 without EVIOCGRAB. Record one contact per prompt.
// Interrupt via physical power button or Ctrl-C; no display writes.
#include <linux/input.h>
#include <sys/ioctl.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <signal.h>
#include <cerrno>
#include <cstring>
#include <cstdio>
#include <cstdint>
static volatile sig_atomic_t stop_flag=0;
static void stop_now(int){stop_flag=1;}
static const char* places[]={"TOP_LEFT","TOP_RIGHT","BOTTOM_LEFT","BOTTOM_RIGHT"};
int main(int argc,char**argv){
 const char* device=argc>1?argv[1]:"/dev/input/event1";
 signal(SIGTERM,stop_now); signal(SIGINT,stop_now);
 int fd=open(device,O_RDONLY|O_NONBLOCK|O_CLOEXEC);
 if(fd<0){std::printf("ERROR open %s: %s\n",device,std::strerror(errno));return 2;}
 char name[128]={}; ioctl(fd,EVIOCGNAME(sizeof(name)),name);
 std::printf("CP-KOBO-024 device=%s name=%s\n",device,name);std::fflush(stdout);
 int stage=0;int x=-1,y=-1;bool active=false,down=false,hasx=false,hasy=false;
 for(;stage<4 && !stop_flag;){
  std::printf("TOUCH %s (one finger), then release; no onscreen markers\n",places[stage]);std::fflush(stdout);
  // At most 25 s per corner (100 s total); no system changes.
  int elapsed=0;bool captured=false;
  while(elapsed<25000&&!stop_flag&&!captured){
   pollfd p{fd,POLLIN,0};int r=poll(&p,1,250);elapsed+=250;
   if(r<0){if(errno==EINTR)continue;std::printf("ERROR poll: %s\n",std::strerror(errno));close(fd);return 3;}
   if(r==0)continue;
   input_event e{};
   while(read(fd,&e,sizeof(e))==sizeof(e)){
    if(e.type==EV_SYN&&e.code==SYN_DROPPED){active=false;down=false;hasx=hasy=false;continue;}
    if(e.type==EV_ABS){
     if(e.code==ABS_MT_TRACKING_ID){
      if(e.value>=0){active=true;hasx=hasy=false;}
      else {active=false; if(down&&hasx&&hasy) captured=true; down=false;}
     }else if(e.code==ABS_MT_POSITION_X){x=e.value;hasx=true;}
     else if(e.code==ABS_MT_POSITION_Y){y=e.value;hasy=true;}
    }
    if(e.type==EV_SYN&&e.code==SYN_REPORT&&active&&hasx&&hasy) down=true;
    if(captured)break;
   }
  }
  if(!captured){std::printf("TIMEOUT %s\n",places[stage]);close(fd);return 4;}
  std::printf("RESULT %s X=%d Y=%d\n",places[stage],x,y);std::fflush(stdout);stage++;
 }
 close(fd);
 if(stage==4){std::puts("CP-KOBO-024 calibration finished");return 0;}
 std::puts("CP-KOBO-024 interrupted");return 5;
}
