describe('Adding crew to profile', function() {
  const { owner, admin } = require('../fixtures/user.js');

  Cypress.on('uncaught:exception', (err, runnable) => {
    return false;
  });

  it('Add new member to profile and edit roles', function() {
    cy.server();
    cy.route('**/edit').as('edit-form');
    cy.route('POST', '**/edit').as('edit-member');
    cy.route('POST', '**/delete').as('delete-member');

    cy.relogin('/testcypressproject');
    cy.get('a[data-cy-btn="profile-crew"]').click();

    cy.add_member(admin.username, 'owner');

    cy.get('[data-cy="member"]')
      .contains(admin.username)
      .click();
    cy.wait('@edit-form');
    cy.get('button[data-cy-btn="revoke"]').click();
    cy.get('button')
      .contains('Delete')
      .click();
    cy.wait('@delete-member');
    cy.get('[data-cy="member"]')
      .contains(admin.username)
      .should('not.exist');

    cy.add_member(admin.username, 'owner');
    cy.get('[data-cy="member"]')
      .contains(admin.username)
      .click();
    cy.wait('@edit-form');
    cy.get('#is_owner').click();
    cy.get('button')
      .contains('Edit membership')
      .click();
    cy.wait('@edit-member');
    cy.get('[data-cy="member"]')
      .contains(admin.username)
      .parents('.user-box')
      .find('[data-cy="role"]')
      .contains('Admin');
  });

  after(function() {
    cy.relogin('/testcypressproject');
    cy.logout();
  });
});
