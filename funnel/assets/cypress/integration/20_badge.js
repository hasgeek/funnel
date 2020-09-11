describe('View participant badge', function () {
  const usher = require('../fixtures/user.json').usher;
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');
  const ticketEvents = require('../fixtures/ticket_events.json');
  const ticketParticipants = require('../fixtures/ticket_participants.json');

  it('View participant badge', function () {
    cy.login('/', usher.username, usher.password);

    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="setup-ticket-events"').click();
    cy.location('pathname').should('contain', '/admin');
    cy.get('a[data-cy="' + ticketEvents[1].title + '"]').click();
    var firstname = ticketParticipants[2].fullname.split(' ')[0];
    cy.get('td[data-cy="ticket-participant"]')
      .contains(ticketParticipants[2].fullname)
      .parent()
      .find('a[data-cy="show-badge"]')
      .invoke('removeAttr', 'target')
      .click();
    cy.url().should('contain', 'badge');
    cy.get('.first-name').should('contain', firstname);
    cy.screenshot('badge');
  });
});
