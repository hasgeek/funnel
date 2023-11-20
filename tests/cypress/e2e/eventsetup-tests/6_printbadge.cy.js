/* eslint-disable global-require */
describe('View badges to be printed', () => {
  const { user, usher } = require('../../fixtures/user.json');
  const project = require('../../fixtures/project.json');
  const ticketEvents = require('../../fixtures/ticket_events.json');
  const ticketParticipants = require('../../fixtures/ticket_participants.json');

  it('View badges to be printed', () => {
    cy.server();
    cy.route('POST', '**/ticket_participants/checkin?*').as('checkin');
    cy.route('**/ticket_participants/json').as('ticket-participant-list');

    cy.login('/', usher.username, usher.password);

    cy.get(`[data-testid="${project.title}"]`).first().click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-testid="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-testid="setup-ticket-events"').click();
    cy.location('pathname').should('contain', '/admin');
    cy.get(`a[data-testid="${ticketEvents[0].title}"]`).click();
    const firstname1 = ticketParticipants[0].fullname.split(' ')[0];
    const firstname2 = ticketParticipants[1].fullname.split(' ')[0];
    cy.get('a[data-testid="badges-to-printed"]').invoke('removeAttr', 'target').click();
    cy.url().should('contain', 'badges');
    cy.get('.first-name').should('contain', firstname1);
    cy.get('.first-name').should('contain', firstname2);
    cy.get('.first-name').should('contain', user.username);
  });
});
