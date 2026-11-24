@echo off
rem Updates Tuned in Markets to the latest version. Keeps your .env, data and settings. Stop the app first (Ctrl+C in its window).
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist .venv\Scripts\python.exe (echo Run install.bat first. & pause & exit /b 1)
.venv\Scripts\python tools\update.py
pause
