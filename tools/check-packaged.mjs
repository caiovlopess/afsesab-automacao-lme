/** Verificação rápida do app empacotado (sem chamadas ao Gemini). */
import { chromium } from 'playwright';

const browser = await chromium.connectOverCDP('http://127.0.0.1:9224');
try {
  const pages = browser.contexts().flatMap((c) => c.pages());
  const sidebar = pages.find((p) => p.url().startsWith('af://'));
  const portal = pages.find((p) => p.url().includes('afsesab'));
  console.log({
    sidebar: await sidebar.evaluate(() => ({
      api: typeof window.afDesktop,
      badge: document.getElementById('backend-badge')?.textContent,
    })),
    rea: await portal.evaluate(() => typeof window.__AF_REA__),
    inspecao: (await sidebar.evaluate(() => window.afDesktop.inspectStructure())).cssSelectors.length,
  });
} finally {
  await browser.close();
}
