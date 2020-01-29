describe('Profile admin roles', function() {
  const { owner, admin } = require('../fixtures/user.js');

  before(function() {
    cy.server();
    cy.route('POST', '**/login').as('login');
    cy.login('/testcypressproject/new', admin.username, admin.password);
    cy.wait('@login', { timeout: 20000 });
    cy.get('a.mui-btn')
      .contains('Cancel')
      .click();
  });

  it('Check roles of profile admins', function() {
    cy.get('a[data-cy-btn="profile-crew"]').click();
    cy.get('button[data-cy-btn="add-member"]').should('not.exist');
    cy.get('[data-cy="member"]')
      .contains(admin.username)
      .click();
    cy.get('#member-form', { timeout: 10000 }).should('not.be.visible');
    cy.get('[data-cy="member"]')
      .contains(owner.username)
      .click();
    cy.get('#member-form', { timeout: 10000 }).should('not.be.visible');
  });
});
