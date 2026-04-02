// e2e-tests/global-setup.ts
// Draait één keer vóór alle tests: maakt sessies aan

import { chromium } from '@playwright/test';
import { setupAllSessions } from './fixtures/auth';
import './guards/environment';

async function globalSetup() {
  const browser = await chromium.launch();
  await setupAllSessions(browser);
  await browser.close();
}

export default globalSetup;
