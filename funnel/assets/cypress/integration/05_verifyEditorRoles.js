describe('Verify roles of editor', function() {
  const admin = require('../fixtures/user.json').admin;
  const project = require('../fixtures/project.json');

  it('Access available for editor in project settings', function() {
    cy.login('/testcypressproject', admin.username, admin.password);
    cy.get('[data-cy-project="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="edit"]').should('exist');
    cy.get('a[data-cy="add-livestream"]').should('exist');
    cy.get('a[data-cy="manage-venues"]').should('exist');
    cy.get('a[data-cy="add-cfp"]').should('exist');
    cy.get('a[data-cy="edit-schedule"]').should('exist');
    cy.get('a[data-cy="manage-labels"]').should('exist');
    cy.get('a[data-cy="setup-events"]').should('not.exist');
    cy.get('a[data-cy="scan-checkin"]').should('not.exist');
    cy.get('a[data-cy="download-csv"]').should('exist');
    cy.get('a[data-cy="download-json"]').should('exist');
    cy.get('a[data-cy="download-schedule-json"]').should('exist');
  });
});
