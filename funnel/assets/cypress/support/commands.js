// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************

Cypress.Commands.add('login', (route, username, password) => {
  cy.visit(route, { failOnStatusCode: false })
    .get('#hgnav')
    .find('.header__button')
    .click();
  cy.get('#showmore').click();
  cy.get('.field-username').type(username);
  cy.get('.field-password').type(password);
  cy.get('.form-actions')
    .find('button')
    .click();
});

Cypress.Commands.add('relogin', route => {
  cy.visit(route)
    .get('#hgnav')
    .then($header => {
      if ($header.find('.header__button').length > 0) {
        cy.get('#hgnav')
          .find('.header__button')
          .click();
        cy.location('pathname').should('include', route);
      }
    });
});

Cypress.Commands.add('enterlogindetails', (username, password) => {
  cy.get('#showmore').click();
  cy.get('.field-username')
    .type(username)
    .should('have.value', username);
  cy.get('.field-password')
    .type(password)
    .should('have.value', password);
  cy.get('.form-actions')
    .find('button')
    .click();
});

Cypress.Commands.add('logout', () => {
  cy.get('a[data-cy="account-link"]').click();
  cy.get('a[data-cy="my-account"]').click();
  cy.get('.card__footer')
    .find('a')
    .contains('Logout')
    .click();
  cy.clearCookies();
});
