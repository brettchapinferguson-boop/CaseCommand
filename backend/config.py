import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")  # anon key for client
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")  # service role for server ops
    
    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    default_model: str = "claude-sonnet-4-5-20250929"
    complex_model: str = "claude-opus-4-6"
    
    # App
    app_name: str = "CaseCommand v2.0"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "https://*.vercel.app"]
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
