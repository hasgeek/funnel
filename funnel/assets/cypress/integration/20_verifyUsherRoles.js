describe('Verify roles of usher', function() {
  const { usher } = require('../fixtures/user.js');
  const project = require('../fixtures/project.json');

  before(function() {
    cy.server();
    cy.route('POST', '**/login').as('login');
    cy.login(
      '/testcypressproject/2020/proposals/new',
      usher.username,
      usher.password
    );
    cy.wait('@login', { timeout: 20000 });
    cy.get('a.home-desktop').click();
  });

  it('Access available for usher in project settings', function() {
    cy.get('[data-cy-project="' + project.title + '"]')
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
    cy.get('a[data-cy="setup-events"]').should('not.exist');
    cy.get('a[data-cy="scan-checkin"]').should('exist');
    cy.get('a[data-cy="download-csv"]').should('not.exist');
    cy.get('a[data-cy="download-json"]').should('not.exist');
    cy.get('a[data-cy="download-schedule-json"]').should('not.exist');
  });

  after(function() {
    cy.visit('/testcypressproject');
    cy.logout();
  });
});
