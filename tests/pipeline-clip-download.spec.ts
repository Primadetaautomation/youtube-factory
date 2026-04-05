// pipeline-clip-download.spec.ts
// FUNCTIONELE TEST — echte API calls, geen mocks
// Focus: clip download pipeline (stap 1-5) met echte YouTube downloads
//
// === RISICOANALYSE ===
// App-type: Video productie pipeline (YouTube Factory)
// Kritiek pad: Script -> Voiceover -> Clips zoeken -> Clips downloaden -> Video samenstellen
// Externe diensten: OpenAI, ElevenLabs, YouTube (yt-dlp), Gemini
// Top 5 risico's:
//   1. yt-dlp downloads falen op cloud IPs (YouTube blocking) - DIT IS HET HUIDIGE PROBLEEM
//   2. OpenAI/ElevenLabs API timeouts bij script/voiceover generatie
//   3. Clips downloaden maar niet als .mp4 opgeslagen (format mismatch)
//   4. Download progress UI toont "mislukt" maar server returnt 200
//   5. Race condition bij parallel downloaden van 20+ clips

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3333';

// Langere timeouts voor echte API calls
test.setTimeout(300_000);

// Productie-bescherming
const url = new URL(BASE_URL);
const PRODUCTION_DOMAINS = ['youtube-factory-production.up.railway.app'];
const isProduction = PRODUCTION_DOMAINS.some(d => url.hostname === d);
if (isProduction) {
  throw new Error('Tests draaien NIET op productie. Gebruik BASE_URL=http://localhost:3333');
}

test.describe('YouTube Factory — Clip Download Pipeline @functional', () => {

  test('API status: alle externe diensten connected @functional @smoke', async ({ page }) => {
    const response = await page.request.get(`${BASE_URL}/api/status`, { timeout: 10_000 });
    expect(response.status()).toBe(200);
    const data = await response.json();

    console.log('API Status:', JSON.stringify(data));
    expect(data.openai, 'OpenAI niet connected').toBe(true);
    expect(data.elevenlabs, 'ElevenLabs niet connected').toBe(true);
    expect(data.youtube, 'YouTube niet connected').toBe(true);
  });

  test('login werkt met correcte credentials @functional @smoke', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Login form invullen
    await page.locator('input[type="email"], input[placeholder*="mail"]').fill('admin@youtubefactory.nl');
    await page.locator('input[type="password"]').fill('factory2026!');
    await page.locator('button:has-text("Inloggen"), button:has-text("Login")').click();

    // Wacht tot pipeline zichtbaar is (stap 1 geladen)
    await expect(page.locator('#pipeline')).toBeVisible({ timeout: 10_000 });
    console.log('Login geslaagd');
  });

  test('volledige pipeline tot clip download @functional', async ({ page }) => {
    // ─── LOGIN ───
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.locator('input[type="email"], input[placeholder*="mail"]').fill('admin@youtubefactory.nl');
    await page.locator('input[type="password"]').fill('factory2026!');
    await page.locator('button:has-text("Inloggen"), button:has-text("Login")').click();
    await expect(page.locator('#pipeline')).toBeVisible({ timeout: 10_000 });

    // ─── STAP 1: Onderwerp kiezen + Script genereren ───
    console.log('STAP 1: Script genereren...');
    await page.locator('#topicInput').fill('Carlos Alcaraz tennis');
    await page.locator('#generateBtn').click();

    // Wacht op script response (kan 30+ sec duren met OpenAI)
    await page.waitForResponse(
      resp => resp.url().includes('/api/generate-script') && resp.status() === 200,
      { timeout: 60_000 }
    );
    await page.waitForTimeout(2000);
    console.log('Script gegenereerd');

    // ─── STAP 2: Script reviewen -> door naar voiceover ───
    console.log('STAP 2: Door naar voiceover...');
    // Knop "Voiceover genereren" (onclick="goToVoiceover()")
    const goToVoiceBtn = page.locator('button:has-text("Voiceover genereren")').first();
    await expect(goToVoiceBtn).toBeVisible({ timeout: 10_000 });
    await goToVoiceBtn.click();

    // ─── STAP 3: Voiceover genereren ───
    console.log('STAP 3: Voiceover genereren...');
    // Wacht tot voices geladen zijn
    await page.waitForResponse(
      resp => resp.url().includes('/api/voices') && resp.status() === 200,
      { timeout: 15_000 }
    );
    await page.waitForTimeout(1000);

    // Selecteer eerste voice card
    const voiceCard = page.locator('.voice-card').first();
    if (await voiceCard.isVisible()) {
      await voiceCard.click();
    }

    // Klik "Voiceover genereren" (onclick="startVoiceover()")
    const startVoiceBtn = page.locator('button:has-text("Voiceover genereren")').first();
    await startVoiceBtn.click();

    await page.waitForResponse(
      resp => resp.url().includes('/api/generate-voiceover') && resp.status() === 200,
      { timeout: 120_000 }
    );
    console.log('Voiceover gegenereerd');

    // ─── STAP 4: Clips zoeken & kiezen ───
    console.log('STAP 4: Clips zoeken...');
    // Na voiceover komt er een "Clips zoeken" knop
    const clipsZoekenBtn = page.locator('button:has-text("Clips zoeken")');
    await expect(clipsZoekenBtn).toBeVisible({ timeout: 10_000 });

    // Intercepteer search response voordat we klikken
    const searchResponsePromise = page.waitForResponse(
      resp => resp.url().includes('/api/search-clips') && resp.status() === 200,
      { timeout: 300_000 }
    );
    await clipsZoekenBtn.click();

    await searchResponsePromise;
    await page.waitForTimeout(2000);
    console.log('Clips gevonden');

    // ─── STAP 5: Clips downloaden — DE KRITIEKE TEST ───
    console.log('STAP 5: Clips downloaden (FOCUS TEST)...');

    // Klik "Download geselecteerde clips"
    const downloadBtn = page.locator('button:has-text("Download geselecteerde clips")');
    await expect(downloadBtn).toBeVisible({ timeout: 10_000 });

    // Intercepteer de download-clips response
    const downloadResponsePromise = page.waitForResponse(
      resp => resp.url().includes('/api/download-clips'),
      { timeout: 180_000 }
    );

    await downloadBtn.click();

    const downloadResponse = await downloadResponsePromise;
    const downloadData = await downloadResponse.json();

    console.log('Download response status:', downloadResponse.status());
    console.log('Download data:', JSON.stringify(downloadData, null, 2));
    console.log(`Clips gedownload: ${downloadData.count || 0}`);

    // KRITIEKE VERIFICATIE: minstens 1 clip moet gedownload zijn
    expect(downloadResponse.status(), 'Download endpoint returned error').toBe(200);
    expect(downloadData.count, 'GEEN clips gedownload - dit is het productie-probleem!').toBeGreaterThan(0);

    // Verifieer dat gedownloade clips echte files zijn
    if (downloadData.clips && downloadData.clips.length > 0) {
      for (const clip of downloadData.clips) {
        expect(clip.file, `Clip ${clip.index} heeft geen filename`).toBeTruthy();
        expect(clip.file, `Clip ${clip.index} is geen .mp4`).toContain('.mp4');
        console.log(`  Clip ${clip.index}: ${clip.file} - "${clip.title}"`);
      }
    }

    console.log(`RESULTAAT: ${downloadData.count} clips succesvol gedownload`);
  });

  // Directe API test voor clip download (zonder UI)
  test('directe API test: enkele clip downloaden @functional', async ({ page }) => {
    // Login voor auth token
    const loginResp = await page.request.post(`${BASE_URL}/api/auth/login`, {
      data: { email: 'admin@youtubefactory.nl', password: 'factory2026!' },
      timeout: 10_000,
    });
    expect(loginResp.status()).toBe(200);
    const { token } = await loginResp.json();

    // Download 1 specifieke clip om yt-dlp te testen
    const downloadResp = await page.request.post(`${BASE_URL}/api/download-clips`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 120_000,
      data: {
        topic: 'test-clip-download',
        clips: [
          {
            url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', // bekende stabiele video
            index: 1,
            title: 'Test clip download',
          },
        ],
      },
    });

    console.log('Direct API download status:', downloadResp.status());
    const data = await downloadResp.json();
    console.log('Direct API download result:', JSON.stringify(data, null, 2));

    expect(downloadResp.status()).toBe(200);
    expect(data.count, 'Directe clip download mislukt - yt-dlp werkt niet').toBeGreaterThan(0);
    expect(data.clips[0].file).toContain('.mp4');
    console.log(`Direct download OK: ${data.clips[0].file}`);
  });
});
