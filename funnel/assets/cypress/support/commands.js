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
  cy.visit(route)
    .get('#hgnav')
    .find('.header__button')
    .click();
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
  cy.location('pathname').should('include', '/JSFoo');
});
