/* eslint-disable global-require */
describe('Profile admin roles', () => {
  const { owner, admin } = require('../fixtures/user.json');
  const profile = require('../fixtures/profile.json');

  it('Check roles of profile admins', () => {
    cy.server();
    cy.route('GET', '**/updates?*').as('fetch-updates');

    cy.login(`/${profile.title}`, admin.username, admin.password);

    cy.get('a[data-testid="admin-dropdown"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="edit-details"]:visible').click();
    cy.get('#field-description')
      .find('.cm-editor .cm-line')
      .type(profile.description, { force: true });
    cy.get('button[data-testid="form-submit-btn"]').click();
    // TODO: After imgee merger, add tests to upload and select image
    cy.get('[data-testid="add-banner"]').should('exist');

    cy.get('a[data-testid="admin-dropdown"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="profile-crew"]:visible').click();
    cy.get('button[data-testid="add-member"]').should('not.exist');
    cy.get('[data-testid="member"]').contains(admin.username).click();
    cy.get('#member-form', { timeout: 10000 }).should('not.be.visible');
    cy.get('[data-testid="member"]').contains(owner.username).click();
    cy.get('#member-form', { timeout: 10000 }).should('not.be.visible');
    cy.wait(1000);

    cy.get('a[data-testid="my-updates"]:visible').click();
    cy.wait('@fetch-updates');
    cy.get('[data-testid="notification-box"]').contains(profile.title);
  });
});
