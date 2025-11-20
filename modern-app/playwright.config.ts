import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 80_000,
  fullyParallel: true,
  use: {
    baseURL: 'http://localhost:5174',
    trace: 'on-first-retry'
  },
  webServer: {
    command: 'npm run dev:full',
    url: 'http://localhost:5174',
    reuseExistingServer: true,
    timeout: 120_000,
    stdout: 'ignore'
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chromium'] }
    }
  ]
})
