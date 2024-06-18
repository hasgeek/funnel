import { admin } from '../fixtures/user.json';
import project from '../fixtures/project.json';
import proposal from '../fixtures/proposal.json';

describe('Add video to session', () => {
  it('Add videos to session', () => {
    cy.intercept('GET', '**/admin').as('fetch-admin-panel');
    cy.intercept('**/schedule/*').as('view-session');

    cy.login('/', admin.username, admin.password);

    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('[data-cy-navbar="schedule"]').click();
    cy.get('.schedule__row__column--talks').contains(proposal.title).click();
    cy.wait('@view-session');
    cy.get('#session-modal').should('be.visible');
    cy.get('[data-cy-admin="edit-session"]').click();
    cy.get('#field-video_url').type(proposal.session_video);
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.get('[data-cy="session-video"]').find('iframe').should('be.visible');
    cy.get('[data-cy="view-proposal"]').invoke('removeAttr', 'target').click();
    cy.get('[data-cy="session-video"]').find('iframe').should('be.visible');
    cy.get('img[data-cy="proposal-video-thumbnail"]').should('be.visible');
    cy.get('img[data-cy="session-video-thumbnail"]').should('be.visible');
    cy.get('a[data-cy="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy="editor-panel"]:visible').click();
    cy.wait('@fetch-admin-panel');
    cy.get('[data-cy="edit-session-video"]').should('exist');
  });
});
