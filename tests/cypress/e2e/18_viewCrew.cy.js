/* eslint-disable global-require */
describe('View crew', () => {
  const { admin, promoter, usher } = require('../fixtures/user.json');
  const project = require('../fixtures/project.json');

  it('View crew of the project', () => {
    cy.visit('/');
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-testid="crew"]').click();
    cy.get('button[data-testid="add-member"]').should('not.exist');
    cy.get('[data-testid="member"]')
      .contains(admin.username)
      .parents('.member')
      .find('[data-testid="role"]')
      .contains('Editor');
    cy.get('[data-testid="member"]')
      .contains(promoter.username)
      .parents('.member')
      .find('[data-testid="role"]')
      .contains('Promoter');
    cy.get('[data-testid="member"]')
      .contains(usher.username)
      .parents('.member')
      .find('[data-testid="role"]')
      .contains('Usher');
    cy.get('[data-testid="member"]').contains(admin.username).click();
    cy.get('#member-form', { timeout: 10000 }).should('not.be.visible');
  });
});
