/**
 * REA — Reverse Engineering & Analysis (Preload do BrowserView do AFSESAB).
 *
 * Observa o DOM da SPA de forma PASSIVA:
 *  - MutationObserver detecta mudanças de conteúdo/atributos;
 *  - 'selectionchange' captura texto selecionado pelo farmacêutico;
 *  - 'input'/'change' captura valores de campos de busca (sem alterá-los).
 *
 * Roda em mundo isolado (contextIsolation) com sandbox, portanto o portal não
 * consegue acessar esta API. Nenhuma mutação é feita no DOM do portal.
 */

import { contextBridge, ipcRenderer } from 'electron';
import type { InspectionResult, RawContext } from '../../shared/types';

/**
 * Metadados de calibração (copiados de selectors.ts).
 * Preloads sandboxed NÃO suportam `require` relativo, por isso os valores
 * precisam estar inline neste arquivo. Fonte: tools/recon/src (source maps).
 */
const PORTAL_ROUTES = {
  dashboard: 'dashboard',
  medicamentos: 'lista-medicamento',
  lme: 'lme',
  cid: 'cid',
  pcdt: 'parametros-pcdt-list',
  atendimento: 'consulta-atendimento',
} as const;
const SEARCH_FIELD_HINTS = {
  medicamentos: ['Lista', 'Código Simpas', 'Medicamento/Descrição Resumida Simpas', 'Programa'],
  lme: ['Status', 'CID', 'Medicamentos', 'Paciente com LME de:', 'Avaliador'],
  cid: ['Código ou Descrição', 'Status'],
  pcdt: ['Patologia', 'CID', 'Medicamento', 'Critérios Obrigatório'],
} as const;
const BLOCKED_FIELD_LABELS = ['CPF', 'CNS', 'Nome do Paciente', 'Prontuário', 'APAC', 'CNES'] as const;
const QUERY_FIELD_MODELS = {
  lista: 'queryFilter.nome',
  codigoSimpas: 'queryFilter.codigo_simpas',
  medicamento: 'queryFilter.procedimento_id',
  medicamentoBusca: 'searchProcedimento',
  programa: 'queryFilter.programa_saude_id',
} as const;
const API_ENDPOINTS = {
  listaMedicamentos: 'GET /api/v1/lista-medicamento/get-lista-medicamento',
  medicamentosPorLista: 'GET /api/v1/lista-medicamento/get-medicamentos-by-lista',
  comunicadosCarrossel: 'GET /api/v1/comunicados/carrossel',
  lmesAguardando: 'GET /api/v1/lmes/get-qtd-aguardando-avaliacao',
} as const;

type InputSnapshot = RawContext['inputs'][number];

let enabled = true;
let lastSentAt = 0;
let pending: RawContext | null = null;
const THROTTLE_MS = 350;

/* ------------------------------------------------------------------ */
/* Helpers de seleção (somente leitura)                                */
/* ------------------------------------------------------------------ */

function cssSelectorFor(el: Element): string {
  if (el.id) return `#${CSS.escape(el.id)}`;
  const parts: string[] = [];
  let node: Element | null = el;
  while (node && node !== document.documentElement) {
    let part = node.tagName.toLowerCase();
    if (node.className && typeof node.className === 'string') {
      const classes = node.className.trim().split(/\s+/).slice(0, 2);
      if (classes.length) part += `.${classes.map((c) => CSS.escape(c)).join('.')}`;
    }
    const parent: Element | null = node.parentElement;
    if (parent) {
      const siblings = Array.from(parent.children).filter((c) => c.tagName === node!.tagName);
      if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
    }
    parts.unshift(part);
    node = parent;
  }
  return parts.join(' > ');
}

function xpathFor(el: Element): string {
  const segments: string[] = [];
  let node: Element | null = el;
  while (node && node.nodeType === Node.ELEMENT_NODE) {
    let segment = node.tagName.toLowerCase();
    const parent: Element | null = node.parentElement;
    if (parent) {
      const sameTag = Array.from(parent.children).filter((c) => c.tagName === node!.tagName);
      if (sameTag.length > 1) segment += `[${sameTag.indexOf(node) + 1}]`;
    }
    segments.unshift(segment);
    node = parent;
  }
  return `/${segments.join('/')}`;
}

function labelFor(el: Element): string {
  const id = el.getAttribute('id');
  if (id) {
    const label = document.querySelector(`label[for="${CSS.escape(id)}"]`);
    if (label?.textContent) return label.textContent.trim().slice(0, 120);
  }
  const parentLabel = el.closest('label');
  if (parentLabel?.textContent) return parentLabel.textContent.trim().slice(0, 120);
  return (el.getAttribute('aria-label') ?? el.getAttribute('placeholder') ?? '').slice(0, 120);
}

/**
 * Campos que jamais devem ser lidos pelo REA. Calibrado a partir do mapa real
 * da tela LME (tools/recon/routes/lme.json): CPF, CNS, Nome do Paciente,
 * Prontuário, APAC e CNES. Bloqueamos na origem, antes de qualquer leitura.
 */
const PII_FIELD_RE = /cpf|cns|nome do paciente|prontu[aá]rio|apac|cnes|paciente com lme/i;

function collectInputs(): InputSnapshot[] {
  const nodes = Array.from(
    document.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(
      'input:not([type=hidden]), select, textarea',
    ),
  );

  const snapshots: InputSnapshot[] = [];
  for (const el of nodes) {
    if (snapshots.length >= 120) break;

    const name = el.getAttribute('name') ?? '';
    const label = labelFor(el);
    const hints = `${label} ${name} ${el.id} ${el.getAttribute('placeholder') ?? ''}`;
    if (PII_FIELD_RE.test(hints)) continue; // skip antes de ler `.value`

    snapshots.push({
      selector: cssSelectorFor(el),
      name,
      id: el.id ?? '',
      type: el.getAttribute('type') ?? el.tagName.toLowerCase(),
      value: ('value' in el ? String(el.value) : '').slice(0, 200),
      label,
    });
  }
  return snapshots;
}

function readSelection(): string {
  return (window.getSelection()?.toString() ?? '').trim().slice(0, 2000);
}

function snapshot(): RawContext {
  return {
    selectedText: readSelection(),
    inputs: collectInputs(),
    url: location.href,
    capturedAt: new Date().toISOString(),
  };
}

function sendThrottled(): void {
  const now = Date.now();
  if (now - lastSentAt < THROTTLE_MS) {
    pending = snapshot();
    return;
  }
  lastSentAt = now;
  ipcRenderer.send('rea:context-raw', snapshot());
}

/** Inspeção completa para calibração de seletores (modo debug/acadêmico). */
function inspectStructure(): InspectionResult {
  const interactive = Array.from(
    document.querySelectorAll<HTMLElement>(
      'input, select, textarea, button, a[href], [role=button], [role=combobox]',
    ),
  ).slice(0, 150);

  return {
    url: location.href,
    title: document.title,
    capturedAt: new Date().toISOString(),
    cssSelectors: interactive.map((el) => ({
      tag: el.tagName.toLowerCase(),
      selector: cssSelectorFor(el),
      text: (el.textContent ?? '').trim().slice(0, 120) || labelFor(el),
      type: el.getAttribute('type') ?? el.getAttribute('role') ?? el.tagName.toLowerCase(),
    })),
    xpath: interactive.map((el) => ({ xpath: xpathFor(el), text: (el.textContent ?? '').trim().slice(0, 80) })),
    frames: Array.from(document.querySelectorAll('iframe')).map((f) => f.src).filter(Boolean),
  };
}

/* ------------------------------------------------------------------ */
/* Observadores passivos                                               */
/* ------------------------------------------------------------------ */

function installObservers(): void {
  document.addEventListener('selectionchange', () => {
    if (enabled) sendThrottled();
  }, { passive: true });

  document.addEventListener('input', (event) => {
    if (!enabled) return;
    const target = event.target as HTMLElement | null;
    if (target && /INPUT|SELECT|TEXTAREA/.test(target.tagName)) sendThrottled();
  }, { passive: true });

  document.addEventListener('change', () => {
    if (enabled) sendThrottled();
  }, { passive: true });

  const observer = new MutationObserver(() => {
    if (enabled) sendThrottled();
  });
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['value', 'placeholder', 'aria-label', 'class'],
  });

  // Drena o último snapshot quando o throttle expira.
  window.setInterval(() => {
    if (pending && Date.now() - lastSentAt >= THROTTLE_MS) {
      const queued = pending;
      pending = null;
      lastSentAt = Date.now();
      ipcRenderer.send('rea:context-raw', queued);
    }
  }, THROTTLE_MS);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', installObservers, { once: true });
} else {
  installObservers();
}

/* ------------------------------------------------------------------ */
/* API isolada exposta ao Main (via executeJavaScript) e ao próprio mundo */
/* ------------------------------------------------------------------ */

const reaApi = {
  getContext: (): RawContext => snapshot(),
  inspect: (): InspectionResult => inspectStructure(),
  setEnabled: (value: boolean): boolean => {
    enabled = Boolean(value);
    return enabled;
  },
  isEnabled: (): boolean => enabled,
  /** Metadados de calibração (sem dados de pacientes). */
  getSelectors: () => ({
    routes: PORTAL_ROUTES,
    hints: SEARCH_FIELD_HINTS,
    models: QUERY_FIELD_MODELS,
    endpoints: API_ENDPOINTS,
    blocked: BLOCKED_FIELD_LABELS,
  }),
};

contextBridge.exposeInMainWorld('__AF_REA__', reaApi);

/** API de dados fictícios para o clone do portal (sem token no renderer). */
contextBridge.exposeInMainWorld('afPortal', {
  getStats: () => ipcRenderer.invoke('portal:stats'),
  getUsers: (limit: number) => ipcRenderer.invoke('portal:users', limit),
  getLmes: (status?: string, limit?: number) => ipcRenderer.invoke('portal:lmes', status, limit),
  getView: (key: string) => ipcRenderer.invoke('portal:view', key),
  openPdf: (lmeId: number) => ipcRenderer.invoke('portal:open-pdf', lmeId),
  createMedication: (nome: string, principio: string, apresentacao: string) =>
    ipcRenderer.invoke('portal:create-medication', nome, principio, apresentacao),
  exportView: (key: string, formato: 'csv' | 'pdf') =>
    ipcRenderer.invoke('portal:export', key, formato),
  setStatus: (id: number, status: string, motivo: string) =>
    ipcRenderer.invoke('lme:set-status', id, status, motivo),
  getAudit: () => ipcRenderer.invoke('portal:audit'),
  exportAudit: (formato: 'csv' | 'pdf') => ipcRenderer.invoke('portal:export-audit', formato),
  logout: () => ipcRenderer.invoke('app:logout'),
  getSession: () => ipcRenderer.invoke('portal:session'),
  askAdmin: (pergunta: string) => ipcRenderer.invoke('ai:ask', pergunta),
  getAlerts: () => ipcRenderer.invoke('ai:audit'),
  validateLmeReceipt: (id: number) => ipcRenderer.invoke('lme:validate-receipt', id),
});
