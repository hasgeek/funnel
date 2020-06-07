describe('Publish project', function () {
  const editor = require('../fixtures/user.json').editor;
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');

  it('Publish project', function () {
    // Failing now - project in draft state is not visible to editor
    // cy.login('/' + profile.title, editor.username, editor.password);
    // cy.get('[data-cy-project="' + project.title + '"]')
    //   .first()
    //   .click();

    cy.login(
      '/' + profile.title + '/' + project.url,
      editor.username,
      editor.password
    );

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
