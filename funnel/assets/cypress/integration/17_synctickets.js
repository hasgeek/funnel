describe('Sync tickets from Boxoffice', function () {
  const promoter = require('../fixtures/user.json').promoter;
  const user = require('../fixtures/user.json').user;
  const project = require('../fixtures/project.json');
  const ticketEvents = require('../fixtures/ticket_events.json');
  const { ticket_client } = require('../fixtures/boxoffice.js');

  it('Sync tickets from Boxoffice', function () {
    cy.login('/', promoter.username, promoter.password);

    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
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
    cy.wait(30000);
    cy.get('button[data-cy="sync-tickets"').click();

    cy.fixture('ticket_events').then((ticketEvents) => {
      ticketEvents.forEach(function (ticketEvent) {
        cy.get('li[data-cy-ticket="' + ticketEvent.title + '"]')
          .find('a[data-cy="ticket-edit"]')
          .click();
        cy.get('label').contains(ticketEvent.title).click();
        cy.get('button[data-cy="form-submit-btn"]').click();
      });
    });

    cy.get('button[data-cy="sync-tickets"').click();
    cy.wait(30000);
    cy.get('button[data-cy="sync-tickets"').click();

    cy.get('a[data-cy="' + ticketEvents[0].title + '"]').click();
    cy.get('td[data-cy="ticket-participant"]').contains(user.username);
    cy.get('a[data-cy="back-to-setup"]').click();

    cy.get('a[data-cy="' + ticketEvents[1].title + '"]').click();
    cy.get('td[data-cy="ticket-participant"]').contains(user.username);
    cy.get('a[data-cy="back-to-setup"]').click();
  });
});
