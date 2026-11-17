/**
 * Cliente HTTP para o ai-backend. Executa EXCLUSIVAMENTE no processo Main,
 * de forma que o token local nunca seja exposto ao Renderer.
 */

import type {
  AnalysisResponse,
  SanitizedContext,
  ValidationResponse,
} from '../../shared/types';
import { getInternalAuthToken } from '../security/local-auth';

const BACKEND_URL = process.env.AF_BACKEND_URL ?? 'http://127.0.0.1:8000';

let sessionToken = '';
export function setSessionToken(token: string): void { sessionToken = token; }

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'X-Internal-Auth-Token': getInternalAuthToken() };
  if (sessionToken) headers['X-Session-Token'] = sessionToken;
  return headers;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`Backend respondeu ${response.status}: ${detail.slice(0, 500)}`);
  }
  return (await response.json()) as T;
}

export async function analyzeContext(context: SanitizedContext): Promise<AnalysisResponse> {
  const response = await fetch(`${BACKEND_URL}/api/v1/analyze-context`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(context),
  });
  return parseResponse<AnalysisResponse>(response);
}

export async function validatePrescription(
  fileName: string,
  bytes: ArrayBuffer,
  context: SanitizedContext | null,
): Promise<ValidationResponse> {
  const form = new FormData();
  const blob = new Blob([bytes], {
    type: inferMime(fileName),
  });
  form.append('file', blob, fileName);
  form.append('context', context ? JSON.stringify(context) : '{}');

  const response = await fetch(`${BACKEND_URL}/api/v1/validate-prescription`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  });
  return parseResponse<ValidationResponse>(response);
}

function inferMime(fileName: string): string {
  const lower = fileName.toLowerCase();
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return 'image/jpeg';
  if (lower.endsWith('.pdf')) return 'application/pdf';
  return 'application/octet-stream';
}

export function backendUrl(): string {
  return BACKEND_URL;
}

/* ---------------- dados fictícios para o clone do portal ---------------- */

export interface FictionalStats {
  total_usuarios: number;
  total_lmes: number;
  por_status: Record<string, number>;
  top_medicamentos: Record<string, number>;
}

export async function getFictionalStats(): Promise<FictionalStats> {
  const response = await fetch(`${BACKEND_URL}/api/v1/fictional/stats`, { headers: authHeaders() });
  return parseResponse<FictionalStats>(response);
}

export interface FictionalView {
  key: string;
  title: string;
  columns: string[];
  rows: Array<Array<string | number>>;
  note: string;
}

/** Bytes do PDF de uma LME fictícia. */
/** Cadastro de medicamento no catálogo do administrador. */
export async function createMedication(
  nome: string, principio: string, apresentacao: string,
): Promise<{ codigo: string; nome: string; principio: string; apresentacao: string }> {
  const response = await fetch(`${BACKEND_URL}/api/v1/fictional/medicamentos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ nome, principio, apresentacao }),
  });
  return parseResponse(response);
}

/** Exporta uma tela do clone em CSV ou PDF (bytes + nome sugerido). */
export async function exportView(
  key: string,
  formato: 'csv' | 'pdf',
): Promise<{ bytes: ArrayBuffer; filename: string }> {
  const response = await fetch(
    `${BACKEND_URL}/api/v1/fictional/export/${encodeURIComponent(key)}?formato=${formato}`,
    { headers: authHeaders() },
  );
  if (!response.ok) throw new Error(`Falha ao exportar: ${response.status}`);
  const disposition = response.headers.get('content-disposition') ?? '';
  const filename = disposition.match(/filename="?([^";]+)"?/)?.[1] ?? `relatorio.${formato}`;
  return { bytes: await response.arrayBuffer(), filename };
}

/** Consulta em linguagem natural sobre a base. */
export async function askAdmin(pergunta: string): Promise<{
  answer: string; columns: string[]; rows: Array<Array<string | number>>;
  intent: string; model: string; suggestions: string[];
}> {
  const response = await fetch(`${BACKEND_URL}/api/v1/admin/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ pergunta }),
  });
  return parseResponse(response);
}

/** Altera o status de uma LME (ação real com auditoria). */
export async function changeLmeStatus(
  id: number, status: string, motivo: string,
): Promise<{ id: number; status: string; por: string }> {
  const response = await fetch(`${BACKEND_URL}/api/v1/fictional/lmes/${id}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ status, motivo }),
  });
  return parseResponse(response);
}

/** Log de auditoria (append-only). */
export async function listAudit(): Promise<Array<Record<string, string | number>>> {
  const response = await fetch(`${BACKEND_URL}/api/v1/fictional/audit`, { headers: authHeaders() });
  return parseResponse(response);
}

export async function exportAudit(formato: 'csv' | 'pdf'): Promise<{ bytes: ArrayBuffer; filename: string }> {
  const response = await fetch(`${BACKEND_URL}/api/v1/fictional/audit/export?formato=${formato}`, {
    headers: authHeaders(),
  });
  const disposition = response.headers.get('content-disposition') ?? '';
  return {
    bytes: await response.arrayBuffer(),
    filename: disposition.match(/filename="?([^";]+)"?/)?.[1] ?? `auditoria.${formato}`,
  };
}

/** Auditoria de problemas na base. */
export async function auditBase(): Promise<{
  total: number; achados: Array<{ titulo: string; detalhe: string; severidade: string }>;
}> {
  const response = await fetch(`${BACKEND_URL}/api/v1/admin/audit`, {
    method: 'POST',
    headers: authHeaders(),
  });
  return parseResponse(response);
}

/** Insights agregados (sem dados pessoais) para o administrador. */
export async function getAdminInsights(foco: string): Promise<{
  resumo: string; insights: string[]; alertas: string[]; acoes: string[]; model: string; periodo: string;
}> {
  const response = await fetch(`${BACKEND_URL}/api/v1/admin/insights`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ foco }),
  });
  return parseResponse(response);
}

export async function getLmePdf(lmeId: number): Promise<ArrayBuffer> {
  const response = await fetch(
    `${BACKEND_URL}/api/v1/fictional/lmes/${lmeId}/pdf`,
    { headers: authHeaders() },
  );
  if (!response.ok) {
    throw new Error(`Falha ao gerar PDF da LME ${lmeId}: ${response.status}`);
  }
  return response.arrayBuffer();
}

export async function getFictionalView(key: string): Promise<FictionalView> {
  const response = await fetch(
    `${BACKEND_URL}/api/v1/fictional/view/${encodeURIComponent(key)}`,
    { headers: authHeaders() },
  );
  return parseResponse<FictionalView>(response);
}

export async function getFictionalUsers(limit = 50): Promise<Array<{ id: number; nome: string; email: string; unidade: string }>> {
  const response = await fetch(`${BACKEND_URL}/api/v1/fictional/users?limit=${limit}`, { headers: authHeaders() });
  return parseResponse(response);
}

export async function getFictionalLmes(status?: string, limit = 50): Promise<Array<{
  id: number; medicamento: string; cid10: string; dosagem: string; status: string; valor: number;
}>> {
  const query = new URLSearchParams({ limit: String(limit) });
  if (status) query.set('status', status);
  const response = await fetch(`${BACKEND_URL}/api/v1/fictional/lmes?${query}`, { headers: authHeaders() });
  return parseResponse(response);
}

export async function login(username: string, password: string): Promise<{
  username: string; nome: string; perfil: string; unidade: string; session_token: string;
}> {
  const response = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  return parseResponse(response);
}
