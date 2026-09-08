from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "ScholarEdge"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Storage paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'scholaredge.db'}"

    # Document processing
    MAX_UPLOAD_SIZE_MB: int = 50
    CHUNK_SIZE_CHARS: int = 600
    CHUNK_OVERLAP_CHARS: int = 100

    # AI Providers (defaults for development)
    LLM_PROVIDER: str = "development"
    EMBEDDING_PROVIDER: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def ensure_directories(self) -> None:
        """Ensure runtime directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
