import { test, expect } from '@playwright/test';
const { LoginPage } = require('../page/login');
const { ProjectCrewFormPage } = require('../page/project-crew-form');
const profile = require('../fixtures/profile.json');
const project = require('../fixtures/project.json');
const { owner } = require('../fixtures/user.json');

export class ProjectPage {
  constructor(page) {
    this.page = page;
  }

  async createNewProject(projectName) {
    await this.page.getByTestId('new-project').click();
    await this.page.locator('input#title').fill(projectName);
    await this.page.locator('input#location').type(project.location);
    await this.page.locator('input#tagline').type(project.tagline);
    await this.page.locator('#field-description .cm-editor .cm-line').fill(project.description);
    await this.page.getByTestId('form-submit-btn').click();
  }

  async publishProject() {
    await this.page.getByTestId('project-menu').click();
    await this.page.getByTestId('settings').click();
    await this.page.getByTestId('publish').click();
    await this.page.getByTestId('member":has-text("Published")').isVisible();
  }

  async addLabels() {
    await this.page.getByTestId('project-menu').locator('visible=true').click();
    await this.page.getByTestId('settings').locator('visible=true').click();
    await this.page.getByTestId('manage-labels').click();

    for (let label of project.labels) {
      await this.page.getByTestId('add-labels').click();
      await this.page.locator('input#title').fill(label.title);
      if (label.sublabels) {
        for (let i=0; i<label.sublabels.length; i++) {
          await this.page.locator('#add-sublabel-form').click();
          await this.page.locator('#child-form > .ui-draggable-box').locator(`nth=${i}`).locator('input#title').type(label.sublabels[i]);
        }
      }
      if (label.adminLabel) {
        await this.page.locator('#field-restricted label').click();
      }
      await this.page.getByTestId('save-label').click();
    }
    await this.page.getByTestId("project-page").click();
  }

  async addVenue() {
    await this.page.getByTestId('project-menu').locator("visible=true").click();
    await this.page.getByTestId('settings').locator("visible=true").waitFor();
    await this.page.getByTestId('settings').locator("visible=true").click();
    await this.page.getByTestId('manage-venues').click();
    await this.page.getByTestId('new-venue').click();
    await this.page.locator('input#title').fill('Online');
    await this.page.locator('#field-description .cm-editor .cm-line').fill('Zoom Link');
    await this.page.getByTestId('form-submit-btn').click();
    await this.page.locator(`.card[data-testid="Online-rooms"] a[data-testid="add-room"]`).click();
    await this.page.locator('input#title').fill('Zoom');
    await this.page.locator('#field-description .cm-editor .cm-line').fill('Zoom link');
    await this.page.getByTestId('form-submit-btn').click();
    await this.page.getByTestId("Zoom").isVisible();
    await this.page.getByTestId("project-page").click();
  }

  async openCFP() {
    await this.page.getByTestId('submissions').click();
    await this.page.getByTestId('add-cfp').click();
    await this.page.locator('#field-instructions .cm-editor .cm-line').fill(project.cfp_instructions);
    await this.page.getByTestId('add-cfp').click();
    await this.page.locator('label.switch-label').locator("visible=true").click();
  }

  async addProject(loginUser, crew) {
    let randomProjectName = Math.random().toString(36).substring(2, 7);
    let projectNameCapitalize = randomProjectName.charAt(0).toUpperCase() + randomProjectName.slice(1);
    let loginPage;
    loginPage = new LoginPage(this.page);
    await loginPage.login(`/${profile.title}`, owner.username, owner.password);
    await this.createNewProject(projectNameCapitalize);
    let crewForm = new ProjectCrewFormPage(this.page);
    await this.page.getByTestId('crew').click();
    for(let member in crew) {
      await crewForm.addMember(member.username, member.role);
    }
    await this.addLabels();
    await this.addVenue();
    await this.openCFP();
    await this.publishProject();

    await loginPage.logout();
    return randomProjectName;
  }

}
