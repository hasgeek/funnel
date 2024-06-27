import { admin, promoter, usher } from '../fixtures/user.json';
import project from '../fixtures/project.json';

describe('View crew', () => {
  it('View crew of the project', () => {
    cy.visit('/');
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="crew"]').click();
    cy.get('button[data-cy-btn="add-member"]').should('not.exist');
    cy.get('[data-cy="member"]')
      .contains(admin.username)
      .parents('.member')
      .find('[data-cy="role"]')
      .contains('Editor');
    cy.get('[data-cy="member"]')
      .contains(promoter.username)
      .parents('.member')
      .find('[data-cy="role"]')
      .contains('Promoter');
    cy.get('[data-cy="member"]')
      .contains(usher.username)
      .parents('.member')
      .find('[data-cy="role"]')
      .contains('Usher');
    cy.get('[data-cy="member"]').contains(admin.username).click();
    cy.get('#member-form', { timeout: 10000 }).should('not.be.visible');
  });
});
