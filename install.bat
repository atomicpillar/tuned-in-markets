@echo off
rem One-time install on Windows: a private Python environment and the libraries. About two minutes. Nothing is sent anywhere.
rem The market data and the strategy lab are built by the app itself the first time you run it.
cd /d "%~dp0"
set PYTHONUTF8=1
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% -c "import sys; assert sys.version_info >= (3, 10)" 2>nul || (echo Python 3.10 or newer is needed: https://www.python.org/downloads/ ^(tick "Add python.exe to PATH" in the installer^) & pause & exit /b 1)
echo Setting up a private Python environment...
%PY% -m venv .venv
.venv\Scripts\python -m pip install -q --upgrade pip
.venv\Scripts\pip install -q -r requirements.txt
if not exist data mkdir data
if not exist .env copy .env.example .env >nul
.venv\Scripts\python tools\setup_contact.py
echo.
echo Installed. Start Tuned in Markets by double-clicking run.bat
echo The first start builds your data and the strategy lab in the background. Give it 30 to 40 minutes the very first time.
pause
