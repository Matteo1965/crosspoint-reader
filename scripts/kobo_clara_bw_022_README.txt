CP-KOBO-022 — Kobo Clara BW read-only diagnostic (NOT CrossPoint Reader)

This package is intended for ONE manual hardware inventory on Kobo Clara BW.
It does not display CrossPoint, install firmware, stop Nickel, or use evdev grabs.

BEFORE FIRST USE
1. Preserve your existing NickelMenu and KOReader files.
2. Unzip the package on your Windows PC.
3. Copy ONLY the contents of the crosspoint folder to:
   KOBOeReader/.adds/crosspoint/
4. Add the SINGLE line from nickelmenu-entry.txt to an existing NickelMenu
   configuration file inside KOBOeReader/.adds/nm/.
   Do not replace or overwrite your existing configuration.
5. Safely eject the Kobo, then use your existing NickelMenu reload/restart
   procedure as applicable. Open NickelMenu > Clara BW HW Probe.
6. The probe runs briefly without a user interface. Reconnect USB and read:
   KOBOeReader/.adds/crosspoint/logs/clara-bw-hardware.txt

SAFETY
- This is a diagnostic, not a Kobo CrossPoint firmware or reader app.
- The ARM executable is statically linked but NOT YET TESTED ON A CLARA BW.
- The script does not request root, stop Nickel, update firmware, or draw.
- It uses 'timeout 15' where available; otherwise the diagnostic is run
  without a hard timeout. This short read-only probe is not the 120-second
  CrossPoint watchdog.
- If the log is absent, the executable might not run on your Kobo.
- Remove the added NickelMenu line to undo the menu entry.
- A test failure may require the ordinary Kobo restart; no safe operation
  can be guaranteed before actual device validation.

Please share the hardware TXT result, not private books or account files.
