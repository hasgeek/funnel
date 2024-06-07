import { promoter } from '../../fixtures/user.json';
import project from '../../fixtures/project.json';
import { ticket_client } from '../../fixtures/boxoffice.js';

describe('Sync tickets from Boxoffice', () => {
  it('Sync tickets from Boxoffice', () => {
    cy.login('/', promoter.username, promoter.password);

    cy.get(`[data-cy-title="${project.title}"]`).first().click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-navbar="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="setup-ticket-events"').click();
    cy.location('pathname').should('contain', '/admin');

    cy.get('a[data-cy="new-ticket-client"').click();
    cy.get('#name').type(ticket_client.client_id, { log: false });
    cy.get('#clientid').type(ticket_client.client_id, { log: false });
    cy.get('#client_eventid').type(ticket_client.ic_id, { log: false });
    cy.get('#client_secret').type(ticket_client.secret, { log: false });
    cy.get('#client_access_token').type(ticket_client.access_key, {
      log: false,
    });
    cy.get('button[data-cy="form-submit-btn"]').click();

    cy.get('button[data-cy="sync-tickets"').click();
    cy.wait(12000);
    cy.get('button[data-cy="sync-tickets"').click();

    cy.fixture('ticket_events').then((fticketEvents) => {
      fticketEvents.forEach((ticketEvent) => {
        cy.get(`li[data-cy-ticket="${ticketEvent.title}"]`)
          .find('a[data-cy="ticket-edit"]')
          .click();
        cy.get('label').contains(ticketEvent.title).click();
        cy.get('button[data-cy="form-submit-btn"]').click();
      });
    });

    cy.get('button[data-cy="sync-tickets"').click();
    cy.wait(12000);
    cy.get('button[data-cy="sync-tickets"').click();
  });
});
