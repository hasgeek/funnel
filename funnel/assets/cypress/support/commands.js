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
  cy.get('.field-username').type(username, { log: false });
  cy.get('.field-password').type(password, { log: false });
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

Cypress.Commands.add('logout', () => {
  cy.get('a[data-cy="account-link"]').click();
  cy.get('a[data-cy="my-account"]').click();
  cy.get('.card__footer')
    .find('a')
    .contains('Logout')
    .click();
  cy.clearCookies();
});

Cypress.Commands.add('add_member', (username, role) => {
  cy.server();
  cy.route('**/membership/new').as('member-form');
  cy.route('POST', '**/membership/new').as('add-member');

  cy.get('button[data-cy-btn="add-member"]').click();
  cy.wait('@member-form');
  cy.get('.select2-selection__arrow').click({ multiple: true });
  cy.get('.select2-search__field').type(username, {
    force: true,
  });
  cy.get('.select2-results__option--highlighted', { timeout: 20000 }).should(
    'be.visible'
  );
  cy.get('.select2-results__option')
    .contains(username)
    .click();
  cy.get('.select2-results__options', { timeout: 10000 }).should('not.visible');
  cy.get(`#is_${role}`).click();
  cy.get('button')
    .contains('Add member')
    .click();
  cy.wait('@add-member');
  var roleString = role[0].toUpperCase() + role.slice(1);
  cy.get('[data-cy="member"]')
    .contains(username)
    .parents('.user-box')
    .find('[data-cy="role"]')
    .contains(roleString);
});

Cypress.Commands.add('checkin', participant => {
  cy.server();
  cy.route('POST', '**/participants/checkin').as('checkin');
  cy.route('**/participants/json').as('participant-list');

  cy.get('td[data-cy="participant"]')
    .contains(participant)
    .parent()
    .find('button[data-cy="checkin"]')
    .click();
  cy.wait('@checkin', { timeout: 15000 });
  cy.wait('@participant-list', { timeout: 20000 });
  cy.wait('@participant-list', { timeout: 20000 });
  cy.wait('@participant-list', { timeout: 20000 }).then(xhr => {
    cy.get('button[data-cy="cancel-checkin"]').should('exist');
  });
});
