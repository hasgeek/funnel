/* eslint-disable global-require */
describe('Add video to session', () => {
  const { admin } = require('../fixtures/user.json');
  const project = require('../fixtures/project.json');
  const proposal = require('../fixtures/proposal.json');

  it('Add videos to session', () => {
    cy.server();
    cy.route('GET', '**/admin').as('fetch-admin-panel');
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
    cy.get('[data-testid="edit-session"]').click();
    cy.get('#field-video_url').type(proposal.session_video);
    cy.get('button[data-testid="form-submit-btn"]').click();
    cy.get('[data-testid="session-video"]').find('iframe').should('be.visible');
    cy.get('[data-testid="view-proposal"]').invoke('removeAttr', 'target').click();
    cy.get('[data-testid="session-video"]').find('iframe').should('be.visible');
    cy.get('img[data-testid="proposal-video-thumbnail"]').should('be.visible');
    cy.get('img[data-testid="session-video-thumbnail"]').should('be.visible');
    cy.get('a[data-testid="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="editor-panel"]:visible').click();
    cy.wait('@fetch-admin-panel');
    cy.get('[data-testid="edit-session-video"]').should('exist');
  });
});
