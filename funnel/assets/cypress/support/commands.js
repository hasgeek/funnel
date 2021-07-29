Cypress.Commands.add('login', (route, username, password) => {
  cy.visit(route, { failOnStatusCode: false })
    .get('#hgnav')
    .find('.header__button')
    .click();
  cy.fill_login_details(username, password);
});

Cypress.Commands.add('logout', () => {
  cy.get('#hgnav').find('a[data-cy="my-account"]').click();
  cy.wait(1000);
  cy.get('button[data-cy="Logout"]:visible').click();
});

Cypress.Commands.add('fill_login_details', (username, password) => {
  cy.server();
  cy.route('POST', '**/login').as('login');

  cy.get('.field-username').type(username, { log: false });
  cy.get('.field-password').type(password, { log: false });
  cy.get('.form-actions').find('button').click();
  cy.wait('@login', { timeout: 20000 });
});

Cypress.Commands.add(
  'add_profile_member',
  (username, field, role, fail = false) => {
    cy.server();
    cy.route('**/new').as('member-form');
    cy.route('POST', '**/new').as('add-member');

    cy.wait(2000);
    cy.get('button[data-cy-btn="add-member"]').click();
    cy.wait('@member-form');
    cy.get('.select2-selection__arrow').click({ multiple: true });
    cy.get('.select2-search__field').type(username, {
      force: true,
    });
    cy.get('.select2-results__option--highlighted', { timeout: 20000 }).should(
      'be.visible'
    );
    cy.get('.select2-results__option').contains(username).click();
    cy.get('.select2-results__options', { timeout: 10000 }).should('not.exist');
    cy.get(`#${field}`).click();
    cy.get('button').contains('Add member').click();
    cy.wait('@add-member');

    if (!fail) {
      const roleString = role[0].toUpperCase() + role.slice(1);
      cy.get('[data-cy="member"]')
        .contains(username)
        .parents('.member')
        .find('[data-cy="role"]')
        .contains(roleString);
    } else {
      cy.get('p.mui--text-danger').should('be.visible');
    }
    cy.wait(6000); // Wait for toastr notice to fade out
  }
);

Cypress.Commands.add('add_member', (username, role, fail = false) => {
  cy.server();
  cy.route('**/new').as('member-form');
  cy.route('POST', '**/new').as('add-member');

  cy.wait(2000);
  cy.get('button[data-cy-btn="add-member"]').click();
  cy.wait('@member-form');
  cy.get('.select2-selection__arrow').click({ multiple: true });
  cy.get('.select2-search__field').type(username, {
    force: true,
  });
  cy.get('.select2-results__option--highlighted', { timeout: 20000 }).should(
    'be.visible'
  );
  cy.get('.select2-results__option').contains(username).click();
  cy.get('.select2-results__options', { timeout: 10000 }).should('not.exist');
  cy.get(`#is_${role}`).click();
  cy.get('button').contains('Add member').click();
  cy.wait('@add-member');

  if (!fail) {
    const roleString = role[0].toUpperCase() + role.slice(1);
    cy.get('[data-cy="member"]')
      .contains(username)
      .parents('.member')
      .find('[data-cy="role"]')
      .contains(roleString);
  } else {
    cy.get('p.mui--text-danger').should('be.visible');
  }
  cy.wait(6000); // Wait for toastr notice to fade out
});

Cypress.Commands.add('checkin', (ticketParticipant) => {
  cy.server();
  cy.route('POST', '**/ticket_participants/checkin').as('checkin');
  cy.route('**/ticket_participants/json').as('ticket-participant-list');

  cy.get('td[data-cy="ticket-participant"]')
    .contains(ticketParticipant)
    .parent()
    .find('button[data-cy="checkin"]')
    .click();
  cy.wait('@checkin', { timeout: 15000 });
  cy.wait('@ticket-participant-list', { timeout: 20000 });
  cy.wait('@ticket-participant-list', { timeout: 20000 });
  cy.wait('@ticket-participant-list', { timeout: 20000 }).then((xhr) => {
    cy.get('button[data-cy="cancel-checkin"]').should('exist');
  });
});
