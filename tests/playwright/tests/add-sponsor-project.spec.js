import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { owner, editor, admin } = require('../fixtures/user.json');

test('Add sponsor to project', async ({ page }) => {
  let loginPage = new LoginPage(page);
  await loginPage.login(
    `/${editor.owns_profile}/${editor.project}`,
    owner.username,
    owner.password
  );

  await page.getByTestId('site-editor-menu').locator('visible=true').click();
  await page.locator('.mui-dropdown__menu').locator('visible=true').waitFor(1000);
  await Promise.all([
    page.waitForRequest((request) => request.url().includes('/sponsor'), {
      timeout: 60000,
    }),
    await page.getByTestId('add-sponsor').click(),
  ]);
  await page.locator('.select2-selection__arrow').waitFor();
  await page.locator('.select2-selection__arrow').click();
  await page.locator('.select2-search__field').waitFor();
  await page.locator('.select2-search__field').fill(admin.owns_profile);
  await page.locator('.select2-results__option').waitFor();
  await page.locator('.select2-results__option').click();

  await Promise.all([
    page.waitForResponse(
      (response) => response.url().includes('/sponsor') && response.status() === 200,
      { timeout: 60000 }
    ),
    page.getByTestId('form-submit-btn').click(),
  ]);
  await page.getByTestId('sponsor-link":has-text(`${admin.owns_profile}`)').isVisible();

  await Promise.all([
    page.waitForRequest((request) => request.url().includes('/edit'), {
      timeout: 60000,
    }),
    await page.getByTestId('edit-sponsor').locator('nth=1').click(),
  ]);
  await page.locator('#is_promoted').click();
  await Promise.all([
    page.waitForResponse(
      (response) => response.url().includes('/edit') && response.status() === 200,
      { timeout: 60000 }
    ),
    page.getByTestId('form-submit-btn').click(),
  ]);
  await page.reload();
  await page.getByTestId('promoted').locator('nth=1').isVisible();

  await Promise.all([
    page.waitForRequest((request) => request.url().includes('/remove'), {
      timeout: 60000,
    }),
    await page.getByTestId('remove-sponsor').locator('nth=1').click(),
  ]);
  await Promise.all([
    page.waitForResponse(
      (response) => response.url().includes('/remove') && response.status() === 200,
      { timeout: 60000 }
    ),
    page.locator('input[value="Remove"]').click(),
  ]);
  await page.reload();
  await expect.soft(page.getByTestId('sponsor-card')).toBeHidden();
});
