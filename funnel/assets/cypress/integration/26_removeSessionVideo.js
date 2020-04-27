describe('Remove video to session', function() {
  const editor = require('../fixtures/user.json').editor;
  const project = require('../fixtures/project.json');
  const proposal = require('../fixtures/proposal.json');

  it('Add videos to session', function() {
    cy.server();
    cy.route('**/viewsession-popup').as('view-session');

    cy.login('/', editor.username, editor.password);

    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('[data-cy-navbar="schedule"]').click();
    cy.get('.schedule__row__column--talks')
      .contains(proposal.title)
      .click();
    cy.wait('@view-session');
    cy.get('#session-modal').should('be.visible');
    cy.get('[data-cy="edit-video"]').click();
    cy.get('#video_url').clear();
    cy.get('button')
      .contains('save session')
      .click();
    cy.get('#session-modal')
      .find('iframe')
      .should('not.exist');
    cy.get('[data-cy="close-modal"]').click();
    cy.get('[data-cy-navbar="video"]').click();
    cy.get('[data-cy="title"]')
      .contains(proposal.title)
      .should('not.exist');
  });
});
