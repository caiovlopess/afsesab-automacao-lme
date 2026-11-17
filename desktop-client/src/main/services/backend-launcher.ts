/**
 * Inicialização automática do ai-backend pelo próprio aplicativo desktop.
 *
 * O usuário abre apenas o .exe — não precisa de PowerShell.
 * Nenhuma chave de API passa por aqui: o backend lê `.env` dele mesmo.
 */

import { spawn, type ChildProcess } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { app } from 'electron';

const BACKEND_URL = process.env.AF_BACKEND_URL ?? 'http://127.0.0.1:8000';

let child: ChildProcess | null = null;

function backendDir(): string {
  if (process.env.AF_BACKEND_DIR) return process.env.AF_BACKEND_DIR;

  // Executando a partir de dist/main/services (dev).
  if (!app.isPackaged) return resolve(__dirname, '../../../../ai-backend');

  // App empacotado: sobe até encontrar ai-backend/.venv (release/win-unpacked -> AF).
  let current = dirname(process.execPath);
  for (let i = 0; i < 6; i += 1) {
    const candidate = join(current, 'ai-backend');
    if (existsSync(join(candidate, '.venv', 'Scripts', 'python.exe'))) return candidate;
    const parent = dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return join(dirname(process.execPath), 'ai-backend');
}

function pythonBin(dir: string): string {
  return process.platform === 'win32'
    ? join(dir, '.venv', 'Scripts', 'python.exe')
    : join(dir, '.venv', 'bin', 'python');
}

async function isHealthy(): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      signal: AbortSignal.timeout(1500),
    });
    return response.ok;
  } catch {
    return false;
  }
}

/** Garante que o backend esteja ativo; retorna true se pronto. */
export async function ensureBackend(): Promise<boolean> {
  if (await isHealthy()) return true;

  const dir = backendDir();
  const python = pythonBin(dir);
  if (!existsSync(python)) {
    console.error(`[backend-launcher] Python não encontrado: ${python}`);
    return false;
  }

  console.log(`[backend-launcher] iniciando backend em ${dir}`);
  child = spawn(
    python,
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'],
    {
      cwd: dir,
      stdio: 'ignore',
      windowsHide: true,
      detached: false,
      env: { ...process.env },
    },
  );
  child.on('error', (error) => console.error('[backend-launcher]', error.message));

  for (let attempt = 0; attempt < 120; attempt += 1) {
    await new Promise((done) => setTimeout(done, 500));
    if (await isHealthy()) return true;
  }
  console.error('[backend-launcher] backend não respondeu em 60s');
  return false;
}

/** Encerra o backend iniciado por este processo (não mata um servidor externo). */
export function stopBackend(): void {
  if (child && !child.killed) {
    child.kill();
    child = null;
  }
}
