@echo off
setlocal

set ROOT=%~dp0..
cd /d %ROOT%\backend

if "%LIVEKIT_URL%"=="" (
  echo LIVEKIT_URL is not set. Point it at your LiveKit Cloud websocket URL.
  exit /b 1
)

if "%LIVEKIT_API_KEY%"=="" (
  echo LIVEKIT_API_KEY is not set.
  exit /b 1
)

if "%LIVEKIT_API_SECRET%"=="" (
  echo LIVEKIT_API_SECRET is not set.
  exit /b 1
)

set ENABLE_STAGEHAND=true
set STAGEHAND_SERVER_MODE=bridge
if "%STAGEHAND_MODEL_NAME%"=="" (
  if not "%OPENROUTER_API_KEY%"=="" (
    set STAGEHAND_MODEL_NAME=openrouter/openai/gpt-4.1-mini
  ) else (
    set STAGEHAND_MODEL_NAME=openai/gpt-4.1-mini
  )
)
set PLAYWRIGHT_HEADLESS=true
set ENABLE_VOICE=true
set VOICE_PROVIDER=openai_realtime
set VOICE_TTS_PROVIDER=auto
if "%OPENAI_REALTIME_MODEL%"=="" (
  set OPENAI_REALTIME_MODEL=gpt-realtime
)
set UVICORN_RELOAD=false
set DISABLE_ANTHROPIC=true
if "%OPENROUTER_API_KEY%"=="" (
  set DETERMINISTIC_DEMO_MODE=true
) else (
  set DETERMINISTIC_DEMO_MODE=false
)

if "%OPENROUTER_MODEL%"=="" (
  set OPENROUTER_MODEL=nvidia/nemotron-nano-9b-v2:free
)

C:\Python313\python.exe run.py

endlocal
