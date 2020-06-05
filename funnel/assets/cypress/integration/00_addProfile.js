describe('Profile', function () {
  const owner = require('../fixtures/user.json').owner;
  const profile = require('../fixtures/profile.json');
  const hguser = require('../fixtures/user.json').hguser;

  it('Create a new profile', function () {
    cy.login('/', owner.username, owner.password);

    cy.visit('/organizations');
    cy.get('a').contains('new organization').click();
    cy.location('pathname').should('contain', '/new');

    cy.get('#title').type(profile.title);
    cy.get('#name').type(profile.title);
    cy.get('button').contains('Next').click();
    cy.logout();

    cy.login('/', hguser.username, hguser.password);
    cy.visit('/organizations');
    cy.get('a').contains('new organization').click();
    cy.get('.alert--error').should('exist');
  });
});
