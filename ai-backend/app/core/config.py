"""Configuração centralizada via variáveis de ambiente (.env).

Nenhuma chave de API é lida pelo Electron: tudo passa por aqui.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # /ai-backend (app/core/config.py -> parents[2])


class Settings(BaseSettings):
    app_name: str = "AF Copilot AI Backend"
    environment: str = "local"

    # LLM (somente no backend)
    gemini_api_key: str = Field(default="", description="Chave da API Google Gemini")
    gemini_model: str = "gemini-3.8-flash"
    # Usado se o modelo principal atingir cota/indisponibilidade.
    gemini_fallback_models: Annotated[list[str], NoDecode] = [
        "gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
    ]
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Segurança
    # NoDecode: o .env usa lista separada por vírgulas, não JSON.
    cors_origins: Annotated[list[str], NoDecode] = ["af://af-desktop"]
    max_upload_bytes: int = 5 * 1024 * 1024  # 5 MB
    auth_token_path: Path = BASE_DIR / "runtime" / "auth_token"

    # Persistência local / Fase 2
    vector_store_dir: Path = BASE_DIR / "vector_store"
    upload_dir: Path = BASE_DIR / "runtime" / "uploads"
    database_url: str | None = None  # ex.: mongodb://localhost:27017 (Fase 2)
    sqlite_path: Path | None = BASE_DIR / "runtime" / "af_copilot.db"

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", "gemini_fallback_models", mode="before")
    @classmethod
    def _split_comma_list(cls, value: object) -> object:
        """Aceita lista separada por vírgulas em .env."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
