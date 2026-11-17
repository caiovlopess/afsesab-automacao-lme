# ai-backend (FastAPI)

Serviço isolado de IA. Toda chave de API vive aqui em `.env`.

## Instalação

```bash
python -m venv .venv
.\.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env           # preencha GEMINI_API_KEY
```

## Rodar

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Ao iniciar, o backend cria `runtime/auth_token`. O Electron lê esse arquivo.

## Indexar protocolos (RAG)

```bash
mkdir docs\pcdt
# coloque os PDFs dos PCDTs do Ministério da Saúde / portarias SESAB em docs\pcdt
python ingest.py docs\pcdt\*.pdf
```

O índice persiste em `vector_store/` (ChromaDB). Embeddings locais
`sentence-transformers/...` são baixados na primeira execução (funciona offline depois).

## Endpoints

| Método | Rota | Autenticação | Descrição |
| --- | --- | --- | --- |
| GET | `/health` | não | Status + índice vetorial |
| POST | `/api/v1/analyze-context` | `X-Internal-Auth-Token` | RAG de protocolos |
| POST | `/api/v1/validate-prescription` | `X-Internal-Auth-Token` | OCR/multimodal de receita/LME |

### Exemplo

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze-context \
  -H "Content-Type: application/json" \
  -H "X-Internal-Auth-Token: $(Get-Content runtime\auth_token)" \
  -d '{"drugs":["metformina"],"dosages":["850 mg"],"cid10":["E11"],"clinicalTerms":["diabetes"],"safeText":"metformina 850 mg E11 diabetes","capturedAt":"2026-01-01T12:00:00Z","source":"afsesab"}'
```

## Segurança implementada

- CORS restrito a `af://af-desktop` (ver `CORS_ORIGINS`);
- token local com `hmac.compare_digest`;
- Pydantic v2 com `extra="forbid"`, limites de tamanho e re-sanitização LGPD;
- upload máx. 5 MB com validação de **magic bytes** (PNG/JPG/PDF);
- logs com redação de CPF/CNS/e-mail;
- handler global que não vaza stack traces.

## Fase 2

`pymongo` já está em `requirements.txt` e o Repository Pattern está pronto.
Defina `DATABASE_URL` no `.env` e descomente o serviço `mongo` no `docker-compose.yml`.
