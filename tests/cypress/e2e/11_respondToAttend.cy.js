import { user } from '../fixtures/user.json';
import project from '../fixtures/project.json';

describe('Responding yes to attend a project', () => {
  it('Respond to attend a project', () => {
    cy.intercept('POST', '**/save').as('bookmark-project');

    cy.login('/testcypressproject', user.username, user.password);

    cy.get('.upcoming').find('.card').contains(project.title).click({ force: true });
    cy.location('pathname').should('contain', project.url);
    cy.get('a#rsvp-btn:visible').click();
    cy.wait(2000);
    cy.get('button[data-cy="confirm"]:visible').click();
    cy.get('[data-cy="registered"]').should('exist');
    cy.wait(2000);
    cy.get('a#cancel-rsvp-btn:visible').click();
    cy.wait(2000);
    cy.get('button[data-cy="cancel-rsvp"]:visible').click();
    cy.get('[data-cy="unregistered"]').should('exist');
    cy.wait(2000);
    cy.get('a#rsvp-btn:visible').click();
    cy.wait(2000);
    cy.get('button[data-cy="confirm"]:visible').click();
    cy.wait(2000);
    cy.get('button[data-cy="bookmark"]').click();
    cy.wait('@bookmark-project');
    cy.get('button[data-cy="bookmarked"]').should('exist');
    cy.get('[data-cy="share-project"]').click();
    cy.wait(1000);
    cy.get('[data-cy="share-dropdown"]').should('exist');

    cy.get('a[data-cy-navbar="settings"]').should('not.exist');
  });
});
