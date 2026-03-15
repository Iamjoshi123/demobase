"""Application configuration loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# Resolve .env from project root (one level above backend/)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./agentic_demo_brain.db"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "demo_brain"

    # LiveKit
    livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "devsecret0123456789devsecret0123456789"

    # LLM providers
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "nvidia/nemotron-nano-9b-v2:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    ollama_base_url: str = "http://localhost:11434"
    disable_anthropic: bool = False
    deterministic_demo_mode: bool = False

    # AWS Bedrock
    aws_bedrock_token: Optional[str] = None
    aws_bedrock_region: str = "us-west-2"
    aws_bedrock_model: str = "anthropic.claude-3-5-haiku-20241022-v1:0"

    # Encryption
    encryption_key: str = "placeholder-generate-a-real-key"

    # Browser
    playwright_headless: bool = True
    enable_browser_use_fallback: bool = False
    enable_stagehand: bool = False
    stagehand_server_mode: str = "bridge"
    stagehand_model_name: str = "openai/gpt-4.1-mini"
    stagehand_cdp_port: int = 9222
    stagehand_bridge_url: str = "http://127.0.0.1:4545"

    # Voice
    enable_voice: bool = False
    voice_provider: str = "local"
    voice_whisper_model: str = "base.en"
    voice_language: str = "en"
    voice_min_transcript_chars: int = 2
    voice_tts_provider: str = "auto"
    voice_tts_voice: str = "en-US-AriaNeural"
    voice_transcript_debug: bool = False
    openai_realtime_model: str = "gpt-realtime"
    openai_realtime_voice: str = "alloy"
    openai_realtime_transcription_model: str = "gpt-4o-mini-transcribe"
    openai_realtime_silence_ms: int = 280

    # Sandbox
    default_allowed_domain: str = "localhost"
    session_timeout_seconds: int = 1800

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    model_config = {"env_file": str(_ENV_FILE), "env_file_encoding": "utf-8"}

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"

    @property
    def has_bedrock(self) -> bool:
        return bool(self.aws_bedrock_token)

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_openrouter(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key) and not self.disable_anthropic


settings = Settings()
