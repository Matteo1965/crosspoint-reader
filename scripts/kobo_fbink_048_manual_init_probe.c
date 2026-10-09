/* CP-KOBO-048: manual-only guarded FBInk FBFD_AUTO initialization probe.
 * MANUAL TEST ONLY. No auto-start, drawing or display refresh.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <sys/stat.h>
#include <time.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include "fbink.h"

static const char * const marker="/mnt/onboard/.adds/crosspoint/logs/cp-kobo-048.attempted";
static const char * const logfile="/mnt/onboard/.adds/crosspoint/logs/cp-kobo-048-init.txt";
static int durable_log(const char *line) {
    int fd=open(logfile,O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC,0600);
    if(fd<0)return -1;
    size_t len=strlen(line);
    ssize_t nw=write(fd,line,len);
    int ok=(nw==(ssize_t)len && fsync(fd)==0)?0:-1;
    close(fd);
    return ok;
}
static int record_attempt_once(void) {
    int fd=open(marker,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
    if(fd<0)return -1;
    const char msg[]="ATTEMPTED: never retry automatically\n";
    int ok=(write(fd,msg,sizeof msg-1)==(ssize_t)(sizeof msg-1) && fsync(fd)==0)?0:-1;
    close(fd);
    if(ok != 0) return -1;
    int dfd=open("/mnt/onboard/.adds/crosspoint/logs",O_RDONLY|O_DIRECTORY|O_CLOEXEC);
    if(dfd<0)return -1;
    ok=fsync(dfd);
    close(dfd);
    return ok;
}
static int preflight(void) {
    FILE *fp=fopen("/mnt/onboard/.kobo/version","r");
    if(!fp){fprintf(stderr,"MODEL_OPEN_ERROR errno=%d\n",errno);return 10;}
    char line[256]={0};
    if(!fgets(line,sizeof line,fp)){fclose(fp);fputs("MODEL_READ_ERROR\n",stderr);return 11;}
    fclose(fp);
    size_t n=strcspn(line,"\r\n");
    if(n<3 || line[n-3]!='3' || line[n-2]!='9' || line[n-1]!='5'){
       fputs("MODEL_MISMATCH (requires 395)\n",stderr);return 12;
    }
    int fd=open("/dev/fb0",O_RDONLY|O_NONBLOCK|O_CLOEXEC);
    if(fd<0){fprintf(stderr,"FB_OPEN_ERROR errno=%d\n",errno);return 13;}
    struct fb_var_screeninfo v={0};
    struct fb_fix_screeninfo f={0};
    int rc=(ioctl(fd,FBIOGET_VSCREENINFO,&v)==0 && ioctl(fd,FBIOGET_FSCREENINFO,&f)==0)?0:14;
    close(fd);
    if(rc){fputs("FB_IOCTL_ERROR\n",stderr);return rc;}
    if(v.xres!=1072||v.yres!=1448||v.bits_per_pixel!=32||v.rotate!=3||
       v.red.offset!=0||v.red.length!=8||v.green.offset!=8||v.green.length!=8||
       v.blue.offset!=16||v.blue.length!=8||v.transp.offset!=24||v.transp.length!=8||
       f.line_length!=4288){
        fputs("FB_METADATA_MISMATCH\n",stderr);return 15;
    }
    puts("CP-KOBO-048 PREFLIGHT PASS: model 395, fb metadata verified");
    return 0;
}
int main(int argc,char **argv){
    if(argc!=2||strcmp(argv[1],"--explicit-init-risk-acknowledged")!=0){
        fputs("CP-KOBO-048 BLOCKED: manual only; init requires explicit argument\n",stderr);
        return 64;
    }
    int rc=preflight();
    if(rc)return rc;
    if(durable_log("CP-KOBO-048 PREFLIGHT PASS\n")!=0) return 30;
    if(record_attempt_once()!=0) {
        fputs("CP-KOBO-048 ALREADY_ATTEMPTED_OR_MARKER_ERROR\n",stderr);
        return 31;
    }
    if(durable_log("CP-KOBO-048 INIT ENTER\n")!=0) return 32;
    fflush(NULL);
    const FBInkConfig cfg={0};
    fprintf(stderr,"CP-KOBO-048 INIT ENTER (FBFD_AUTO)\n");
    fflush(stderr);
    rc=fbink_init(FBFD_AUTO,&cfg);
    fprintf(stderr,"CP-KOBO-048 INIT RETURN rc=%d\n",rc);
    if(durable_log(rc==0?"CP-KOBO-048 INIT RETURN SUCCESS\n":"CP-KOBO-048 INIT RETURN FAILED\n")!=0)return 33;
    if(rc!=0)return 20;
    FBInkState state={0};
    fbink_get_state(&cfg,&state);
    printf("device_id=%u\nis_mtk=%u\nbpp=%u\npixel_format_enum=%u\nrotation=%u\nscreen=%ux%u\n",
      (unsigned)state.device_id,(unsigned)state.is_mtk,(unsigned)state.bpp,
      (unsigned)state.pixel_format,(unsigned)state.current_rota,
      state.screen_width,state.screen_height);
    if(durable_log("CP-KOBO-048 FINISHED\n")!=0)return 34;
    puts("CP-KOBO-048 FINISHED");
    return 0;
}
