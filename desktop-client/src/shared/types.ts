/**
 * Tipos compartilhados entre Main, Preload e Renderer.
 * Mantidos em um único lugar para garantir contrato de dados consistente.
 */

/** Contexto bruto capturado pelo REA dentro do portal AFSESAB. */
export interface RawContext {
  selectedText: string;
  inputs: Array<{
    selector: string;
    name: string;
    id: string;
    type: string;
    value: string;
    label: string;
  }>;
  url: string;
  capturedAt: string;
}

/** Contexto já sanitizado (LGPD) que cruza a fronteira do Electron. */
export interface SanitizedContext {
  drugs: string[];
  dosages: string[];
  cid10: string[];
  clinicalTerms: string[];
  /** Texto residual contendo APENAS tokens clínicos permitidos. */
  safeText: string;
  capturedAt: string;
  source: 'afsesab';
}

/** Resposta da Methodology A (RAG de protocolos clínicos). */
export interface AnalysisResponse {
  inclusionCriteria: string[];
  requiredExams: string[];
  dispensingAlerts: string[];
  sources: string[];
  passos: string[];
  exemplo: string;
  disclaimer: string;
}

/** Resultado do validador multimodal de receitas/LME (Methodology B). */
export interface ValidationResponse {
  extracted: {
    activeIngredient: string;
    concentration: string;
    posology: string;
    cid: string;
    issueDate: string;
  };
  inconsistencies: string[];
  status: 'ok' | 'warning' | 'error';
  disclaimer: string;
}

/** Mapa de seletores gerado pelo modo inspeção (debug/acadêmico). */
export interface InspectionResult {
  url: string;
  title: string;
  capturedAt: string;
  /** Seletores CSS candidatos para os elementos interativos da tela. */
  cssSelectors: Array<{ tag: string; selector: string; text: string; type: string }>;
  /** XPath absoluto dos elementos mapeados. */
  xpath: Array<{ xpath: string; text: string }>;
  /** Frame(s) detectados (ex.: portais legados dentro de iframe). */
  frames: string[];
}

/** Insights agregados gerados pela IA para o administrador. */
export interface AdminInsights {
  resumo: string;
  insights: string[];
  alertas: string[];
  acoes: string[];
  model: string;
  periodo: string;
}

/** API exposta ao Renderer via contextBridge. */
export interface AFDesktopAPI {
  onContext: (callback: (context: SanitizedContext) => void) => () => void;
  onStatus: (callback: (message: string) => void) => () => void;
  inspectStructure: () => Promise<InspectionResult>;
  analyzeContext: (context: SanitizedContext) => Promise<AnalysisResponse>;
  validatePrescription: (fileName: string, bytes: ArrayBuffer, context: SanitizedContext | null) => Promise<ValidationResponse>;
  getBackendUrl: () => Promise<string>;
  getAdminInsights: (foco: string) => Promise<AdminInsights>;
  askAdmin: (pergunta: string) => Promise<{
    answer: string; columns: string[]; rows: Array<Array<string | number>>;
    intent: string; model: string; suggestions: string[];
  }>;
  auditBase: () => Promise<{
    total: number; achados: Array<{ titulo: string; detalhe: string; severidade: string }>;
  }>;
}

declare global {
  interface Window {
    afDesktop: AFDesktopAPI;
  }
}
