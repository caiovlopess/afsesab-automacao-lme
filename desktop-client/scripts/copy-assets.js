/** Copia assets estáticos da Sidebar para dist/renderer após o tsc. */
const { mkdirSync, copyFileSync } = require('node:fs');
const { resolve } = require('node:path');

const root = resolve(__dirname, '..');
const from = resolve(root, 'src/renderer');
const to = resolve(root, 'dist/renderer');

mkdirSync(to, { recursive: true });
for (const file of ['index.html', 'styles.css']) {
  copyFileSync(resolve(from, file), resolve(to, file));
}
// Tela de login.
copyFileSync(resolve(root, 'src/login/index.html'), resolve(to, 'login.html'));
copyFileSync(resolve(root, 'src/login/app.js'), resolve(to, 'login.js'));
// Brasão exibido dentro do cartão de login.
copyFileSync(resolve(root, 'assets/brasao-bahia.png'), resolve(to, 'brasao.png'));
// Clone local do portal (modo demo com dados fictícios).
mkdirSync(resolve(to, 'clone'), { recursive: true });
for (const file of ['index.html', 'styles.css', 'app.js']) {
  copyFileSync(resolve(root, 'src/clone', file), resolve(to, 'clone', file));
}
console.log(`[copy-assets] assets copiados para ${to}`);
