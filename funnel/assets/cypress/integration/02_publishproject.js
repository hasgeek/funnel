describe('Project', function() {
  const admin = require('../fixtures/admin.json');
  const project = require('../fixtures/project.json');

  it('Publish project', function() {
    cy.login('/JSFoo', admin.username, admin.password);

    cy.get('[title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);

    cy.get('button[data-cy-state="publish"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('[data-cy="project-state"]').contains('Published');
  });
});
