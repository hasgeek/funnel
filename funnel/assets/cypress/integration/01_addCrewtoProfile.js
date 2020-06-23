describe('Adding crew to profile', function () {
  const owner = require('../fixtures/user.json').owner;
  const admin = require('../fixtures/user.json').admin;
  const profile = require('../fixtures/profile.json');
  const hguser = require('../fixtures/user.json').hguser;

  Cypress.on('uncaught:exception', (err, runnable) => {
    return false;
  });

  it('Add new member to profile and edit roles', function () {
    cy.server();
    cy.route('**/edit').as('edit-form');
    cy.route('POST', '**/edit').as('edit-member');
    cy.route('GET', '**/delete').as('delete-form');
    cy.route('POST', '**/delete').as('delete-member');
    cy.route('**/new').as('member-form');
    cy.route('POST', '**/new').as('add-member');

    cy.login('/' + profile.title, owner.username, owner.password);
    cy.get('a[data-cy-btn="profile-crew"]').click();

    cy.add_profile_member(admin.username, 'is_owner-1', 'owner');

    cy.get('[data-cy="member"]').contains(admin.username).click();
    cy.wait('@edit-form');
    cy.get('button[data-cy-btn="revoke"]').click();
    cy.wait('@delete-form');
    cy.get('button').contains('Remove').click();
    cy.wait('@delete-member');
    cy.get('[data-cy="member"]').contains(admin.username).should('not.exist');
    cy.wait(4000);

    cy.add_profile_member(admin.username, 'is_owner-1', 'owner');
    cy.wait(4000);

    cy.get('[data-cy="member"]').contains(admin.username).click();
    cy.wait('@edit-form');
    cy.get('#is_owner-0').click();
    cy.get('button').contains('Edit membership').click();
    cy.wait('@edit-member');
    cy.get('[data-cy="member"]')
      .contains(admin.username)
      .parents('.user__box')
      .find('[data-cy="role"]')
      .contains('Admin');

    cy.add_member(hguser.username, 'owner', (fail = true));
  });
});
