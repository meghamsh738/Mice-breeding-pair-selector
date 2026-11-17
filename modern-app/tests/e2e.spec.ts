import { test, expect } from '@playwright/test'

test('example data requires review of parent records and locus assumptions', async ({ page }) => {
  await page.goto('/')
  await page.addStyleTag({ content: '* { transition: none !important; animation: none !important; } .signature { display: none !important; }' })

  await page.getByLabel('Use Example Data').check()
  await page.getByLabel('Allow pairs when parent IDs are incomplete').check()
  await page.getByTestId('process-btn').click()
  await expect(page.getByRole('heading', { name: /Needs review before ranking/ })).toBeVisible()
  await expect(page.getByText(/Confirm the simple two-allele inheritance model/).first()).toBeVisible()

  await page.getByLabel('Use a simple two-allele inheritance model for each gene').check()
  await page.getByTestId('process-btn').click()
  await expect(page.getByRole('heading', { name: /Pairs that can produce the target at each locus/ })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: 'Lowest locus' })).toBeVisible()
  await expect(page.getByTestId('indirect-results').getByRole('columnheader', { name: 'Similarity score' })).toBeVisible()
  await expect(page.getByText(/combined probability not calculated/)).toBeVisible()

  await page.getByLabel('Calculate a combined probability assuming loci assort independently').check()
  await page.getByTestId('process-btn').click()
  await expect(page.getByRole('columnheader', { name: 'Probability' })).toBeVisible()
  const selectButtons = page.getByRole('button', { name: 'Select' })
  await expect.poll(() => selectButtons.count()).toBeGreaterThan(1)
  if (await page.getByTestId('indirect-results').count()) {
    await expect(page.getByTestId('indirect-results').getByRole('button', { name: 'Select' })).toHaveCount(0)
  }
  await selectButtons.nth(1).click()
  await page.getByRole('button', { name: 'Lock selected pair' }).click()
  await expect(page.getByText('Add a short reason when choosing a different eligible pair.')).toBeVisible()
  await page.getByRole('textbox', { name: 'Reason for this choice' }).fill('Keeps the preferred line available for this litter.')
  await page.getByRole('button', { name: 'Lock selected pair' }).click()
  await expect(page.getByText('Locked for this review')).toBeVisible()

  const downloadPromise = page.waitForEvent('download')
  await page.getByTestId('breeding-export-btn').click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('breeder_pairs.xlsx')

  await page.reload()
  await expect(page.getByText('Locked for this review')).toBeVisible()
  if (process.env.BREEDING_QA_SCREENSHOT_PATH) {
    await page.getByTestId('breeding-results-panel').screenshot({ path: process.env.BREEDING_QA_SCREENSHOT_PATH })
  }
})

test('uploaded CSV keeps missing genotypes and known shared parents visible', async ({ page }) => {
  await page.goto('/')
  await page.locator('[data-testid="breeders-upload-field"]').setInputFiles({
    name: 'parent-review.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from([
      'breeder_id,breeder_name,gender,sire_id,dam_id,cre,reporter',
      'M1,Male one,male,SHARED,MD1,+/-,+/+',
      'M2,Male two,male,SM2,DM2,+/-,+/+',
      'F1,Female one,female,SF1,SHARED,,+/+',
      'F2,Female two,female,SF2,DF2,+/-,+/+',
    ].join('\n')),
  })

  await expect(page.getByText('Loaded breeders: 4')).toBeVisible()
  await expect(page.getByLabel('Assume blank gene values use the configured wild type')).not.toBeChecked()
  await page.getByTestId('process-btn').click()
  await expect(page.getByRole('heading', { name: 'Excluded pairs' })).toBeVisible()
  await expect(page.getByText(/known shared parent/)).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Needs review before ranking' })).toBeVisible()
  await expect(page.getByText(/Missing genotypes: Female cre/)).toBeVisible()
})
