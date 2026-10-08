// CP-KOBO-025: time-limited read-only raw event diagnostic for Clara BW.
// No EVIOCGRAB, no display writes, no modification of input configuration.
#include <linux/input.h>
#include <sys/ioctl.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <chrono>
int main(int argc,char**argv) {
 const char* path=argc>1?argv[1]:"/dev/input/event1";
 int fd=open(path,O_RDONLY|O_NONBLOCK|O_CLOEXEC);
 if(fd<0){std::printf("ERROR open %s errno=%d %s\n",path,errno,std::strerror(errno));return 2;}
 char name[128]={};
 if(ioctl(fd,EVIOCGNAME(sizeof(name)),name)<0)
   std::snprintf(name,sizeof(name),"<name unavailable>");
 std::printf("CP-KOBO-025 device=%s name=%s\n",path,name);
 std::printf("READ_ONLY no_grab=1 duration_seconds=30\n");
 std::fflush(stdout);
 using clock=std::chrono::steady_clock;
 auto end=clock::now()+std::chrono::seconds(30);
 unsigned long count=0;
 while(clock::now()<end) {
   auto left=std::chrono::duration_cast<std::chrono::milliseconds>(end-clock::now()).count();
   if(left<=0) break;
   pollfd p{fd,POLLIN,0};
   int result=poll(&p,1,left<250?static_cast<int>(left):250);
   if(result<0){if(errno==EINTR)continue;std::printf("ERROR poll errno=%d\n",errno);close(fd);return 3;}
   if(result==0)continue;
   if(p.revents&(POLLERR|POLLNVAL)){std::printf("ERROR poll revents=%d\n",p.revents);close(fd);return 4;}
   input_event e{};
   while(read(fd,&e,sizeof(e))==sizeof(e)){
     // Record a bounded number of events while always draining device input.
     if(count<4000){
       const auto elapsed_ms=std::chrono::duration_cast<std::chrono::milliseconds>(
         clock::now()-(end-std::chrono::seconds(30))).count();
       std::printf("EV %lu elapsed_ms=%lld type=%u code=%u value=%d\n",
         count,static_cast<long long>(elapsed_ms),e.type,e.code,e.value);
       std::fflush(stdout);
     }
     ++count;
   }
 }
 std::printf("CP-KOBO-025 finished total_events=%lu logged_events=%lu\n",
   count,count<4000?count:4000UL);
 close(fd);
 return 0;
}
