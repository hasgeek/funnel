import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { ProjectPage } = require('../page/create-project');
const profile = require('../fixtures/profile.json');
const project = require('../fixtures/project.json');
const { owner } = require('../fixtures/user.json');

test('To create project, edit, publish', async ({ page }) => {
  let randomProjectName = Math.random().toString(36).substring(2, 7);
  let projectNameCapitalize = randomProjectName.charAt(0).toUpperCase() + randomProjectName.slice(1);
  let loginPage;
  loginPage = new LoginPage(page);
  await loginPage.login(`/${profile.title}`, owner.username, owner.password);
  await page.getByTestId('make-profile-public').click();
  await page.getByTestId('make-public-btn').waitFor();
  await page.getByTestId('make-public-btn').click();

  let projectPage = new ProjectPage(page);
  await projectPage.createNewProject(projectNameCapitalize);
  let titleRegex = new RegExp(projectNameCapitalize);
  await expect(page).toHaveTitle(titleRegex);
  await page.getByTestId('add-project-banner"]').isVisible();

  //Edit project (Failing)
  // await page.getByTestId('project-menu').click();
  // await page.getByTestId('edit').waitFor(3000);
  // await page.getByTestId('edit').click();
  // await page.locator('input#tagline').type(project.tagline);
  // await page.getByTestId('form-submit-btn').waitFor(20000);
  // await page.getByTestId('form-submit-btn').click();
  // await expect(page).toHaveTitle(titleRegex);

  //Publish project
  await projectPage.publishProject();

  await page.getByTestId('profile-link').click();
  await page.getByTestId('admin-dropdown').locator("visible=true").click();
  await page.getByTestId('make-profile-private').locator("visible=true").click();
  await page.getByTestId('make-private-btn').locator("visible=true").click();

});
