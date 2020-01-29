describe('Adding crew', function() {
  const { admin, concierge, usher } = require('../fixtures/user.js');
  const project = require('../fixtures/project.json');

  Cypress.on('uncaught:exception', (err, runnable) => {
    return false;
  });

  it('Add crew to project', function() {
    cy.relogin('/testcypressproject');
    cy.get('[data-cy-project="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="crew"]').click();

    cy.add_member(concierge.username, 'concierge');
    cy.add_member(usher.username, 'usher');
  });
});
