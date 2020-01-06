describe('Login', function() {
  const { admin } = require('../fixtures/user.js');

  it('Create a new project', function() {
    cy.login('/new', admin.username, admin.password);
    cy.wait(120000);
  });
});
