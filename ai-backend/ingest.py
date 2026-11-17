"""Indexa PDFs de PCDTs/portarias no ChromaDB.

Uso:
    python ingest.py docs/pcdt/*.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.rag_service import RAGService


def main() -> None:
    configure_logging()
    paths = [Path(arg) for arg in sys.argv[1:]]
    if not paths:
        print("Uso: python ingest.py <pdf> [pdf ...]")
        raise SystemExit(1)

    service = RAGService(get_settings())
    count = service.index_documents(paths)
    print(f"Chunks indexados: {count}")


if __name__ == "__main__":
    main()
