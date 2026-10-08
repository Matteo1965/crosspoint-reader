// CP-KOBO-030 static ARM file-writing control, no device access.
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <cstdio>
#include <cstring>
int main(int argc,char**argv){
 if(argc!=2){std::fprintf(stderr,"usage: probe OUTPUT\n");return 2;}
 int fd=open(argv[1],O_CREAT|O_TRUNC|O_WRONLY|O_CLOEXEC,0644);
 if(fd<0){std::fprintf(stderr,"open errno=%d\n",errno);return 3;}
 const char text[]="CP-KOBO-030 ARM WRITE OK\n";
 if(write(fd,text,sizeof(text)-1)!=(ssize_t)(sizeof(text)-1)){close(fd);return 4;}
 if(fsync(fd)!=0){std::fprintf(stderr,"fsync errno=%d\n",errno);close(fd);return 5;}
 if(close(fd)!=0)return 6;
 return 0;
}
