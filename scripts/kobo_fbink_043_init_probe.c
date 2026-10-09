/* CP-KOBO-043: FBInk init probe. COMPILE-ONLY, NOT FOR DEVICE DEPLOYMENT.
 * Intended future usage requires explicit safety approval after full call-graph audit.
 * Does not request drawing/refresh but fbink_init may have device side effects.
 */
#include <stdio.h>
#include <string.h>
#include "fbink.h"
int main(int argc, char **argv) {
    if (argc != 2 || strcmp(argv[1], "--explicit-init-risk-acknowledged") != 0) {
        fputs("CP-KOBO-043 BLOCKED: no implicit FBInk initialization.\n", stderr);
        return 64;
    }
    const FBInkConfig cfg = {0};
    int fd = fbink_open();
    if (fd < 0) { fputs("CP-KOBO-043 OPEN FAILED\n", stderr); return 2; }
    int rc = fbink_init(fd, &cfg);
    if (rc != 0) { fputs("CP-KOBO-043 INIT FAILED\n", stderr); fbink_close(fd); return 3; }
    FBInkState state = {0};
    fbink_get_state(&cfg, &state);
    printf("CP-KOBO-043 INIT RETURNED\n");
    printf("deviceId=%u\n", (unsigned)state.device_id);
    printf("isMTK=%u\n", (unsigned)state.is_mtk);
    printf("bpp=%u\n", (unsigned)state.bpp);
    printf("pixel_format_enum=%u\n", (unsigned)state.pixel_format);
    fbink_close(fd);
    return 0;
}
