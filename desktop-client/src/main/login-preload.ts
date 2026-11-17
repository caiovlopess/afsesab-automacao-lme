import { contextBridge, ipcRenderer } from 'electron';

interface LoginResult {
  username: string;
  nome: string;
  perfil: string;
  unidade: string;
  session_token: string;
}

contextBridge.exposeInMainWorld('afAuth', {
  submit: (username: string, password: string): Promise<LoginResult> =>
    ipcRenderer.invoke('auth:login', username, password),
  openMain: (result: LoginResult): Promise<void> =>
    ipcRenderer.invoke('auth:open-main', result),
});
