import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { ProjectCrewFormPage } = require('../page/project-crew-form');
const { ProjectPage } = require('../page/create-project');
const profile = require('../fixtures/profile.json');
const venues = require('../fixtures/venues.json');
const { owner, admin, promoter, usher, editor, hguser } = require('../fixtures/user.json');

test('Add venue to project', async ({ page }) => {
  let randomProjectName = Math.random().toString(36).substring(2, 7);
  let projectNameCapitalize = randomProjectName.charAt(0).toUpperCase() + randomProjectName.slice(1);
  let loginPage;
  loginPage = new LoginPage(page);
  await loginPage.login(`/${profile.title}`, owner.username, owner.password);
  // await page.getByTestId('make-profile-public').click();
  // await page.getByTestId('make-public-btn').waitFor();
  // await page.getByTestId('make-public-btn').click();

  let projectPage = new ProjectPage(page);
  await projectPage.createNewProject(projectNameCapitalize);


  await page.getByTestId('project-menu').locator("visible=true").click();
  await page.getByTestId('settings').locator("visible=true").waitFor();
  await page.getByTestId('settings').locator("visible=true").click();
  await page.getByTestId('manage-venues').click();

  let venue = venues[0];

  await page.getByTestId('new-venue').click();
  await page.locator('input#title').fill(venue.venue_title);
  await page.locator('#field-description .cm-editor .cm-line').fill(venue.venue_description);
  await page.locator('input#address1').fill(venue.venue_address1);
  await page.locator('input#address2').fill(venue.venue_address2);
  await page.locator('input#city').fill(venue.venue_city);
  await page.locator('input#state').fill(venue.venue_state);
  await page.locator('input#postcode').fill(venue.venue_postcode);
  await page.getByTestId('form-submit-btn').click();

  // cy.get(`[data-testid="${venues[1].venue_title}"]`).click();
  // cy.get('[data-testid="set-primary-venue"]').click();
  // cy.get(`[data-testid="${venues[1].venue_title}"]`).find('em').contains('(primary)');

  // venues.forEach((venue) => {
  //   cy.get(`.card[data-testid="${venue.venue_title}"]`)
  //     .find('a[data-testid="add-room"]')
  //     .click();
  //   cy.location('pathname').should('contain', '/new');
  //   cy.get('#title').type(venue.room.title);
  //   cy.get('#field-description')
  //     .find('.cm-editor .cm-line')
  //     .type(venue.room.description, { force: true });
  //   cy.get('#bgcolor').clear().type(venue.room.bgcolor);
  //   cy.get('button[data-testid="form-submit-btn"]').click();
  //   cy.location('pathname').should(
  //     'include',
  //     `/testcypressproject/${project.url}/venues`
  //   );
  //   cy.get(`.card[data-testid="${venue.venue_title}"]`)
  //     .find('li')
  //     .contains(venue.room.title);
  // });

  // venues.forEach((venue) => {
  //   cy.get(`[data-testid="${venue.room.title}"]`).should('exist');
  // });




});
