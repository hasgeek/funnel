import { admin } from '../fixtures/user.json';
import project from '../fixtures/project.json';
import proposal from '../fixtures/proposal.json';

describe('Remove video to session', () => {
  it('Add videos to session', () => {
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
    cy.get('[data-cy="edit-video"]').click();
    cy.get('#video_url').clear();
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.get('#session-modal').find('iframe').should('not.exist');
    cy.get('[data-cy="close-modal"]').click();
    cy.get('[data-cy-navbar="about"]').click();
    cy.get('[data-cy="title"]').contains(proposal.title).should('not.exist');
  });
});
