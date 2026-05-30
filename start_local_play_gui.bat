@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"

cd /d "%PROJECT_ROOT%"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python not found in PATH.
  echo Install Python or add it to PATH, then retry.
  pause
  exit /b 1
)

python "%PROJECT_ROOT%scripts\local_play_gui.py"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] local_play_gui.py exited with code %EXIT_CODE%.
  pause
)

exit /b %EXIT_CODE%
