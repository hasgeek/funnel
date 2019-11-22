describe('Project', function() {
  const admin = require('../fixtures/admin.json');
  const project = require('../fixtures/project.json');
  const events = require('../fixtures/events.json');
  const participants = require('../fixtures/participants.json');

  it('View participant badge', function() {
    cy.server();
    cy.route('POST', '**/participants/checkin?*').as('checkin');
    cy.route('**/participants/json').as('participant-list');

    cy.login('/JSFoo/' + project.url, admin.username, admin.password);

    cy.get('a[data-cy="checkin"').click();
    cy.location('pathname').should('contain', '/admin');
    cy.get('a[data-cy="' + events[1].title + '"]').click();
    cy.get('td[data-th="Name"]').contains(participants[2].fullname);
    var firstname = participants[2].fullname.split(' ')[0];
    cy.get('a[data-cy="show-badge"]')
      .invoke('removeAttr', 'target')
      .click();
    cy.url().should('contain', 'badge');
    cy.get('.first-name').should('contain', firstname);
    cy.screenshot('badge');
  });
});
