describe('Project', function() {
  const { admin } = require('../fixtures/user.js');
  const project = require('../fixtures/project.json');

  it('Publish project', function() {
    cy.relogin('/testcypressproject');

    cy.get('[title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('button[data-cy-state="publish"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('[data-cy="project-state"]').contains('Published');
  });
});
