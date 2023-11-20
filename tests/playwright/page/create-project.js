import { test, expect } from '@playwright/test';
const project = require('../fixtures/project.json');

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

}
