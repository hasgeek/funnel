describe('Setup ticketed event for checkin', function () {
  const concierge = require('../fixtures/user.json').concierge;
  const project = require('../fixtures/project.json');
  const ticketEvents = require('../fixtures/ticket_events.json');
  const ticketParticipants = require('../fixtures/ticket_participants.json');

  it('Setup ticketed event for checkin', function () {
    cy.login('/', concierge.username, concierge.password);

    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="setup-ticket-events"').click();
    cy.location('pathname').should('contain', '/admin');

    cy.fixture('ticket_events').then((ticketEvents) => {
      ticketEvents.forEach(function (ticketEvent) {
        cy.get('a[data-cy="new-ticket-event"]').click();
        cy.get('#title').type(ticketEvent.title);
        cy.get('#badge_template').type(ticketEvent.badge_template);
        cy.get('button[data-cy="form-submit-btn"]').click();
      });
    });
  });
});
