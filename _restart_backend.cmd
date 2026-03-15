@echo off
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
start "" /B cmd /c start-backend-live.cmd
timeout /t 12 >nul
curl http://127.0.0.1:8000/health
