/**
 * Leitura do token de sessão local gerado pelo backend na inicialização.
 *
 * O token NUNCA é escrito no código do Electron. Ele é criado pelo FastAPI
 * em `ai-backend/runtime/auth_token` (permissões restritas) e lido aqui.
 * Ambos os processos rodam sob o mesmo usuário na mesma máquina.
 */

import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/** Sobe directories até encontrar ai-backend/runtime/auth_token (dev ou empacotado). */
function findTokenPath(): string {
  if (process.env.AF_INTERNAL_TOKEN_PATH) return process.env.AF_INTERNAL_TOKEN_PATH;
  let current = __dirname;
  for (let i = 0; i < 14; i += 1) {
    const candidate = resolve(current, 'ai-backend', 'runtime', 'auth_token');
    if (existsSync(candidate)) return candidate;
    const parent = resolve(current, '..');
    if (parent === current) break;
    current = parent;
  }
  return resolve(__dirname, '../../../../ai-backend/runtime/auth_token');
}

const DEFAULT_TOKEN_PATH = findTokenPath();

let cachedToken: string | null = null;

export function getInternalAuthToken(): string {
  if (cachedToken) return cachedToken;

  const tokenPath = process.env.AF_INTERNAL_TOKEN_PATH ?? DEFAULT_TOKEN_PATH;
  try {
    const token = readFileSync(tokenPath, 'utf8').trim();
    if (!token || token.length < 16) {
      throw new Error('Token local inválido (muito curto).');
    }
    cachedToken = token;
    return token;
  } catch (error) {
    throw new Error(
      `Não foi possível ler o token de sessão local em "${tokenPath}". ` +
        'Inicie o ai-backend antes do cliente. Detalhe: ' +
        (error as Error).message,
    );
  }
}

export function resetTokenCache(): void {
  cachedToken = null;
}
