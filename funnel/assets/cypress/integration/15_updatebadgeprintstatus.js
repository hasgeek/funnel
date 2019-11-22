describe('Project', function() {
  const admin = require('../fixtures/admin.json');
  const project = require('../fixtures/project.json');
  const events = require('../fixtures/events.json');
  const participants = require('../fixtures/participants.json');

  it('View badges to be printed', function() {
    cy.server();
    cy.route('POST', '**/participants/checkin?*').as('checkin');
    cy.route('**/participants/json').as('participant-list');

    cy.login('/JSFoo/' + project.url, admin.username, admin.password);

    cy.get('a[data-cy="checkin"').click();
    cy.location('pathname').should('contain', '/admin');
    cy.get('a[data-cy="' + events[0].title + '"]').click();
    cy.get('select#badge_printed').select('Printed', { force: true });
    cy.get('#badge-form-submit').click();
    cy.get('a[data-cy="badges-to-printed"]')
      .invoke('removeAttr', 'target')
      .click();
    cy.url().should('contain', 'badges');
    cy.get('.first-name').should('not.exist');
  });
});
