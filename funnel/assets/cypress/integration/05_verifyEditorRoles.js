describe('Verify roles of editor', function () {
  const editor = require('../fixtures/user.json').editor;
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');

  it('Access available for editor in project settings', function () {
    cy.login('/' + profile.title, editor.username, editor.password);
    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-navbar="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="edit"]').should('exist');
    cy.get('a[data-cy="add-livestream"]').should('exist');
    cy.get('a[data-cy="manage-venues"]').should('exist');
    cy.get('a[data-cy="add-cfp"]').should('exist');
    cy.get('a[data-cy="edit-schedule"]').should('exist');
    cy.get('a[data-cy="manage-labels"]').should('exist');
    cy.get('a[data-cy="setup-ticket-events"]').should('not.exist');
    cy.get('a[data-cy="scan-checkin"]').should('not.exist');
  });
});
