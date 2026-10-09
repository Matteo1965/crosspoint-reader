/* CP-KOBO-046: COMPILE-ONLY guarded FBInk FBFD_AUTO initialization probe.
 * DO NOT DEPLOY until complete init call graph and recovery gates cleared.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include "fbink.h"

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
    puts("CP-KOBO-046 PREFLIGHT PASS: model 395, fb metadata verified");
    return 0;
}
int main(int argc,char **argv){
    if(argc!=2||strcmp(argv[1],"--explicit-init-risk-acknowledged")!=0){
        fputs("CP-KOBO-046 BLOCKED: compile-only source; init requires explicit argument\n",stderr);
        return 64;
    }
    int rc=preflight();
    if(rc)return rc;
    fflush(NULL);
    const FBInkConfig cfg={0};
    fprintf(stderr,"CP-KOBO-046 INIT ENTER (FBFD_AUTO)\n");
    fflush(stderr);
    rc=fbink_init(FBFD_AUTO,&cfg);
    fprintf(stderr,"CP-KOBO-046 INIT RETURN rc=%d\n",rc);
    if(rc!=0)return 20;
    FBInkState state={0};
    fbink_get_state(&cfg,&state);
    printf("device_id=%u\nis_mtk=%u\nbpp=%u\npixel_format_enum=%u\nrotation=%u\nscreen=%ux%u\n",
      (unsigned)state.device_id,(unsigned)state.is_mtk,(unsigned)state.bpp,
      (unsigned)state.pixel_format,(unsigned)state.current_rota,
      state.screen_width,state.screen_height);
    puts("CP-KOBO-046 FINISHED");
    return 0;
}
