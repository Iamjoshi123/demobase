@echo off
setlocal
cd /d "%~dp0"

call :load_env LIVEKIT_URL
call :load_env LIVEKIT_API_KEY
call :load_env LIVEKIT_API_SECRET
call :load_env OPENROUTER_API_KEY
call :load_env OPENAI_API_KEY
call :load_env ENABLE_VOICE
call :load_env VOICE_PROVIDER
call :load_env OPENAI_REALTIME_MODEL

if "%LIVEKIT_URL%"=="" (
  echo LIVEKIT_URL is missing in .env
  exit /b 1
)

if "%LIVEKIT_API_KEY%"=="" (
  echo LIVEKIT_API_KEY is missing in .env
  exit /b 1
)

if "%LIVEKIT_API_SECRET%"=="" (
  echo LIVEKIT_API_SECRET is missing in .env
  exit /b 1
)

if "%OPENAI_API_KEY%"=="" (
  echo OPENAI_API_KEY is missing in .env
  exit /b 1
)

set ENABLE_VOICE=true
set ENABLE_STAGEHAND=true
set STAGEHAND_SERVER_MODE=bridge
set STAGEHAND_MODEL_NAME=openrouter/openai/gpt-4.1-mini
set PLAYWRIGHT_HEADLESS=true
if "%VOICE_PROVIDER%"=="" set VOICE_PROVIDER=openai_realtime
if "%OPENAI_REALTIME_MODEL%"=="" set OPENAI_REALTIME_MODEL=gpt-realtime

call scripts\run-backend-stagehand-cloud.cmd > backend-out.log 2> backend-err.log
endlocal
exit /b %errorlevel%

:load_env
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /c:"%~1=" .env`) do set "%~1=%%B"
exit /b 0




