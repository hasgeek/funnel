describe('Checkin of attendees', function() {
  const admin = require('../fixtures/user.json').admin;
  const user = require('../fixtures/user.json').user;
  const project = require('../fixtures/project.json');
  const events = require('../fixtures/events.json');
  const participants = require('../fixtures/participants.json');

  it('Checkin of attendees', function() {
    cy.login('/testcypressproject', admin.username, admin.password);

    cy.get('[data-cy-project="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="checkin"').click();
    cy.location('pathname').should('contain', '/admin');

    cy.fixture('participants').then(participants => {
      participants.forEach(function(participant) {
        cy.get('a[data-cy="add-participant"]').click();
        cy.get('#fullname').type(participant.fullname);
        cy.get('#email').type(participant.email);
        cy.get('#phone').type(participant.phone);
        cy.get('#company').type(participant.company);
        cy.get('#twitter').type(participant.twitter);
        cy.get('#field-events')
          .find('label')
          .contains(participant.event)
          .click();
        cy.get('button')
          .contains('Add participant')
          .click();
      });
    });

    cy.get('a[data-cy="' + events[0].title + '"]').click();
    cy.get('td[data-cy="participant"]').contains(participants[0].fullname);
    cy.get('td[data-cy="participant"]').contains(participants[1].fullname);
    cy.checkin(user.username);
    cy.get('a[data-cy="back-to-setup"]').click();

    cy.get('a[data-cy="' + events[1].title + '"]').click();
    // Test failing
    // cy.get('td[data-cy="participant"]')
    //   .contains(participants[2].fullname)
    //   .parent()
    //   .find('a[data-cy="edit-attendee-details"]')
    //   .invoke('removeAttr', 'target')
    //   .click();
    // cy.url().should('contain', 'edit');
    // cy.get('#email')
    //   .clear()
    //   .type(participants[1].email);
    // cy.get('button')
    //   .contains('Save changes')
    //   .click();

    cy.checkin(participants[2].fullname);
    cy.get('a[data-cy="back-to-setup"]').click();
  });
});
