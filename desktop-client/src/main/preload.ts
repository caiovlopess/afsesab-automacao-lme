/**
 * Preload da Sidebar (Renderer confiável da própria aplicação).
 * Expõe uma API mínima e tipada via contextBridge — nenhum Node.js é vazado.
 */

import { contextBridge, ipcRenderer } from 'electron';
import type { AFDesktopAPI } from '../shared/types';

const api: AFDesktopAPI = {
  onContext: (callback) => {
    const listener = (_event: Electron.IpcRendererEvent, context: Parameters<typeof callback>[0]) => {
      callback(context);
    };
    ipcRenderer.on('rea:context', listener);
    return () => ipcRenderer.removeListener('rea:context', listener);
  },

  onStatus: (callback) => {
    const listener = (_event: Electron.IpcRendererEvent, message: string) => callback(message);
    ipcRenderer.on('app:status', listener);
    return () => ipcRenderer.removeListener('app:status', listener);
  },

  inspectStructure: () => ipcRenderer.invoke('rea:inspect'),
  analyzeContext: (context) => ipcRenderer.invoke('ai:analyze', context),
  validatePrescription: (fileName, bytes, context) =>
    ipcRenderer.invoke('ai:validate', fileName, bytes, context),
  getBackendUrl: () => ipcRenderer.invoke('app:backend-url'),
  getAdminInsights: (foco: string) => ipcRenderer.invoke('ai:insights', foco),
  askAdmin: (pergunta: string) => ipcRenderer.invoke('ai:ask', pergunta),
  auditBase: () => ipcRenderer.invoke('ai:audit'),
};

contextBridge.exposeInMainWorld('afDesktop', api);
