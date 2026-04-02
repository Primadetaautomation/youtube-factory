// e2e-tests/fixtures/test-data.ts

import { faker } from '@faker-js/faker';
import '../guards/environment';

// Vaste testgebruikers — credentials via env vars (zelfde als APP_EMAIL/APP_PASSWORD)
export const TEST_USERS = {
  admin: {
    email: process.env.TEST_ADMIN_EMAIL || process.env.APP_EMAIL || 'admin@test.local',
    password: process.env.TEST_ADMIN_PASSWORD || process.env.APP_PASSWORD || 'TestAdmin123!',
    name: 'Test Admin',
  },
  user: {
    email: process.env.TEST_USER_EMAIL || process.env.APP_EMAIL || 'user@test.local',
    password: process.env.TEST_USER_PASSWORD || process.env.APP_PASSWORD || 'TestUser123!',
    name: 'Test Gebruiker',
  },
} as const;

// Unieke testdata per run — voorkomt conflicten bij parallelle runs
export function generateUniqueTopic() {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  return {
    topic: `Test Topic ${id}`,
    duration: 4,
  };
}

export function generateUniqueUser() {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  return {
    email: `test-${id}@test.local`,
    password: 'TestWelkom123!',
    name: `Test User ${id}`,
  };
}

// Cleanup — reset pipeline state via API
export async function cleanupPipeline(): Promise<void> {
  const baseUrl = process.env.BASE_URL || 'http://localhost:3333';
  try {
    await fetch(`${baseUrl}/api/reset`, { method: 'POST' });
  } catch (err) {
    console.warn(`⚠️ Pipeline reset mislukt:`, err);
  }
}
