import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { admin } = require('../fixtures/user.json');
const videos = require('../fixtures/embed_video.json');

test('Add livestream and verify embed youtube and vimeo urls', async ({ page }) => {
  let loginPage = new LoginPage(page);
  await loginPage.login(`/${admin.owns_profile}/${admin.project}`, admin.username, admin.password);

  await page.getByTestId('add-livestream-btn').click();
  for(let video of videos) {
    await page.locator('#livestream_urls').type(video.url);
    await page.locator('#livestream_urls').press('Enter');
  }
  await page.getByTestId('form-submit-btn').click();

  for(let index=0; index<videos.length; index++) {
    await page.locator(`#tab-${index+1}`).click();
    await await page.locator(`#pane-justified-${index+1}`).waitFor(6000);
    if(videos[index].valid) {
      await page.locator(`#pane-justified-${index+1}`).frameLocator('iframe').locator(videos[index].video_classname).isVisible();
    } else {
      await page.locator(`#pane-justified-${index+1}`).frameLocator('iframe').locator(videos[index].video_classname).isHidden();
    }
  }

});
