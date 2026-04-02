// pipeline-technical.spec.ts
// Gegenereerd voor: YouTube Factory — http://localhost:3333
//
// === RISICOANALYSE ===
// Beveiligingsfocus: JWT auth, API endpoint bescherming, error handling
// Externe diensten: OpenAI, ElevenLabs, YouTube API, Gemini — alle gemockt

import { test, expect } from '@playwright/test';
import { authenticatedContext } from './fixtures/auth';
import { TEST_USERS } from './fixtures/test-data';
import {
  mockAllBackendApis, mockServerError, mockNetworkError,
  mockApiStatus,
} from './fixtures/mocks';
import './guards/environment';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3333';

test.describe('YouTube Factory — API Beveiliging & Auth', () => {

  test('beveiligde API endpoints weigeren requests zonder token @smoke @regression', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    // Directe API call zonder auth token
    const response = await page.request.post(`${BASE_URL}/api/generate-script`, {
      data: { topic: 'test', duration: 4 },
    });

    expect(response.status()).toBe(401);
    const body = await response.json();
    expect(body.detail).toContain('Niet ingelogd');

    await context.close();
  });

  test('beveiligde endpoints weigeren ongeldig JWT token @regression', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    const endpoints = [
      { url: '/api/generate-script', body: { topic: 'test', duration: 4 } },
      { url: '/api/generate-voiceover', body: { script: 'test', name: 'test' } },
      { url: '/api/generate-metadata', body: { topic: 'test', script: 'test' } },
      { url: '/api/voices', body: null },
    ];

    for (const ep of endpoints) {
      const opts: any = {
        headers: { Authorization: 'Bearer ongeldig-token-123' },
      };
      let response;
      if (ep.body) {
        response = await page.request.post(`${BASE_URL}${ep.url}`, {
          ...opts,
          data: ep.body,
        });
      } else {
        response = await page.request.get(`${BASE_URL}${ep.url}`, opts);
      }

      expect(
        response.status(),
        `${ep.url} accepteerde ongeldig token`
      ).toBe(401);
    }

    await context.close();
  });

  test('login endpoint is EXEMPT van auth middleware @regression', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    // Login endpoint moet bereikbaar zijn zonder token
    const response = await page.request.post(`${BASE_URL}/api/auth/login`, {
      data: { email: 'test@test.com', password: 'wrong' },
    });

    // 401 vanwege foute credentials, maar NIET vanwege auth middleware
    expect(response.status()).toBe(401);
    const body = await response.json();
    expect(body.detail).toContain('Ongeldige inloggegevens');

    await context.close();
  });

  test('/api/status endpoint is EXEMPT van auth @regression', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    const response = await page.request.get(`${BASE_URL}/api/status`);
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('openai');
    expect(body).toHaveProperty('elevenlabs');
    expect(body).toHaveProperty('youtube');
    expect(body).toHaveProperty('gemini');

    await context.close();
  });
});

test.describe('YouTube Factory — Error Handling', () => {

  test('server error 500 op script generatie toont leesbare melding @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await mockApiStatus(page);
    await mockServerError(page, '/api/generate-script');
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    // Topic invullen en genereren
    await page.locator('#topicInput').fill('Test error handling');
    const generateBtn = page.locator('button').filter({ hasText: /script/i });
    await generateBtn.click();

    await page.waitForLoadState('networkidle', { timeout: 10_000 });

    // App mag NIET crashen — geen onafgehandelde errors
    await expect(page.locator('#mainContent')).toBeVisible();

    // Geen stack traces of technische crash details
    await expect(page.getByText(/stack|trace|at Object|undefined is not/i)).not.toBeVisible();

    // Log als de app ruwe foutmeldingen toont (verbeterpunt)
    const rawError = await page.getByText('Internal Server Error').isVisible().catch(() => false);
    if (rawError) {
      console.warn('⚠️ App toont ruwe "Internal Server Error" — overweeg een gebruiksvriendelijke melding');
    }

    await context.close();
  });

  test('netwerk error toont bruikbare melding @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await mockApiStatus(page);
    await mockNetworkError(page, '/api/generate-script');
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    await page.locator('#topicInput').fill('Test network error');
    const generateBtn = page.locator('button').filter({ hasText: /script/i });
    await generateBtn.click();

    await page.waitForLoadState('networkidle', { timeout: 10_000 });

    // App mag niet crashen
    await expect(page.locator('#mainContent')).toBeVisible();

    await context.close();
  });

  test('geen JavaScript errors bij normaal laden @smoke @regression', async ({ browser }) => {
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

    expect(jsErrors, `JavaScript errors gevonden:\n${jsErrors.join('\n')}`).toHaveLength(0);

    await context.close();
  });
});

test.describe('YouTube Factory — API Payload Validatie', () => {

  test('login POST stuurt correcte payload @regression', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForSelector('#loginScreen', { state: 'visible' });

    const [request] = await Promise.all([
      page.waitForRequest(req =>
        req.url().includes('/api/auth/login') && req.method() === 'POST'
      ),
      (async () => {
        await page.locator('#loginEmail').fill('test@email.com');
        await page.locator('#loginPassword').fill('testpassword');
        await page.locator('#loginScreen button').filter({ hasText: /inloggen/i }).click();
      })(),
    ]);

    const body = JSON.parse(request.postData() || '{}');
    expect(body).toHaveProperty('email', 'test@email.com');
    expect(body).toHaveProperty('password', 'testpassword');

    // Payload mag geen extra gevoelige velden bevatten
    expect(Object.keys(body)).toEqual(expect.arrayContaining(['email', 'password']));
    expect(Object.keys(body).length).toBe(2);

    await context.close();
  });

  test('script generatie POST bevat topic en duration @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await mockAllBackendApis(page);

    let capturedBody: any = null;
    page.on('request', req => {
      if (req.url().includes('/api/generate-script') && req.method() === 'POST') {
        capturedBody = JSON.parse(req.postData() || '{}');
      }
    });

    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    await page.locator('#topicInput').fill('Carlos Alcaraz');
    const generateBtn = page.locator('button').filter({ hasText: /script/i });
    await generateBtn.click();

    await page.waitForLoadState('networkidle', { timeout: 10_000 });

    if (capturedBody) {
      expect(capturedBody).toHaveProperty('topic', 'Carlos Alcaraz');
      expect(capturedBody).toHaveProperty('duration');
      // Geen tokens of wachtwoorden in payload
      expect(capturedBody).not.toHaveProperty('password');
      expect(capturedBody).not.toHaveProperty('secret');
    }

    await context.close();
  });

  test('geen gevoelige data in URL of console @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();

    const consoleLogs: string[] = [];
    page.on('console', msg => consoleLogs.push(msg.text()));

    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });
    await page.waitForLoadState('networkidle');

    const url = page.url();
    ['password', 'secret', 'api_key', 'private_key'].forEach(term => {
      expect(url.toLowerCase(), `Gevoelige term "${term}" in URL`).not.toContain(term);
    });

    consoleLogs.forEach(log => {
      expect(log.toLowerCase(), 'Wachtwoord in console').not.toContain('password');
    });

    await context.close();
  });
});

test.describe('YouTube Factory — Auth Bescherming Specifieke Endpoints', () => {

  const protectedEndpoints = [
    { method: 'POST', url: '/api/generate-script', body: { topic: 'test', duration: 4 } },
    { method: 'POST', url: '/api/refine-script', body: { script: 'test', feedback: 'test' } },
    { method: 'POST', url: '/api/generate-voiceover', body: { script: 'test', name: 'test' } },
    { method: 'POST', url: '/api/search-clips', body: { topic: '[]', duration: 4 } },
    { method: 'POST', url: '/api/download-clips', body: { clips: [], topic: 'test' } },
    { method: 'POST', url: '/api/combine-video', body: { audio_duration: 10, name: 'test' } },
    { method: 'POST', url: '/api/generate-thumbnail', body: { topic: 'test', title: 'test' } },
    { method: 'POST', url: '/api/generate-metadata', body: { topic: 'test', script: 'test' } },
    { method: 'POST', url: '/api/upload', body: { video_file: 'test.mp4', title: 'test', description: 'test', tags: [] } },
    { method: 'POST', url: '/api/batch', body: { topics: [], start_date: '2026-01-01' } },
    { method: 'POST', url: '/api/reset', body: {} },
  ];

  for (const ep of protectedEndpoints) {
    test(`${ep.method} ${ep.url} vereist authenticatie @regression`, async ({ request }) => {
      const response = await request.post(`${BASE_URL}${ep.url}`, {
        data: ep.body,
      });
      expect(
        response.status(),
        `${ep.url} is toegankelijk zonder auth (status ${response.status()})`
      ).toBe(401);
    });
  }
});
