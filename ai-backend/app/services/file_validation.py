"""Validação de upload: tamanho e magic bytes (PNG/JPG/PDF apenas)."""

from __future__ import annotations

from fastapi import HTTPException, UploadFile, status

from ..core.config import Settings

ALLOWED: tuple[tuple[str, tuple[bytes, ...]], ...] = (
    ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    ("image/jpeg", (b"\xff\xd8\xff",)),
    ("application/pdf", (b"%PDF-",)),
)


async def read_validated_upload(file: UploadFile, settings: Settings) -> tuple[bytes, str]:
    """Lê no máximo max_upload_bytes+1 e valida assinatura do arquivo."""
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo excede o limite de {settings.max_upload_bytes} bytes.",
        )
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio.")

    declared = (file.content_type or "").split(";")[0].strip().lower()
    matched: str | None = None
    for mime, signatures in ALLOWED:
        if any(content.startswith(sig) for sig in signatures):
            matched = mime
            break
    if matched is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato inválido. Aceitos: PNG, JPG e PDF (validado por magic bytes).",
        )
    if declared not in {"", "application/octet-stream", matched}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Content-Type não corresponde à assinatura do arquivo.",
        )
    return content, matched
