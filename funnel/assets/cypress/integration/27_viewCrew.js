describe('View crew', function () {
  const admin = require('../fixtures/user.json').admin;
  const concierge = require('../fixtures/user.json').concierge;
  const usher = require('../fixtures/user.json').usher;
  const project = require('../fixtures/project.json');

  it('View crew of the project', function () {
    cy.visit('/');
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="crew"]').click();
    cy.get('button[data-cy-btn="add-member"]').should('not.exist');
    cy.get('[data-cy="member"]')
      .contains(admin.username)
      .parents('.user__box')
      .find('[data-cy="role"]')
      .contains('Editor');
    cy.get('[data-cy="member"]')
      .contains(concierge.username)
      .parents('.user__box')
      .find('[data-cy="role"]')
      .contains('Concierge');
    cy.get('[data-cy="member"]')
      .contains(usher.username)
      .parents('.user__box')
      .find('[data-cy="role"]')
      .contains('Usher');
    cy.get('[data-cy="member"]').contains(admin.username).click();
    cy.get('#member-form', { timeout: 10000 }).should('not.be.visible');
  });
});
