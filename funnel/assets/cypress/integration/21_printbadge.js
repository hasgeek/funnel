describe('View badges to be printed', function () {
  const usher = require('../fixtures/user.json').usher;
  const user = require('../fixtures/user.json').user;
  const project = require('../fixtures/project.json');
  const ticketEvents = require('../fixtures/ticket_events.json');
  const ticketParticipants = require('../fixtures/ticket_participants.json');

  it('View badges to be printed', function () {
    cy.server();
    cy.route('POST', '**/ticket_participants/checkin?*').as('checkin');
    cy.route('**/ticket_participants/json').as('ticket-participant-list');

    cy.login('/', usher.username, usher.password);

    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="setup-ticket-events"').click();
    cy.location('pathname').should('contain', '/admin');
    cy.get('a[data-cy="' + ticketEvents[0].title + '"]').click();
    var firstname1 = ticketParticipants[0].fullname.split(' ')[0];
    var firstname2 = ticketParticipants[1].fullname.split(' ')[0];
    cy.get('a[data-cy="badges-to-printed"]')
      .invoke('removeAttr', 'target')
      .click();
    cy.url().should('contain', 'badges');
    cy.get('.first-name').should('contain', firstname1);
    cy.get('.first-name').should('contain', firstname2);
    cy.get('.first-name').should('contain', user.username);
  });
});
