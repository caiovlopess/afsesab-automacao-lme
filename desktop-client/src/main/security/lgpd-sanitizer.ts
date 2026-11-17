/**
 * Filtro LGPD no cliente (Zero-Trust).
 *
 * REGRA: antes de qualquer dado sair do Electron em direção ao backend,
 * apenas fármaco, dosagem, CID-10 e termos clínicos podem trafegar.
 *
 * Estratégia em duas camadas:
 *  1. REDACTION  -> remove PII estruturado (CPF, CNS, data de nascimento,
 *                  prontuário, nome próprio heurístico, e-mail, telefone).
 *  2. WHITELIST  -> só preserva tokens que casam com CID-10, dosagem,
 *                  vocabulário clínico ou nomes de fármacos conhecidos.
 *
 * AVISO: remoção de nomes por regex é heurística (best-effort). Em produção,
 * complementar com NER e validar com o time de privacidade (LGPD Arts. 6º/7º).
 */

import type { RawContext, SanitizedContext } from '../../shared/types';

/** Padrões de PII que jamais devem deixar o processo local. */
const PII_PATTERNS: RegExp[] = [
  /\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b/g,                       // CPF
  /\b\d{15}\b/g,                                              // CNS (15 dígitos)
  /\b(?:0[1-9]|[12]\d|3[01])[\/\-](?:0[1-9]|1[0-2])[\/\-](?:18|19|20)\d{2}\b/g, // data de nascimento
  /\b(?:prontu[áa]rio|prontuario|registro|hist[óo]rico|histórico)\s*[:#]?\s*[\w\-\/]{3,}\b/gi,
  /\b[\w.%-]+@[\w.-]+\.[a-z]{2,}\b/gi,                        // e-mail
  /\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}[\s-]?\d{4}\b/g, // telefone
  // Nome próprio heurístico: 2-4 palavras capitalizadas (pode ter falsos positivos)
  /\b(?:[A-ZÀ-Ý][a-zà-ÿ]{2,}\s+){1,3}[A-ZÀ-Ý][a-zà-ÿ]{2,}\b/g,
];

/** CID-10: letra A-T ou V-Z + 2 dígitos + opcional .xxx */
const CID10_RE = /\b(?:[A-TV-Z][A-TV-Z]?|[A-TV-Z])\d{2}(?:\.\d{1,4})?\b/g;

/** Dosagem: valor + unidade farmacêutica comum. */
const DOSAGE_RE = /\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|g|ml|ui|u|unid(?:ades)?|cp|comprimid(?:o|os)|amp|frasco|%)?\b/gi;

/** Vocabulário clínico mínimo (ampliar com os termos dos PCDTs indexados). */
const CLINICAL_LEXICON = new Set<string>([
  'hipertensao', 'hipertensão', 'diabetes', 'asma', 'dpoc', 'epilepsia', 'artrite',
  'psoriasi', 'psoríase', 'crohn', 'colite', 'hepatite', 'hiv', 'aids', 'cancer', 'câncer',
  'oncologia', 'transplante', 'imunossupressao', 'imunossupressão', 'anti-inflamatorio',
  'anticonvulsivante', 'antirretroviral', 'biologico', 'biológico', 'insulina',
  'creatinina', 'hemograma', 'transaminases', 'glicemia', 'hba1c', 'colesterol',
  'gravidez', 'gestante', 'lactacao', 'lactação', 'pediatrico', 'pediátrico',
  'contraindicacao', 'contraindicação', 'posologia', 'via', 'oral', 'intravenosa',
  'infusao', 'infusão', 'tratamento', 'diagnostico', 'diagnóstico', 'sintoma',
  'exame', 'laboratorio', 'laboratório', 'imagem', 'ressonancia', 'ressonância',
  'tomografia', 'ultrassom', 'eletrocardiograma', 'consultorio', 'consultório',
  'lme', 'ime', 'pcdt', 'ceaf', 'protocolo', 'dispensacao', 'dispensação',
]);

/** Fármacos comuns do componente especializado (ampliável via config). */
const DRUG_LEXICON = new Set<string>([
  'paracetamol', 'ibuprofeno', 'dipirona', 'amoxicilina', 'azitromicina', 'ceftriaxona',
  'metformina', 'insulina', 'losartana', 'enalapril', 'anlodipino', 'hidroclorotiazida',
  'atorvastatina', 'rosuvastatina', 'sinvastatina', 'aspirina', 'clopidogrel',
  'omeprazol', 'pantoprazol', 'ranitidina', 'salbutamol', 'budesonida', 'formoterol',
  'tiotropio', 'carbamazepina', 'fenitoina', 'valproato', 'levotiroxina', 'prednisona',
  'dexametasona', 'metotrexato', 'adalimumabe', 'infliximabe', 'etanercepte',
  'rituximabe', 'trastuzumabe', 'bevacizumabe', 'imatinibe', 'etoposido',
  'tenofovir', 'lamivudina', 'efavirenz', 'lopinavir', 'ritonavir', 'darunavir',
  'sofosbuvir', 'ledipasvir', 'interferon', 'ribavirina', 'micofenolato',
  'ciclosporina', 'tacrolimo', 'sirolimo', 'azatioprina', 'letalimida',
  'sildenafil', 'bosentana', 'epoprostenol', 'treprostinil', 'macitentana',
]);

function normalize(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9\s.\-\/]/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Protege fármacos conhecidos ANTES da redaction. Sem isso, o heurístico de
 * nome próprio pode apagar "Metformina" quando ele vem após um rótulo como
 * "Descrição Resumida Simpas" (sequência de palavras capitalizadas).
 */
function protectDrugs(input: string): { text: string; restore: (value: string) => string } {
  const saved = new Map<string, string>();
  let text = input;
  let index = 0;
  for (const drug of DRUG_LEXICON) {
    const pattern = new RegExp(`\\b${drug.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
    text = text.replace(pattern, () => {
      const token = `__FARMACO${index++}__`;
      saved.set(token, drug);
      return token;
    });
  }
  return {
    text,
    restore: (value: string) => {
      let result = value;
      for (const [token, drug] of saved) result = result.split(token).join(drug);
      return result;
    },
  };
}

function redact(input: string): string {
  const { text, restore } = protectDrugs(input);
  let output = text;
  for (const pattern of PII_PATTERNS) {
    output = output.replace(pattern, '[REDACTED]');
  }
  return restore(output);
}

/** Extrai e classifica somente os tokens clínicos autorizados. */
export function extractClinicalSignals(input: string): Omit<SanitizedContext, 'capturedAt' | 'source'> {
  const redacted = redact(input);
  const cid10 = Array.from(new Set(redacted.match(CID10_RE) ?? []));
  const dosages = Array.from(new Set(
    (redacted.match(DOSAGE_RE) ?? []).map((d) => d.trim()).filter((d) => /\d/.test(d)),
  ));

  const tokens = normalize(redacted).split(' ').filter(Boolean);
  const drugs: string[] = [];
  const clinicalTerms: string[] = [];

  for (const token of tokens) {
    const bare = token.replace(/[.\-/]/g, '');
    if (DRUG_LEXICON.has(bare)) {
      if (!drugs.includes(bare)) drugs.push(bare);
    } else if (CLINICAL_LEXICON.has(bare) || CLINICAL_LEXICON.has(token)) {
      if (!clinicalTerms.includes(token)) clinicalTerms.push(token);
    }
  }

  const safeTokens = [...drugs, ...dosages, ...cid10, ...clinicalTerms]
    .filter((t) => t && t !== '[REDACTED]');

  return {
    drugs: drugs.slice(0, 30),
    dosages: dosages.slice(0, 30),
    cid10: cid10.slice(0, 20),
    clinicalTerms: clinicalTerms.slice(0, 50),
    safeText: safeTokens.join(' ').slice(0, 4000),
  };
}

/** Converte o contexto bruto do REA em contexto sanitizado pronto para a rede. */
export function sanitizeContext(raw: RawContext): SanitizedContext {
  // Rótulos (labels) NÃO entram: "Descrição Resumida Simpas" é ruído e
  // dispara falsos positivos no heurístico de nome próprio.
  const joined = [
    raw.selectedText,
    ...raw.inputs.map((i) => i.value),
  ].join('\n');

  return {
    ...extractClinicalSignals(joined),
    capturedAt: raw.capturedAt,
    source: 'afsesab',
  };
}
