@echo off
setlocal
cd /d "%~dp0"
echo CrossPoint X4 local build
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\build_x4_local.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo BUILD FAILED - error code %RC%
  pause
  exit /b %RC%
)
echo Firmware is in build-output\
pause
