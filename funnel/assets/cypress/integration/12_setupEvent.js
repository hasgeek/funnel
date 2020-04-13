describe('Setup event for checkin', function() {
  const admin = require('../fixtures/user.json').admin;
  const project = require('../fixtures/project.json');
  const events = require('../fixtures/events.json');
  const participants = require('../fixtures/participants.json');

  it('Setup event for checkin', function() {
    cy.login('/testcypressproject', admin.username, admin.password);

    cy.get('[data-cy-project="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="checkin"').click();
    cy.location('pathname').should('contain', '/admin');

    cy.fixture('events').then(events => {
      events.forEach(function(event) {
        cy.get('a[data-cy="new-event"]').click();
        cy.get('#title').type(event.title);
        cy.get('#badge_template').type(event.badge_template);
        cy.get('button')
          .contains('Add event')
          .click();
      });
    });
  });
});
