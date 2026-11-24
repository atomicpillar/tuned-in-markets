@echo off
rem Starts Tuned in Markets so your other devices can open it over Tailscale (a free private network between your own devices).
cd /d "%~dp0"
set PYTHONUTF8=1
where tailscale >nul 2>nul || (echo Tailscale is not installed. Get it from https://tailscale.com/download, sign in, then run this again. & pause & exit /b 1)
for /f %%i in ('tailscale ip -4') do set TUNED_HOST=%%i
if "%TUNED_HOST%"=="" (echo Tailscale is installed but not connected. Open the Tailscale app, sign in, switch it on, then run this again. & pause & exit /b 1)
if not exist .venv\Scripts\python.exe (echo Run install.bat first. & pause & exit /b 1)
echo.
echo Tuned in Markets is starting. On your other devices, with Tailscale on, open:
echo.
echo     http://%TUNED_HOST%:8810
echo.
echo Keep this window open. Press Ctrl+C to stop.
.venv\Scripts\python -u app.py
