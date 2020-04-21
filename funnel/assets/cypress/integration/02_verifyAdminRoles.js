describe('Profile admin roles', function() {
  const owner = require('../fixtures/user.json').owner;
  const admin = require('../fixtures/user.json').admin;

  it('Check roles of profile admins', function() {
    cy.login('/testcypressproject/new', admin.username, admin.password);
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
