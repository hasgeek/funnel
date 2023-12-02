import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { ProjectCrewFormPage } = require('../page/project-crew-form');
const { ProjectPage } = require('../page/create-project');
const profile = require('../fixtures/profile.json');
const project = require('../fixtures/project.json');
const { owner, editor } = require('../fixtures/user.json');
const cfp = require('../fixtures/cfp.json');
const labels = require('../fixtures/labels.json');
const dayjs = require('dayjs');

test('Open call for proposal of the project and add schedule', async ({ page }) => {
  let randomProjectName = Math.random().toString(36).substring(2, 7);
  let projectNameCapitalize = randomProjectName.charAt(0).toUpperCase() + randomProjectName.slice(1);
  let loginPage;
  loginPage = new LoginPage(page);
  await loginPage.login(`/${profile.title}`, owner.username, owner.password);
  let projectPage = new ProjectPage(page);
  await projectPage.createNewProject(projectNameCapitalize);
  let crewForm = new ProjectCrewFormPage(page);
  await page.getByTestId('crew').click();
  await crewForm.addMember(editor.username, 'editor');
  projectPage.publish();
  await loginPage.logout();

  await loginPage.login(`/${profile.title}/${randomProjectName}`, editor.username, editor.password);

  await page.getByTestId('submissions').click();
  await page.getByTestId('add-cfp').click();
  await page.locator('#field-instructions .cm-editor .cm-line').fill(cfp.instructions);
  await page.getByTestId('add-cfp').click();
  await page.locator('label.switch-label').click();
  await page.getByTestId('cfp-state', { hasText: 'Accepting submissions' }).isVisible();
  await page.getByTestId('propose-a-session').isVisible();

  await page.getByTestId('project-menu').locator('visible=true').click();
  await page.getByTestId('settings').locator('visible=true').click();
  await page.getByTestId('manage-labels').click();

  await page.getByTestId('project-menu').locator('visible=true').click();
  await page.getByTestId('settings').locator('visible=true').click();
  await page.getByTestId('manage-labels').click();

  for (let label of labels) {
    await page.getByTestId('add-labels').click();
    await page.locator('input#title').fill(label.title);
    await page.locator('.emojionearea-button').click();
    await page.locator('.emojionearea-picker').waitFor();
    await page.locator('.emojionearea-category[name="smileys_people"] i[title="Innocent"]').click();
    await expect(page.locator('.emojionearea-picker')).toBeHidden();

    if (label.label1) {
      await page.locator('#add-sublabel-form').click();
      await page.locator('#child-form > .ui-draggable-box #title').type(label.label1);
      await page.locator('#child-form > .ui-draggable-box .emojionearea-button').click();
      await page.locator('#child-form > .ui-draggable-box .emojionearea-picker').waitFor();

      // Emoji Relaxed is throwing not a valid emoji error
      await page.locator('#child-form > .ui-draggable-box .emojionearea-category[name="smileys_people"] i[title="Joy"]').click();
      await expect(page.locator('#child-form > .ui-draggable-box .emojionearea-picker')).toBeHidden();
    }

    if (label.label2) {
      await page.locator('#add-sublabel-form').click();
      await page.locator('#child-form > .ui-draggable-box').locator('nth=1').locator('input#title').type(label.label2);
      await page.locator('#child-form > .ui-draggable-box').locator('nth=1').locator('.emojionearea-button').click();
      await page.locator('#child-form > .ui-draggable-box').locator('nth=1').locator('.emojionearea-picker').waitFor();
      await page.locator('#child-form > .ui-draggable-box').locator('nth=1').locator('.emojionearea-category[name="smileys_people"] i[title="Smile"]').click();
      await expect(page.locator('#child-form > .ui-draggable-box').locator('nth=1').locator('.emojionearea-picker')).toBeHidden();
    }

    if (label.adminLabel) {
      await page.locator('#field-restricted label').click();
    }
    await page.getByTestId('save-label').click();
  };

  await page.locator('.ui-draggable-box').locator('nth=0').locator('.drag-handle').hover();
  await page.mouse.down();
  await page.locator('.ui-draggable-box').locator('nth=1').locator('.drag-box__action').hover();
  await page.mouse.up();
  await page.getByTestId('save-label-seq').click();
  await expect(page.locator('.ui-draggable-box').locator('nth=0').locator('.label-box__inner__heading')).toContainText(labels[1].title);
  await this.page.getByTestId("project-page").click();

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

  const tomorrow = dayjs().add(1, 'days').format('YYYY-MM-DD');
  await page.locator('#select-date').fill(tomorrow);
  await Promise.all([
    page.waitForResponse(response => response.url().includes("/new") && response.status() === 200, {timeout: 60000}),
    page.locator('.fc-slot108 .fc-widget-content').click(5, 5)
  ]);
  await page.locator('#title').fill(project.session_title);
  await page.locator('select#venue_room_id').click();
  await page.getByText(`${project.venue.title} – ${project.venue.room}`).locator('visible=true').click();
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
  await page.locator('#session-save').click();


});
