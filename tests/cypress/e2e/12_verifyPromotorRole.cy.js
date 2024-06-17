/* eslint-disable global-require */
describe('Verify roles of promoter', () => {
  const { promoter } = require('../fixtures/user.json');
  const project = require('../fixtures/project.json');

  it('Access available for promoter in project settings', () => {
    cy.login('/', promoter.username, promoter.password);

    cy.get(`[data-testid="${project.title}"]`).first().click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-testid="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-testid="edit"]').should('not.exist');
    cy.get('a[data-testid="add-livestream"]').should('not.exist');
    cy.get('a[data-testid="manage-venues"]').should('not.exist');
    cy.get('a[data-testid="add-cfp"]').should('not.exist');
    cy.get('a[data-testid="edit-schedule"]').should('not.exist');
    cy.get('a[data-testid="manage-labels"]').should('not.exist');
    cy.get('a[data-testid="setup-ticket-events"]').should('exist');
    cy.get('a[data-testid="scan-checkin"]').should('exist');
  });
});
