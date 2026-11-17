"""Banco SQLite embutido para massa de dados fictícia do aplicativo.

SQLite é a melhor escolha aqui: 10k+ usuários é volumes trivial, não há servidor
para gerenciar e o app roda inteiro na máquina local. MongoDB segue reservado
para auditoria/cache na Fase 2.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings, BASE_DIR

settings = get_settings()

_sqlite_path = settings.sqlite_path or (BASE_DIR / "runtime" / "af_copilot.db")
_sqlite_path.parent.mkdir(parents=True, exist_ok=True)

# Permissões restritas no arquivo (best-effort no Windows; no Unix usa 0600).
try:
    _sqlite_path.touch(exist_ok=True)
    _sqlite_path.chmod(0o600)
except OSError:
    pass
if settings.environment == "production":
    try:  # Windows: remove herança e limita ao usuário atual
        import subprocess

        subprocess.run(
            ["icacls", str(_sqlite_path), "/inheritance:r", "/grant:r", f"{__import__('getpass').getuser()}:F"],
            check=False, capture_output=True,
        )
    except Exception:  # noqa: BLE001
        pass

engine = create_engine(
    f"sqlite:///{_sqlite_path}",
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    """Cria as tabelas se ainda não existirem."""
    from ..models import app_user, operational, sql_models  # noqa: F401  (registra os modelos)

    Base.metadata.create_all(bind=engine)


def get_session():
    """Gerador de sessão para injeção de dependência."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
