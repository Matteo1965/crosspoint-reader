from pathlib import Path
import runpy

# Compatibility entry point for the CPHUN-135r4b build workflow.
# The actual safe logic now lives directly in cphun135r4b_patch_driver.py.
driver = Path(__file__).with_name("cphun135r4b_patch_driver.py")
runpy.run_path(str(driver), run_name="__main__")
