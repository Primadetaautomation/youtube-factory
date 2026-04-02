// e2e-tests/guards/environment.ts
// VEILIGHEIDSCHECK — voorkomt dat tests op productie draaien
// Dit bestand wordt geïmporteerd in elk spec-bestand

const BASE_URL = process.env.BASE_URL || 'http://localhost:3333';

// Lijst van productie-domeinen — uitbreiden met jouw domeinen
const PRODUCTION_DOMAINS = [
  'youtube-factory.com',
  'yt-factory.com',
  // Voeg hier jouw productie-URL's toe
];

const url = new URL(BASE_URL);
const isProduction = PRODUCTION_DOMAINS.some(domain =>
  url.hostname === domain || url.hostname.endsWith(`.${domain}`)
);

if (isProduction) {
  throw new Error(
    `🚨 GEBLOKKEERD: Tests draaien nooit op productie.\n` +
    `BASE_URL is ingesteld op: ${BASE_URL}\n` +
    `Gebruik: BASE_URL=http://localhost:3333 npx playwright test\n` +
    `Of:      BASE_URL=https://staging.jouwapp.nl npx playwright test`
  );
}

export const TEST_BASE_URL = BASE_URL;
export const IS_STAGING = url.hostname.includes('staging') || url.hostname.includes('test');
export const IS_LOCAL = url.hostname === 'localhost' || url.hostname === '127.0.0.1';
