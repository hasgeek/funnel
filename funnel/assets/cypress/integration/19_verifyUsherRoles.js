/* eslint-disable global-require */
describe('Verify roles of usher', () => {
  const { usher } = require('../fixtures/user.json');
  const project = require('../fixtures/project.json');

  it('Access available for usher in project settings', () => {
    cy.login('/', usher.username, usher.password);

    cy.get(`[data-cy-title="${project.title}"]`).first().click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-navbar="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="edit"]').should('not.exist');
    cy.get('a[data-cy="add-livestream"]').should('not.exist');
    cy.get('a[data-cy="manage-venues"]').should('not.exist');
    cy.get('a[data-cy="add-cfp"]').should('not.exist');
    cy.get('a[data-cy="edit-schedule"]').should('not.exist');
    cy.get('a[data-cy="manage-labels"]').should('not.exist');
    cy.get('a[data-cy="setup-ticket-events"]').should('exist');
    cy.get('a[data-cy="scan-checkin"]').should('exist');
  });
});
