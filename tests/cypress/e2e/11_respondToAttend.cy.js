/* eslint-disable global-require */
describe('Responding yes to attend a project', () => {
  const { user } = require('../fixtures/user.json');
  const project = require('../fixtures/project.json');

  it('Respond to attend a project', () => {
    cy.server();
    cy.route('POST', '**/save').as('bookmark-project');

    cy.login('/testcypressproject', user.username, user.password);

    cy.get('.upcoming').find('.card').contains(project.title).click({ force: true });
    cy.location('pathname').should('contain', project.url);
    cy.get('a#rsvp-btn:visible').click();
    cy.wait(2000);
    cy.get('button[data-testid="confirm"]:visible').click();
    cy.get('[data-testid="registered"]').should('exist');
    cy.wait(2000);
    cy.get('a#cancel-rsvp-btn:visible').click();
    cy.wait(2000);
    cy.get('button[data-testid="cancel-rsvp"]:visible').click();
    cy.get('[data-testid="unregistered"]').should('exist');
    cy.wait(2000);
    cy.get('a#rsvp-btn:visible').click();
    cy.wait(2000);
    cy.get('button[data-testid="confirm"]:visible').click();
    cy.wait(2000);
    cy.get('button[data-testid="bookmark"]').click();
    cy.wait('@bookmark-project');
    cy.get('button[data-testid="bookmarked"]').should('exist');
    cy.get('[data-testid="share-project"]').click();
    cy.wait(1000);
    cy.get('[data-testid="share-dropdown"]').should('exist');

    cy.get('a[data-testid="settings"]').should('not.exist');
  });
});
