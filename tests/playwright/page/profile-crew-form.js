import { test, expect } from '@playwright/test';

export class ProfileCrewFormPage {

  constructor(page) {
    this.page = page;
  }

  async addMember(username, owner=true, success=true) {
    await Promise.all([
      this.page.waitForResponse(response => response.url().includes("/new") && response.status() === 200, {timeout: 60000}),
      this.page.getByTestId('add-member').click()
    ]);
    await this.page.locator('.select2-selection__arrow').waitFor()
    await this.page.locator('.select2-selection__arrow').click();
    await this.page.locator('.select2-search__field').waitFor();
    await this.page.locator('.select2-search__field').fill(username);
    await this.page.locator('.select2-results__option').waitFor();
    await this.page.locator('.select2-results__option').click();
    if(owner) {
      await this.page.locator('div#field-is_owner input[value="True"]').click();
    }
    else {
      await this.page.locator('div#field-is_owner input[value="False"]').click();
    }
    await Promise.all([
      this.page.waitForRequest(request => request.url().includes("/new"), {timeout: 60000}),
      this.page.getByTestId('form-submit-btn').getByText('Add member').click()
    ]);
    if(success) {
      await this.page.locator('data-test-id="member":has-text("' + username + '")').isVisible();
      await expect(this.page.locator('.toast-message')).toHaveCount(0, {timeout: 7000});
    } else {
      await this.page.locator('p.mui--text-danger').isVisible();
      await this.page.locator('a.modal__close').locator('visible=true').click();
    }

  }

  async deleteMember(username) {
    await Promise.all([
      this.page.waitForResponse(response => response.url().includes("/edit") && response.status() === 200, {timeout: 60000}),
      this.page.getByTestId('member').getByText(username).click(),
    ]);
    await Promise.all([
      this.page.waitForResponse(response => response.url().includes("/delete") && response.status() === 200, {timeout: 60000}),
      this.page.getByTestId('revoke-btn').click(),
    ]);
    await this.page.getByTestId('form-submit-btn').waitFor(3000);
    await this.page.getByTestId('form-submit-btn').click();
  }

}
