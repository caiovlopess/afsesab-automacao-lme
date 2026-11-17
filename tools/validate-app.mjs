/**
 * Validação end-to-end do Electron + backend via CDP (porta 9223).
 * Verifica: Sidebar, API contextBridge, IPC -> Main -> FastAPI, REA no portal.
 */
import { chromium } from 'playwright';

const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
try {
  const pages = browser.contexts().flatMap((c) => c.pages());
  const sidebar = pages.find((p) => p.url().startsWith('af://'));
  const portal = pages.find((p) => p.url().includes('afsesab'));
  if (!sidebar || !portal) throw new Error('Páginas não encontradas');

  console.log('--- Sidebar ---');
  console.log(await sidebar.evaluate(() => ({
    title: document.title,
    hasApi: typeof window.afDesktop,
    buttons: [...document.querySelectorAll('button')].map((b) => b.id),
    badge: document.getElementById('backend-badge')?.textContent,
  })));

  console.log('\n--- REA no portal ---');
  console.log(await portal.evaluate(() => ({
    rea: typeof window.__AF_REA__,
    title: document.title,
  })));

  console.log('\n--- inspectStructure (IPC -> executeJavaScript) ---');
  const inspection = await sidebar.evaluate(() => window.afDesktop.inspectStructure());
  console.log({ url: inspection.url, elementos: inspection.cssSelectors.length, frames: inspection.frames.length });

  console.log('\n--- analyzeContext (IPC -> Main -> FastAPI) ---');
  const result = await sidebar.evaluate(() => window.afDesktop.analyzeContext({
    drugs: ['metformina'],
    dosages: ['850 mg'],
    cid10: ['E11'],
    clinicalTerms: ['diabetes'],
    safeText: 'metformina 850 mg E11 diabetes',
    capturedAt: new Date().toISOString(),
    source: 'afsesab',
  }));
  console.log(result);

  console.log('\n--- backend url ---');
  console.log(await sidebar.evaluate(() => window.afDesktop.getBackendUrl()));
} finally {
  await browser.close();
}
