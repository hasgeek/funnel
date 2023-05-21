/* eslint-disable global-require */
describe('Test otp login', () => {
  const { hguser } = require('../fixtures/user.json');

  it('Test OTP login', () => {
    cy.visit('/', { failOnStatusCode: false })
      .get('#hgnav')
      .find('.header__button')
      .click();
    cy.get('.field-username').type(hguser.email, { log: false });
    cy.get('button[data-cy="form-submit-btn"]:visible').click();
    cy.get('#otp').type(1234, { log: false });
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.wait(2000);
    cy.get('div[data-cy="login-wrapper"]').should('exist');
    cy.get('p.mui-form__error').should('exist');
  });
});
