/* eslint-disable global-require */
describe('View project videos page', () => {
  const project = require('../fixtures/project.json');
  const session = require('../fixtures/session.json');
  const proposal = require('../fixtures/proposal.json');

  it('View project videos page', () => {
    cy.visit('/');
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('img[data-testid="thumbnail"]').should('be.visible');
    cy.get('[data-testid="title"]').contains(proposal.title);
    cy.get('[data-testid="title"]').contains(session.title);
  });
});
