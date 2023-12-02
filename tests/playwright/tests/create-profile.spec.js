import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { ProfileCrewFormPage } = require('../page/profile-crew-form');
const { owner, admin, promoter, hguser } = require('../fixtures/user.json');

test('To create profile, edit, add crew and update banner', async ({ page }) => {
  let randomOrgName = Math.random().toString(36).substring(2,7);
  let orgNameCapitalize = randomOrgName.charAt(0).toUpperCase() + randomOrgName.slice(1);
  let loginPage;
  loginPage = new LoginPage(page);
  await loginPage.login('/', owner.username, owner.password);
  await page.getByTestId('my-account').click();
  await page.getByTestId('org').click();
  await page.getByTestId('new').click();
  await page.locator('input#title').fill(orgNameCapitalize);
  await page.locator('input#name').fill(randomOrgName);
  await page.getByTestId('form-submit-btn').click();
  await page.locator('#field-description .cm-editor .cm-line').fill('Lorem Ipsum is simply dummy text of the printing and typesetting industry');
  await page.getByTestId('form-submit-btn').click();
  let titleRegex = new RegExp(orgNameCapitalize);
  await expect(page).toHaveTitle(titleRegex);

  // Add, edit  crew
  let crewForm = new ProfileCrewFormPage(page);
  await page.getByTestId('admins').click();
  await crewForm.addMember(admin.username, false);
  await crewForm.addMember(promoter.username, true);
  await crewForm.deleteMember(promoter.username);
  await crewForm.addMember(hguser.username,false, false);

  // Profile  transition from public to private
  await page.getByTestId('admin-dropdown').click();
  await page.getByTestId('make-profile-private').waitFor();
  await page.getByTestId('make-profile-private').click();
  await page.getByTestId('make-private-btn').waitFor();
  await page.getByTestId('make-private-btn').click();
  await page.getByTestId('make-profile-public').isVisible();
  await loginPage.logout();

  // Permissions for profile owner
  await loginPage.login(`/${randomOrgName}`, admin.username, admin.password);
  await page.getByTestId('admin-dropdown').locator('visible=true').click();
  await expect.soft(page.getByTestId('edit-details').locator('visible=true')).toBeVisible();
  await page.getByTestId('admins').click();
  await expect.soft(page.getByTestId('add-member')).toBeHidden();

  // Edit profile and update banner
  await page.getByTestId('admin-dropdown').locator('visible=true').click();
  await page.getByTestId('edit-details').locator('visible=true').waitFor(5000);
  await page.getByTestId('edit-details').locator('visible=true').click();
  await page.locator('#field-description .cm-editor .cm-line').fill('Lorem Ipsum is simply dummy');
  await page.getByTestId('form-submit-btn').click();
  await page.getByTestId('add-banner').isVisible();

  // Verify notification update
  await page.getByTestId('my-updates').locator('visible=true').click();
  await page.waitForResponse('/updates?page=1');
  await page.getByTestId('notification-box:has-text("' + orgNameCapitalize + '")');
});
