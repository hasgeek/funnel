describe('Creating a new user account', function () {
  const newuser = require('../fixtures/user.json').newuser;

  it('Signup', function () {
    cy.visit('/', { failOnStatusCode: false })
      .get('#hgnav')
      .find('.header__button')
      .click();
    cy.get('a[data-cy="signup"]').click();
    cy.location('pathname').should('contain', '/register');
    cy.get('#fullname').type(newuser.fullname);
    cy.get('#email').type(newuser.email);
    cy.get('#password').type(newuser.password);
    cy.get('#confirm_password').type(newuser.password);
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.get('.alert--success').should('visible');
    cy.get('a[data-cy="my-account"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy="account"]:visible').click();
    cy.get('a[data-cy="add-username"]').click();
    cy.get('#username').type(newuser.username);
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.get('a[data-cy="change-password"]').click();
    cy.get('#old_password').type(newuser.password);
    cy.get('#password').type(newuser.newpassword);
    cy.get('#confirm_password').type(newuser.newpassword);
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.get('button[data-cy="Logout"]:visible').click();

    cy.login('/', newuser.username, newuser.newpassword);
  });
});
