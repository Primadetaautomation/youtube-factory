// playwright.config.ts

import { defineConfig, devices } from '@playwright/test';
import './e2e-tests/guards/environment';

export default defineConfig({
  testDir: './e2e-tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : 4,

  // Sessies eenmalig aanmaken vóór alle tests (session caching)
  globalSetup: './e2e-tests/global-setup.ts',

  reporter: [
    ['html', { open: 'on-failure', outputFolder: 'playwright-report' }],
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }],
  ],

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3333',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },

  projects: [
    { name: 'Desktop Chrome',   use: { ...devices['Desktop Chrome'] } },
    { name: 'Desktop Firefox',  use: { ...devices['Desktop Firefox'] } },
    { name: 'Desktop Safari',   use: { ...devices['Desktop Safari'] } },
    { name: 'Mobile iPhone 14', use: { ...devices['iPhone 14'] } },
    { name: 'Mobile Android',   use: { ...devices['Pixel 7'] } },
  ],
});
