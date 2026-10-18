@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")
if not exist .venv\Scripts\python.exe (
  %PY% -m venv .venv
  if errorlevel 1 goto failed
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Open http://127.0.0.1:8765 in your browser.
echo Keep this window open. Press Ctrl+C to stop.
.venv\Scripts\python.exe app.py
exit /b %errorlevel%
:failed
echo Setup failed. Install Python 3.12 or newer, then retry.
pause
exit /b 1
