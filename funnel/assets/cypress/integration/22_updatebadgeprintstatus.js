describe('View and update print status of badge', function () {
  const admin = require('../fixtures/user.json').admin;
  const project = require('../fixtures/project.json');
  const ticketEvents = require('../fixtures/ticket_events.json');
  const ticketParticipants = require('../fixtures/ticket_participants.json');

  it('View badges to be printed', function () {
    cy.server();
    cy.route('POST', '**/ticket_participants/checkin?*').as('checkin');
    cy.route('**/ticket_participants/json').as('ticket-participant-list');

    cy.login('/testcypressproject', admin.username, admin.password);

    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');

    cy.get('a[data-cy="setup-ticket-events"').click();
    cy.location('pathname').should('contain', '/admin');
    cy.get('a[data-cy="' + ticketEvents[0].title + '"]').click();
    cy.get('select#badge_printed').select('Printed', { force: true });
    cy.get('#badge-form-submit').click();
    cy.get('a[data-cy="badges-to-printed"]')
      .invoke('removeAttr', 'target')
      .click();
    cy.url().should('contain', 'badges');
    cy.get('.first-name').should('not.exist');
  });
});
