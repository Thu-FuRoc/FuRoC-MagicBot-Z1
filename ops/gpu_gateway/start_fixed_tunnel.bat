@echo off
setlocal EnableDelayedExpansion
cd /d %~dp0

if not exist cloudflared.exe (
  echo [ERR] cloudflared.exe not found in current folder.
  exit /b 1
)
if not exist fixed_tunnel.env (
  echo [ERR] fixed_tunnel.env not found.
  exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%a in ("fixed_tunnel.env") do (
  if /I "%%a"=="TUNNEL_TOKEN" set "TUNNEL_TOKEN=%%b"
  if /I "%%a"=="PUBLIC_HOSTNAME" set "PUBLIC_HOSTNAME=%%b"
  if /I "%%a"=="LOCAL_GATEWAY_URL" set "LOCAL_GATEWAY_URL=%%b"
)

if "%TUNNEL_TOKEN%"=="REPLACE_WITH_CLOUDFLARE_TUNNEL_TOKEN" (
  echo [ERR] Please fill TUNNEL_TOKEN in fixed_tunnel.env
  exit /b 1
)
if "%LOCAL_GATEWAY_URL%"=="" set "LOCAL_GATEWAY_URL=http://127.0.0.1:8088"

if not exist runtime mkdir runtime
set "LOG_OUT=runtime\tunnel_fixed.out.log"
set "LOG_ERR=runtime\tunnel_fixed.err.log"

echo [INFO] Starting fixed tunnel to %PUBLIC_HOSTNAME% -> %LOCAL_GATEWAY_URL%
start "Cloudflare Fixed Tunnel" cmd /c "set TUNNEL_TOKEN=%TUNNEL_TOKEN% && cloudflared.exe tunnel run > \"%LOG_OUT%\" 2> \"%LOG_ERR%\""

timeout /t 3 >nul
start "" "https://%PUBLIC_HOSTNAME%"
echo [OK] Tunnel started. URL: https://%PUBLIC_HOSTNAME%
echo [LOG] %LOG_OUT%
endlocal
