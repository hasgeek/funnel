import { owner, admin } from '../fixtures/user.json';
import profile from '../fixtures/profile.json';

describe('Profile admin roles', () => {
  it('Check roles of profile admins', () => {
    cy.intercept('GET', '**/updates?*').as('fetch-updates');

    cy.login(`/${profile.title}`, admin.username, admin.password);

    cy.get('a[data-cy="admin-dropdown"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-btn="edit-details"]:visible').click();
    cy.get('#field-description')
      .find('.cm-editor .cm-line')
      .type(profile.description, { force: true });
    cy.get('button[data-cy="form-submit-btn"]').click();
    // TODO: After imgee merger, add tests to upload and select image
    cy.get('[data-cy="add-banner"]').should('exist');

    cy.get('a[data-cy="admin-dropdown"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-btn="profile-crew"]:visible').click();
    cy.get('button[data-cy-btn="add-member"]').should('not.exist');
    cy.get('[data-cy="member"]').contains(admin.username).click();
    cy.get('#member-form', { timeout: 10000 }).should('not.be.visible');
    cy.get('[data-cy="member"]').contains(owner.username).click();
    cy.get('#member-form', { timeout: 10000 }).should('not.be.visible');
    cy.wait(1000);

    cy.get('a[data-cy="my-updates"]:visible').click();
    cy.wait('@fetch-updates');
    cy.get('[data-cy="notification-box"]').contains(profile.title);
  });
});
