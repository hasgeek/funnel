describe('Publish project', function() {
  const editor = require('../fixtures/user.json').editor;
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');

  it('Publish project', function() {
    cy.login('/' + profile.title, editor.username, editor.password);
    cy.get('[data-cy-title="' + project.title + '"]')
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
