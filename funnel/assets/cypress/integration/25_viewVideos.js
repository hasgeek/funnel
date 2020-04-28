describe('View project videos page', function() {
  const project = require('../fixtures/project.json');
  const session = require('../fixtures/session.json');
  const proposal = require('../fixtures/proposal.json');

  it('View project videos page', function() {
    cy.visit('/');
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('[data-cy-navbar="video"]').click();
    cy.get('img[data-cy="thumbnail"]').should('be.visible');
    cy.get('[data-cy="title"]').contains(proposal.title);
    cy.get('[data-cy="title"]').contains(session.title);
  });
});
