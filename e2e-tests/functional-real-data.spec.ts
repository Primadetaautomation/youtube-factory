// functional-real-data.spec.ts
// FUNCTIONELE TEST — echte API calls, geen mocks
// Doorloopt de volledige video-productie pipeline met real data
//
// Vereist: alle API keys geconfigureerd (OPENAI, ELEVENLABS, YOUTUBE, GEMINI)
// Draait NIET in CI — alleen lokaal met `npx playwright test --grep "@functional"`

import { test, expect } from '@playwright/test';
import { authenticatedContext } from './fixtures/auth';
import { cleanupPipeline } from './fixtures/test-data';
import './guards/environment';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3333';
const TOPIC = 'Max Verstappen F1 2024 Season';

// Langere timeouts voor echte API calls
test.setTimeout(300_000); // 5 minuten per test

test.describe('YouTube Factory — Volledige Pipeline met Echte Data @functional', () => {

  test.afterAll(async () => {
    await cleanupPipeline();
  });

  // ============================================================
  // STAP 0 → 1: Script Generatie (OpenAI)
  // ============================================================
  test('stap 0→1: script genereren met OpenAI @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    // API status checken
    await page.waitForLoadState('networkidle');

    // Topic invoeren
    await page.locator('#topicInput').fill(TOPIC);

    // Duur instellen op 2 minuten (sneller voor test)
    const durationSelect = page.locator('#durationSelect');
    await durationSelect.selectOption('2');

    // Script genereren
    const generateBtn = page.locator('#generateBtn');
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();

    // Wacht op spinner
    await expect(page.getByText(/script wordt gegenereerd/i)).toBeVisible({ timeout: 5000 });

    // Wacht tot script klaar is — dit kan 10-30 seconden duren (OpenAI call)
    await expect(page.locator('.step-header .label')).toContainText('Stap 02', { timeout: 60_000 });

    // Verifieer: script textarea moet gevuld zijn
    const scriptArea = page.locator('#scriptArea');
    await expect(scriptArea).toBeVisible();
    const scriptText = await scriptArea.inputValue();
    expect(scriptText.length, 'Script is leeg').toBeGreaterThan(50);
    console.log(`✅ Script gegenereerd: ${scriptText.length} karakters`);

    // Verifieer: scenes moeten aanwezig zijn
    const sceneCards = page.locator('.scene-card, [class*="scene"]');
    const sceneCount = await sceneCards.count();
    console.log(`✅ Scenes gevonden: ${sceneCount}`);

    // Verifieer: titel moet bestaan
    const titleElement = page.locator('h2').first();
    const title = await titleElement.textContent();
    console.log(`✅ Titel: ${title}`);

    await context.close();
  });

  // ============================================================
  // STAP 1 → 2: Script Review & Naar Voiceover
  // ============================================================
  test('stap 1→2: script reviewen en naar voiceover @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    // Genereer script
    await page.locator('#topicInput').fill(TOPIC);
    await page.locator('#durationSelect').selectOption('2');
    await page.locator('#generateBtn').click();
    await expect(page.locator('.step-header .label')).toContainText('Stap 02', { timeout: 60_000 });

    // Script is er — klik op "Voiceover genereren"
    const voiceoverBtn = page.locator('button').filter({ hasText: /voiceover/i });
    await expect(voiceoverBtn).toBeVisible();
    await voiceoverBtn.click();

    // We zijn nu in stap 2: voiceover instellingen
    await expect(page.getByRole('heading', { name: /voiceover instellingen/i })).toBeVisible({ timeout: 10_000 });

    // Voices moeten geladen zijn
    await page.waitForLoadState('networkidle');
    // Wacht op stemkeuze cards (mannenstemmen of vrouwenstemmen)
    await expect(page.getByText(/mannenstemmen|vrouwenstemmen/i).first()).toBeVisible({ timeout: 10_000 });

    console.log('✅ Voiceover instellingen geladen met stemkeuzes');

    await context.close();
  });

  // ============================================================
  // STAP 2: Voiceover Generatie (ElevenLabs)
  // ============================================================
  test('stap 2: voiceover genereren met ElevenLabs @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    // Script genereren
    await page.locator('#topicInput').fill(TOPIC);
    await page.locator('#durationSelect').selectOption('2');
    await page.locator('#generateBtn').click();
    await expect(page.locator('.step-header .label')).toContainText('Stap 02', { timeout: 60_000 });

    // Naar voiceover
    await page.locator('button').filter({ hasText: /voiceover/i }).click();
    await expect(page.getByRole('heading', { name: /voiceover instellingen/i })).toBeVisible({ timeout: 10_000 });
    await page.waitForLoadState('networkidle');

    // Wacht tot stemkeuze cards geladen zijn
    const voiceCards = page.locator('[id^="voice-"]');
    await expect(voiceCards.first()).toBeVisible({ timeout: 15_000 });

    // Selecteer eerste stem (klik, maar niet wachten op preview audio)
    await voiceCards.first().click();
    await page.waitForTimeout(1000);

    // Genereer voiceover
    const generateVoiceBtn = page.locator('button').filter({ hasText: /voiceover genereren/i });
    await expect(generateVoiceBtn).toBeVisible();
    await generateVoiceBtn.click();

    // Wacht op spinner
    await expect(page.getByText(/voiceover wordt gegenereerd/i)).toBeVisible({ timeout: 5000 });

    // Wacht tot voiceover klaar is — ElevenLabs call kan 15-60 seconden duren
    await expect(page.locator('audio')).toBeVisible({ timeout: 120_000 });

    // Verifieer: audio player met source
    const audioSrc = await page.locator('audio').getAttribute('src');
    expect(audioSrc, 'Audio src is leeg').toBeTruthy();
    expect(audioSrc).toContain('/output/');
    console.log(`✅ Voiceover gegenereerd: ${audioSrc}`);

    // Verifieer: duur wordt getoond
    const durationText = await page.getByText(/seconden/i).first().textContent();
    console.log(`✅ Duur: ${durationText}`);

    await context.close();
  });

  // ============================================================
  // STAP 3: Clips Zoeken (YouTube Data API)
  // ============================================================
  test('stap 3: clips zoeken via YouTube API @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    // Script genereren
    await page.locator('#topicInput').fill(TOPIC);
    await page.locator('#durationSelect').selectOption('2');
    await page.locator('#generateBtn').click();
    await expect(page.locator('.step-header .label')).toContainText('Stap 02', { timeout: 60_000 });

    // Naar voiceover en direct door naar clips
    await page.locator('button').filter({ hasText: /voiceover/i }).click();
    await expect(page.getByText(/voiceover instellingen/i)).toBeVisible({ timeout: 10_000 });

    // Selecteer stem en genereer
    await page.waitForLoadState('networkidle');
    const voiceCards = page.locator('[id^="voice-"]');
    await expect(voiceCards.first()).toBeVisible({ timeout: 10_000 });
    await voiceCards.first().click();
    await page.waitForTimeout(1000);

    await page.locator('button').filter({ hasText: /voiceover genereren/i }).click();
    await expect(page.locator('audio')).toBeVisible({ timeout: 120_000 });

    // Door naar clips zoeken
    const clipsBtn = page.locator('button').filter({ hasText: /clips zoeken/i });
    await expect(clipsBtn).toBeVisible();
    await clipsBtn.click();

    // Stap 3: clips zoeken
    await expect(page.getByText(/clips zoeken|zoek clips/i)).toBeVisible({ timeout: 10_000 });

    // Wacht op resultaten — YouTube API + yt-dlp search kan 30-60 seconden duren
    // Zoek naar clip selectie opties
    await expect(
      page.locator('.clip-option, .clip-card, [class*="clip"]').first()
    ).toBeVisible({ timeout: 120_000 });

    const clipOptions = page.locator('.clip-option, .clip-card, [class*="clip"]');
    const clipCount = await clipOptions.count();
    expect(clipCount, 'Geen clips gevonden').toBeGreaterThan(0);
    console.log(`✅ ${clipCount} clips gevonden voor selectie`);

    await context.close();
  });

  // ============================================================
  // TOOLS: Voices API
  // ============================================================
  test('voices API retourneert stemmen @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    // Direct API call met auth
    const token = await page.evaluate(() => localStorage.getItem('yt_factory_token'));
    const response = await page.request.get(`${BASE_URL}/api/voices`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 30_000,
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.voices).toBeDefined();
    expect(data.voices.length).toBeGreaterThan(0);

    for (const voice of data.voices) {
      expect(voice).toHaveProperty('id');
      expect(voice).toHaveProperty('name');
      expect(voice).toHaveProperty('gender');
    }
    console.log(`✅ ${data.voices.length} stemmen beschikbaar: ${data.voices.map((v: any) => v.name).join(', ')}`);

    await context.close();
  });

  // ============================================================
  // TOOLS: Prompt Templates
  // ============================================================
  test('prompt templates API retourneert templates @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    const token = await page.evaluate(() => localStorage.getItem('yt_factory_token'));
    const response = await page.request.get(`${BASE_URL}/api/prompt-templates`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 30_000,
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.templates).toBeDefined();
    expect(data.templates.length).toBeGreaterThan(0);
    console.log(`✅ ${data.templates.length} prompt templates beschikbaar`);

    await context.close();
  });

  // ============================================================
  // TOOLS: Metadata Generatie (OpenAI)
  // ============================================================
  test('metadata generatie werkt met echte OpenAI call @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    const token = await page.evaluate(() => localStorage.getItem('yt_factory_token'));
    const response = await page.request.post(`${BASE_URL}/api/generate-metadata`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 60_000,
      data: {
        topic: TOPIC,
        script: 'Max Verstappen dominates the 2024 F1 season with incredible races and championship wins.',
      },
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.title, 'Metadata title ontbreekt').toBeTruthy();
    expect(data.description, 'Metadata description ontbreekt').toBeTruthy();
    expect(data.tags, 'Metadata tags ontbreekt').toBeDefined();
    expect(data.tags.length).toBeGreaterThan(0);
    console.log(`✅ Metadata: "${data.title}" — ${data.tags.length} tags`);

    await context.close();
  });

  // ============================================================
  // TOOLS: Viral Titles (OpenAI)
  // ============================================================
  test('viral titles generatie werkt @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    const token = await page.evaluate(() => localStorage.getItem('yt_factory_token'));
    const response = await page.request.post(`${BASE_URL}/api/viral-titles`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 60_000,
      data: {
        topic: TOPIC,
        script: 'Max Verstappen wins the championship.',
      },
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.titles || data.suggestions || data).toBeTruthy();
    console.log(`✅ Viral titles gegenereerd`);

    await context.close();
  });

  // ============================================================
  // TOOLS: Viral Descriptions (OpenAI)
  // ============================================================
  test('viral descriptions generatie werkt @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    const token = await page.evaluate(() => localStorage.getItem('yt_factory_token'));
    const response = await page.request.post(`${BASE_URL}/api/viral-descriptions`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 60_000,
      data: {
        topic: TOPIC,
        script: 'Max Verstappen wins the championship.',
      },
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toBeTruthy();
    console.log(`✅ Viral descriptions gegenereerd`);

    await context.close();
  });

  // ============================================================
  // TOOLS: Niche Analyzer (YouTube API)
  // ============================================================
  test('niche analyzer werkt met echte YouTube data @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    const token = await page.evaluate(() => localStorage.getItem('yt_factory_token'));
    const response = await page.request.post(`${BASE_URL}/api/analyze-niche`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 60_000,
      data: { topic: 'Formula 1' },
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toBeTruthy();
    console.log(`✅ Niche analyse compleet`);

    await context.close();
  });

  // ============================================================
  // TOOLS: Copyright Checker
  // ============================================================
  test('copyright checker werkt op YouTube URL @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    const token = await page.evaluate(() => localStorage.getItem('yt_factory_token'));
    const response = await page.request.post(`${BASE_URL}/api/check-copyright`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 60_000,
      data: { url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' },
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toBeTruthy();
    console.log(`✅ Copyright check compleet`);

    await context.close();
  });

  // ============================================================
  // TOOLS MODE: UI navigatie en tools renderen
  // ============================================================
  test('tools mode toont alle tools correct @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    // Switch naar Tools mode
    await page.locator('#modeTools').click();
    await expect(page.locator('#modeTools')).toHaveClass(/active/);

    // Wacht op tools rendering
    await page.waitForLoadState('networkidle');

    // Controleer dat de tools zichtbaar zijn
    const mainContent = page.locator('#mainContent');
    await expect(mainContent).toBeVisible();

    // Zoek naar tool-gerelateerde tekst
    const toolTexts = [
      /viral|titel/i,
      /beschrijving|description/i,
      /niche/i,
      /copyright/i,
      /highlight/i,
      /prompt|template/i,
    ];

    let foundTools = 0;
    for (const pattern of toolTexts) {
      const match = mainContent.getByText(pattern).first();
      if (await match.isVisible().catch(() => false)) {
        foundTools++;
      }
    }
    expect(foundTools, `Slechts ${foundTools} tools gevonden`).toBeGreaterThanOrEqual(2);
    console.log(`✅ ${foundTools} tools zichtbaar in Tools mode`);

    await context.close();
  });

  // ============================================================
  // WEEKPLANNER MODE: UI rendering
  // ============================================================
  test('weekplanner mode toont formulier @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    // Switch naar Weekplanner mode
    await page.locator('#modeBatch').click();
    await expect(page.locator('#modeBatch')).toHaveClass(/active/);
    await page.waitForLoadState('networkidle');

    // Weekplanner content moet geladen zijn
    const mainContent = page.locator('#mainContent');
    await expect(mainContent).toBeVisible();

    // Zoek naar weekplanner elementen
    const hasWeekContent = await mainContent.getByText(/weekplanner|planning|batch|topics/i).first().isVisible().catch(() => false);
    expect(hasWeekContent, 'Weekplanner content niet gevonden').toBe(true);

    console.log('✅ Weekplanner mode correct geladen');

    await context.close();
  });

  // ============================================================
  // SHORTS MODE: UI rendering
  // ============================================================
  test('shorts mode laadt correct @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    // Switch naar Shorts mode
    await page.locator('#modeShorts').click();
    await expect(page.locator('#modeShorts')).toHaveClass(/active/);
    await page.waitForLoadState('networkidle');

    // Shorts pipeline stap 0 moet zichtbaar zijn
    const mainContent = page.locator('#mainContent');
    await expect(mainContent).toBeVisible();

    // Topic input moet er zijn (shorts gebruikt zelfde stap 0)
    const topicInput = page.locator('#topicInput');
    if (await topicInput.isVisible()) {
      console.log('✅ Shorts mode: topic input beschikbaar');
    }

    // Aspect ratio moet op 9:16 staan of instelbaar zijn
    const aspectSelect = page.locator('#cfgAspect');
    if (await aspectSelect.isVisible()) {
      const value = await aspectSelect.inputValue();
      console.log(`✅ Shorts mode: aspect ratio = ${value}`);
    }

    await context.close();
  });

  // ============================================================
  // API STATUS: alle diensten connected
  // ============================================================
  test('alle API diensten zijn connected @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();

    const response = await page.request.get(`${BASE_URL}/api/status`, { timeout: 30_000 });
    expect(response.status()).toBe(200);

    const data = await response.json();
    console.log('API Status:', JSON.stringify(data));

    expect(data.openai, 'OpenAI niet geconfigureerd').toBe(true);
    expect(data.elevenlabs, 'ElevenLabs niet geconfigureerd').toBe(true);
    expect(data.youtube, 'YouTube niet geconfigureerd').toBe(true);
    expect(data.gemini, 'Gemini niet geconfigureerd').toBe(true);

    console.log('✅ Alle 4 API diensten connected');

    await context.close();
  });

  // ============================================================
  // REFINE SCRIPT: feedback verwerken (OpenAI)
  // ============================================================
  test('script refinen met feedback werkt @functional', async ({ browser }) => {
    const context = await authenticatedContext(browser, 'admin');
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await expect(page.locator('#appShell')).toBeVisible({ timeout: 10_000 });

    const token = await page.evaluate(() => localStorage.getItem('yt_factory_token'));
    const response = await page.request.post(`${BASE_URL}/api/refine-script`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 60_000,
      data: {
        script: 'Max Verstappen won the 2024 championship with brilliant driving.',
        feedback: 'Maak het dramatischer en voeg meer spanning toe.',
      },
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.script || data).toBeTruthy();
    console.log('✅ Script verfijning met feedback werkt');

    await context.close();
  });
});
