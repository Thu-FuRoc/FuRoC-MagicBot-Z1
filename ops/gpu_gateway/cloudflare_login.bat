@echo off
setlocal
chcp 65001 >nul
cd /d %~dp0

echo [INFO] Working dir: %cd%
if not exist cloudflared.exe (
  echo [ERR] cloudflared.exe not found in this folder.
  echo Put cloudflared.exe in: %cd%
  pause
  exit /b 1
)

echo [STEP] Running Cloudflare login...
cloudflared.exe tunnel login
set EC=%ERRORLEVEL%

echo.
if "%EC%"=="0" (
  echo [OK] Login finished successfully.
  echo Next: tell Codex your target hostname, e.g. gpu-gateway.yourdomain.com
) else (
  echo [ERR] Login failed with code %EC%.
  echo Re-run this script and complete browser authorization.
)

echo.
pause
endlocal
