describe('Confirm propose button', function() {
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');
  const labels = require('../fixtures/labels.json');

  it('Confirm Add proposal button', function() {
    cy.visit('/testcypressproject');
    cy.get('a[data-cy-project="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="proposals"]').click();
    cy.location('pathname').should('contain', 'proposals');
    cy.get('a[data-cy="propose-a-session"]').should('exist');

    cy.get('a[data-cy="profile-link"]').click();
    cy.location('pathname').should('contain', 'testcypressproject');
    cy.get('[data-cy="profile-title"]').should('contain', 'testcypressproject');
  });

  after(function() {
    cy.relogin('/testcypressproject');
    cy.logout();
  });
});
