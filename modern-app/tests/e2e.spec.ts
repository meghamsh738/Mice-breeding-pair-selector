import { test, expect } from '@playwright/test'
import { promises as fs } from 'fs'

test('example data pairing/distribution flow', async ({ page }) => {
  await page.goto('/')

  await page.getByLabel('Use Example Data').check()
  await page.getByTestId('process-btn').click()
  await expect(page.getByRole('heading', { name: /Direct Pairs/ })).toBeVisible()

  await fs.mkdir('screenshots', { recursive: true })
  await page.screenshot({ path: 'screenshots/example_run.png', fullPage: true })
})
