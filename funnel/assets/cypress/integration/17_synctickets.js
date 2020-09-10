describe('Sync tickets from Boxoffice', function () {
  const concierge = require('../fixtures/user.json').concierge;
  const user = require('../fixtures/user.json').user;
  const project = require('../fixtures/project.json');
  const events = require('../fixtures/events.json');
  const { ticket_client } = require('../fixtures/boxoffice.js');

  it('Sync tickets from Boxoffice', function () {
    cy.login('/', concierge.username, concierge.password);

    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="setup-events"').click();
    cy.location('pathname').should('contain', '/admin');

    cy.get('a[data-cy="new-ticket-client"').click();
    cy.get('#name').type(ticket_client.client_id, { log: false });
    cy.get('#clientid').type(ticket_client.client_id, { log: false });
    cy.get('#client_eventid').type(ticket_client.ic_id, { log: false });
    cy.get('#client_secret').type(ticket_client.secret, { log: false });
    cy.get('#client_access_token').type(ticket_client.access_key, {
      log: false,
    });
    cy.get('button').contains('Add ticket client').click();

    cy.get('button[data-cy="sync-tickets"').click();
    cy.wait(120000);
    cy.get('button[data-cy="sync-tickets"').click();

    cy.fixture('events').then((events) => {
      events.forEach(function (event) {
        cy.get('li[data-cy-ticket="' + event.title + '"]')
          .find('a[data-cy="ticket-edit"]')
          .click();
        cy.get('label').contains(event.title).click();
        cy.get('button').contains('Save changes').click();
      });
    });

    cy.get('button[data-cy="sync-tickets"').click();
    cy.wait(120000);
    cy.get('button[data-cy="sync-tickets"').click();

    cy.get('a[data-cy="' + events[0].title + '"]').click();
    cy.get('td[data-cy="ticket-participant"]').contains(user.username);
    cy.get('a[data-cy="back-to-setup"]').click();

    cy.get('a[data-cy="' + events[1].title + '"]').click();
    cy.get('td[data-cy="ticket-participant"]').contains(user.username);
    cy.get('a[data-cy="back-to-setup"]').click();
  });
});
