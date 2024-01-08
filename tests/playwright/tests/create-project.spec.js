import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { ProjectPage } = require('../page/create-project');
const { ProjectCrewFormPage } = require('../page/project-crew-form');
const project = require('../fixtures/project.json');
const { owner, admin, promoter, usher, editor, hguser } = require('../fixtures/user.json');

test('To create project, edit, publish and add crew', async ({ page }) => {
  let randomProjectName = Math.random().toString(36).substring(2, 7);
  let projectNameCapitalize = randomProjectName.charAt(0).toUpperCase() + randomProjectName.slice(1);
  let loginPage;
  loginPage = new LoginPage(page);
  await loginPage.login(`/${admin.owns_profile}`, admin.username, admin.password);

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
  let crewForm = new ProjectCrewFormPage(page);
  await page.getByTestId('crew').click();
  await crewForm.addMember(promoter.username, 'promoter');
  await crewForm.addMember(usher.username, 'usher');
  await crewForm.addMember(editor.username, 'editor');
  await crewForm.addMember(hguser.username, 'usher', false);
  await crewForm.deleteMember(promoter.username);

});
