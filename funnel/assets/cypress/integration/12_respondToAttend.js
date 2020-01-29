describe('Responding yes to attend a project', function() {
  const { user } = require('../fixtures/user.js');
  const project = require('../fixtures/project.json');

  it('Respond to attend a project', function() {
    cy.relogin('/testcypressproject');
    cy.get('a[data-cy-project="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').should('not.exist');
    cy.get('#tickets')
      .find('button[title="Going"]')
      .click();
    cy.get('[data-cy-rsvp="going"]').should('exist');
  });

  after(function() {
    cy.logout();
  });
});
