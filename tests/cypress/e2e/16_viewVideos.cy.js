import project from '../fixtures/project.json';
import session from '../fixtures/session.json';
import proposal from '../fixtures/proposal.json';

describe('View project videos page', () => {
  it('View project videos page', () => {
    cy.visit('/');
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('img[data-cy="thumbnail"]').should('be.visible');
    cy.get('[data-cy="title"]').contains(proposal.title);
    cy.get('[data-cy="title"]').contains(session.title);
  });
});
