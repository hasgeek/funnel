import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { usher, user, newuser } = require('../fixtures/user.json');
const project = require('../fixtures/project.json');

test('Add update to project', async ({ page }) => {
  let loginPage = new LoginPage(page);
  await loginPage.login(
    `/${usher.owns_profile}/${usher.project}`,
    usher.username,
    usher.password
  );

  await page.getByTestId('updates').click();
  await page.getByTestId('add-update').click();
  await page.locator('#title').fill(project.update_title);
  await page.locator('#field-body .cm-editor .cm-line').fill(project.update_body);
  await page.locator('#is_pinned').click();
  await page.getByTestId('form-submit-btn').click();
  await page.getByTestId('form-submit-btn').click();
  await page.getByTestId('add-update').click();
  await page.locator('#title').fill(project.restricted_update_title);
  await page
    .locator('#field-body .cm-editor .cm-line')
    .fill(project.restricted_update_body);
  await page.locator('#is_restricted').click();
  await page.getByTestId('form-submit-btn').click();
  await page.getByTestId('form-submit-btn').click();
  await loginPage.logout();

  await loginPage.login(
    `/${usher.owns_profile}/${usher.project}`,
    user.username,
    user.password
  );
  await expect(
    page.locator('.pinned__update__heading').locator('visible=true')
  ).toContainText(project.update_title);
  await page.getByTestId('updates').click();
  await expect(
    page.locator('.update').locator('nth=1').getByTestId('update-heading')
  ).toContainText(project.restricted_update_title);
  await loginPage.logout();

  await loginPage.login(
    `/${usher.owns_profile}/${usher.project}`,
    newuser.username,
    newuser.password
  );
  await page.getByTestId('updates').click();
  await expect(
    page.locator('.pinned__update__heading').locator('visible=true')
  ).toContainText(project.update_title);
  await page.getByTestId('updates').click();
  await expect(page.locator('.update').locator('nth=1')).toBeHidden();
  await loginPage.logout();
});
