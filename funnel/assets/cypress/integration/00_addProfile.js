describe('Profile', function() {
  const owner = require('../fixtures/user.json').owner;

  it('Create a new profile', function() {
    cy.login('/organizations', owner.username, owner.password);

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
