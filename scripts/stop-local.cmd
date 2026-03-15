@echo off
setlocal

for %%T in ("agent-vinod-stagehand-bridge" "agent-vinod-backend" "agent-vinod-frontend") do (
  taskkill /FI "WINDOWTITLE eq %%~T" /T /F >nul 2>nul
)

for %%P in (3000 4545 8000) do (
  for /f "tokens=5" %%I in ('netstat -ano ^| findstr :%%P ^| findstr LISTENING') do (
    taskkill /PID %%I /F >nul 2>nul
  )
)

endlocal
