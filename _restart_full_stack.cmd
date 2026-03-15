@echo off
setlocal
cd /d "%~dp0"
call scripts\stop-local.cmd
call scripts\start-cloud-stagehand.cmd
endlocal
