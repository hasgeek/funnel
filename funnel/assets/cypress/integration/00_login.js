describe('Login', function() {
  const { admin } = require('../fixtures/user.js');

  beforeEach(function() {
    Cypress.Cookies.defaults({
      whitelist: ['lastuser', 'root_session'],
    });
  });

  it('Create a new project', function() {
    cy.login('https://auth.hasgeek.com', admin.username, admin.password);
  });
});
