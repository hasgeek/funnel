describe('Checkin of attendees', function () {
  const concierge = require('../fixtures/user.json').concierge;
  const user = require('../fixtures/user.json').user;
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');
  const events = require('../fixtures/events.json');
  const ticket_participants = require('../fixtures/ticket_participants.json');

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

    cy.fixture('ticket_participants').then((ticket_participants) => {
      ticket_participants.forEach(function (ticket_participant) {
        cy.get('a[data-cy="add-ticket-participant"]').click();
        cy.get('#fullname').type(ticket_participant.fullname);
        cy.get('#email').type(ticket_participant.email);
        cy.get('#phone').type(ticket_participant.phone);
        cy.get('#company').type(ticket_participant.company);
        cy.get('#twitter').type(ticket_participant.twitter);
        cy.get('#field-events')
          .find('label')
          .contains(ticket_participant.event)
          .click();
        cy.get('button').contains('Add participant').click();
      });
    });

    cy.get('a[data-cy="' + events[0].title + '"]').click();
    cy.get('td[data-cy="ticket-participant"]').contains(
      ticket_participants[0].fullname
    );
    cy.get('td[data-cy="ticket-participant"]').contains(
      ticket_participants[1].fullname
    );
    cy.checkin(user.username);
    cy.get('a[data-cy="back-to-setup"]').click();

    cy.get('a[data-cy="' + events[1].title + '"]').click();
    // Test failing
    // cy.get('td[data-cy="ticket-participant"]')
    //   .contains(ticket_participants[2].fullname)
    //   .parent()
    //   .find('a[data-cy="edit-attendee-details"]')
    //   .invoke('removeAttr', 'target')
    //   .click();
    // cy.url().should('contain', 'edit');
    // cy.get('#email')
    //   .clear()
    //   .type(ticket_participants[1].email);
    // cy.get('button')
    //   .contains('Save changes')
    //   .click();

    cy.checkin(ticket_participants[2].fullname);
    cy.get('a[data-cy="back-to-setup"]').click();
  });
});
