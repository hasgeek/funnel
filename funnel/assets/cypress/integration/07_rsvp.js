describe('Project', function() {
  const user = require('../fixtures/user.json');
  const project = require('../fixtures/project.json');

  it('RSVP', function() {
    cy.login('/JSFoo/', user.username, user.password);

    cy.get('a[data-cy-project="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('#tickets')
      .find('button[title="Going"]')
      .click();
    cy.get('[data-cy-rsvp="going"]').should('exist');
  });
});
