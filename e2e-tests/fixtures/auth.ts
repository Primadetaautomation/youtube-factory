// e2e-tests/fixtures/auth.ts
// Session caching: één keer inloggen per testrun, niet bij elke test opnieuw

import { Page, Browser } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { TEST_USERS } from './test-data';
import '../guards/environment';

const SESSION_DIR = path.join(__dirname, '.sessions');

if (!fs.existsSync(SESSION_DIR)) {
  fs.mkdirSync(SESSION_DIR, { recursive: true });
}

function sessionPath(role: string): string {
  return path.join(SESSION_DIR, `session-${role}.json`);
}

function sessionIsValid(role: string): boolean {
  const p = sessionPath(role);
  if (!fs.existsSync(p)) return false;
  const age = Date.now() - fs.statSync(p).mtimeMs;
  return age < 60 * 60 * 1000; // 1 uur geldig
}

// Maak een browser-context met opgeslagen sessie
export async function authenticatedContext(browser: Browser, role: keyof typeof TEST_USERS) {
  if (sessionIsValid(role)) {
    return browser.newContext({ storageState: sessionPath(role) });
  }
  const context = await browser.newContext();
  const page = await context.newPage();
  await loginViaUI(page, role);
  await context.storageState({ path: sessionPath(role) });
  await page.close();
  return context;
}

// Login via de UI — YouTube Factory gebruikt een custom login screen met JWT in localStorage
export async function loginViaUI(page: Page, role: keyof typeof TEST_USERS): Promise<void> {
  const user = TEST_USERS[role];
  const baseUrl = process.env.BASE_URL || 'http://localhost:3333';

  await page.goto(baseUrl);

  // Wacht op het login scherm
  await page.waitForSelector('#loginScreen', { state: 'visible', timeout: 10_000 });

  await page.locator('#loginEmail').fill(user.email);
  await page.locator('#loginPassword').fill(user.password);
  await page.locator('#loginScreen button').filter({ hasText: /inloggen/i }).click();

  // Wacht tot de app shell zichtbaar wordt (login geslaagd)
  await page.waitForSelector('#appShell', { state: 'visible', timeout: 10_000 });

  // Verifieer dat login echt gelukt is
  const loginError = await page.locator('#loginError').textContent();
  if (loginError && loginError.trim()) {
    throw new Error(
      `Login mislukt voor rol "${role}" met email "${user.email}": ${loginError}. ` +
      `Controleer APP_EMAIL en APP_PASSWORD env vars.`
    );
  }
}

// Sessies eenmalig aanmaken vóór alle tests
export async function setupAllSessions(browser: Browser): Promise<void> {
  for (const role of Object.keys(TEST_USERS) as Array<keyof typeof TEST_USERS>) {
    if (!sessionIsValid(role)) {
      console.log(`🔐 Sessie aanmaken voor rol: ${role}`);
      const context = await browser.newContext();
      const page = await context.newPage();
      try {
        await loginViaUI(page, role);
        await context.storageState({ path: sessionPath(role) });
        console.log(`✅ Sessie opgeslagen: ${sessionPath(role)}`);
      } catch (e) {
        console.warn(`⚠️ Login mislukt voor ${role}, tests met deze rol zullen falen:`, e);
      }
      await page.close();
      await context.close();
    } else {
      console.log(`♻️ Bestaande sessie hergebruikt voor rol: ${role}`);
    }
  }
}
