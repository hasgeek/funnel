describe('Adding crew', function() {
  const owner = require('../fixtures/user.json').owner;
  const admin = require('../fixtures/user.json').admin;
  const concierge = require('../fixtures/user.json').concierge;
  const project = require('../fixtures/project.json');

  Cypress.on('uncaught:exception', (err, runnable) => {
    return false;
  });

  it('Add crew to project', function() {
    cy.login('/testcypressproject', admin.username, admin.password);
    cy.get('[data-cy-project="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="crew"]').click();

    cy.add_member(concierge.username, 'concierge');
    cy.add_member(usher.username, 'usher');
  });
});
