export class LoginPage {

  constructor(page) {
    this.page = page;
    this.loginBtn = this.page.getByTestId('login');
    this.loginOutBtn = this.page.getByTestId('logout');
    this.usernameInputBox = this.page.locator('input.field-username');
    this.passwordInputBox = this.page.locator('input.field-password');
    this.passwordBtn = this.page.getByTestId('password-login');
    this.submitBtn = this.page.getByTestId('login-submit');
    this.accountBtn = this.page.getByTestId('my-account');
  }

  async login(route, username, password) {
    await this.page.goto(route);
    await this.loginBtn.click();
    await this.usernameInputBox.fill(username);
    await this.passwordBtn.click();
    await this.passwordInputBox.fill(password);
    await Promise.all([
      this.page.waitForResponse(response => response.url().includes("/login") && response.status() === 200, {timeout: 60000}),
      this.submitBtn.click()
    ]);
  }

  async logout() {
    await this.accountBtn.click();
    await this.loginOutBtn.waitFor();
    await this.loginOutBtn.click();
  }

}
