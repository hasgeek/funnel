import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { ProjectCrewFormPage } = require('../page/project-crew-form');
const { ProjectPage } = require('../page/create-project');
const profile = require('../fixtures/profile.json');
const project = require('../fixtures/project.json');
const { owner, admin, promoter, usher, editor, hguser } = require('../fixtures/user.json');

test('Add crew to project', async ({ page }) => {
  let randomProjectName = Math.random().toString(36).substring(2, 7);
  let projectNameCapitalize = randomProjectName.charAt(0).toUpperCase() + randomProjectName.slice(1);
  let loginPage;
  loginPage = new LoginPage(page);
  await loginPage.login(`/${profile.title}`, owner.username, owner.password);
  let projectPage = new ProjectPage(page);
  await projectPage.createNewProject(projectNameCapitalize);

  //Add crew
  let crewForm = new ProjectCrewFormPage(page);
  await page.getByTestId('crew').click();
  await crewForm.addMember(promoter.username, 'promoter');
  await crewForm.addMember(usher.username, 'usher');
  await crewForm.addMember(editor.username, 'editor');
  await crewForm.addMember(hguser.username, 'usher', false);
  await crewForm.deleteMember(promoter.username);

});
