describe('Verify roles of concierge', function () {
  const concierge = require('../fixtures/user.json').concierge;
  const project = require('../fixtures/project.json');

  it('Access available for concierge in project settings', function () {
    cy.login('/', concierge.username, concierge.password);

    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="edit"]').should('not.exist');
    cy.get('a[data-cy="add-livestream"]').should('not.exist');
    cy.get('a[data-cy="manage-venues"]').should('not.exist');
    cy.get('a[data-cy="add-cfp"]').should('not.exist');
    cy.get('a[data-cy="edit-schedule"]').should('not.exist');
    cy.get('a[data-cy="manage-labels"]').should('not.exist');
    cy.get('a[data-cy="setup-ticket-events"]').should('exist');
    cy.get('a[data-cy="scan-checkin"]').should('exist');
    cy.get('a[data-cy="download-csv"]').should('exist');
    cy.get('a[data-cy="download-json"]').should('exist');
    cy.get('a[data-cy="download-schedule-json"]').should('exist');
  });
});
