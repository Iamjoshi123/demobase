@echo off
setlocal

set ROOT=%~dp0..
cd /d %ROOT%\backend

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

C:\Python313\python.exe run.py

endlocal
