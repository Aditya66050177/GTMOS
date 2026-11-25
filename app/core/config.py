from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./gtmos.db"
    LLM_API_KEY: str = ""
    LLM_MODE: str = "mock"
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-3.8-flash"

    # Public demo safeguards (used by app/api/public.py, the Vercel entrypoint).
    # Rate limits are per server instance only: on Vercel each warm instance keeps
    # its own counters, so they are a best-effort brake, not a global guarantee.
    DEMO_MAX_BODY_BYTES: int = 16_384
    DEMO_RATE_LIMIT_PER_MINUTE: int = 120
    DEMO_WRITE_LIMIT_PER_MINUTE: int = 30
    DEMO_RESET_LIMIT_PER_MINUTE: int = 5
    DEMO_MAX_SANDBOXES: int = 200
    DEMO_SANDBOX_TTL_SECONDS: int = 7_200
    DEMO_SANDBOX_DIR: str = ""  # empty = a folder next to the template database

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
