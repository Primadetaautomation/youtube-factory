// e2e-tests/fixtures/mocks.ts
// Externe diensten mocken — tests draaien nooit met echte AI-APIs

import { Page } from '@playwright/test';

// === OPENAI (Script generatie) ===

export async function mockOpenAISuccess(page: Page): Promise<void> {
  await page.route('**/api.openai.com/**', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        choices: [{
          message: {
            content: JSON.stringify({
              title: 'Test Video Title',
              script: 'Dit is een test script voor de video pipeline.',
              scenes: [
                { visual: 'Test scene 1', narration: 'Eerste scene narration.' },
                { visual: 'Test scene 2', narration: 'Tweede scene narration.' },
              ],
            }),
          },
        }],
      }),
    })
  );
}

// === ELEVENLABS (Voiceover) ===

export async function mockElevenLabsSuccess(page: Page): Promise<void> {
  await page.route('**/api.elevenlabs.io/**', route =>
    route.fulfill({
      status: 200,
      contentType: 'audio/mpeg',
      body: Buffer.from('fake-audio-data'),
    })
  );
}

// === GEMINI (Clip analyse, Thumbnail AI) ===

export async function mockGeminiSuccess(page: Page): Promise<void> {
  await page.route('**/generativelanguage.googleapis.com/**', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        candidates: [{
          content: {
            parts: [{ text: 'Mock Gemini response for testing' }],
          },
        }],
      }),
    })
  );
}

// === YOUTUBE DATA API (Clip zoeken) ===

export async function mockYouTubeSearchSuccess(page: Page): Promise<void> {
  await page.route('**/www.googleapis.com/youtube/**', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          { id: { videoId: 'dQw4w9WgXcQ' }, snippet: { title: 'Test Clip 1' } },
          { id: { videoId: 'jNQXAC9IVRw' }, snippet: { title: 'Test Clip 2' } },
        ],
      }),
    })
  );
}

// === BACKEND API MOCKS (voor geïsoleerde frontend tests) ===

export async function mockScriptGeneration(page: Page): Promise<void> {
  await page.route('**/api/generate-script', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        title: 'Mock Video: Test Onderwerp',
        script: 'Dit is een mock script gegenereerd voor testdoeleinden. Het bevat voldoende tekst om een realistische video te simuleren.',
        scenes: [
          { visual: 'Opening shot van het onderwerp', narration: 'Welkom bij deze video.' },
          { visual: 'Uitleg met graphics', narration: 'Laten we dieper ingaan op het onderwerp.' },
          { visual: 'Conclusie shot', narration: 'Bedankt voor het kijken.' },
        ],
      }),
    })
  );
}

export async function mockVoiceoverGeneration(page: Page): Promise<void> {
  await page.route('**/api/generate-voiceover', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        path: 'test_voiceover.mp3',
        duration: 45.5,
        word_timestamps: [
          { word: 'Welkom', start: 0.0, end: 0.5 },
          { word: 'bij', start: 0.5, end: 0.7 },
          { word: 'deze', start: 0.7, end: 1.0 },
          { word: 'video', start: 1.0, end: 1.5 },
        ],
      }),
    })
  );
}

export async function mockClipSearch(page: Page): Promise<void> {
  await page.route('**/api/search-clips', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        visuals: [
          {
            scene: 'Opening shot',
            clips: [
              { url: 'https://youtube.com/watch?v=test1', title: 'Test Clip 1', duration: 30 },
              { url: 'https://youtube.com/watch?v=test2', title: 'Test Clip 2', duration: 45 },
            ],
          },
          {
            scene: 'Uitleg scene',
            clips: [
              { url: 'https://youtube.com/watch?v=test3', title: 'Test Clip 3', duration: 60 },
            ],
          },
        ],
      }),
    })
  );
}

export async function mockClipDownload(page: Page): Promise<void> {
  await page.route('**/api/download-clips', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        clips: [
          { index: 0, file: 'clip_0.mp4', title: 'Test Clip 1' },
          { index: 1, file: 'clip_1.mp4', title: 'Test Clip 2' },
        ],
        count: 2,
        clips_dir: '/tmp/test-clips',
      }),
    })
  );
}

export async function mockCombineVideo(page: Page): Promise<void> {
  await page.route('**/api/combine-video', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ video: 'test_final.mp4' }),
    })
  );
}

export async function mockThumbnailGeneration(page: Page): Promise<void> {
  await page.route('**/api/generate-thumbnail', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ thumbnail: 'test_thumbnail.png' }),
    })
  );
}

export async function mockMetadataGeneration(page: Page): Promise<void> {
  await page.route('**/api/generate-metadata', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        title: 'Mock Video Title - Test',
        description: 'Dit is een mock beschrijving voor testdoeleinden.',
        tags: ['test', 'mock', 'youtube-factory'],
      }),
    })
  );
}

export async function mockUpload(page: Page): Promise<void> {
  await page.route('**/api/upload', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        video_id: 'mock_video_id_123',
        url: 'https://youtu.be/mock_video_id_123',
      }),
    })
  );
}

export async function mockVoicesList(page: Page): Promise<void> {
  await page.route('**/api/voices', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        voices: [
          { id: 'voice1', name: 'George', gender: 'man', accent: 'Brits', desc: 'Warm verteller' },
          { id: 'voice2', name: 'Alice', gender: 'vrouw', accent: 'Brits', desc: 'Helder, educatief' },
        ],
      }),
    })
  );
}

export async function mockApiStatus(page: Page): Promise<void> {
  await page.route('**/api/status', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        openai: true,
        elevenlabs: true,
        youtube: true,
        gemini: true,
      }),
    })
  );
}

// Mock alle backend endpoints tegelijk voor geïsoleerde frontend tests
export async function mockAllBackendApis(page: Page): Promise<void> {
  await mockApiStatus(page);
  await mockVoicesList(page);
  await mockScriptGeneration(page);
  await mockVoiceoverGeneration(page);
  await mockClipSearch(page);
  await mockClipDownload(page);
  await mockCombineVideo(page);
  await mockThumbnailGeneration(page);
  await mockMetadataGeneration(page);
  await mockUpload(page);
}

// === SERVER ERROR ===

export async function mockServerError(page: Page, endpoint: string): Promise<void> {
  await page.route(`**${endpoint}`, route =>
    route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Internal Server Error' }),
    })
  );
}

export async function mockNetworkError(page: Page, endpoint: string): Promise<void> {
  await page.route(`**${endpoint}`, route => route.abort('internetdisconnected'));
}
