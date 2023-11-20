/* eslint-disable global-require */
describe('Verify roles of editor and publish project', () => {
  const { editor } = require('../fixtures/user.json');
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');

  it('Verify roles of editor and publish project', () => {
    cy.login(`/${profile.title}`, editor.username, editor.password);
    cy.get(`[data-testid="${project.title}"]`).first().click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-testid="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-testid="edit"]').should('exist');
    cy.get('a[data-testid="add-livestream"]').should('exist');
    cy.get('a[data-testid="manage-venues"]').should('exist');
    cy.get('a[data-testid="add-cfp"]').should('exist');
    cy.get('a[data-testid="edit-schedule"]').should('exist');
    cy.get('a[data-testid="manage-labels"]').should('exist');
    cy.get('a[data-testid="setup-ticket-events"]').should('not.exist');
    cy.get('a[data-testid="scan-checkin"]').should('not.exist');
    cy.get('button[data-testid="publish"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-testid="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('[data-testid="project-state"]').contains('Published');
  });
});
