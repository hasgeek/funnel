/* eslint-disable global-require */
describe('Test adding new phone number and email to account', () => {
  const { hguser } = require('../fixtures/user.json');

  it('Add new phone number and email', () => {
    cy.login('/', hguser.username, hguser.password);
    cy.get('#hgnav').find('a[data-cy="my-account"]').click();
    cy.wait(1000);
    cy.get('a[data-cy="account"]').click();
    cy.get('a[data-cy="add-new-email"]').click();
    cy.get('#email').type(hguser.email, { log: false });
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.get('div.alert--success').should('exist');

    cy.get('a[data-cy="add-new-phone"]').click();
    cy.get('#phone').type(hguser.phone, { log: false });
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.get('div[data-cy="login-wrapper"]').should('exist');
    cy.get('p.mui-form__error').should('exist');
    cy.get('#phone').clear();
    cy.get('#phone').type(12015550127, { log: false });
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.get('#otp').should('exist');
    cy.get('#otp').type(1234, { log: false });
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.get('div[data-cy="login-form-wrapper"]').should('exist');
    cy.get('p.mui-form__error').should('exist');
  });
});
