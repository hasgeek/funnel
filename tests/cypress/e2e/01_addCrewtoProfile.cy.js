/* eslint-disable global-require */
describe('Adding crew to profile', () => {
  const { owner, admin, hguser } = require('../fixtures/user.json');
  const profile = require('../fixtures/profile.json');

  Cypress.on('uncaught:exception', () => {
    return false;
  });

  it('Add new member to profile and edit roles', () => {
    cy.server();
    cy.route('**/edit').as('edit-form');
    cy.route('POST', '**/edit').as('edit-member');
    cy.route('GET', '**/delete').as('delete-form');
    cy.route('POST', '**/delete').as('delete-member');
    cy.route('GET', '**/new').as('member-form');
    cy.route('POST', '**/new').as('add-member');

    cy.login(`/${profile.title}`, owner.username, owner.password);
    cy.get('a[data-cy="admin-dropdown"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-btn="profile-crew"]:visible').click();

    cy.add_profile_member(admin.username, 'is_owner-1', 'owner');

    cy.get('[data-cy="member"]').contains(admin.username).click();
    cy.wait('@edit-form');
    cy.get('button[data-cy-btn="revoke"]').click();
    cy.wait('@delete-form');
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.wait('@delete-member');
    cy.get('[data-cy="member"]').contains(admin.username).should('not.exist');

    cy.add_profile_member(admin.username, 'is_owner-1', 'owner');

    cy.get('[data-cy="member"]').contains(admin.username).click();
    cy.wait('@edit-form');
    cy.get('#is_owner-0').click();
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.wait('@edit-member');
    cy.get('[data-cy="member"]')
      .contains(admin.username)
      .parents('.member')
      .find('[data-cy="role"]')
      .contains('Admin');

    cy.add_member(hguser.username, 'owner', true);
    cy.get('a.modal__close:visible').click();
    cy.wait(1000);

    cy.get('a[data-cy="profile-public"]:visible').click();
    cy.wait(1000);
    cy.get('button[data-cy="make-public-btn"]:visible').click();
    cy.wait(1000);
  });
});
