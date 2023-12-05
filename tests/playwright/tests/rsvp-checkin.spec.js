import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { ProjectPage } = require('../page/create-project');
const profile = require('../fixtures/profile.json');
const project = require('../fixtures/project.json');
const { promoter, usher, user } = require('../fixtures/user.json');
const events = require('../fixtures/ticket_events.json');
const ticket_participants = require('../fixtures/ticket_participants.json');

test('Open rsvp, for all and members only', async ({ page }) => {
  // let projectPage = new ProjectPage(page);
  // let randomProjectName = await projectPage.addProject([{'username': promoter.username, 'role': 'promoter'}, {'username': usher.username, 'role': 'usher'}]);
  // let loginPage = new LoginPage(page);
  // await loginPage.login(`/${profile.title}/${randomProjectName}`, promoter.username, promoter.password);

  let loginPage = new LoginPage(page);
  await loginPage.login('testcypressproject/zgs0w', promoter.username, promoter.password);

  await page.getByTestId('project-menu').locator('visible=true').click();
  await page.getByTestId('settings').locator('visible=true').click();
  await page.getByTestId('setup-ticket-events').click();

  for (let event of events) {
    await page.getByTestId('new-ticket-event').click();
    await page.locator('#title').fill(event.title);
    await page.locator('#badge_template').fill(event.badge_template);
    await page.getByTestId('form-submit-btn').click();
  }

  await page.getByTestId('new-ticket-client').click();
  await page.locator('#name').fill(process.env.BOXOFFICE_CLIENT_ID);
  await page.locator('#clientid').fill(process.env.BOXOFFICE_CLIENT_ID);
  await page.locator('#client_eventid').fill(process.env.BOXOFFICE_IC_ID);
  await page.locator('#client_secret').fill(process.env.BOXOFFICE_SECRET_KEY);
  await page.locator('#client_access_token').fill(process.env.BOXOFFICE_ACCESS_KEY);
  await page.getByTestId('form-submit-btn').click();

  await page.getByTestId('sync-tickets').click();
  await page.waitForTimeout(12000);
  await page.getByTestId('sync-tickets').click();

  for (let event of events) {
    await page.locator(`li[data-testid="${event.title}"] a[data-testid="ticket-edit"]`).click();
    await page.getByLabel(event.title).click();
    await page.getByTestId('form-submit-btn').click();
  }

  await page.getByTestId('sync-tickets').click();
  await page.waitForTimeout(12000);
  await page.getByTestId('sync-tickets').click();

  for (let participant of ticket_participants) {
    await page.getByTestId('add-ticket-participant').click();
    await page.locator('#fullname').fill(participant.fullname);
    await page.locator('#email').fill(participant.email);
    await page.locator('#phone').fill(participant.phone);
    await page.locator('#company').fill(participant.company);
    await page.locator('#twitter').fill(participant.twitter);
    await page.getByLabel(participant.ticketEvent).click();
    await page.getByTestId('form-submit-btn').click();
  }

  await page.getByTestId(`{ticketEvents[0].title}`).click();
  await page.getByTestId('ticket-participant', { hasText: ticketParticipants[0].fullname }).isVisible();
  await page.getByTestId('ticket-participant', { hasText: ticketParticipants[1].fullname }).isVisible();
  await Promise.all([
    page.waitForResponse(response => response.url().includes("/json") && response.status() === 200, {timeout: 60000}),
    page.getByTestId('ticket-participant', { hasText: user.username }).getByTestId('checkin').click()
  ]);
  await page.getByTestId('cancel-checkin').isVisible();
  await page.getByTestId('back-to-setup').click();

});
