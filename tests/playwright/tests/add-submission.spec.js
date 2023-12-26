import { test, expect } from '@playwright/test';

const { LoginPage } = require('../page/login');
const { ProjectPage } = require('../page/create-project');
const project = require('../fixtures/project.json');
const { user, usher } = require('../fixtures/user.json');
const proposal = require('../fixtures/proposal.json');
let randomProjectName;

test('Submitting a proposal to a project', async ({ page }) => {
  let projectPage = new ProjectPage(page);
  randomProjectName = await projectPage.addProject(usher);
  let loginPage = new LoginPage(page);
  await loginPage.login(`/${usher.owns_profile}/${randomProjectName}`, usher.username, usher.password);
  await projectPage.addLabels();
  await projectPage.openCFP();
  await loginPage.logout();

  await loginPage.login(`/${usher.owns_profile}/${randomProjectName}`, user.username, user.password);
  await page.getByTestId('propose-a-session').locator('visible=true').click();
  await page.getByTestId('close-consent-modal').click();
  await page.locator('#title').fill(proposal.title);
  await page.locator('#field-body .cm-editor .cm-line').fill(proposal.content);
  await page.getByTestId('add-video').click();
  await page.locator('#field-video_url').waitFor(1000);
  await page.locator('#video_url').fill(proposal.preview_video);
  await page.getByTestId('save').locator('visible=true').click();
  await page.getByTestId('add-label').click();
  await page.locator('fieldset').waitFor(1000);
  await page.getByLabel(project.labels[0].sublabels[0]).click();
  await page.getByLabel(project.labels[1].sublabels[2]).click();
  await page.getByTestId('save').locator('visible=true').click();
  await page.getByTestId('form-submit-btn').click();

  await expect(page.getByTestId('proposal-title')).toContainText(proposal.title);
  await page.getByTestId('proposal-video iframe').isVisible();
  await page.getByTestId('proposal-menu').locator('visible=true').click();
  await page.getByTestId('edit').waitFor(1000);
  await page.getByTestId('edit').locator('visible=true').click();
  await page.getByTestId('close-consent-modal').click();

  await page.getByTestId('add-collaborator-modal').click();
  await Promise.all([
    page.waitForResponse(response => response.url().includes("/new") && response.status() === 200, {timeout: 60000}),
    page.getByTestId('add-collaborator').click()
  ]);
  await page.locator('.select2-selection__arrow').waitFor();
  await page.locator('.select2-selection__arrow').click();
  await page.locator('.select2-search__field').waitFor();
  await page.locator('.select2-search__field').fill(usher.username);
  await page.locator('.select2-results__option').waitFor();
  await page.locator('.select2-results__option').click();
  await page.locator('#label').fill('Editor');
  await Promise.all([
    page.waitForRequest(request => request.url().includes("/new"), {timeout: 60000}),
    page.locator('.modal').locator('button[data-testid="form-submit-btn"]').locator('visible=true').click()
  ]);
  await expect(page.locator('.toast-message')).toHaveCount(0, {timeout: 7000});
  await page.locator('a.modal__close').locator('visible=true').click();
  await page.getByTestId('form-submit-btn').waitFor(60000);
  await page.getByTestId('form-submit-btn').click();
  await page.locator('.user__box__userid user__box__fullname', { hasText: usher.username }).isVisible();
  await page.locator('.user__box__userid user__box__userid badge', { hasText: 'Editor' }).isVisible();

  await page.getByTestId('proposal-menu').locator('visible=true').click();
  await page.locator('.mui-dropdown__menu').locator('visible=true').waitFor(1000);
  await page.getByTestId('delete').isVisible();
  await page.getByTestId('edit-proposal-video').isVisible();

  await page.getByTestId('post-comment').click();
  await page.getByTestId('new-form').locator('.cm-editor .cm-line').fill(proposal.proposer_note);
  await Promise.all([
    page.waitForRequest(request => request.url().includes("/new"), {timeout: 60000}),
    page.getByTestId('new-form').getByTestId('submit-comment').click()
  ]);
  await expect(page.locator('.comment__body')).toContainText(proposal.proposer_note);
  await expect(page.locator('.comment__header')).toContainText(user.username);

});
