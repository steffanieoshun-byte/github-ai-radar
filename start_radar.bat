@echo off
setlocal
cd /d "%~dp0"

set "RADAR_URL=http://127.0.0.1:8765/"
set "RADAR_HEALTH=http://127.0.0.1:8765/health"

echo [GitHub AI Radar] Checking local service...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -Uri '%RADAR_HEALTH%' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch { exit 1 }"
if not errorlevel 1 goto open_app

if not exist ".venv\Scripts\python.exe" (
  echo [GitHub AI Radar] Creating Python virtual environment...
  python -m venv .venv
  if errorlevel 1 goto failed
)

if not exist ".env" if exist ".env.example" (
  echo [GitHub AI Radar] Creating local .env from .env.example...
  copy ".env.example" ".env" >nul
)

echo [GitHub AI Radar] Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed

echo [GitHub AI Radar] Starting server...
start "GitHub AI Radar Server" cmd /k ""%cd%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8765"

echo [GitHub AI Radar] Waiting for service...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(30); do { try { $r=Invoke-WebRequest -Uri '%RADAR_HEALTH%' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; Start-Sleep -Milliseconds 500 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 goto failed

:open_app
echo [GitHub AI Radar] Opening %RADAR_URL%
start "" "%RADAR_URL%"
exit /b 0

:failed
echo.
echo [GitHub AI Radar] Startup failed. Check the messages above.
pause
exit /b 1
