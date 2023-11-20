/* eslint-disable global-require */
describe('View and update print status of badge', () => {
  const { admin } = require('../../fixtures/user.json');
  const project = require('../../fixtures/project.json');
  const ticketEvents = require('../../fixtures/ticket_events.json');

  it('View badges to be printed', () => {
    cy.server();
    cy.route('POST', '**/ticket_participants/checkin?*').as('checkin');
    cy.route('**/ticket_participants/json').as('ticket-participant-list');

    cy.login('/testcypressproject', admin.username, admin.password);

    cy.get(`[data-testid="${project.title}"]`).first().click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-testid="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');

    cy.get('a[data-testid="setup-ticket-events"').click();
    cy.location('pathname').should('contain', '/admin');
    cy.get(`a[data-testid="${ticketEvents[0].title}"]`).click();
    cy.get('select#badge_printed').select('Printed', { force: true });
    cy.get('#badge-form-submit').click();
    cy.get('a[data-testid="badges-to-printed"]').invoke('removeAttr', 'target').click();
    cy.url().should('contain', 'badges');
    cy.get('.first-name').should('not.exist');
  });
});
