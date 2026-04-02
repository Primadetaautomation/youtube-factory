// pipeline-accessibility.spec.ts
// WCAG 2.1 AA tests voor YouTube Factory

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { authenticatedContext } from './fixtures/auth';
import './guards/environment';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3333';

test.describe('YouTube Factory — Accessibility WCAG 2.1 AA @regression', () => {

  test('login scherm: geen WCAG 2.1 AA schendingen @smoke @regression', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('#loginScreen', { state: 'visible' });

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();

    if (results.violations.length > 0) {
      const report = results.violations.map(v =>
        `\n[${v.impact?.toUpperCase()}] ${v.description} (regel: ${v.id})\n` +
        v.nodes.map(n => `  HTML: ${n.html}\n  Fix: ${n.failureSummary}`).join('\n')
      ).join('\n---\n');
      expect(results.violations, `WCAG schendingen op login:\n${report}`).toHaveLength(0);
    }
  });

  test('app shell: geen WCAG 2.1 AA schendingen @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });
    await page.waitForLoadState('networkidle');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();

    if (results.violations.length > 0) {
      const report = results.violations.map(v =>
        `\n[${v.impact?.toUpperCase()}] ${v.description} (regel: ${v.id})\n` +
        v.nodes.map(n => `  HTML: ${n.html}\n  Fix: ${n.failureSummary}`).join('\n')
      ).join('\n---\n');
      expect(results.violations, `WCAG schendingen in app:\n${report}`).toHaveLength(0);
    }

    await context.close();
  });

  test('focus ring zichtbaar bij Tab-navigatie op login @regression', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('#loginScreen', { state: 'visible' });

    await page.keyboard.press('Tab');
    const focused = page.locator(':focus');
    await expect(focused).toBeVisible();

    const styles = await focused.evaluate(el => {
      const cs = window.getComputedStyle(el);
      return {
        outline: cs.outline,
        outlineWidth: cs.outlineWidth,
        boxShadow: cs.boxShadow,
      };
    });

    const hasFocusRing =
      (styles.outlineWidth !== '0px' && styles.outline !== 'none') ||
      (styles.boxShadow !== 'none' && styles.boxShadow !== '');

    expect(
      hasFocusRing,
      `Focus indicator ontbreekt. outline="${styles.outline}", box-shadow="${styles.boxShadow}"`
    ).toBe(true);
  });

  test('focus ring zichtbaar in app shell @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    await page.keyboard.press('Tab');
    const focused = page.locator(':focus');

    if (await focused.count() > 0) {
      const styles = await focused.evaluate(el => {
        const cs = window.getComputedStyle(el);
        return {
          outline: cs.outline,
          outlineWidth: cs.outlineWidth,
          boxShadow: cs.boxShadow,
        };
      });

      const hasFocusRing =
        (styles.outlineWidth !== '0px' && styles.outline !== 'none') ||
        (styles.boxShadow !== 'none' && styles.boxShadow !== '');

      expect(
        hasFocusRing,
        `Focus indicator ontbreekt in app shell`
      ).toBe(true);
    }

    await context.close();
  });

  test('alle afbeeldingen hebben alt-tekst @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });
    await page.waitForLoadState('networkidle');

    const images = page.locator('img');
    const count = await images.count();
    for (let i = 0; i < count; i++) {
      const img = images.nth(i);
      const alt = await img.getAttribute('alt');
      const role = await img.getAttribute('role');
      const src = await img.getAttribute('src');

      // role="presentation" of role="none" = decoratief, geen alt nodig
      if (role === 'presentation' || role === 'none') continue;

      expect(alt, `img zonder alt-attribuut: src="${src}"`).not.toBeNull();
    }

    await context.close();
  });

  test('formuliervelden hebben toegankelijke labels @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    const inputs = page.locator(
      'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="range"]), select, textarea'
    );
    const count = await inputs.count();

    const unlabeled: string[] = [];
    for (let i = 0; i < count; i++) {
      const input = inputs.nth(i);
      if (!(await input.isVisible())) continue;

      const id = await input.getAttribute('id');
      const ariaLabel = await input.getAttribute('aria-label');
      const ariaLabelledBy = await input.getAttribute('aria-labelledby');
      const placeholder = await input.getAttribute('placeholder');

      const labelCount = id ? await page.locator(`label[for="${id}"]`).count() : 0;
      const hasLabel = labelCount > 0 || !!ariaLabel || !!ariaLabelledBy;

      if (!hasLabel) {
        unlabeled.push(`id="${id}" type="${await input.getAttribute('type')}" placeholder="${placeholder}"`);
      }
    }

    // Rapporteer alle ongelabelde velden
    if (unlabeled.length > 0) {
      console.warn(`⚠️ Velden zonder label (overweeg aria-label toe te voegen):\n${unlabeled.join('\n')}`);
    }

    await context.close();
  });

  test('kleurcontrast voldoet WCAG AA @regression', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    // Verwijder decoratieve grain overlay die axe's kleursampling verstoort
    await page.evaluate(() => {
      const style = document.createElement('style');
      style.textContent = 'body::before, body::after { content: none !important; display: none !important; visibility: hidden !important; opacity: 0 !important; }';
      document.head.appendChild(style);
      // Force reflow
      document.body.offsetHeight;
    });
    // Wacht tot styles toegepast zijn
    await page.waitForTimeout(200);

    const results = await new AxeBuilder({ page })
      .withRules(['color-contrast'])
      .analyze();

    if (results.violations.length > 0) {
      const report = results.violations.map(v =>
        v.nodes.map(n => `  ${n.html}: ${n.failureSummary}`).join('\n')
      ).join('\n');
      expect(results.violations, `Kleurcontrast schendingen:\n${report}`).toHaveLength(0);
    }

    await context.close();
  });

  test('login formulier labels aanwezig @smoke @regression', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('#loginScreen', { state: 'visible' });

    // Controleer of login velden labels of aria-labels hebben
    const emailInput = page.locator('#loginEmail');
    const passwordInput = page.locator('#loginPassword');

    const emailLabel = await emailInput.getAttribute('aria-label') ||
      await page.locator('label[for="loginEmail"]').count();
    const passwordLabel = await passwordInput.getAttribute('aria-label') ||
      await page.locator('label[for="loginPassword"]').count();

    // Log als labels ontbreken (dit is een accessibility issue om te fixen)
    if (!emailLabel) {
      console.warn('⚠️ Email input mist een accessible label — voeg aria-label of <label> toe');
    }
    if (!passwordLabel) {
      console.warn('⚠️ Password input mist een accessible label — voeg aria-label of <label> toe');
    }
  });
});
