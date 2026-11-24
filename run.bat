@echo off
rem Starts Tuned in Markets at http://localhost:8810 and opens it in the browser. Keep this window open: closing it stops the app.
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist .venv\Scripts\python.exe (echo Run install.bat first. & pause & exit /b 1)
echo Tuned in Markets is starting. Keep this window open. Press Ctrl+C to stop.
start "" /min cmd /c "timeout /t 6 /nobreak >nul & start http://localhost:8810"
.venv\Scripts\python -u app.py
