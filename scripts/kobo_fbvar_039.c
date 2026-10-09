#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
int main(void) {
    const char *dev = "/dev/fb0";
    int fd = open(dev, O_RDONLY | O_CLOEXEC | O_NONBLOCK);
    if(fd < 0) { fprintf(stderr,"CP-KOBO-039 OPEN_ERROR errno=%d %s\n",errno,strerror(errno)); return 2; }
    struct fb_var_screeninfo v = {0};
    struct fb_fix_screeninfo f = {0};
    if(ioctl(fd,FBIOGET_VSCREENINFO,&v)<0) { fprintf(stderr,"CP-KOBO-039 VINFO_ERROR errno=%d %s\n",errno,strerror(errno));close(fd);return 3; }
    if(ioctl(fd,FBIOGET_FSCREENINFO,&f)<0) { fprintf(stderr,"CP-KOBO-039 FINFO_ERROR errno=%d %s\n",errno,strerror(errno));close(fd);return 4; }
    printf("CP-KOBO-039 START\n");
    printf("device=%s\n",dev);
    printf("resolution=%ux%u\n",v.xres,v.yres);
    printf("virtual_resolution=%ux%u\n",v.xres_virtual,v.yres_virtual);
    printf("offset=%u,%u\n",v.xoffset,v.yoffset);
    printf("bpp=%u\n",v.bits_per_pixel);
    printf("rotation=%u\n",v.rotate);
    printf("grayscale=%u\n",v.grayscale);
    printf("red=%u,%u,%u\n",v.red.offset,v.red.length,v.red.msb_right);
    printf("green=%u,%u,%u\n",v.green.offset,v.green.length,v.green.msb_right);
    printf("blue=%u,%u,%u\n",v.blue.offset,v.blue.length,v.blue.msb_right);
    printf("transp=%u,%u,%u\n",v.transp.offset,v.transp.length,v.transp.msb_right);
    printf("line_length=%u\n",f.line_length);
    printf("smem_len=%u\n",f.smem_len);
    printf("visual=%u\n",f.visual);
    printf("CP-KOBO-039 FINISHED\n");
    close(fd);
    return 0;
}
