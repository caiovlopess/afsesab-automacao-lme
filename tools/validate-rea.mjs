/** Valida o fluxo REA: input no portal -> sanitização LGPD -> Sidebar. */
import { chromium } from 'playwright';

const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
try {
  const pages = browser.contexts().flatMap((c) => c.pages());
  const portal = pages.find((p) => p.url().includes('afsesab'));
  const sidebar = pages.find((p) => p.url().startsWith('af://'));

  await portal.goto('https://afsesab.sesab.ba.gov.br/#/app/lista-medicamento', {
    waitUntil: 'domcontentloaded',
  });
  await portal.waitForTimeout(2500);

  console.log('URL portal:', portal.url());
  const inputs = await portal.evaluate(() =>
    [...document.querySelectorAll('input')].slice(0, 8).map((i) => ({
      placeholder: i.getAttribute('placeholder') || i.getAttribute('aria-label') || '',
    })),
  );
  console.log('Campos:', inputs);

  // Dispara evento de input via JS (o REA escuta `input` no document).
  await portal.evaluate(() => {
    const el = document.querySelector('input[aria-label="Email"]');
    if (!el) return;
    el.value = 'metformina 850 mg E11 CPF 123.456.789-00';
    el.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await portal.waitForTimeout(1500);

  const captured = await sidebar.evaluate(() => ({
    view: document.getElementById('context-view')?.textContent,
    status: document.getElementById('ctx-status')?.textContent,
    btnEnabled: !document.getElementById('btn-analyze')?.disabled,
  }));
  console.log('\nSidebar após input:');
  console.log(captured);
} finally {
  await browser.close();
}
