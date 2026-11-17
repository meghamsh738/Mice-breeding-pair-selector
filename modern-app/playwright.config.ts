import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 80_000,
  fullyParallel: true,
  expect: {
    // Self-hosted fonts may take a moment to be marked as "ready" in headless Chromium.
    timeout: 15_000,
    toHaveScreenshot: { animations: 'disabled', caret: 'hide' }
  },
  use: {
    baseURL: 'http://127.0.0.1:19522',
    trace: 'on-first-retry',
    viewport: { width: 1440, height: 900 },
    colorScheme: 'light',
    reducedMotion: 'reduce',
    video: 'retain-on-failure'
  },
  webServer: [
    {
      command: 'npm run dev:back',
      url: 'http://127.0.0.1:18522/openapi.json',
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: 'npm run dev:front',
      url: 'http://127.0.0.1:19522',
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chromium'],
        viewport: { width: 1440, height: 900 },
        colorScheme: 'light',
        reducedMotion: 'reduce'
      }
    }
  ]
})
