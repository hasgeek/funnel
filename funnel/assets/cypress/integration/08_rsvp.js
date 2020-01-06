describe('RSVP yes to project', function() {
  const { user } = require('../fixtures/user.js');
  const project = require('../fixtures/project.json');

  it('RSVP', function() {
    cy.relogin('/testcypressproject');
    cy.get('a[data-cy-project="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('#tickets')
      .find('button[title="Going"]')
      .click();
    cy.get('[data-cy-rsvp="going"]').should('exist');
  });

  after(function() {
    cy.logout();
  });
});
