@echo off
rem Installs TradingAgents (Tauric Research, Apache-2.0, release v0.3.1) into %USERPROFILE%\tradingagents with its own private Python environment.
rem Needs Git for Windows: https://git-scm.com/download/win . About 3 to 5 minutes. Nothing is sent anywhere.
set DEST=%USERPROFILE%\tradingagents
where git >nul 2>nul || (echo Git is needed: https://git-scm.com/download/win & pause & exit /b 1)
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
if not exist "%DEST%\.git" (git clone --depth 1 --branch v0.3.1 https://github.com/TauricResearch/TradingAgents "%DEST%") else (git -C "%DEST%" fetch --depth 1 origin tag v0.3.1 & git -C "%DEST%" checkout -q v0.3.1)
cd /d "%DEST%"
%PY% -m venv .venv
.venv\Scripts\python -m pip install -q --upgrade pip
.venv\Scripts\pip install -q .
echo.
echo Installed in %DEST%
echo Next: put your OpenAI key in the .env file in the Tuned in Markets folder (see .env.example), then restart Tuned in Markets.
pause
