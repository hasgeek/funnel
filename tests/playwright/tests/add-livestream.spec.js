import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { ProjectPage } = require('../page/create-project');
const project = require('../fixtures/project.json');
const { admin, editor } = require('../fixtures/user.json');
const videos = require('../fixtures/embed_video.json');

test('Add livestream and verify embed youtube and vimeo urls', async ({ page }) => {
  let projectPage = new ProjectPage(page);
  let randomProjectName = await projectPage.addProject(admin, [{'username': editor.username, 'role': 'editor'}]);
  let loginPage = new LoginPage(page);
  await loginPage.login(`/${admin.owns_profile}/${randomProjectName}`, editor.username, editor.password);

  await page.getByTestId('add-livestream').click();
  for(let video of videos) {
    await page.locator('#livestream_urls').type(video);
    await page.locator('#livestream_urls').press('Enter');
  }
  await page.getByTestId('form-submit-btn').click();

  for(let index=0; index<videos.length; index++) {
    await page.locator(`#tab-${index+1}`).click();
    await page.locator(`#pane-justified-${index+1}`).frameLocator('iframe').locator('[aria-label="Play"]').click();
    await page.locator(`#pane-justified-${index+1}`).frameLocator('iframe').locator('video').isVisible();
    await expect(page.locator(`#pane-justified-${index+1}`).frameLocator('iframe').locator('video')).toHaveAttribute('src');
  }

});
