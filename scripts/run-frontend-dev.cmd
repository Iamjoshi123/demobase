@echo off
setlocal

set ROOT=%~dp0..
cd /d %ROOT%\frontend

if exist .next rd /s /q .next

npm run dev

endlocal
