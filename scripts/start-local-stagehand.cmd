@echo off
setlocal

set ROOT=%~dp0..
set BRIDGE_OUT=%ROOT%\stagehand-bridge-out.log
set BRIDGE_ERR=%ROOT%\stagehand-bridge-err.log
set BACKEND_OUT=%ROOT%\backend-out.log
set BACKEND_ERR=%ROOT%\backend-err.log
set FRONTEND_OUT=%ROOT%\frontend-out.log
set FRONTEND_ERR=%ROOT%\frontend-err.log

call "%~dp0stop-local.cmd"

del /f /q "%BRIDGE_OUT%" "%BRIDGE_ERR%" "%BACKEND_OUT%" "%BACKEND_ERR%" "%FRONTEND_OUT%" "%FRONTEND_ERR%" >nul 2>nul

start "agent-vinod-stagehand-bridge" /min cmd /c call "%~dp0run-stagehand-bridge.cmd" ^> "%BRIDGE_OUT%" 2^> "%BRIDGE_ERR%"

start "agent-vinod-backend" /min cmd /c call "%~dp0run-backend-stagehand.cmd" ^> "%BACKEND_OUT%" 2^> "%BACKEND_ERR%"

start "agent-vinod-frontend" /min cmd /c call "%~dp0run-frontend-dev.cmd" ^> "%FRONTEND_OUT%" 2^> "%FRONTEND_ERR%"

echo Stagehand bridge log: %BRIDGE_OUT%
echo Backend log: %BACKEND_OUT%
echo Frontend log: %FRONTEND_OUT%

endlocal
