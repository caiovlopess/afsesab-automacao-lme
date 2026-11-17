/**
 * Electron Main — orquestra Split-View, isolamento de contexto e IPC seguro.
 *
 * Segurança aplicada:
 *  - contextIsolation: true, nodeIntegration: false, sandbox: true (ambos os lados);
 *  - origem do portal fixa em ALLOWED_ORIGINS (bloqueia navegação arbitrária);
 *  - sanitização LGPD no Main antes de qualquer dado sair do processo;
 *  - token local e chamadas HTTP confinados ao Main.
 */

import { app, BrowserWindow, BrowserView, dialog, ipcMain, Menu, protocol, shell } from 'electron';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import type { InspectionResult, RawContext, SanitizedContext } from '../shared/types';
import { sanitizeContext } from './security/lgpd-sanitizer';
import {
  analyzeContext,
  askAdmin,
  auditBase,
  backendUrl,
  createMedication,
  exportView,
  getAdminInsights,
  getFictionalLmes,
  getFictionalStats,
  getFictionalView,
  getFictionalUsers,
  getLmePdf,
  changeLmeStatus,
  exportAudit,
  listAudit,
  login,
  setSessionToken,
  validatePrescription,
} from './services/backend-client';
import { ensureBackend, stopBackend } from './services/backend-launcher';

const CUSTOM_SCHEME = 'af';
const CUSTOM_HOST = 'af-desktop';
const APP_ICON = resolve(__dirname, '../../assets/app.ico');

// Modo demo: portal local com dados 100% fictícios (sem acessar o site real).
const DEMO_MODE = process.env.AF_DEMO_MODE === '1' || process.argv.includes('--demo');
const PORTAL_URL = DEMO_MODE
  ? pathToFileURL(resolve(__dirname, '../renderer/clone/index.html')).href
  : 'https://afsesab.sesab.ba.gov.br/#/';
const ALLOWED_ORIGINS = ['https://afsesab.sesab.ba.gov.br'];

process.env['ELECTRON_DISABLE_SECURITY_WARNINGS'] = 'true';

protocol.registerSchemesAsPrivileged([
  {
    scheme: CUSTOM_SCHEME,
    privileges: { standard: true, secure: true, supportFetchAPI: true, bypassCSP: false },
  },
]);

let mainWindow: BrowserWindow | null = null;
let loginWindow: BrowserWindow | null = null;
let portalView: BrowserView | null = null;

function isAllowedUrl(url: string): boolean {
  if (DEMO_MODE && (url.startsWith(`${CUSTOM_SCHEME}://${CUSTOM_HOST}`) || url.startsWith('file://'))) return true;
  try {
    const parsed = new URL(url);
    return ALLOWED_ORIGINS.includes(parsed.origin);
  } catch {
    return false;
  }
}

function layoutView(): void {
  if (!mainWindow || !portalView) return;
  const [width, height] = mainWindow.getContentSize();
  portalView.setBounds({ x: 0, y: 0, width: Math.floor(width * 0.7), height });
  portalView.setAutoResize({ width: true, height: true });
}

function enforcePortalNavigation(view: BrowserView): void {
  view.webContents.on('will-navigate', (event, url) => {
    if (!isAllowedUrl(url)) {
      event.preventDefault();
      mainWindow?.webContents.send('app:status', `Navegação bloqueada: ${url}`);
    }
  });

  view.webContents.on('will-frame-navigate', (event) => {
    if (!isAllowedUrl(event.url)) event.preventDefault();
  });

  view.webContents.setWindowOpenHandler(({ url }) => {
    if (isAllowedUrl(url)) return { action: 'allow' };
    shell.openExternal(url).catch(() => undefined);
    return { action: 'deny' };
  });
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 950,
    minWidth: 1100,
    icon: APP_ICON,
    title: 'AF Copilot — Assistência Farmacêutica',
    webPreferences: {
      preload: resolve(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
    },
  });

  mainWindow.loadURL(`${CUSTOM_SCHEME}://${CUSTOM_HOST}/index.html`);

  portalView = new BrowserView({
    webPreferences: {
      preload: resolve(__dirname, 'rea/webview-preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      partition: 'persist:afsesab',
    },
  });

  enforcePortalNavigation(portalView);
  mainWindow.addBrowserView(portalView);
  portalView.webContents.loadURL(PORTAL_URL);
  layoutView();

  mainWindow.on('resize', layoutView);
  mainWindow.on('closed', () => {
    portalView = null;
    mainWindow = null;
  });
}

function createLoginWindow(): void {
  loginWindow = new BrowserWindow({
    width: 460,
    height: 560,
    resizable: false,
    maximizable: false,
    icon: APP_ICON,
    title: 'AF Copilot — Acesso',
    webPreferences: {
      preload: resolve(__dirname, 'login-preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  loginWindow.loadURL(`${CUSTOM_SCHEME}://${CUSTOM_HOST}/login.html`);
  loginWindow.on('closed', () => { loginWindow = null; });
}

/* ------------------------------------------------------------------ */
/* IPC — ponte única entre REA, Main e Sidebar                          */
/* ------------------------------------------------------------------ */

function registerIpc(): void {
  ipcMain.on('rea:context-raw', (_event, raw: RawContext) => {
    try {
      const sanitized: SanitizedContext = sanitizeContext(raw);
      // Zero-trust: dados chegam ao Renderer já filtrados.
      mainWindow?.webContents.send('rea:context', sanitized);
    } catch (error) {
      mainWindow?.webContents.send('app:status', `Falha na sanitização: ${(error as Error).message}`);
    }
  });

  ipcMain.handle('rea:inspect', async (): Promise<InspectionResult> => {
    if (!portalView) throw new Error('Portal não inicializado.');
    return portalView.webContents.executeJavaScript(
      `window.__AF_REA__ ? window.__AF_REA__.inspect() : null`,
    ) as Promise<InspectionResult>;
  });

  ipcMain.handle('ai:analyze', async (_event, context: SanitizedContext) => analyzeContext(context));

  ipcMain.handle(
    'ai:validate',
    async (_event, fileName: string, bytes: ArrayBuffer, context: SanitizedContext | null) =>
      validatePrescription(fileName, bytes, context),
  );

  ipcMain.handle('app:backend-url', () => backendUrl());
  ipcMain.handle('ai:insights', (_event, foco: string) => getAdminInsights(foco));
  ipcMain.handle('ai:audit', () => auditBase());
  ipcMain.handle('lme:set-status', (_event, id: number, status: string, motivo: string) =>
    changeLmeStatus(id, status, motivo));
  ipcMain.handle('portal:audit', () => listAudit());

  // Valida uma receita enviada contra os dados da LME selecionada (OCR multimodal).
  ipcMain.handle('lme:validate-receipt', async (_event, id: number) => {
    const view = await getFictionalView('lme');
    const row = view.rows.find((r) => Number(r[0]) === Number(id));
    if (!row) throw new Error('LME não encontrada.');

    const picked = await dialog.showOpenDialog({
      title: `Receita da LME ${id}`,
      filters: [{ name: 'Imagem ou PDF', extensions: ['png', 'jpg', 'jpeg', 'pdf'] }],
      properties: ['openFile'],
    });
    if (picked.canceled || !picked.filePaths[0]) return null;

    const filePath = picked.filePaths[0];
    const bytes = readFileSync(filePath);
    const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
    return validatePrescription(
      filePath.split(/[\\/]/).pop() ?? 'receita.pdf',
      buffer,
      {
        drugs: [String(row[1])],
        dosages: [],
        cid10: [String(row[3])],
        clinicalTerms: [],
        safeText: `${row[1]} ${row[3]}`,
        capturedAt: new Date().toISOString(),
        source: 'afsesab',
      },
    );
  });

  ipcMain.handle('portal:export-audit', async (_event, formato: 'csv' | 'pdf') => {
    const { bytes, filename } = await exportAudit(formato);
    const dir = join(app.getPath('downloads'), 'AF Copilot');
    mkdirSync(dir, { recursive: true });
    const filePath = join(dir, filename);
    writeFileSync(filePath, Buffer.from(bytes));
    await shell.openPath(filePath);
    return filePath;
  });
  ipcMain.handle('ai:ask', (_event, pergunta: string) => askAdmin(pergunta));

  // Exportações são salvas na pasta Downloads e abertas automaticamente.
  ipcMain.handle('portal:export', async (_event, key: string, formato: 'csv' | 'pdf') => {
    const { bytes, filename } = await exportView(key, formato);
    const dir = join(app.getPath('downloads'), 'AF Copilot');
    mkdirSync(dir, { recursive: true });
    const filePath = join(dir, filename);
    writeFileSync(filePath, Buffer.from(bytes));
    await shell.openPath(filePath);
    return filePath;
  });
  ipcMain.handle(
    'portal:create-medication',
    (_event, nome: string, principio: string, apresentacao: string) =>
      createMedication(nome, principio, apresentacao),
  );

  ipcMain.handle('portal:stats', () => getFictionalStats());
  ipcMain.handle('portal:view', (_event, key: string) => getFictionalView(key));

  // Abre o PDF da LME em uma janela do próprio app (visualizador do Chromium).
  ipcMain.handle('portal:open-pdf', async (_event, lmeId: number) => {
    const id = Number(lmeId);
    const padded = String(id).padStart(6, '0');
    const bytes = await getLmePdf(id);
    const filePath = join(app.getPath('temp'), `LME-${padded}.pdf`);
    writeFileSync(filePath, Buffer.from(bytes));

    const viewer = new BrowserWindow({
      width: 900,
      height: 1040,
      title: `LME Fictícia ${padded} — AF Copilot`,
      webPreferences: { sandbox: true, contextIsolation: true, nodeIntegration: false },
    });
    viewer.loadURL(pathToFileURL(filePath).href);
    return filePath;
  });
  ipcMain.handle('portal:users', (_event, limit: number) => getFictionalUsers(limit));
  ipcMain.handle('portal:lmes', (_event, status?: string, limit?: number) => getFictionalLmes(status, limit));

  ipcMain.handle('app:logout', () => {
    setSessionToken('');
    if (portalView && mainWindow) mainWindow.removeBrowserView(portalView);
    portalView = null;
    mainWindow?.close();
    mainWindow = null;
    createLoginWindow();
  });

  ipcMain.handle('auth:login', async (_event, username: string, password: string) => {
    const result = await login(username, password);
    setSessionToken(result.session_token);
    appState.sessionUser = {
      username: result.username,
      nome: result.nome,
      perfil: result.perfil,
      unidade: result.unidade,
    };
    return result;
  });

  ipcMain.handle('portal:session', () => appState.sessionUser ?? {
    username: 'convidado', nome: 'Usuário', perfil: 'Farmacêutico', unidade: '',
  });

  ipcMain.handle('auth:open-main', () => {
    try {
      loginWindow?.close();
      loginWindow = null;
      if (!mainWindow) createWindow();
    } catch (error) {
      console.error('[auth:open-main] falha ao abrir app principal:', error);
      throw error;
    }
  });
}

const appState: { sessionUser: null | { username: string; nome: string; perfil: string; unidade: string } } = {
  sessionUser: null,
};

/* ------------------------------------------------------------------ */
/* Ciclo de vida                                                       */
/* ------------------------------------------------------------------ */

app.on('web-contents-created', (_event, contents) => {
  contents.on('will-navigate', (event, url) => {
    // Protege também a Sidebar contra navegação para sites externos.
    if (contents.getType() === 'window' && !url.startsWith(`${CUSTOM_SCHEME}://${CUSTOM_HOST}`)) {
      event.preventDefault();
    }
  });
});

app.whenReady().then(async () => {
  // Esconde a barra de menu padrão (File/Edit/View…) — visual de app desktop real.
  Menu.setApplicationMenu(null);

  protocol.registerFileProtocol(CUSTOM_SCHEME, (request, callback) => {
    // Remove query string (ex.: login.html?) para não virar nome de arquivo.
    const url = request.url.replace(`${CUSTOM_SCHEME}://${CUSTOM_HOST}/`, '').split('?')[0];
    // Assets compilados em dist/renderer (copiados no build).
    const safePath = resolve(__dirname, '../renderer', url || 'index.html');
    callback({ path: safePath });
  });

  registerIpc();

  // O app é autocontido: sobe o backend sozinho se ele não estiver ativo.
  const backendReady = await ensureBackend();
  createLoginWindow();
  if (!backendReady) {
    loginWindow?.webContents.on('did-finish-load', () => {
      loginWindow?.webContents.send('app:status', 'Backend indisponível.');
    });
  }
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createLoginWindow();
  });
});

app.on('before-quit', stopBackend);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
