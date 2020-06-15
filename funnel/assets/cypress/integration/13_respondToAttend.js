describe('Responding yes to attend a project', function() {
  const user = require('../fixtures/user.json').user;
  const project = require('../fixtures/project.json');

  it('Respond to attend a project', function() {
    cy.server();
    cy.route('POST', '**/save').as('bookmark-project');

    cy.login('/testcypressproject', user.username, user.password);

    cy.get('a[data-cy-title="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('#register-btn').click();
    cy.wait(2000);
    cy.get('button[data-cy="confirm"]').click();
    cy.get('.alert--success').should('exist');
    cy.get('button[data-cy="bookmark"]').click();
    cy.wait('@bookmark-project');
    cy.get('button[data-cy="bookmarked"]').should('exist');
    cy.get('[data-cy="share-project"]').click();
    cy.wait(1000);
    cy.get('[data-cy="share-dropdown"]').should('exist');

    cy.get('a[data-cy-navbar="settings"]').should('not.exist');
  });
});
