import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { ProjectPage } = require('../page/create-project');
const profile = require('../fixtures/profile.json');
const project = require('../fixtures/project.json');
const { promoter, editor, user } = require('../fixtures/user.json');
const cfp = require('../fixtures/cfp.json');
const labels = require('../fixtures/labels.json');
const dayjs = require('dayjs');

test('Open call for proposal of the project and add schedule', async ({ page }) => {
  let projectPage = new ProjectPage(page);
  let randomProjectName = await projectPage.addProject(promoter, [{'username': editor.username, 'role': 'editor'}]);
  let loginPage = new LoginPage(page);
  await loginPage.login(`/${promoter.owns_profile}/${randomProjectName}`, editor.username, editor.password);
  await projectPage.addVenue();
  await page.getByTestId('submissions').click();
  await page.getByTestId('add-cfp').click();
  await page.locator('#field-instructions .cm-editor .cm-line').fill(cfp.instructions);
  await page.getByTestId('add-cfp').click();
  await page.locator('label.switch-label').click();
  await page.getByTestId('cfp-state', { hasText: 'Accepting submissions' }).isVisible();
  await page.getByTestId('propose-a-session').locator('nth=0').isVisible();
  await projectPage.addLabels();
  await page.getByTestId('project-menu').locator('visible=true').click();
  await page.getByTestId('settings').locator('visible=true').click();
  await page.getByTestId('manage-labels').click();
  await page.locator('.ui-draggable-box').locator('nth=0').locator('.drag-handle').hover();
  await page.mouse.down();
  await page.locator('.ui-draggable-box').locator('nth=1').locator('.drag-box__action').hover();
  await page.mouse.up();
  await page.getByTestId('save-label-seq').click();
  await expect(page.locator('.ui-draggable-box').locator('nth=0').locator('.label-box__inner__heading')).toContainText(project.labels[1].title);
  await page.getByTestId("project-page").click();

  await page.getByTestId('propose-a-session').locator('visible=true').click();
  await page.getByTestId('close-consent-modal').click();
  await page.locator('#title').fill(project.proposal_title);
  await page.locator('#field-body .cm-editor .cm-line').fill(project.proposal_content);
  await page.getByTestId('add-label').click();
  await page.locator('fieldset').waitFor(1000);
  await page.getByLabel(project.labels[0].sublabels[0]).click();
  await page.getByLabel(project.labels[1].sublabels[2]).click();
  await page.getByTestId('save').locator('visible=true').click();
  await page.getByTestId('form-submit-btn').click();

  await page.getByTestId('proposal-menu').locator('visible=true').click();
  await page.locator('.mui-dropdown__menu.mui--is-open').waitFor(6000);
  await Promise.all([
    page.waitForRequest(request => request.url().includes("/admin"), {timeout: 60000}),
    await page.getByTestId('editor-panel').locator('visible=true').click()
  ]);
  await page.getByTestId('proposal-status').locator('button[value="awaiting_details"]').click();

  await page.getByTestId('proposal-menu').locator('visible=true').click();
  await page.locator('.mui-dropdown__menu.mui--is-open').waitFor(6000);
  await Promise.all([
    page.waitForRequest(request => request.url().includes("/admin"), {timeout: 60000}),
    await page.getByTestId('editor-panel').locator('visible=true').click()
  ]);
  await page.getByTestId('proposal-status').locator('button[value="under_evaluation"]').click();

  await page.getByTestId('proposal-menu').locator('visible=true').click();
  await page.locator('.mui-dropdown__menu.mui--is-open').waitFor(6000);
  await Promise.all([
    page.waitForRequest(request => request.url().includes("/admin"), {timeout: 60000}),
    await page.getByTestId('editor-panel').locator('visible=true').click()
  ]);
  await page.getByTestId('proposal-status').locator('button[value="confirm"]').click();

  await page.getByTestId('schedule').click();
  await page.getByTestId('edit-schedule').click();

  let tomorrow = dayjs().add(1, 'days').format('YYYY-MM-DD');
  await page.locator('#select-date').fill(tomorrow);
  await Promise.all([
    page.waitForResponse(response => response.url().includes("/new") && response.status() === 200, {timeout: 60000}),
    page.locator('.fc-slot108 .fc-widget-content').click(5, 5)
  ]);
  await page.locator('#title').fill(project.session_title);
  await page.locator('select#venue_room_id').click();
  await page.getByText(`${project.venues[0].title} – ${project.venues[0].room}`).locator('visible=true').click();
  await page.locator('#speaker').fill(editor.username);
  await page.locator('#is_break').click();
  await Promise.all([
    page.waitForRequest(request => request.url().includes("/new"), {timeout: 60000}),
    page.locator('#session-save').click()
  ]);

  const destinationElement = await page.locator('.fc-slot112 .fc-widget-content');
  await page.locator('.js-unscheduled').hover();
  await page.mouse.down();
  const box = (await destinationElement.boundingBox());
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await destinationElement.hover();
  await destinationElement.hover();
  await page.mouse.up();
  await Promise.all([
    page.waitForResponse(response => response.url().includes("/schedule") && response.status() === 200, {timeout: 60000})
  ]);
  await page.locator('select#venue_room_id').click();
  await page.getByText(`${project.venues[1].title} – ${project.venues[1].room}`).locator('visible=true').click();
  await page.locator('#session-save').click();

  await page.getByTestId('settings').click();
  await page.getByTestId('collapsible-open').locator('nth=0').click();
  await page.locator('#rooms_sortable .sp-dd').locator('nth=0').click();
  await page.locator('.sp-palette-container').locator('nth=0').isVisible();

  await page.getByTestId('project-page').click();
  await page.getByTestId('schedule').click();
  await Promise.all([
    page.waitForResponse(response => response.url().includes("/schedule") && response.status() === 200, {timeout: 60000}),
    page.getByTestId('session-title').locator('nth=1').click()
  ]);
  await page.getByTestId('edit-session').click();
  await page.locator('input#video_url').fill(project.session_video);
  await page.getByTestId('form-submit-btn').click();
  await page.getByTestId('close-modal').click();
  await loginPage.logout();

  await loginPage.login('/', user.username, user.password);
  await page.locator('.upcoming .card--upcoming').locator('nth=0').click();
  await page.getByTestId('schedule').click();
  await page.getByTestId('add-to-calendar').click();
  await page.getByTestId('schedule-subscribe').isVisible();
  await page.getByTestId('close-modal').click();

  let tomorrowDate = dayjs().add(2, 'days').format('dddd, D MMMM YYYY');
  await expect(page.locator('.schedule__date')).toContainText(tomorrowDate);
  for (let venue of project.venues) {
    await page.locator('.schedule__row__column--header', { hasText: `${venue.title} – ${venue.room}` }).isVisible();
  };
  await Promise.all([
    page.waitForResponse(response => response.url().includes("/schedule") && response.status() === 200, {timeout: 60000}),
    page.getByTestId('session-title').locator('nth=1').click()
  ]);
  await page.locator('#session-modal').isVisible();
  await expect(page.getByTestId('title')).toContainText(project.proposal_title);
  await expect(page.getByTestId('speaker')).toContainText(editor.fullname);
  await page.getByTestId('time').isVisible();
  await expect(page.getByTestId('room')).toContainText(`${project.venues[1].room}, ${project.venues[1].title}`);
  await page.getByTestId('session-video').locator('iframe').isVisible();
  await page.getByTestId('view-proposal"]').isVisible();
  await page.locator('#session-modal a.modal__close').click();

});
