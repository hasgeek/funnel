describe('Profile', function () {
  const owner = require('../fixtures/user.json').owner;
  const profile = require('../fixtures/profile.json');
  const hguser = require('../fixtures/user.json').hguser;

  it('Create a new profile', function () {
    cy.login('/', owner.username, owner.password);

    cy.visit('/new');
    cy.get('#title').type(profile.title);
    cy.get('#name').type(profile.title);
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.logout();
  });
});
