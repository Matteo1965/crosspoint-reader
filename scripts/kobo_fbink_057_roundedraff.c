/* CP-KOBO-057: manual-only FBInk init probe, fail-closed state tracking.
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
#define MARK ROOT "/cp-kobo-057.attempted"
#define LOG ROOT "/cp-kobo-057-state.txt"
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
        fputs("CP-KOBO-057 BLOCKED: explicit acknowledgement required\n",stderr);return 64;
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
    /* CP-KOBO-057: RoundedRaff-inspired Kobo preview.
     * The actual X4 GfxRenderer-based RoundedRaffTheme cannot be invoked
     * from this standalone Linux/FBInk program; we adapt its rounded row,
     * padding and selection vocabulary, without claiming identical rendering.
     */
    if(append_state("DRAW_ENTER")!=0)return 37;
    FBInkConfig clear={0};
    clear.no_refresh=true;
    if(fbink_cls(FBFD_AUTO,&clear,NULL,false)!=0){(void)append_state("CLEAR_FAILED");return 40;}
    if(append_state("CLEAR_RETURNED")!=0)return 41;

    /* RoundedRaff uses rounded filled selectable rows with a small gap.
       Draw 4 rounded-edge gray bars using three adjacent rectangles each. */
    FBInkConfig pill={0};
    pill.bg_color=BG_GRAYE;
    pill.no_refresh=true;
    for(unsigned i=0;i<4;i++){
        unsigned short y=(unsigned short)(440+i*148);
        const FBInkRect top={.left=96,.top=(unsigned short)(y+8),.width=880,.height=92};
        const FBInkRect middle={.left=112,.top=y,.width=848,.height=108};
        if(fbink_cls(FBFD_AUTO,&pill,&top,false)!=0 ||
           fbink_cls(FBFD_AUTO,&pill,&middle,false)!=0){
            (void)append_state("ROW_BACKGROUND_FAILED");return 42;
        }
    }
    const struct {short row; short col; const char *label;unsigned char fontmult;} items[]={
        {2,3,"CROSSPOINT",2},
        {4,3,"HUNGARIAN EDITION",2},
        {7,3,"Kobo Clara BW",2},
        {14,8,"Könyvtár",2},
        {19,8,"Böngésző",2},
        {23,8,"Másolás",2},
        {28,8,"Beállítások",2},
        {37,3,"RoundedRaff  |  Kobo",2}
    };
    for(size_t i=0;i<sizeof(items)/sizeof(items[0]);++i){
        FBInkConfig draw={0};
        draw.fontname=UNIFONT;
        draw.fontmult=items[i].fontmult;
        draw.row=items[i].row;
        draw.col=items[i].col;
        draw.is_flashing=false;
        draw.no_refresh=true;
        int result=fbink_print(FBFD_AUTO,items[i].label,&draw);
        if(result<=0){(void)append_state("DRAW_FAILED");fprintf(stderr,"line=%zu result=%d\\n",i,result);return 43;}
        printf("rendered=%zu\\n",i);
    }
    if(append_state("DRAW_RETURNED")!=0)return 44;
    FBInkConfig refresh={0};
    refresh.is_flashing=false;
    if(append_state("REFRESH_ENTER")!=0)return 45;
    int refresh_rc=fbink_refresh(FBFD_AUTO,0,0,0,0,&refresh);
    if(refresh_rc!=0){(void)append_state("REFRESH_FAILED");return 46;}
    if(append_state("REFRESH_RETURNED")!=0)return 47;
    /* DEVICE_VERIFIED is intentionally not written: requires human Nickel/KOReader check. */
    return 0;
}    /* CP-KOBO-057: FBInk adaptation of RoundedRaff selectable rows.
     * RoundedRaff original uses GfxRenderer::fillRoundedRect; on Kobo
     * paint stepped rounded strips via FBInk grayscale primitives.
     * A bundled DejaVu Sans TTF ensures Hungarian double acute coverage.
     */
    if(append_state("DRAW_ENTER")!=0)return 37;
    FBInkConfig batch={0};
    batch.no_refresh=true;
    if(fbink_cls(FBFD_AUTO,&batch,NULL,false)!=0){(void)append_state("CLEAR_FAILED");return 40;}
    if(append_state("CLEAR_RETURNED")!=0)return 41;
    const char *font="/mnt/onboard/.adds/crosspoint/font-057.ttf";
    int font_rc=fbink_add_ot_font(font,FNT_REGULAR);
    if(font_rc!=0){(void)append_state("FONT_LOAD_FAILED");fprintf(stderr,"font_rc=%d\\n",font_rc);return 48;}
    if(append_state("FONT_LOADED")!=0)return 49;
    const char *names[]={"Könyvtár","Böngésző","Másolás","Beállítások"};
    for(unsigned i=0;i<4;i++){
        const unsigned short x=102,y=(unsigned short)(410+i*190),w=868,h=132;
        /* Discrete strip approximation of 22 px rounded corners;
         * the middle strip covers the full width. */
        for(unsigned j=0;j<11;j++){
            unsigned short inset=(unsigned short)((j<5 ? 5-j : j>5 ? j-5 : 0)*4);
            unsigned short stripy=(unsigned short)(y+j*12);
            FBInkRect bar={.left=(unsigned short)(x+inset),
                           .top=stripy,.width=(unsigned short)(w-2*inset),.height=12};
            int draw_rc=fbink_fill_rect_gray(FBFD_AUTO,&batch,&bar,false,215);
            if(draw_rc!=0){(void)append_state("CARD_FAILED");fprintf(stderr,"card=%u strip=%u rc=%d\\n",i,j,draw_rc);return 50;}
        }
        FBInkOTConfig t={0};
        t.size_px=41;
        t.margins.left=161;
        t.margins.top=(short)(y+37);
        t.margins.right=100;
        t.margins.bottom=0;
        FBInkConfig ink=batch;
        ink.is_bgless=true;
        int rc_text=fbink_print_ot(FBFD_AUTO,names[i],&t,&ink,NULL);
        if(rc_text<=0){(void)append_state("MENU_TEXT_FAILED");fprintf(stderr,"text=%u rc=%d\\n",i,rc_text);return 51;}
        printf("menu_row=%u ok\\n",i);
    }
    FBInkOTConfig header={0};
    header.size_px=53;
    header.margins.left=106;
    header.margins.top=85;
    FBInkConfig fg=batch;
    fg.is_bgless=true;
    if(fbink_print_ot(FBFD_AUTO,"CROSSPOINT",&header,&fg,NULL)<=0){(void)append_state("HEADER_FAILED");return 52;}
    header.size_px=29;
    header.margins.top=160;
    if(fbink_print_ot(FBFD_AUTO,"HUNGARIAN EDITION",&header,&fg,NULL)<=0){(void)append_state("HEADER_FAILED");return 53;}
    FBInkOTConfig caption={0};
    caption.size_px=26;
    caption.margins.left=110;
    caption.margins.top=295;
    if(fbink_print_ot(FBFD_AUTO,"Kobo Clara BW  ·  RoundedRaff",&caption,&fg,NULL)<=0){(void)append_state("CAPTION_FAILED");return 54;}
    if(append_state("DRAW_RETURNED")!=0)return 55;
    FBInkConfig refresh={0};
    if(append_state("REFRESH_ENTER")!=0)return 56;
    int refresh_rc=fbink_refresh(FBFD_AUTO,0,0,0,0,&refresh);
    if(refresh_rc!=0){(void)append_state("REFRESH_FAILED");return 57;}
    if(append_state("REFRESH_RETURNED")!=0)return 58;
    (void)fbink_free_ot_fonts();
    /* DEVICE_VERIFIED is intentionally not written: requires human Nickel/KOReader check. */
    return 0;
}
