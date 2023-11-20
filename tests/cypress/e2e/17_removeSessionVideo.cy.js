/* eslint-disable global-require */
describe('Remove video to session', () => {
  const { admin } = require('../fixtures/user.json');
  const project = require('../fixtures/project.json');
  const proposal = require('../fixtures/proposal.json');

  it('Add videos to session', () => {
    cy.server();
    cy.route('**/schedule/*').as('view-session');

    cy.login('/', admin.username, admin.password);

    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('[data-testid="schedule"]').click();
    cy.get('.schedule__row__column--talks').contains(proposal.title).click();
    cy.wait('@view-session');
    cy.get('#session-modal').should('be.visible');
    cy.get('[data-testid="edit-video"]').click();
    cy.get('#video_url').clear();
    cy.get('button[data-testid="form-submit-btn"]').click();
    cy.get('#session-modal').find('iframe').should('not.exist');
    cy.get('[data-testid="close-modal"]').click();
    cy.get('[data-testid="about"]').click();
    cy.get('[data-testid="title"]').contains(proposal.title).should('not.exist');
  });
});
