from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""  # anon key for client
    supabase_service_key: str = ""  # service role for server ops

    # Anthropic
    anthropic_api_key: str = ""
    default_model: str = "claude-sonnet-4-5-20250929"
    complex_model: str = "claude-opus-4-6"

    # App
    app_name: str = "CaseCommand v2.0"
    max_upload_size: int = 50 * 1024 * 1024  # 50MB

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings():
    return Settings()
