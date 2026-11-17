"""Sanitização LGPD no servidor (Zero-Trust: revalida o que veio do cliente)."""

from __future__ import annotations

import re
import unicodedata

PII_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),  # CPF
    re.compile(r"\b\d{15}\b"),  # CNS
    re.compile(r"\b(?:0[1-9]|[12]\d|3[01])[/-](?:0[1-9]|1[0-2])[/-](?:18|19|20)\d{2}\b"),
    re.compile(r"\b(?:prontu[aá]rio|registro|hist[oó]rico)\s*[:#]?\s*[\w\-/]{3,}\b", re.I),
    re.compile(r"[\w.%-]+@[\w.-]+\.[a-z]{2,}", re.I),
    re.compile(r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}[ -]?\d{4}\b"),
    re.compile(r"\b(?:[A-ZÀ-Ý][a-zà-ÿ]{2,}\s+){1,3}[A-ZÀ-Ý][a-zà-ÿ]{2,}\b"),  # nome heurístico
)

CID10_RE = re.compile(r"\b(?:[A-TV-Z][A-TV-Z]?|[A-TV-Z])\d{2}(?:\.\d{1,4})?\b")
DOSAGE_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|g|ml|ui|u|unid(?:ades)?|cp|comprimid(?:o|os)|amp|frasco|%)?\b", re.I)

CLINICAL_LEXICON: frozenset[str] = frozenset({
    "hipertensao", "diabetes", "asma", "dpoc", "epilepsia", "artrite", "psoriasi",
    "crohn", "colite", "hepatite", "hiv", "aids", "cancer", "oncologia",
    "transplante", "imunossupressao", "antiinflamatorio", "anticonvulsivante",
    "antirretroviral", "biologico", "insulina", "creatinina", "hemograma",
    "transaminases", "glicemia", "hba1c", "colesterol", "gravidez", "gestante",
    "lactacao", "pediatrico", "contraindicacao", "posologia", "oral",
    "intravenosa", "infusao", "tratamento", "diagnostico", "sintoma", "exame",
    "laboratorio", "imagem", "ressonancia", "tomografia", "ultrassom",
    "eletrocardiograma", "lme", "ime", "pcdt", "ceaf", "protocolo", "dispensacao",
    "lactacao", "pediatrico", "contraindicacao", "ressonancia", "ultrassom",
    "consultorio", "antiinflamatorio", "biologico", "imunossupressao",
})

DRUG_LEXICON: frozenset[str] = frozenset({
    "paracetamol", "ibuprofeno", "dipirona", "amoxicilina", "azitromicina",
    "ceftriaxona", "metformina", "insulina", "losartana", "enalapril",
    "anlodipino", "hidroclorotiazida", "atorvastatina", "rosuvastatina",
    "sinvastatina", "aspirina", "clopidogrel", "omeprazol", "pantoprazol",
    "salbutamol", "budesonida", "formoterol", "tiotropio", "carbamazepina",
    "fenitoina", "valproato", "levotiroxina", "prednisona", "dexametasona",
    "metotrexato", "adalimumabe", "infliximabe", "etanercepte", "rituximabe",
    "trastuzumabe", "bevacizumabe", "imatinibe", "tenofovir", "lamivudina",
    "efavirenz", "lopinavir", "ritonavir", "darunavir", "sofosbuvir",
    "ribavirina", "micofenolato", "ciclosporina", "tacrolimo", "sirolimo",
    "azatioprina", "sildenafil", "bosentana", "epoprostenol", "treprostinil",
    # alinhados ao lexicon do cliente (desktop-client)
    "dexametasona", "ranitidina", "etoposido", "interferon", "ledipasvir",
})


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    ascii_only = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9\s.\-/]", " ", ascii_only).strip()


def _redact(text: str) -> str:
    result = text
    for pattern in PII_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def sanitize_payload(payload: dict[str, object]) -> dict[str, object]:
    """Recebe os campos do request e devolve somente sinais clínicos autorizados."""
    joined = " ".join(
        [str(payload.get("safe_text", ""))]
        + [str(v) for key in ("drugs", "dosages", "cid10", "clinical_terms")
           for v in (payload.get(key) or [])]  # type: ignore[operator]
    )
    redacted = _redact(joined[:8000])

    cid10 = list(dict.fromkeys(CID10_RE.findall(redacted)))[:20]
    dosages = list(dict.fromkeys(d.strip() for d in DOSAGE_RE.findall(redacted) if d.strip()))[:30]

    drugs: list[str] = []
    clinical_terms: list[str] = []
    for token in _normalize(redacted).split():
        bare = token.replace(".", "").replace("-", "").replace("/", "")
        if bare in DRUG_LEXICON and bare not in drugs:
            drugs.append(bare)
        elif (bare in CLINICAL_LEXICON or token in CLINICAL_LEXICON) and token not in clinical_terms:
            clinical_terms.append(token)

    drugs = drugs[:30]
    clinical_terms = clinical_terms[:50]
    safe_text = " ".join([*drugs, *dosages, *cid10, *clinical_terms])[:4000]

    return {
        "drugs": drugs,
        "dosages": dosages,
        "cid10": cid10,
        "clinical_terms": clinical_terms,
        "safe_text": safe_text,
    }
