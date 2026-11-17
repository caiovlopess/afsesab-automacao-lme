/** Lê APENAS os rótulos dos menus do portal real (sem valores/dados de pacientes). */
import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
try {
  const p = b.contexts().flatMap(c => c.pages()).find(x => x.url().includes('afsesab'));
  if (!p) throw new Error('aba AFSESAB nao encontrada');
  await p.bringToFront();
  console.log('URL:', p.url());

  const items = await p.evaluate(() =>
    [...document.querySelectorAll('.v-list__tile, .menu-sub-item a, .v-list__group__header')]
      .map(e => (e.textContent || '').trim().replace(/\s+/g, ' '))
      .filter(t => t && t.length < 80)
  );
  console.log('rotulos visiveis:', [...new Set(items)].slice(0, 120));

  // Abre cada menu principal e captura os submenus exibidos.
  const menuLabels = ['Cadastros', 'Administração', 'Planejamento Aquisição',
    'Componente Especializado', 'Farmácia', 'Relatórios',
    'Relatórios Especializado', 'Relatórios SIGAF'];
  for (const label of menuLabels) {
    try {
      await p.getByText(label, { exact: true }).first().click({ timeout: 3000 });
      await p.waitForTimeout(350);
      const subs = await p.evaluate(() =>
        [...document.querySelectorAll('.v-list__group__items .v-list__tile__title, .menu-sub-item')]
          .map(e => (e.textContent || '').trim().replace(/\s+/g, ' '))
          .filter(Boolean)
      );
      console.log(`\n[${label}]`, [...new Set(subs)].slice(0, 40));
    } catch (e) { console.log(`\n[${label}] erro:`, e.message.slice(0, 80)); }
  }
} finally { await b.close(); }
