import { test, expect } from '@playwright/test'

test('example data pairing/distribution flow', async ({ page }) => {
  await page.goto('/')
  await page.addStyleTag({ content: '* { transition: none !important; animation: none !important; }' })

  await page.getByLabel('Use Example Data').check()
  await page.getByTestId('process-btn').click()
  await expect(page.getByRole('heading', { name: /Direct Pairs/ })).toBeVisible()

  await expect(page).toHaveScreenshot('example_run.png', { fullPage: true })
})
