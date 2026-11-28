@echo off
setlocal

cd /d "%~dp0.."

if not exist "logs" mkdir "logs"

echo. >> "logs\daily_update.log"
echo ======================================== >> "logs\daily_update.log"
echo Update started: %DATE% %TIME% >> "logs\daily_update.log"

".venv\Scripts\python.exe" "scripts\daily_update.py" >> "logs\daily_update.log" 2>&1

set "RESULT=%ERRORLEVEL%"

echo Update finished with exit code %RESULT%: %DATE% %TIME% >> "logs\daily_update.log"

exit /b %RESULT%