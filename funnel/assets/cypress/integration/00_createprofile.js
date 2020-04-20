describe('Profile', function() {
  const admin = require('../fixtures/user.json').admin;
  const project = require('../fixtures/project.json');

  it('Create a new profile', function() {
    cy.login('/organizations', admin.username, admin.password);

    cy.get('a')
      .contains('new organization')
      .click();
    cy.location('pathname').should('contain', '/new');

    cy.get('#title').type('testcypressproject');
    cy.get('#name').type('testcypressproject');
    cy.get('#is_public_profile').click();
    cy.get('button')
      .contains('Create')
      .click();
  });
});
