import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { ProjectCrewFormPage } = require('../page/project-crew-form');
const { ProjectPage } = require('../page/create-project');
const venues = require('../fixtures/venues.json');
const { promoter, usher } = require('../fixtures/user.json');

test('Add venue to project', async ({ page }) => {
  let projectPage = new ProjectPage(page);
  let randomProjectName = await projectPage.addProject(promoter, [{'username': usher.username, 'role': 'editor'}]);
  let loginPage = new LoginPage(page);
  await loginPage.login(`/${promoter.owns_profile}/${randomProjectName}`, usher.username, usher.password);

  await page.getByTestId('project-menu').locator("visible=true").click();
  await page.getByTestId('settings').locator("visible=true").waitFor();
  await page.getByTestId('settings').locator("visible=true").click();
  await page.getByTestId('manage-venues').click();

  for (let venue of venues) {
    await page.getByTestId('new-venue').click();
    await page.locator('input#title').fill(venue.venue_title);
    await page.locator('#field-description .cm-editor .cm-line').fill(venue.venue_description);
    if(venue.venue_address1) {
      await page.locator('input#address1').fill(venue.venue_address1);
      await page.locator('input#address2').fill(venue.venue_address2);
      await page.locator('input#city').fill(venue.venue_city);
      await page.locator('input#state').fill(venue.venue_state);
      await page.locator('input#postcode').fill(venue.venue_postcode);
    }
    await page.getByTestId('form-submit-btn').click();
  };

  await page.getByTestId(`${venues[1].venue_title}`).click();
  await page.getByTestId('set-primary-venue').click();
  await page.locator(`data-testid=${venues[1].venue_title}-rooms em`, { hasText: 'Details' }).isVisible();

  for (let venue of venues) {
    await page.locator(`.card[data-testid="${venue.venue_title}-rooms"] a[data-testid="add-room"]`)
      .click();
    await page.locator('input#title').fill(venue.room.title);
    await page.locator('#field-description .cm-editor .cm-line').fill(venue.room.description);
    await page.locator('input#bgcolor').fill(venue.room.bgcolor);
    await page.getByTestId('form-submit-btn').click();
    await page.getByTestId(`${venue.room.title}`).isVisible();
  };


});
