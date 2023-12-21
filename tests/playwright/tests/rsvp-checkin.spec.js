import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { ProjectPage } = require('../page/create-project');
const profile = require('../fixtures/profile.json');
const project = require('../fixtures/project.json');
const { promoter, usher, user } = require('../fixtures/user.json');
const events = require('../fixtures/ticket_events.json');
const ticket_participants = require('../fixtures/ticket_participants.json');
const dayjs = require('dayjs');

test('Open rsvp, for all and members only', async ({ page }) => {
  let projectPage = new ProjectPage(page);
  let randomProjectName = await projectPage.addProject([{'username': promoter.username, 'role': 'promoter'}, {'username': usher.username, 'role': 'usher'}]);
  let loginPage = new LoginPage(page);
  await loginPage.login(`/${profile.title}/${randomProjectName}`, promoter.username, promoter.password);

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

  await page.getByTestId(`event-${events[0].title}`).click();
  await page.getByTestId('ticket-participant', { hasText: ticket_participants[0].fullname }).isVisible();
  await page.getByTestId('ticket-participant', { hasText: ticket_participants[1].fullname }).isVisible();
  await Promise.all([
    page.waitForResponse(response => response.url().includes("/json") && response.status() === 200, {timeout: 60000}),
    page.getByTestId(user.fullname).getByTestId('checkin').click()
  ]);
  await page.getByTestId('cancel-checkin').isVisible();
  await page.getByTestId('back-to-setup').click();
  await page.getByTestId('project-page').click();

  await page.getByTestId('project-menu').locator('visible=true').click();
  await page.getByTestId('edit').locator('visible=true').click();
  let eventStartDate = dayjs().add(1, 'days').format('YYYY-MM-DDTHH:MM');
  let eventEndDate = dayjs().add(10, 'days').format('YYYY-MM-DDTHH:MM');
  await page.locator('#start_at').fill(eventStartDate);
  await page.locator('#end_at').fill(eventEndDate);
  await page.getByTestId('form-submit-btn').click();
  await page.getByTestId('project-menu').locator('visible=true').click();
  await page.getByTestId('settings').locator('visible=true').click();
  await page.getByTestId('publish').click();
  await page.getByTestId('project-menu').locator('visible=true').click();
  await page.getByTestId('settings').locator('visible=true').click();
  await page.getByTestId('add-tickets').click();
  await page.getByLabel('Only members can register').click();
  await page.locator('#has_membership').click();
  await page.getByTestId('form-submit-btn').click();
  await page.getByTestId('rsvp-only-for-members').isVisible();
  await loginPage.logout();

  await loginPage.login(`/${profile.title}/${randomProjectName}`, user.username, user.password);
  await page.getByTestId('project-member').isVisible();
  await page.getByTestId('member-rsvp').click();
  await page.locator('#rsvp-form').waitFor(60000);
  await page.getByTestId('confirm').click();
  await page.getByTestId('registered').isVisible();

});
