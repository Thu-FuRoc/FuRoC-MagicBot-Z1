@echo off
setlocal
set URL=http://127.0.0.1:8088
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8088" ^| findstr "LISTENING"') do (
  set PID=%%a
  goto OPEN
)
echo [WARN] Gateway not listening on 8088. Please run start_gateway.bat first.
pause
exit /b 1
:OPEN
start "" "%URL%"
endlocal
