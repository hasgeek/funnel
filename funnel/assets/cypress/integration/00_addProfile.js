/* eslint-disable global-require */
describe('Profile', () => {
  const { owner } = require('../fixtures/user.json');
  const profile = require('../fixtures/profile.json');

  it('Create a new profile', () => {
    cy.login('/', owner.username, owner.password);

    cy.visit('/new');
    cy.get('#title').type(profile.title);
    cy.get('#name').type(profile.title);
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.logout();
  });
});
