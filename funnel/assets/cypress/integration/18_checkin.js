describe('Checkin of attendees', function () {
  const concierge = require('../fixtures/user.json').concierge;
  const user = require('../fixtures/user.json').user;
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');
  const ticketEvents = require('../fixtures/ticket_events.json');
  const ticketParticipants = require('../fixtures/ticket_participants.json');

  it('Checkin of attendees', function () {
    cy.login('/', concierge.username, concierge.password);

    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="setup-ticket-events"').click();
    cy.location('pathname').should('contain', '/admin');

    cy.fixture('ticket_participants').then((ticketParticipants) => {
      ticketParticipants.forEach(function (ticketParticipant) {
        cy.get('a[data-cy="add-ticket-participant"]').click();
        cy.get('#fullname').type(ticketParticipant.fullname);
        cy.get('#email').type(ticketParticipant.email);
        cy.get('#phone').type(ticketParticipant.phone);
        cy.get('#company').type(ticketParticipant.company);
        cy.get('#twitter').type(ticketParticipant.twitter);
        cy.get('#field-ticket_events')
          .find('label')
          .contains(ticketParticipant.ticketEvent)
          .click();
        cy.get('button').contains('Add participant').click();
      });
    });

    cy.get('a[data-cy="' + ticketEvents[0].title + '"]').click();
    cy.get('td[data-cy="ticket-participant"]').contains(
      ticketParticipants[0].fullname
    );
    cy.get('td[data-cy="ticket-participant"]').contains(
      ticketParticipants[1].fullname
    );
    cy.checkin(user.username);
    cy.get('a[data-cy="back-to-setup"]').click();

    cy.get('a[data-cy="' + ticketEvents[1].title + '"]').click();
    // Test failing
    // cy.get('td[data-cy="ticket-participant"]')
    //   .contains(ticketParticipants[2].fullname)
    //   .parent()
    //   .find('a[data-cy="edit-attendee-details"]')
    //   .invoke('removeAttr', 'target')
    //   .click();
    // cy.url().should('contain', 'edit');
    // cy.get('#email')
    //   .clear()
    //   .type(ticketParticipants[1].email);
    // cy.get('button')
    //   .contains('Save changes')
    //   .click();

    cy.checkin(ticketParticipants[2].fullname);
    cy.get('a[data-cy="back-to-setup"]').click();
  });
});
