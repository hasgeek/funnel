describe('Login', function() {
  const { admin } = require('../fixtures/user.js');

  it('Create a new project', function() {
    cy.login('https://auth.hasgeek.com', admin.username, admin.password);
  });
});
