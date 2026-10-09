/* CP-KOBO-052: manual-only FBInk init probe, fail-closed state tracking.
 * Manual hardware test: limited risk of Nickel display interference. No drawing or refresh API.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>
#include "fbink.h"
#define ROOT "/mnt/onboard/.adds/crosspoint/logs"
#define MARK ROOT "/cp-kobo-052.attempted"
#define LOG ROOT "/cp-kobo-052-state.txt"
static int append_state(const char *state) {
    int fd=open(LOG,O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC,0600);
    if(fd<0)return -1;
    char line[128];
    int n=snprintf(line,sizeof(line),"state=%s\n",state);
    if(n<0||(size_t)n>=sizeof(line)){close(fd);return -1;}
    size_t done=0;
    while(done<(size_t)n){
        ssize_t k=write(fd,line+done,(size_t)n-done);
        if(k<0&&errno==EINTR)continue;
        if(k<=0){close(fd);return -1;}
        done+=(size_t)k;
    }
    int rc=fsync(fd);
    if(close(fd)!=0)rc=-1;
    return rc;
}
static int create_marker(void) {
    int fd=open(MARK,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
    if(fd<0)return -1;
    const char *msg="ATTEMPTED; DO NOT REPEAT\n";
    ssize_t n=write(fd,msg,strlen(msg));
    int rc=(n==(ssize_t)strlen(msg)&&fsync(fd)==0)?0:-1;
    if(close(fd)!=0)rc=-1;
    if(rc<0)return -1;
    int dfd=open(ROOT,O_RDONLY|O_DIRECTORY|O_CLOEXEC);
    if(dfd<0)return -1;
    rc=fsync(dfd);
    if(close(dfd)!=0)rc=-1;
    return rc;
}
static int preflight(void) {
    int fd=open("/mnt/onboard/.kobo/version",O_RDONLY|O_CLOEXEC);
    if(fd<0)return 10;
    char v[512]; size_t n=0;int invalid=0;
    for(;;){
        if(n==sizeof(v)){char extra;ssize_t k=read(fd,&extra,1);if(k!=0)invalid=1;break;}
        ssize_t k=read(fd,v+n,sizeof(v)-n);
        if(k<0&&errno==EINTR)continue;
        if(k<0){invalid=1;break;}
        if(k==0)break;
        n+=(size_t)k;
    }
    close(fd);
    while(n&&(v[n-1]=='\n'||v[n-1]=='\r'))n--;
    if(invalid||n<3||memcmp(v+n-3,"395",3)!=0)return 11;
    fd=open("/dev/fb0",O_RDONLY|O_NONBLOCK|O_CLOEXEC);
    if(fd<0)return 12;
    struct fb_var_screeninfo var={0};
    struct fb_fix_screeninfo fix={0};
    int err=(ioctl(fd,FBIOGET_VSCREENINFO,&var)!=0||ioctl(fd,FBIOGET_FSCREENINFO,&fix)!=0);
    close(fd);
    if(err)return 13;
    if(var.xres!=1072||var.yres!=1448||var.xres_virtual!=1072||
       var.yres_virtual!=1448||var.xoffset!=0||var.yoffset!=0||
       var.bits_per_pixel!=32||var.rotate!=3||
       var.red.offset!=0||var.red.length!=8||
       var.green.offset!=8||var.green.length!=8||
       var.blue.offset!=16||var.blue.length!=8||
       var.transp.offset!=24||var.transp.length!=8||
       fix.line_length!=4288||fix.smem_len!=6243328)return 14;
    return 0;
}
int main(int argc,char **argv){
    if(argc!=2||strcmp(argv[1],"--explicit-init-risk-acknowledged")!=0){
        fputs("CP-KOBO-052 BLOCKED: explicit acknowledgement required\n",stderr);return 64;
    }
    if(mkdir(ROOT,0700)!=0&&errno!=EEXIST)return 30;
    int rc=preflight();
    if(rc){(void)append_state("PREFLIGHT_FAILED");fprintf(stderr,"preflight_rc=%d\n",rc);return rc;}
    if(append_state("PREFLIGHT_PASS")!=0)return 31;
    if(create_marker()!=0){(void)append_state("ATTEMPT_MARKER_ERROR_OR_ALREADY_EXISTS");return 32;}
    if(append_state("ATTEMPTED")!=0)return 33;
    /* A crash from this point leaves ATTEMPTED without INIT_RETURNED/INIT_FAILED:
     * treat as UNKNOWN_INTERRUPTED and never automatically retry. */
    const FBInkConfig cfg={0};
    rc=fbink_init(FBFD_AUTO,&cfg);
    if(rc!=0){
        if(append_state("INIT_FAILED")!=0)return 34;
        fprintf(stderr,"init_rc=%d\n",rc);return 35;
    }
    if(append_state("INIT_RETURNED")!=0)return 36;
    FBInkState st={0};fbink_get_state(&cfg,&st);
    printf("device_id=%u is_mtk=%u bpp=%u pixel_format=%u rotation=%u screen=%ux%u\n",
        (unsigned)st.device_id,(unsigned)st.is_mtk,(unsigned)st.bpp,
        (unsigned)st.pixel_format,(unsigned)st.current_rota,
        st.screen_width,st.screen_height);
    fflush(stdout);
    if(st.device_id!=395 || !st.is_mtk || st.bpp!=32 || st.screen_width!=1072 || st.screen_height!=1448) {
        (void)append_state("POST_INIT_STATE_MISMATCH");
        return 36;
    }
    FBInkConfig draw={0};
    draw.row=5;
    draw.col=2;
    draw.is_cleared=false;
    draw.is_flashing=false;
    draw.is_centered=false;
    draw.no_refresh=false;
    if(append_state("DRAW_ENTER")!=0)return 37;
    int lines=fbink_print(FBFD_AUTO,"CP-KOBO-052  DISPLAY TEST",&draw);
    if(lines<=0){(void)append_state("DRAW_FAILED");fprintf(stderr,"draw_result=%d\\n",lines);return 38;}
    if(append_state("DRAW_RETURNED")!=0)return 39;
    printf("printed_lines=%d\\n",lines);
    fflush(stdout);
    /* DEVICE_VERIFIED is intentionally not written: requires human Nickel/KOReader check. */
    return 0;
}
