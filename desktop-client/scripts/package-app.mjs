/**
 * Empacota o Electron no formato padrão (resources/app) sem electron-builder.
 * Evita a dependência de symlinks/Developer Mode do Windows.
 *
 * Saída: release/AF Copilot/AF Copilot.exe
 */
import { cpSync, copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const electronDist = join(root, 'node_modules', 'electron', 'dist');
const outRoot = join(root, 'release', 'AF Copilot');
const appDir = join(outRoot, 'resources', 'app');

if (!existsSync(electronDist)) throw new Error('electron dist não encontrado. Rode npm install.');

rmSync(outRoot, { recursive: true, force: true });
mkdirSync(appDir, { recursive: true });

// 1. Copia o runtime do Electron.
cpSync(electronDist, outRoot, { recursive: true });
copyFileSync(join(outRoot, 'electron.exe'), join(outRoot, 'AF Copilot.exe'));
rmSync(join(outRoot, 'electron.exe'));

// 2. Copia o código do aplicativo para resources/app.
cpSync(join(root, 'dist'), join(appDir, 'dist'), { recursive: true });
cpSync(join(root, 'src', 'renderer'), join(appDir, 'src', 'renderer'), { recursive: true });
// Ícone (brasão) usado nas janelas.
cpSync(join(root, 'assets'), join(appDir, 'assets'), { recursive: true });

const pkg = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
pkg.main = 'dist/main/main.js';
delete pkg.scripts;
delete pkg.devDependencies;
writeFileSync(join(appDir, 'package.json'), JSON.stringify(pkg, null, 2), 'utf8');

console.log(`App empacotado: ${join(outRoot, 'AF Copilot.exe')}`);
