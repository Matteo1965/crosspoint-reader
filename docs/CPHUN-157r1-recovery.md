# CPHUN-157r1 hardware-button recovery

The CPHUN-157 four-fix firmware compiled and passed CI, but the X4 hardware buttons do not function on the user's device. **Do not distribute the CPHUN-157 artifact as a working build.** Compilation and unit tests did not exercise the physical buttons.

## Regression quarantine

The two new input changes are both rolled back to the byte-identical last hardware-tested CPHUN-152 source:
- `lib/hal/HalGPIO.cpp` and `.h` (remove raw ADC polling helper);
- `src/main.cpp` (restore original low-power idle loop);
- `src/activities/UiListActivity.cpp` and `.h` (restore original list navigation / RenderLock strategy).

The CI workflow checks that these five files are unchanged relative to `agent/cphun-152-hyphen-export`. Do not reintroduce either input change until each is isolated behind its own build and verified on real X4 hardware.

## Remaining fixes under test

- Chapter position on menu re-entry (restore the adapter *after* the CPHUN-152 source regeneration chain).
- End-of-book menu atomic selection.
- Sleep BMP rewind safety; **no reuse of Hungarian Edition's custom grayscale Book > Cover image pipeline** in SleepActivity.

USB remains unchanged and out of scope.

## Release gate

First verify hardware keys (front, side and Power) in book reading, menu navigation, and after waking from sleep. Only then test the remaining fixes. If buttons still fail, revert fully to the known working CPHUN-152 artifact from run 36193506435 and inspect shared build dependencies/submodule versions before trying another feature integration.
