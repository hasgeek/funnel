import { owner, admin, hguser } from '../fixtures/user.json';
import profile from '../fixtures/profile.json';

describe('Adding crew to profile', () => {
  Cypress.on('uncaught:exception', () => {
    return false;
  });

  it('Add new member to profile and edit roles', () => {
    cy.intercept('**/edit').as('edit-form');
    cy.intercept('POST', '**/edit').as('edit-member');
    cy.intercept('GET', '**/delete').as('delete-form');
    cy.intercept('POST', '**/delete').as('delete-member');
    cy.intercept('GET', '**/new').as('member-form');
    cy.intercept('POST', '**/new').as('add-member');

    cy.login(`/${profile.title}`, owner.username, owner.password);
    cy.get('a[data-cy="admin-dropdown"]:visible').click();
    cy.wait(2000);
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
