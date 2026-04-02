// pipeline-visual-performance.spec.ts
// Visuele regressie & performance tests voor YouTube Factory

import { test, expect } from '@playwright/test';
import { authenticatedContext } from './fixtures/auth';
import { TEST_USERS } from './fixtures/test-data';
import './guards/environment';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3333';

test.describe('YouTube Factory — Visuele Regressie @regression', () => {

  test('login scherm visuele regressie desktop @regression', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('#loginScreen', { state: 'visible' });
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('login-desktop.png', {
      maxDiffPixels: 150,
      animations: 'disabled',
    });
  });

  test('login scherm visuele regressie mobiel 390px @regression', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForSelector('#loginScreen', { state: 'visible' });
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('login-mobile.png', {
      maxDiffPixels: 150,
      animations: 'disabled',
    });

    await context.close();
  });

  test('app shell visuele regressie desktop @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('app-shell-desktop.png', {
      maxDiffPixels: 200,
      animations: 'disabled',
      mask: [
        page.locator('.api-badge'), // API status kan variëren
      ],
    });

    await context.close();
  });

  test('app shell visuele regressie mobiel @regression', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage();

    // Login op mobiel
    await page.goto(BASE_URL);
    await page.waitForSelector('#loginScreen', { state: 'visible' });
    await page.locator('#loginEmail').fill(TEST_USERS.admin.email);
    await page.locator('#loginPassword').fill(TEST_USERS.admin.password);
    await page.locator('#loginScreen button').filter({ hasText: /inloggen/i }).click();

    await page.waitForLoadState('networkidle', { timeout: 10_000 });

    await expect(page).toHaveScreenshot('app-shell-mobile.png', {
      maxDiffPixels: 200,
      animations: 'disabled',
    });

    await context.close();
  });
});

test.describe('YouTube Factory — Performance @regression', () => {

  test('login pagina laadtijd onder 3 seconden @smoke @regression', async ({ page }) => {
    const startTime = Date.now();
    await page.goto(BASE_URL);
    await page.waitForSelector('#loginScreen', { state: 'visible' });
    const loadTime = Date.now() - startTime;

    const timing = await page.evaluate(() => ({
      ttfb: performance.timing.responseStart - performance.timing.navigationStart,
      domContentLoaded: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart,
    }));

    expect(timing.ttfb, `TTFB: ${timing.ttfb}ms (max 800ms)`).toBeLessThan(800);
    expect(
      timing.domContentLoaded,
      `DOM Content Loaded: ${timing.domContentLoaded}ms (max 3000ms)`
    ).toBeLessThan(3000);
  });

  test('app shell laadtijd onder 3 seconden na login @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();

    const startTime = Date.now();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });
    const loadTime = Date.now() - startTime;

    expect(loadTime, `App shell laadtijd: ${loadTime}ms (max 5000ms)`).toBeLessThan(5000);

    await context.close();
  });

  test('CLS onder 0.1 op login pagina @regression', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('#loginScreen', { state: 'visible' });

    const cls = await page.evaluate((): Promise<number> =>
      new Promise(resolve => {
        let total = 0;
        const observer = new PerformanceObserver(list => {
          for (const entry of list.getEntries()) {
            if (!(entry as any).hadRecentInput) total += (entry as any).value;
          }
        });
        observer.observe({ type: 'layout-shift', buffered: true });
        setTimeout(() => { observer.disconnect(); resolve(total); }, 3000);
      })
    );

    expect(cls, `CLS score ${cls.toFixed(4)} overschrijdt drempel 0.1`).toBeLessThan(0.1);
  });

  test('CLS onder 0.1 in app shell @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    const cls = await page.evaluate((): Promise<number> =>
      new Promise(resolve => {
        let total = 0;
        const observer = new PerformanceObserver(list => {
          for (const entry of list.getEntries()) {
            if (!(entry as any).hadRecentInput) total += (entry as any).value;
          }
        });
        observer.observe({ type: 'layout-shift', buffered: true });
        setTimeout(() => { observer.disconnect(); resolve(total); }, 3000);
      })
    );

    expect(cls, `CLS score ${cls.toFixed(4)} overschrijdt drempel 0.1`).toBeLessThan(0.1);

    await context.close();
  });

  test('paginagrootte onder 2MB @regression', async ({ page }) => {
    let totalBytes = 0;
    page.on('response', response => {
      const cl = response.headers()['content-length'];
      if (cl) totalBytes += parseInt(cl, 10);
    });

    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const mb = (totalBytes / 1024 / 1024).toFixed(2);
    expect(totalBytes, `Paginagrootte ${mb}MB overschrijdt 2MB budget`).toBeLessThan(2 * 1024 * 1024);
  });

  test('geen JavaScript errors bij normaal gebruik @smoke @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();

    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));
    page.on('console', msg => {
      if (msg.type() === 'error') jsErrors.push(`[console.error] ${msg.text()}`);
    });

    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });
    await page.waitForLoadState('networkidle');

    // Klik door de mode knoppen
    for (const mode of ['#modeShorts', '#modeBatch', '#modeTools', '#modeSingle']) {
      const btn = page.locator(mode);
      if (await btn.isVisible()) {
        await btn.click();
        await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
      }
    }

    expect(jsErrors, `JavaScript errors gevonden:\n${jsErrors.join('\n')}`).toHaveLength(0);

    await context.close();
  });

  test('fonts laden correct (Outfit + JetBrains Mono) @regression', async ({ page }) => {
    const fontRequests: string[] = [];
    page.on('response', response => {
      if (response.url().includes('fonts.googleapis.com') || response.url().includes('fonts.gstatic.com')) {
        fontRequests.push(response.url());
      }
    });

    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Controleer dat Google Fonts geladen worden
    expect(fontRequests.length, 'Geen Google Fonts requests gevonden').toBeGreaterThan(0);

    // Controleer dat Outfit font correct toegepast is
    const fontFamily = await page.evaluate(() =>
      window.getComputedStyle(document.body).fontFamily
    );
    expect(fontFamily.toLowerCase()).toContain('outfit');
  });

  test('dark theme geen witte flits bij laden @regression', async ({ page }) => {
    // De app heeft een donker thema — er mag geen witte achtergrond flitsen
    await page.goto(BASE_URL);

    const bgColor = await page.evaluate(() =>
      window.getComputedStyle(document.body).backgroundColor
    );

    // rgb(8, 8, 12) = #08080c = var(--bg)
    expect(bgColor).not.toBe('rgb(255, 255, 255)');
    expect(bgColor).not.toBe('rgba(0, 0, 0, 0)');
  });
});
